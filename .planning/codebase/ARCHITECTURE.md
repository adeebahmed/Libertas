# Architecture

**Analysis Date:** 2026-04-11

## Pattern Overview

**Overall:** Three-tier client-server with data ingestion pipeline

Libertas uses a **REST API backend (FastAPI) + React frontend** architecture with an **asynchronous data ingestion and refresh pipeline**. All data is persisted locally in SQLite with no cloud dependencies. The system uses a service-layer pattern with routers handling domain logic and a shared models/database layer.

**Key Characteristics:**
- **Privacy-first**: All data stays on the user's machine; no account linking or cloud storage
- **Multi-source ingestion**: CSV watch-folder imports (primary), manual entry (ADR-002), optional Plaid (future)
- **Event-driven file processing**: Watchdog monitors `/data/watch/` for new CSVs and auto-ingests them
- **Price refresh pipeline**: Background tasks refresh stock/crypto prices and record net worth snapshots
- **Rule-based insights**: Server-side calculation engine generates financial insights from holdings + settings

## Layers

**Presentation Layer (Frontend):**
- Purpose: React SPA for user interactions with dashboard, forms, and visualizations
- Location: `/frontend/src`
- Contains: Page components, reusable UI components, typed API client, hooks for data fetching
- Depends on: FastAPI `/api/*` endpoints
- Used by: Web browser (dev: localhost:5173, prod: served by FastAPI at :8000)

**API Layer (Backend Routers):**
- Purpose: REST endpoints organized by domain (accounts, imports, prices, snapshots, insights, etc.)
- Location: `/backend/routers/`
- Contains: Route handlers with FastAPI decorators, Pydantic request/response models
- Depends on: Database models, importers, services
- Used by: Frontend SPA via fetch/XHR, folder watcher (internal HTTP calls)

**Service/Business Logic Layer:**
- Purpose: Core domain logic: CSV parsing, column detection, price fetching, snapshot recording, insight generation
- Location: `/backend/importers/`, `/backend/watchers/`, router functions
- Contains: `ingest.py` (CSV ingestion), `analyzer.py` (column auto-detection), `folder_watcher.py` (watch folder monitor)
- Depends on: Database models, SQLAlchemy ORM
- Used by: Routers, startup routines

**Data Layer:**
- Purpose: SQLite database with SQLAlchemy ORM definitions
- Location: `/backend/database.py` (connection, migrations), `/backend/models.py` (ORM definitions)
- Contains: 10+ ORM models (Account, Institution, Holding, Transaction, BalanceSnapshot, RealEstate, etc.)
- Depends on: SQLAlchemy, SQLite
- Used by: All routers and services

## Data Flow

**CSV Import Flow:**

1. **File Detection**: Watchdog monitors `/data/watch/` folder
   - Location: `backend/watchers/folder_watcher.py`
   - Triggered: On new `.csv`, `.xlsx`, `.xls` file creation

2. **File Reading & Analysis**:
   - `backend/importers/ingest.py:read_file()` → reads CSV/Excel headers and rows
   - `backend/importers/analyzer.py:auto_detect_columns()` → infers column roles (Date, Symbol, Quantity, Price, etc.)

3. **Institution & Account Matching**:
   - `backend/importers/filename_parser.py:parse_filename()` → extracts institution name from filename
   - Looks up or creates Institution record with column mapping
   - Looks up or creates Account for that institution+type combo

4. **Transaction Import**:
   - `backend/importers/ingest.py:ingest_file()` → iterates rows
   - Each row hashed for deduplication (SHA256 of content + filename)
   - Transaction records inserted (one per row) with `import_hash` and `import_log_id`

5. **Holdings Rebuild**:
   - `backend/importers/ingest.py:_rebuild_holdings()` → aggregates all transactions per symbol
   - Calculates position quantity and cost basis (buys add, sells subtract)
   - Creates/updates Holding records

6. **Snapshot Recording**:
   - `backend/importers/ingest.py:_take_snapshot()` → calculates balance at import time
   - Uses most recent prices × quantity for securities, cost basis fallback for unmissed prices
   - Adds real estate equity (value - mortgage_balance)
   - Stores BalanceSnapshot for that account + date

7. **File Archival**:
   - Processed file moved to `/data/watch/processed/[filename]`
   - Location: `backend/watchers/folder_watcher.py:_process_file()`

**Price Refresh Pipeline:**

1. **Trigger**: Manual "Refresh prices" button or startup auto-refresh
   - Location: `backend/routers/prices.py:refresh_prices()`

2. **Stock Prices**:
   - Fetches from Yahoo Finance chart API (no auth needed)
   - Symbols: all unique ticker symbols across all holdings
   - Result: dict of {symbol: price}

3. **Crypto Prices**:
   - Fetches from CoinGecko free API
   - Maps symbol to coin ID (BTC→bitcoin, ETH→ethereum, etc.)
   - Location: `backend/routers/prices.py:CRYPTO_MAP` + `fetch_crypto_prices()`

4. **Update Holdings**:
   - Updates `Holding.last_price` and `Holding.last_updated` in batch
   - All holdings that lack price data fall back to cost basis

5. **Snapshot Recording**:
   - Calls `/api/snapshots/record` (internal HTTP POST via watchdog watcher)
   - Records new BalanceSnapshot with updated prices
   - Location: `backend/routers/snapshots.py:record_snapshots()`

**Insights Generation:**

