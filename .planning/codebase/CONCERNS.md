# Codebase Concerns

**Analysis Date:** 2026-04-11

## Tech Debt

**SQLite Scalability Limits:**
- Issue: SQLite is used as the primary database for all financial data. While adequate for single-user local deployments, it hits hard limits at ~5-10GB databases or under concurrent writes with many transactions.
- Files: `backend/database.py`, `backend/models.py`
- Impact: Cannot horizontally scale portfolio to multiple users or large historical datasets without complete database migration. WAL mode mitigates some contention but doesn't eliminate fundamental limits.
- Fix approach: Plan migration path to PostgreSQL or similar if multi-user support becomes a requirement. No changes needed for current single-user design, but document as a boundary condition.

**News Feed Threading and Lock Management:**
- Issue: Global `_refresh_inflight` flag controlled by `threading.Lock()` for background news refresh. Simple bool-based semaphore is fragile and doesn't prevent partial/failed refreshes from blocking subsequent attempts.
- Files: `backend/routers/news.py` (lines 78-79, 146-170)
- Impact: If a news refresh fails mid-execution and an exception occurs after setting `_refresh_inflight = True`, the lock remains stuck and prevents subsequent refreshes until server restart.
- Fix approach: Use try/finally or context manager pattern in `_refresh_worker()` to guarantee lock release. Consider using `asyncio.Lock` if moving to async background tasks.

**Broad Exception Handling:**
- Issue: Many exception handlers catch generic `Exception` without logging details or re-raising. Examples: `backend/routers/prices.py` lines 36 and 56, `backend/routers/real_estate.py` line 170, `backend/routers/news.py` lines 237-238, 387-388.
- Files: `backend/routers/prices.py`, `backend/routers/real_estate.py`, `backend/routers/news.py`, `backend/ai.py`, `backend/main.py`
- Impact: Silent failures in price fetches, Zillow scrapes, and news feeds. Errors are logged but operators won't know which specific API calls failed or why. Difficult to debug.
- Fix approach: Catch specific exception types (httpx.ConnectError, httpx.TimeoutError, ValueError) and log request details. Avoid catching bare `except Exception:` when returning empty dicts or None.

**Timezone-Naive Datetime Handling:**
- Issue: All datetime operations use `datetime.utcnow()` but some columns store naive datetimes. No consistent timezone specification in SQLAlchemy models.
- Files: `backend/models.py`, `backend/routers/prices.py` (line 122), `backend/routers/real_estate.py` (line 143), `backend/routers/news.py` (line 107)
- Impact: Risk of timestamp collisions and ambiguous sorting when records are created in different time zones or daylight saving transitions occur. Balance snapshots sorted by `published_at` may be out of order.
- Fix approach: Switch all models to use `Column(DateTime(timezone=True))` and consistently use `datetime.now(timezone.utc)` instead of `utcnow()`.

## Known Bugs

**Zillow Scrape Fragility:**
- Symptoms: Zillow estimates fail silently and return None. No fallback or user feedback on why scrape failed (blocked, selector changed, etc.).
- Files: `backend/routers/real_estate.py` (lines 150-172)
- Trigger: Any change to Zillow's HTML structure or blocking of Mozilla User-Agent will cause all scrapes to fail.
- Workaround: Manual override field in UI allows users to set custom estimate. Zillow scrapes are best-effort and not critical path.

**CSV Parser Header Detection Fragility:**
- Symptoms: If a CSV has metadata rows before the header (common in bank exports), the heuristic "first line with 2+ commas" may pick the wrong row as headers.
- Files: `backend/importers/ingest.py` (lines 38-53)
- Trigger: Bank statements that include date ranges or subtotals before actual column headers.
- Workaround: Files can be cleaned manually before import, or column mapping UI can override detected headers (not yet implemented).

**Transaction Balance Snapshot Math Edge Case:**
- Symptoms: `_take_snapshot()` accumulates cost basis and cash balance separately but may produce negative balances for certain transaction sequences (e.g., selling before first buy).
- Files: `backend/importers/ingest.py` (lines 162-243)
- Trigger: Imported CSV with "sell" transactions before "buy" transactions in date order (e.g., dividend distributions, short sales, margin trades).
- Workaround: Cost basis is taken as absolute value; negative quantities are allowed. Works for most retail portfolios but edge cases exist.

