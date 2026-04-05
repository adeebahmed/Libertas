# Libertas — CLAUDE.md

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
- Insights engine is rule-based; optional Claude API chat is opt-in

## Running locally
```bash
./start.sh          # backend (port 8000) + frontend dev server (port 5173/5174)
./start-docs.sh     # VitePress docs dev server
```

### Which port to use
- **`:5174` (Vite dev server)** — use this while developing. Hot reload; no rebuild needed after frontend changes. API calls are proxied to `:8000` automatically.
- **`:8000` (FastAPI)** — serves the compiled frontend after `npm run build --prefix frontend`. Use this to test the production build.

Day-to-day: open `:5174` in your browser. The backend must still be running at `:8000` (both start via `./start.sh`), but you never need to open `:8000` directly.