1. **Trigger**: Dashboard load or explicit refresh
   - Location: `backend/routers/insights.py:_generate_insights()`
   - Called by GET `/api/insights`

2. **Data Aggregation**:
   - Collects all holdings by account type and symbol
   - Sums market values (price × quantity)
   - Separates debt from assets

3. **Rule Evaluation**:
   - **Concentration**: Flag if single symbol > 20% of portfolio
   - **Allocation**: Compare actual vs target allocation by risk profile
   - **Liquidity**: Months of expenses in liquid accounts
   - **Real Estate**: LTV, equity growth, refinance signals
   - **Tax Efficiency**: Asset location recommendations
   - **Trends**: Net worth growth rate changes

4. **Return**: Array of insight cards with category, priority, action text

**State Management:**

- **Backend state**: SQLite persisted, queried on-demand
- **Frontend state**: React hooks (`useState`, `useRef`, `useMemo`) + useApi custom hook
- **Form state**: Pydantic models auto-validate in routers
- **Caching**: News articles cached with 30-min TTL (ADR-003)

## Key Abstractions

**Institution:**
- Purpose: Represents a financial institution (Fidelity, Coinbase, Chase, etc.)
- Examples: `backend/models.py:Institution`
- Pattern: Has many Accounts, stores column mapping for CSV ingestion
- Fields: name, export_url (direct link to export page), file_pattern (glob match), column_mapping (JSON)

**Account:**
- Purpose: User's account at an institution (e.g., "Fidelity Roth IRA", "Chase Checking")
- Examples: `backend/models.py:Account`
- Pattern: Aggregates holdings, transactions, snapshots, and real estate under one entity
- Types: brokerage, crypto, savings, checking, hsa, roth_ira, 401k, credit_card, student_loan, auto_loan, personal_loan

**Holding:**
- Purpose: A security position within an account (e.g., 100 shares of AAPL at $150/share)
- Examples: `backend/models.py:Holding`
- Pattern: Derived from transactions; updated on import and price refresh
- Fields: symbol, quantity, cost_basis (total), last_price, last_updated

**Transaction:**
- Purpose: A single action (buy, sell, deposit, dividend, etc.)
- Examples: `backend/models.py:Transaction`
- Pattern: Immutable record; import_hash ensures deduplication across re-imports
- Fields: account_id, date, type, symbol, quantity, price, amount, raw_row (JSON), import_hash

**BalanceSnapshot:**
- Purpose: Point-in-time net worth for an account on a date
- Examples: `backend/models.py:BalanceSnapshot`
- Pattern: One per account per day; used for net worth history charts
- Calculated: Holdings market value + real estate equity

**RealEstate:**
- Purpose: Property ownership with valuation tracking
- Examples: `backend/models.py:RealEstate`
- Pattern: Linked to account; stores manual override for Zillow estimate
- Fields: address, purchase_price, purchase_date, zillow_estimate, manual_override, mortgage_balance, mortgage_rate

## Entry Points

**Backend:**
- Location: `backend/main.py:app`
- Triggers: `uvicorn backend.main:app` (via `./start.sh`)
- Responsibilities:
  - Register all routers (`/api/accounts/*`, `/api/imports/*`, etc.)
  - Initialize SQLite database and run migrations
  - Start folder watcher in background thread
  - Mount compiled frontend as static files (production)
  - Run post-startup price refresh

**Frontend:**
- Location: `frontend/src/main.tsx` → `App.tsx`
- Triggers: Browser load of http://localhost:5173 (dev) or served by FastAPI (prod)
- Responsibilities:
  - Set up React Router with navigation links
  - Render sidebar with nav, main content area with routes
  - Lazy load pages (Dashboard, Accounts, Import, etc.)
  - Set up API client with dynamic base URL resolution

**Folder Watcher:**
- Location: `backend/watchers/folder_watcher.py:start_watcher()`
- Triggers: On app startup
- Responsibilities:
  - Monitor `/data/watch/` for new CSV files
  - Detect file completion (size stability check)
  - Call `ingest_file()` and move to processed/
  - Trigger price refresh and snapshot recording via HTTP POST

## Error Handling

**Strategy:** Graceful degradation with logging

**Patterns:**
- **Import errors**: Log ImportLog with status='error' + error_message, continue startup
- **Price fetch failures**: Skip unresponsive symbols, use cost basis fallback
- **Watcher failures**: Log warning, disable watcher, allow manual upload via UI
- **Missing data**: Return empty arrays, show "Add Data" insight, don't crash
- **Transaction validation**: Preserve raw_row JSON for debugging; hash dedup prevents exact duplicates

## Cross-Cutting Concerns

**Logging:** Python's standard logging module
- Backend logs to stdout (captured by systemd or `./start.sh`)
- Folder watcher logs to logger with module name prefix
- No external logging service; all logs stay local

**Validation:**
- Pydantic models validate request payloads in routers
- Column analyzer validates headers against known financial fields
- Transaction fields checked for required values (date, amount, etc.)

**Authentication:** None
- Local-only app; no user accounts or permissions
- CORS allows localhost:5173/5174 and dev ports only
- `.env` secrets (API keys) gitignored, never exposed

**Database:**
- SQLite with WAL mode for better concurrency
- Foreign key constraints enabled (`PRAGMA foreign_keys=ON`)
- Cascade deletes for Account → Transactions/Holdings/Snapshots
- Lightweight migrations in `database.py:_apply_sqlite_migrations()`

---

*Architecture analysis: 2026-04-11*