## Security Considerations

**CSV Import File Content Not Validated:**
- Risk: Files dropped into `/data/watch/` are auto-ingested without any content type or file signature validation. Malicious actors with write access to the watch folder can inject arbitrary data into the database.
- Files: `backend/watchers/folder_watcher.py` (lines 52-75), `backend/importers/ingest.py` (lines 246-386)
- Current mitigation: Local-only deployment by design. Single-user assumption. No multi-user access control.
- Recommendations: If shared deployments are ever considered, validate file magic bytes (ensure actual CSV/Excel format), scan file size (prevent DOS), and require user approval for auto-import.

**Claude API Key Storage:**
- Risk: API keys are stored in SQLite settings table as plaintext JSON strings. No encryption at rest.
- Files: `backend/ai.py` (lines 10-34), `backend/routers/settings.py` (setup/retrieval of CLAUDE_API_KEY setting)
- Current mitigation: Single-user local machine. Keys are not transmitted or logged. Assume user has filesystem access control.
- Recommendations: For shared deployments, use encrypted settings or environment variable only. Document that settings table should not be shared.

**Zillow Scrape User-Agent Spoofing:**
- Risk: Zillow scrapes use hardcoded Mozilla User-Agent to bypass detection. Violates Zillow's terms of service and can cause IP blocks.
- Files: `backend/routers/real_estate.py` (line 158)
- Current mitigation: Best-effort scraping; failures are silent and don't break the app. Manual override is always available.
- Recommendations: Remove Zillow scraping entirely or use official API if available. Document that manual estimate entry is the preferred method.

**News Feed URL Validation Incomplete:**
- Risk: URLs fetched from RSS feeds are not fully validated before storage or display. Potential XSS if feeds contain malicious content.
- Files: `backend/routers/news.py` (lines 211-221, 475-500)
- Current mitigation: URLs are validated to be `http://` or `https://` schemes and checked for common redirect patterns. HTML is stripped from summaries. No inline script execution in frontend (React auto-escapes).
- Recommendations: Add stricter URL allowlisting (block localhost, private IPs, and known malicious domains). Consider Content-Security-Policy header in frontend.

## Performance Bottlenecks

**News Feed Fetch on Demand:**
- Problem: News feed refresh can take 20-30+ seconds (multiple RSS feeds, URL validation via HTTP HEAD/GET, HTML parsing). Blocking response time on first `/api/news` call.
- Files: `backend/routers/news.py` (lines 104-130, 173-242)
- Cause: Synchronous `feedparser.parse()` with multiple sequential `httpx.Client` calls. URL validation does additional HEAD/GET requests per article.
- Improvement path: Move all feed fetches to background thread pool. Cache feed results for 2-4 hours. Allow stale cache to be served while refresh runs in background.

**Real Estate Zillow Scrape Timeout:**
- Problem: Single Zillow scrape can take 10 seconds. If user opens real estate page and refreshes all properties, request hangs.
- Files: `backend/routers/real_estate.py` (lines 132-147)
- Cause: Sequential HTTP calls to Zillow. No parallelization. Retries on timeout don't exist.
- Improvement path: Batch scrapes using `asyncio.gather()`. Implement exponential backoff. Cache estimates for 24+ hours.

**Transaction Query N+1 in Portfolio Context:**
- Problem: Building portfolio context for news feed makes separate query for each holding + account type join. Large portfolios (500+ holdings) will be slow.
- Files: `backend/routers/news.py` (lines 260-293)
- Cause: `db.query(Holding.symbol, Account.type).join(Account, ...).all()` is efficient, but called on every news fetch even if portfolio hasn't changed.
- Improvement path: Cache portfolio context in memory with invalidation on import. Use materialized view if portfolio queries become a bottleneck.

**Frontend Chart Re-renders:**
- Problem: Dashboard and Retirement pages render Recharts with full data on every balance snapshot update. No memoization or virtualization.
- Files: `frontend/src/pages/Dashboard.tsx` (lines 1-309), `frontend/src/pages/Retirement.tsx` (lines 1-230)
- Cause: React component receives full snapshot history (up to 365+ data points). Recharts re-renders entire chart on balance change.
- Improvement path: Use `useMemo()` for chart data. Implement Recharts `shouldSetThedomainOfXAxisTicks` and `syncMethod` to prevent redundant re-renders.

