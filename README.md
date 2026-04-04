# Libertas

Personal finance dashboard. Runs locally. No SaaS, no cloud, no account linking. Your data stays on your machine.

## How it works

Drop CSV or Excel exports from any financial institution into `data/watch/`. Libertas automatically:

- Reads the file and figures out what each column is (dates, symbols, amounts, etc.)
- Identifies the institution and account type from the filename
- Creates accounts and imports transactions — deduplicates on re-import
- Rebuilds holdings and tracks net worth over time
- Fetches live prices via Yahoo Finance (stocks) and CoinGecko (crypto)

No configuration, no column mapping, no manual setup. Just drop files in.

## Quick start

```bash
# First time
uv venv --python 3.12 .venv
source .venv/bin/activate
uv pip install -r backend/requirements.txt
cd frontend && bun install && bun run build && cd ..

# Run
./start.sh
```

Backend runs on `localhost:8000`, frontend dev server on `localhost:5173`.

After building the frontend (`bun run build` in `frontend/`), the backend serves the full app at `localhost:8000`.

## Project layout

```
backend/           FastAPI + SQLAlchemy + SQLite
  importers/       Smart CSV analyzer + auto-ingest engine
  routers/         API endpoints
  watchers/        Watch folder file detection
frontend/          Vite + React 18 + TypeScript + Recharts
data/              SQLite DB + watch folder for file drops
  watch/           Drop CSV/Excel files here
  watch/processed/ Ingested files get moved here
docs/              ADRs and documentation
```

## Stack

- **Backend:** Python 3.12, FastAPI, SQLAlchemy, SQLite
- **Frontend:** Vite, React 18, TypeScript, Recharts
- **Prices:** Yahoo Finance (stocks), CoinGecko (crypto)
- **File watch:** watchdog

## Pages

- **Dashboard** — Net worth, allocation chart, account cards
- **Accounts** — List and drill into holdings
- **Import** — Drag-and-drop upload (also works via watch folder)
- **Real Estate** — Property tracking with Zillow estimates
- **Projections** — Growth scenarios (conservative/moderate/aggressive)
- **Insights** — Concentration risk, allocation drift, liquidity, LTV
- **Settings** — Manage accounts, preferences, refresh prices
