# Libertas — Personal Finance Dashboard
**Design Spec | 2026-04-03**

---

## Context

The user has financial assets spread across many institutions: brokerage accounts, crypto exchanges, real estate properties, HSA, Roth IRA, savings, and more. No single tool gives a unified view without paying for a third-party service or handing over account credentials. Libertas is a locally-hosted personal finance dashboard that ingests exported CSV/Excel data from each institution, enriches it with free public price APIs, and presents a unified net worth view with insights, projections, and allocation breakdowns. No third-party services. No cloud. No account linking. All data stays on the user's machine.

**Privacy as a feature:** The "no data collection, locally-hosted" nature is a genuine selling point — it's the kind of thing that convinces users to choose a tool. This should be front-and-center in the UI and docs, not buried.

**Manual refresh trade-off:** The CSV export/import flow introduces friction compared to auto-syncing apps. This is an intentional trade-off for privacy. The UX should minimize this friction wherever possible — watch folder auto-detection, staleness indicators, and one-click institution export links are the primary mitigations already in the spec. Future iterations could explore read-only bank API integrations (Plaid-free) as an opt-in.

---

## Design Inspiration

Study these apps when designing the UI — both are praised for modern, non-generic aesthetics:

| App | Notes |
|---|---|
| **Fey** (fey.com) | Beautiful, clean portfolio UI. Reference for visual quality bar. |
| **Copilot Money** (copilot.money) | Modern portfolio + budgeting app. More polished than typical SaaS. |

Both represent a design direction that's more refined than the generic SaaS aesthetic that dominated 2016–2024. Libertas should feel closer to these than to a typical dashboard tool.

---

## Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11+, FastAPI, SQLAlchemy, SQLite |
| Frontend | Vite + React 18 + TypeScript + Recharts |
| Docs | VitePress (Markdown), deployed to GitHub Pages |
| Stock prices | `yfinance` (Yahoo Finance, no API key) |
| Crypto prices | CoinGecko REST API (free tier, no API key) |
| Real estate values | `httpx` + `beautifulsoup4` scraping Zillow/Redfin, with manual override |
| Dev launcher | Single `start.sh` script (concurrently runs backend + frontend) |

---

## Project Structure

```
/Libertas
  /backend
    main.py               ← FastAPI app entrypoint, serves built frontend as static files
    database.py           ← SQLite setup via SQLAlchemy
    models.py             ← ORM table definitions
    /routers
      accounts.py         ← CRUD for accounts and institutions
      imports.py          ← CSV/Excel ingestion, column mapping, deduplication
      prices.py           ← stock + crypto price refresh
      real_estate.py      ← property CRUD, Zillow scraping, manual override
      projections.py      ← growth projection calculations
      snapshots.py        ← net worth snapshot recording
      insights.py         ← rule-based insight engine
      settings.py         ← app settings CRUD
    /watchers
      folder_watcher.py   ← watchdog-based watch folder monitor
    /importers
      base.py             ← abstract importer interface
      fidelity.py         ← Fidelity preset column mapping
      schwab.py
      coinbase.py
      robinhood.py
      generic.py          ← fallback auto-mapper for unknown institutions
  /frontend
    /src
      /components         ← reusable UI: charts, cards, tables, badges
      /pages
        Dashboard.tsx
        Accounts.tsx
        Import.tsx
        RealEstate.tsx
        Projections.tsx
        Insights.tsx
        Settings.tsx
      /api                ← typed fetch wrappers (one file per router)
      /types              ← shared TypeScript interfaces mirroring DB models
      /hooks              ← useAccounts, usePrices, useInsights, etc.
    vite.config.ts
    tsconfig.json
  /docs                   ← VitePress documentation site
    index.md
    /guide
      getting-started.md
      importing-data.md
      real-estate.md
      insights.md
      projections.md
    /reference
      accounts.md
      faq.md
    .vitepress/config.ts
  /data
    libertas.db           ← SQLite database (all user data)
    /watch                ← watched folder: drop exported CSVs here
  .github/workflows/
    docs.yml              ← builds VitePress and deploys to GitHub Pages
  start.sh                ← starts backend + frontend concurrently
  start-docs.sh           ← starts VitePress dev server for editing docs
```

