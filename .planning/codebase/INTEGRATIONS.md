# External Integrations

**Analysis Date:** 2026-04-11

## APIs & External Services

**Stock Price Data:**
- Yahoo Finance (`yfinance` 0.2.40)
  - Used by: `backend/routers/prices.py`
  - Implementation: Direct HTTP calls to Yahoo Finance chart API (`https://query2.finance.yahoo.com/v8/finance/chart/{symbol}`)
  - Method: Custom async fetch function `fetch_stock_prices()` (lines 18-38)
  - User-Agent header required (lines 12-15)
  - Returns: Most recent price via `regularMarketPrice` or `previousClose` JSON field
  - Symbols: Any stock ticker (AAPL, GOOG, etc.)

**Cryptocurrency Price Data:**
- CoinGecko Free API
  - Used by: `backend/routers/prices.py`
  - Implementation: Async HTTP calls to `https://api.coingecko.com/api/v3/simple/price`
  - Method: `fetch_crypto_prices()` function (lines 41-57)
  - Symbol mapping: `CRYPTO_MAP` dict (lines 61-78) maps ticker symbols to CoinGecko IDs
  - Examples: BTC→bitcoin, ETH→ethereum, SOL→solana, etc.
  - Returns: USD prices for requested crypto IDs

**Real Estate Valuation:**
- Zillow Web Scraping
  - Used by: `backend/routers/real_estate.py`
  - Implementation: Best-effort scraping in `_scrape_zillow()` (lines 150-172)
  - Endpoint: `https://www.zillow.com/homes/{address}_rb/`
  - Method: BeautifulSoup HTML parsing to extract Zestimate value
  - Parser: Looks for `[data-testid="zestimate-text"]` element
  - Fallback: Manual override field available if scrape fails or is blocked
  - Risk: Zillow may block requests; graceful failure returns None
  - User-Agent: Standard Mozilla UA string

**Financial News Aggregation:**
- Google News RSS
  - Used by: `backend/routers/news.py`
  - Implementation: RSS feed parsing via `feedparser` library
  - Function: `_google_news_rss_url()` (line 459-460)
  - Endpoint: `https://news.google.com/rss/search?q={query}`
  - Queries: Symbol-based (portfolio holdings) and account-type-based queries
  - Example queries: "bitcoin" for crypto, "mortgage rates" for real estate, "federal reserve interest rates" for checking accounts
  - TTL: 2 hours cache (CACHE_TTL_HOURS, line 32)

**Generic Finance News RSS Feeds:**
- Multiple sources (no API integration, public RSS):
  - Morning Brew: `https://www.morningbrew.com/feed.xml`
  - Yahoo Finance: `https://finance.yahoo.com/rss/`
  - Reuters: `https://feeds.reuters.com/reuters/businessNews`
  - Financial Times: `https://www.ft.com/rss/home`
  - MarketWatch: `https://feeds.marketwatch.com/marketwatch/topstories/`
  - CNBC: `https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114`
- Parsing: feedparser library
- Paywall filtering: Detects paywalled domains (WSJ, Bloomberg, FT, etc.) and skips or marks them (lines 52-59, 463-472)
- Summary cleaning: HTML stripping via regex (lines 82-90)

**AI News Feeds (Google News):**
- Queries: AI industry coverage
  - "artificial intelligence OR generative ai OR llm OR model release"
  - "nvidia OR amd OR tsmc OR ai chips OR gpu demand"
  - "ai regulation OR openai OR anthropic OR google deepmind"
- Relevance: AI keyword matching (lines 73-77)

## Data Storage

**Database:**
- SQLite at `/data/libertas.db` (configured in `backend/database.py` line 5)
- ORM: SQLAlchemy 2.0.30
- Client: aiosqlite 0.20.0 (async driver)
- Schemas: All models in `backend/models.py` (Account, Holding, RealEstate, BalanceSnapshot, NewsCache, Setting, etc.)
- Connection options:
  - WAL mode enabled for concurrent read/write
  - Foreign key constraints enabled
  - Thread safety disabled (SQLite in-process)

