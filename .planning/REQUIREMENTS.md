# Libertas — Requirements

## Scope: V1 (MVP → Multi-Model)

Plaid Integration is out of V1 scope but architecture must accommodate it.

---

## Functional Requirements

### FR-1: Data Entry & Import

**FR-1.1 Manual Data Entry** (GitHub #28)
- User can manually add/edit accounts with name, type, balance, and currency
- Account types: checking, savings, brokerage, IRA/401k, crypto, real estate, auto loan, student loan, mortgage, credit card, other
- Balance and valuation can be manually overridden at any time
- Holdings (individual positions) can be entered manually for investment accounts
- Debt accounts support principal, interest rate, minimum payment, and payoff date fields

**FR-1.2 CSV Import**
- Watch folder auto-detects new CSV files from supported institutions
- Column mapping UI shows auto-matched columns + 3 sample rows for user verification
- Preview shows: transaction count, date range, detected duplicates
- Import is idempotent: SHA256 hash on (date + amount + description) prevents duplicates
- Confirmation toast shows: "N new, N skipped (already imported)"
- Institution mappings persist across sessions
- Graceful handling of: encoding mismatches, junk header rows, header drift, date format ambiguity
- Bad-row parse failures shown with count and sample — never silently dropped

**FR-1.3 Price Refresh**
- Stock and ETF prices refresh via yfinance
- Crypto prices refresh via CoinGecko free tier
- Real estate values refresh via Zillow scrape (with Redfin fallback)
- Staleness indicators on accounts: green (<3d), yellow (3-7d), red (>7d)
- Manual price override always available regardless of refresh status

---

### FR-2: Net Worth Dashboard

**FR-2.1 Hero Metrics**
- Single net worth figure prominently displayed (total assets minus total liabilities)
- Net worth change: dollar amount and percentage vs. 30 days ago
- Last updated timestamp visible

**FR-2.2 Asset Allocation**
- Donut/pie chart showing allocation by asset class
- Classes: Equities, Fixed Income, Cash & Equivalents, Real Estate, Crypto, Liabilities
- Percentages and dollar amounts on hover

**FR-2.3 Net Worth Over Time**
- Line chart showing net worth history
- Selectable time ranges: 1M, 3M, 6M, YTD, 1Y, All
- Monthly snapshot stored at end of each month

**FR-2.4 Account List**
- All accounts visible with current balance and staleness indicator
- Grouped by type (Investments, Cash, Real Estate, Liabilities)
- Quick-add account from list view
- Click-through to account detail

---

### FR-3: Account Depth Views

**FR-3.1 Transaction History**
- Per-account searchable transaction list
- Filter by date range, amount range, description keyword
- Manual transaction entry for accounts without CSV import

**FR-3.2 Holdings Breakdown**
- For investment accounts: per-position view with symbol, shares, price, value, gain/loss
- Cost basis tracked per position (FIFO default)
- Performance vs. S&P 500 for investment accounts

**FR-3.3 Real Estate Detail**
- Current estimated value (Zillow/manual)
- Mortgage balance and LTV ratio
- Equity calculation (value minus mortgage balance)

---

### FR-4: Insights Engine (Rule-Based)

**FR-4.1 Insight Cards**
- Concentration risk: single position >20% of portfolio
- Liquidity ratio: cash + liquid assets vs. monthly expenses
- Allocation drift: actual vs. target allocation (user-defined targets optional)
- Emergency fund coverage: liquid assets / monthly expenses in months
- Debt-to-income estimate (approximated from account data)

**FR-4.2 Insights must work fully offline** — no AI dependency

---

### FR-5: FIRE Model / Projections (GitHub #24, #11)

**FR-5.1 Financial Freedom Calculator**
- User inputs: current savings rate, annual expenses, expected return, target retirement date
- Output: projected retirement readiness (% of FIRE number achieved)
- Three scenarios: conservative (4%), base (6%), optimistic (8%) CAGR
- "Can I retire by [date]?" answer with plain-language explanation

**FR-5.2 User Journey**
- Goal-setting flow (#11): user defines financial freedom target
- Dashboard surfaces progress toward goal with timeline visualization

---

### FR-6: Onboarding (GitHub #25, #10)

**FR-6.1 First-Run Wizard**
- Step 1: Choose data entry method (manual entry or CSV import)
- Step 2: Add first account (guided, with type selection)
- Step 3: Set financial freedom goal (optional, skippable)
- Step 4: See net worth dashboard (even if incomplete)

**FR-6.2 Mission Differentiation** (GitHub #10)
- In-app messaging about local-first / privacy-by-design positioning
- Prominent callout: "Your data never leaves this machine"

---

### FR-7: AI Chat (GitHub #18-#23)

**FR-7.1 LLM Provider Abstraction** (GitHub #18)
- Abstract provider interface supporting multiple LLM backends
- User selects provider in Settings (Claude, OpenAI, Ollama, none)
- API keys stored locally, never transmitted

**FR-7.2 Provider Implementations**
- Claude (Anthropic) via API (#19)
- OpenAI via API (#20)
- Local Ollama models (#21)

**FR-7.3 Model Selection UI** (GitHub #22)
- Settings page shows available providers and models
- Cost estimate visible per provider (GitHub #27)

**FR-7.4 Prompt & Context Management** (GitHub #23)
- Summarization layer for large transaction histories (rolling 90-day window default)
- System prompt includes: net worth summary, top holdings, recent spending patterns
- Answers labeled as informational, not financial advice
- Conversation history persisted per session, clearable

---

## Non-Functional Requirements

**NFR-1: Performance**
- All dashboard queries complete in <500ms against local SQLite
- CSV import of 10,000 rows completes in <10 seconds
- App startup (frontend load + first data render) in <3 seconds

**NFR-2: Privacy & Security**
- No telemetry, no analytics calls to external services
- API keys stored in local config, never logged
- No credentials required for core functionality
- HTTPS not required (localhost-only)

**NFR-3: Reliability**
- CSV re-import of same file produces identical result (idempotency)
- SQLite database is the source of truth; no in-memory-only state
- Failed price refreshes shown clearly, never silently stale

**NFR-4: Extensibility (for future Plaid)**
- Account schema supports `external_id` and `sync_source` fields
- Transaction schema designed to receive either CSV-imported or API-pushed transactions
- No hardcoded CSV-only assumptions in data models

---

## Out of Scope for V1

- Budgeting / envelope system
- Bill pay integration
- Mobile native app
- Goals tracking (beyond FIRE)
- Multi-user / household support
- Plaid / direct bank connections (Phase 5)