---

## Data Model

### `accounts`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| name | TEXT | User-defined label (e.g. "Fidelity Roth IRA") |
| type | TEXT | brokerage \| crypto \| real_estate \| savings \| hsa \| roth_ira \| 401k \| checking |
| institution_id | INTEGER FK | Links to institutions table |
| currency | TEXT | Default USD |
| created_at | DATETIME | |

### `institutions`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| name | TEXT | e.g. "Fidelity", "Coinbase" |
| export_url | TEXT | Direct link to the export page on their website |
| file_pattern | TEXT | Glob pattern to auto-match files, e.g. `Fidelity_*.csv` |
| column_mapping | JSON | Saved after first import: maps their headers to Libertas fields |
| importer_preset | TEXT | fidelity \| schwab \| coinbase \| robinhood \| generic |
| notes | TEXT | Optional user notes (e.g. "Select 'All Accounts' before exporting") |

### `holdings`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| account_id | INTEGER FK | |
| symbol | TEXT | Ticker or coin ID |
| quantity | REAL | |
| cost_basis | REAL | Total cost basis |
| last_price | REAL | Updated via price refresh |
| last_updated | DATETIME | |

### `transactions`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| account_id | INTEGER FK | |
| date | DATE | |
| type | TEXT | buy \| sell \| deposit \| withdrawal \| dividend \| transfer |
| symbol | TEXT | Nullable for cash transactions |
| quantity | REAL | |
| price | REAL | |
| amount | REAL | Total dollar value |
| description | TEXT | |
| raw_row | JSON | Original CSV row, preserved for debugging |
| import_hash | TEXT | SHA256 of raw row for deduplication |

### `balance_snapshots`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| account_id | INTEGER FK | |
| date | DATE | |
| balance | REAL | Point-in-time balance in USD |

### `real_estate`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| account_id | INTEGER FK | |
| address | TEXT | |
| purchase_price | REAL | |
| purchase_date | DATE | |
| zillow_estimate | REAL | Last scraped value |
| manual_override | REAL | If set, used instead of Zillow estimate |
| effective_value | REAL | Computed: manual_override ?? zillow_estimate |
| mortgage_balance | REAL | |
| last_updated | DATETIME | |

### `settings`
| Column | Type | Notes |
|---|---|---|
| key | TEXT PK | |
| value | TEXT | JSON-serialized |

Settings keys: `monthly_expenses`, `risk_profile`, `claude_api_key`, `watch_folder_path`, `projection_return_rates`

---

## Pages & Screens

### Dashboard
- Total net worth (large hero number, delta since last snapshot)
- Asset allocation donut chart: stocks / crypto / real estate / cash / HSA / retirement
- Net worth over time line chart (monthly balance snapshots)
- Top movers today (gainers and losers across all holdings)
- Account balance cards with staleness indicator (green < 3 days, yellow 3-7 days, red > 7 days)

### Accounts
- List all accounts with current balance, type badge, last updated
- Click into account → transaction history table, holdings breakdown, performance chart

### Import
- Drag-and-drop zone for CSV/Excel (or auto-picked up from watch folder)
- Institution selector — shows all saved institutions with their one-click export links
- "Add new institution" flow: name, export URL, paste a sample CSV to teach column mapping
- Auto column-mapping preview with correction UI before confirm
- Import history log with row counts and timestamps

### Real Estate
- Property cards: address, current value, mortgage balance, equity, LTV percentage
- Add/edit property form
- Equity over time chart per property
- Zillow/Redfin auto-refresh with "Override value" field that takes precedence

### Projections
- Configure: annual return rate, monthly contribution, time horizon (years)
- Three scenario curves: conservative (4%), moderate (7%), aggressive (10%)
- Total projected value by year, broken down by account type
- Assumes current balances as starting point