**File Storage:**
- Local filesystem only — no cloud storage
- Watch folder: `/data/watch/` for CSV imports (monitored by watchdog)
- Processed folder: `/data/watch/processed/` for imported files
- Database file: `/data/libertas.db`
- Backups: Users can export/backup via `/api/backups/` endpoint

**Caching:**
- Database-backed caching: NewsCache table stores fetched articles
- TTL enforcement: Python datetime comparisons (news cached 2 hours)
- In-memory state: None persistent; all state lives in SQLite

## Authentication & Identity

**Auth Provider:**
- None — local-only application
- No user accounts, no login system
- Single-user desktop app (runs on localhost only)
- CORS enabled for localhost ports: 5173, 5174 (dev servers)

**API Security:**
- CORS middleware: Allows localhost origins only (`backend/main.py` lines 25-37)
- No authentication middleware (assumes trusted local environment)

## Monitoring & Observability

**Error Tracking:**
- None configured
- Logging via Python `logging` module
- Backend logs: Optional file at `$TMPDIR/libertas-backend.log` (see `./start.sh`)

**Logs:**
- Python logging: `logging.getLogger(__name__)` throughout
- Log levels: info (startup), warning (errors), no explicit debug configuration
- Examples: News refresh failures, backend startup messages (see `backend/routers/news.py` line 16)

## Webhooks & Callbacks

**Incoming:**
- None — application is local only

**Outgoing:**
- None — application does not push events to external services

## Scheduled Tasks

**Price Refresh:**
- Trigger: API endpoint `/api/prices/refresh` (POST)
- Or: Automatic on startup via `_post_startup_refresh()` async function (`backend/main.py` lines 90-105)
- Function: `refresh_prices()` async endpoint in `backend/routers/prices.py` (lines 92-131)
- Behavior: Fetches stock prices from Yahoo Finance, crypto from CoinGecko, updates holding prices in DB
- Snapshots: After price refresh, snapshots are recorded automatically

**News Refresh:**
- Trigger: API endpoint `/api/news/refresh` (POST) or auto-triggered if cache stale
- Cache TTL: 2 hours (CACHE_TTL_HOURS)
- Execution: Background thread (daemon) in `_refresh_worker()` (`backend/routers/news.py` lines 158-170)
- Locking: Thread lock prevents concurrent refreshes (lines 78, 145-155)
- Feed sources: RSS feeds (Google News, Morning Brew, Yahoo Finance, Reuters, FT, MarketWatch, CNBC)

**Watch Folder Polling:**
- Handler: `watchdog` library via `backend/watchers/folder_watcher.py`
- Trigger: File system events in `/data/watch/`
- Behavior: Auto-ingest new CSV files using learned column mappings
- Startup: Initiated in `@app.on_event("startup")` (`backend/main.py` line 78)

## Environment Configuration

**Required env vars:** (optional, stored in DB or environment)
- `CLAUDE_API_KEY` - Optional for Claude API chat feature (see `backend/ai.py` line 11)

**Optional env vars:**
- `LIBERTAS_RELOAD` - Set to "1" to enable Uvicorn reload mode during development (see `./start.sh` line 60)

**Secrets location:**
- Environment variables (`.env` file, optional)
- Database settings table: `CLAUDE_API_KEY` can be stored as JSON in `Setting` model (see `backend/ai.py` lines 24-32)
- No hardcoded secrets in code

## Optional AI Integration

**Claude API (Opt-in Chat):**
- Implementation: `backend/ai.py`
- Model: `claude-sonnet-4-6`
- Endpoint: `https://api.anthropic.com/v1/messages`
- Auth: `x-api-key` header with API key from env or database
- Usage: Optional chat feature for financial insights (referenced in routers but not mandatory)
- Max tokens: 1024 per request
- Error handling: Raises `ValueError` if key not configured; HTTP errors propagate
- Function: `chat(messages, system)` async function (lines 37-65)
- Configuration check: `is_configured()` function (line 17) checks key availability before use

---

*Integration audit: 2026-04-11*
