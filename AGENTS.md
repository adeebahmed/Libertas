# Libertas — AGENTS.md

Locally-hosted personal finance dashboard. No SaaS, no cloud, no account linking. All data stays on this machine.

## Stack
- **Backend:** Python 3.11+, FastAPI, SQLAlchemy, SQLite (`/data/libertas.db`)
- **Frontend:** Vite + React 18 + TypeScript + Recharts
- **Docs:** VitePress → GitHub Pages
- **Price data:** yfinance (stocks), CoinGecko free tier (crypto)
- **Dev:** `./start.sh` runs backend (port 8000) + frontend (port 5173) concurrently

## Project layout
```
/backend        FastAPI app, routers, importers, watchers
/frontend       Vite+React app
/docs           VitePress site + ADRs
/data           libertas.db + /watch folder for CSV drops
start.sh        dev launcher
```

## ADR pattern
Every significant architectural decision or feature gets an ADR in `docs/adr/`.
- Format: `NNN-short-title.md` (e.g. `002-real-estate-valuation.md`)
- Number sequentially; generate one with every PR that introduces a new subsystem or non-trivial design decision
- ADR-001 (`docs/adr/001-finance-dashboard-design.md`) is the founding spec

## Design bar
Reference apps: **Fey** (fey.com) and **Copilot Money** (copilot.money).
Aim for modern, clean, non-generic UI — not the flat-SaaS look of 2016–2024.

## Key decisions (from ADR-001)
- CSV/Excel import only — no direct institution API links (privacy trade-off, intentional)
- Watch folder (`/data/watch/`) auto-detects new files via watchdog
- First import teaches column mapping; subsequent imports use saved mapping
- Built-in presets: Fidelity, Schwab, Robinhood, Coinbase, Chase, Vanguard
- Real estate values: Zillow scrape with manual override
- Insights engine is rule-based; optional Claude API chat is opt-in (claude-sonnet-4-6)

## Running locally
```bash
./start.sh          # backend + frontend
./start-docs.sh     # VitePress docs dev server
```
After `npm run build --prefix frontend`, FastAPI serves the compiled frontend at `localhost:8000`.

## API routing convention
All backend routers are mounted under `/api`. Frontend `api.get('/accounts')` → `/api/accounts`.

## Backend routers (backend/routers/)
| File | Prefix | Notes |
|------|--------|-------|
| accounts.py | /api/accounts | CRUD + `/institutions`; `/{id}/transactions`; `/{id}/performance` |
| snapshots.py | /api/snapshots | `/current` (NetWorth), `/net-worth` (history) |
| imports.py | /api/imports | Upload CSV; `/{id}/rollback`; `/preview` |
| watcher.py | /api/watcher | `/latest` — most recent ImportLog entry |
| insights.py | /api/insights | Rule-based list; `POST /chat` (Claude AI) |
| debt.py | /api/debt | Summary + `/strategies` + `/{id}/extra-payment` |
| retirement.py | /api/retirement | Projection; `/plan` (personalized, uses settings) |
| taxes.py | /api/taxes | `/estimate`; `/harvesting`; `/entity-recommendations` |
| news.py | /api/news | Cached RSS feed (5 sources, 2h TTL); `POST /refresh` |
| backups.py | /api/backups | `GET/POST`; `/{id}/download` |
| prices.py | /api/prices | `POST /refresh` |
| settings.py | /api/settings | `GET`; `PUT /{key}` |
| real_estate.py | /api/real-estate | Properties + Zillow scrape |
| projections.py | /api/projections | Legacy — kept for compat; prefer /retirement |

## Key models (backend/models.py)
- **Transaction** — has nullable `import_log_id` FK to ImportLog; set at ingest time for rollback support
- **ImportLog** — tracks each CSV import; `status` field ("completed" | "rolled_back")
- **Backup** — filename + size_bytes; JSON exports saved to `data/backups/`
- **NewsCache** — source, title, url, published_at, fetched_at; TTL-expired and refreshed by news router

## Settings keys (stored in `settings` table as key/value)
| Key | Type | Used by |
|-----|------|---------|
| monthly_expenses | float | Insights, retirement target (25× rule) |
| risk_profile | str | Insights (conservative/moderate/aggressive) |
| claude_api_key | str | ai.py — fallback if env var not set |
| income_w2 | float | taxes.py, insights.py (sum with income_1099 for total income) |
| income_1099 | float | taxes.py, insights.py (sum with income_w2 for total income) |
| tax_filing_status | str | taxes.py (single/married_filing_jointly/etc.) |
| birth_year | int | retirement.py /plan |
| retirement_age | int | retirement.py /plan |
| monthly_contribution | float | retirement.py /plan |
| retirement_target_amount | float | retirement.py /plan (overrides 25× auto) |

**Income convention:** use `income_w2 + income_1099` to compute total annual income. Do NOT use a legacy `annual_income` key.

## Claude AI integration (backend/ai.py)
- `get_api_key()` — checks `CLAUDE_API_KEY` env var first, then `claude_api_key` setting in DB
- `is_configured() -> bool`
- `async chat(messages, system="") -> str` — calls `claude-sonnet-4-6` via httpx
- Used by `insights.py POST /chat` with full portfolio context injected as system prompt

## Import rollback
1. `ingest_file()` flushes the ImportLog early to get its `.id`
2. Every new Transaction is tagged with `import_log_id=log.id`
3. `POST /api/imports/{id}/rollback` deletes all transactions with that ID, rebuilds holdings + snapshot, sets log status="rolled_back"

## Watch folder notification (frontend)
`WatchNotification` component in `Import.tsx` polls `GET /api/watcher/latest` every 5s. Tracks `lastSeenId` in a ref; shows a dismissable banner when a new (higher) ID appears.

## Insights shape
Every insight has: `title`, `description`, `category`, `priority` ("high"|"medium"|"low"), `action` (one-liner), `why`.
Categories: Risk, Performance, Allocation, Liquidity, Trends, Retirement, Debt, Tax, Behavioral, Estate.

## Frontend pages (frontend/src/pages/)
| File | Route | Notes |
|------|-------|-------|
| Dashboard.tsx | / | Net worth hero, area chart, allocation donut, accounts grid, news sidebar |
| Accounts.tsx | /accounts | Holdings per account |
| Import.tsx | /import | CSV upload + WatchNotification + rollback log |
| Debt.tsx | /debt | Summary + avalanche/snowball strategies |
| Retirement.tsx | /retirement | On-track status + scenarios (replaced Projections) |
| Taxes.tsx | /taxes | Estimate breakdown + harvesting + entity recs |
| Insights.tsx | /insights | Priority-filtered cards + "Ask Claude" chat tab |
| RealEstate.tsx | /real-estate | Property management |
| Settings.tsx | /settings | General, Income & Tax, Retirement, Institutions, Accounts, Data |

## Current runtime notes (2026-04-05)
- Dashboard news is fetched from `/api/news` with async background refresh; hard reload sends `?refresh=1`.
- News feed keeps cached cards fast, shows a loading spinner while fetching, and prioritizes AI-relevant headlines in top cards.
- Paywalled domains are filtered from direct links where possible; links should resolve to article pages (not search pages).
- Keep `data/watch/*.csv` fixtures tracked for local dummy/demo data.
- Dev run expectation: backend API on `:8000`; frontend Vite dev server may run on `:5173` or next available port if occupied.