### Insights
- Card grid, one card per insight
- Color-coded categories: Risk / Performance / Tax Efficiency / Liquidity / Trends
- Each card: title, plain-English explanation, "Why this matters" line
- Insight categories:
  - **Concentration:** single-stock or single-asset overweight
  - **Allocation:** deviation from target mix by risk profile
  - **Performance vs benchmarks:** YTD vs S&P 500, BTC benchmark for crypto
  - **Liquidity:** months of expenses in liquid accounts
  - **Real estate:** LTV, equity growth rate, refinance opportunity signals
  - **Tax efficiency:** asset placement (bonds in taxable, growth in Roth, etc.)
  - **Trends:** net worth growth rate change, accelerating/decelerating savings
- Optional Claude API chat at bottom: ask questions about your finances in natural language (opt-in, requires API key in Settings)

### Settings
- Manage institutions: add, edit export URL, view/reset column mapping
- Manage accounts: add, rename, delete, assign institution
- Watch folder path configuration
- Monthly expenses (used for liquidity calculations)
- Risk profile selector (conservative / moderate / aggressive)
- Claude API key (optional, for Insights chat)
- Export all data as JSON backup
- Manual "Refresh prices" button

---

## Data Refresh Flow

1. User opens dashboard — staleness indicators show which accounts need updating (color-coded)
2. User clicks account card → one-click button opens the institution's export URL directly in browser
3. User logs in, navigates to export, downloads CSV, saves to the watch folder (`/data/watch/`)
4. App detects new file via folder watcher → matches to institution by filename pattern
5. Auto-maps columns using saved mapping (no user action needed after first import)
6. Shows preview toast: "Detected 143 new transactions from Fidelity — Import?" → one click confirm
7. Transactions deduplicated by hash → holdings and balance snapshot updated
8. Prices refreshed via yfinance/CoinGecko → net worth recalculated → insights re-run

---

## CSV Ingestion Detail

**First-time import for a new institution:**
1. User uploads file and selects or creates an institution
2. Backend inspects headers + 3 sample rows, scores each header against known field types
3. Presents mapping table: their column → Libertas field (editable)
4. User confirms → mapping saved to `institutions.column_mapping`
5. Data imported, import_hash stored per row for future deduplication

**Subsequent imports:**
- Saved mapping applied automatically
- Only new rows (by import_hash) are inserted
- Re-importing the same file is always safe

**Built-in presets (zero-config on first import):**
Fidelity, Schwab, Robinhood, Coinbase, Chase, Vanguard

---

## Documentation Site

VitePress in `/docs`, deployed to GitHub Pages via GitHub Actions on every push to `main`.

**Public URL:** `https://<username>.github.io/libertas`

Only the compiled static docs are deployed — no app code, no data, no SQLite file is ever exposed.

**Structure:**
- Landing page with feature overview
- Getting Started: install, first run, adding your first account
- Importing Data: step-by-step per institution type, watch folder setup
- Real Estate: adding properties, Zillow estimates, manual override
- Insights: what each insight type means and how to act on it
- Projections: how scenarios are calculated
- Reference: account types, FAQ

Docs are Markdown files in `/docs`. Updating docs = editing a `.md` file and pushing. No separate deploy step needed.

---

## Startup

```bash
./start.sh         # starts FastAPI (port 8000) + Vite dev server (port 5173) concurrently
./start-docs.sh    # starts VitePress dev server for editing docs locally
```

For daily use after building: `npm run build --prefix frontend` once, then only `./start.sh` needed — FastAPI serves the compiled frontend at `localhost:8000`.

---

## Verification

- `localhost:8000` serves the dashboard
- Drop a sample CSV into `/data/watch/` → toast appears within 2 seconds
- Import confirms → transaction count increases in Accounts page
- Dashboard net worth updates to reflect new balances
- Insights tab shows at least one card after data is populated
- Projections page renders three scenario curves
- `https://<username>.github.io/libertas` renders VitePress docs after first push to `main`