## Fragile Areas

**Column Auto-Detection Logic:**
- Files: `backend/importers/analyzer.py` (lines 90-226)
- Why fragile: Heuristics for detecting date, symbol, and amount columns rely on pattern matching and regex. Edge cases: "1.5" could be quantity or price; "2025-01-15" could be date or numeric ID; "BTC" could be symbol or acronym in description.
- Safe modification: Add explicit column mapping UI so users can override auto-detection. Store mapping per institution so subsequent imports don't need re-detection.
- Test coverage: No unit tests for `auto_detect_columns()`. No test fixtures for edge cases (all-numeric, mixed dates, no clear amounts).

**News Feed Relevance Filtering:**
- Files: `backend/routers/news.py` (lines 304-308)
- Why fragile: Relevance is determined by keyword matching on portfolio holdings + account types. A user with "BTC" holdings will match articles containing "bitcoin" but also "bit torrenting", "bitwise", etc. False positives pollute feed.
- Safe modification: Add explicit relevance tuning parameters (keyword weights, regex patterns). Allow users to block domains or keywords.
- Test coverage: No test cases for relevance filtering. No fixtures with real portfolio data.

**Holdings Calculation from Transactions:**
- Files: `backend/importers/ingest.py` (lines 125-159)
- Why fragile: Rebuilding holdings from transactions assumes `type` is always "buy", "sell", or "other". If a new transaction type is added (e.g., "split", "conversion"), the holdings math breaks silently.
- Safe modification: Add validation that all transaction types are recognized. Warn on unknown types instead of ignoring them.
- Test coverage: No tests for holdings reconstruction. No fixtures with edge cases (zero quantities, fractional shares, short sales).

**Debt Snapshot Projection:**
- Files: `backend/routers/debt.py` (likely projections for payoff dates)
- Why fragile: Projections assume constant interest rates and minimum payments. Actual behavior differs if accounts are paid off early or rates change.
- Safe modification: Add scenario planning UI where users can specify alternative payoff rates or extra payments.
- Test coverage: Not reviewed in detail but likely needs test fixtures with real debt scenarios.

## Scaling Limits

**Concurrent User Load:**
- Current capacity: Single-user, single-machine deployment. SQLite has no connection pooling; all requests serialize through one engine.
- Limit: 2-3 concurrent requests max before database locks occur. Any background job (news fetch, price refresh) will block foreground API requests.
- Scaling path: Migrate to PostgreSQL with connection pooling. Implement worker queue for background tasks (Celery + Redis). Add API rate limiting.

**Portfolio Size:**
- Current capacity: 1000-5000 holdings without noticeable slowdown. Balance snapshot history grows linearly with imported transactions.
- Limit: >10,000 holdings or >100,000 transactions will cause UI lag and slow balance queries.
- Scaling path: Implement pagination/lazy loading in accounts view. Archive old balance snapshots (keep monthly instead of daily).

**File Upload Size:**
- Current capacity: CSV/Excel files up to ~100MB can be handled (limited by memory for tempfile buffering).
- Limit: >500MB file uploads will cause OOM or timeout.
- Scaling path: Stream uploads to disk instead of buffering in memory. Validate file size before accepting upload.

**News Feed Freshness:**
- Current capacity: 100+ articles in cache without slowdown. Cache age TTL is 2 hours (hardcoded).
- Limit: RSS feeds update faster than cache refresh in a multi-user scenario. Users see stale news.
- Scaling path: Implement per-feed refresh frequency. Add webhook support for feeds that support it.

## Dependencies at Risk

**yfinance Deprecation Risk:**
- Risk: yfinance is community-maintained and wraps Yahoo Finance API which is not officially documented. Yahoo can change API without notice or block bots.
- Impact: All stock price lookups fail silently if Yahoo blocks the bot or changes API response format.
- Migration plan: Migrate to official stock APIs (Alpha Vantage, IEX, Polygon.io) or use web scraping with Selenium as fallback.

**feedparser Legacy:**
- Risk: feedparser is stable but no longer actively maintained. RSS/Atom feed format is fragile; malformed feeds can hang the parser.
- Impact: Single malformed feed in the list will hang background refresh, preventing other feeds from being fetched.
- Migration plan: Add per-feed timeout and error handling. Consider switching to `httpx` with hand-rolled feed parsing if feedparser becomes a bottleneck.

**Beautiful Soup Web Scraping:**
- Risk: Web scraping is always fragile. Any website change breaks the scraper immediately.
- Impact: Zillow scrapes fail silently. No property valuations until user manually overrides.
- Migration plan: Remove web scraping. Use official property APIs (Zillow API if available) or accept manual data entry only.

**SQLAlchemy 2.0 Async Support:**
- Risk: Project uses sync SQLAlchemy with async FastAPI routes. Session management is sync and can block event loop.
- Impact: Under load, API requests will hang if a database query takes >100ms. No async database driver (aiosqlite) is used.
- Migration plan: Implement async SQLAlchemy with `aiosqlite` ORM patterns or migrate to async database driver.

## Missing Critical Features

**Transaction Categorization:**
- Problem: Transactions are typed as "buy", "sell", "other" but not categorized (e.g., "dividend", "tax", "fee"). No way to filter by expense type or calculate tax-lot FIFO/LIFO.
- Blocks: Tax reporting, detailed portfolio analysis, high-level financial categorization.

**Conflict Resolution for Duplicate Imports:**
- Problem: Duplicate detection is hash-based and catches exact matches, but doesn't handle near-duplicates (same transaction imported twice with slightly different formatting).
- Blocks: Robust re-import workflow. Users must manually delete near-duplicates from the database.

**Account Reconciliation:**
- Problem: No mechanism to reconcile imported balance snapshots against official account statements. No "balance match" validation before committing an import.
- Blocks: Data integrity checks. Silent balance drift over time.

**Multi-Currency Support:**
- Problem: All amounts are stored as floats without currency field per transaction. Currency is account-level only.
- Blocks: True forex portfolio tracking. Crypto accounts work by accident (prices in USD), but international stocks don't.

## Test Coverage Gaps

**CSV Import Analyzer:**
- What's not tested: `auto_detect_columns()` function with edge cases (all-text columns, no dates, mixed formats, blank cells, duplicate headers).
- Files: `backend/importers/analyzer.py`
- Risk: Undetected bugs in column detection cause silent wrong imports or skipped rows.
- Priority: High — this is a critical path for data ingestion.

**Holdings Rebuild Logic:**
- What's not tested: `_rebuild_holdings()` with fractional shares, short sales, splits, dividend reinvestment scenarios.
- Files: `backend/importers/ingest.py` (lines 125-159)
- Risk: Holdings accumulate incorrectly over time. Quantities and cost basis drift for complex portfolios.
- Priority: High — holdings accuracy is core to the app.

**Balance Snapshot Math:**
- What's not tested: `_take_snapshot()` with zero balances, negative cash, all-dividend accounts, or accounts with only transfers.
- Files: `backend/importers/ingest.py` (lines 162-243)
- Risk: Charts show incorrect balances. Month-over-month snapshots are out of order.
- Priority: High — balance history is the primary visual output.

**News Feed Relevance:**
- What's not tested: `_is_relevant()` and `_enforce_ai_mix()` with empty portfolio, single holding, all-AI feeds, or mixed sources.
- Files: `backend/routers/news.py` (lines 304-308, 405-445)
- Risk: AI articles are over/under-represented. Irrelevant articles appear in top-2. Entire feed becomes dominated by one source.
- Priority: Medium — feed quality degrades silently but doesn't block functionality.

**Frontend API Error Handling:**
- What's not tested: Error boundaries and fallback UI when backend is unavailable. Behavior when fetch requests fail (no network, 500 errors).
- Files: `frontend/src/api/client.ts`, `frontend/src/hooks/useApi.ts`
- Risk: UI crashes with uncaught errors. Loading states never resolve. Empty state messaging is missing.
- Priority: Medium — poor user feedback but app doesn't corrupt data.

**Settings Persistence:**
- What's not tested: Claude API key retrieval when settings are malformed JSON, missing, or corrupted. Fallback to env var.
- Files: `backend/ai.py` (lines 21-34)
- Risk: Settings lookups fail silently and fall back to env var without logging. Confusing for debugging.
- Priority: Low — env var fallback is always available.

---

*Concerns audit: 2026-04-11*
