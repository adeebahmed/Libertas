# Technical Overview

This page reflects the current implementation state as of April 2026.

## Runtime topology

- Backend: FastAPI app on `:8000`
- Frontend: Vite dev server on `:5173`/`:5174`
- Database: SQLite at `data/libertas.db`
- Watch folder: `data/watch/` for auto-detected imports
- Docs: VitePress static site on GitHub Pages

Run locally:

```bash
./start.sh
```

## Frontend architecture

- React 18 + TypeScript + React Router
- Theme context with two UI themes: `onyx` and `retro`
- Major routes:
  - `/` Overview dashboard
  - `/accounts`
  - `/import`
  - `/debt`
  - `/retirement`
  - `/real-estate`
  - `/taxes`
  - `/insights`
  - `/settings`

## Backend API map

All routes are mounted under `/api`.

- `/accounts` account + institution CRUD, transactions, holdings, performance
- `/snapshots` current + historical net worth and snapshot recording
- `/imports` upload, preview, rollback
- `/watcher` watch-folder import logs and latest import event
- `/debt` debt summary, strategies, payoff chart, extra payment simulation
- `/retirement` projections and personalized plan endpoint
- `/taxes` estimate, harvesting opportunities, entity recommendations
- `/insights` deterministic rules + optional Claude chat
- `/news` cached RSS/news aggregation with refresh endpoint
- `/dashboard` overview market tape payloads for collapsed hero UX
- `/backups` local backup creation and download
- `/prices` holdings price refresh + status
- `/settings` local key-value configuration storage
- `/real-estate` property CRUD + valuation refresh
- `/integrations` optional Plaid and Sheets sync endpoints

## Data ingest model

Current ingest paths:

1. Manual account/transaction updates in-app
2. CSV/Excel uploads or watch-folder ingestion
3. Optional Plaid connection
4. Optional Google Sheets CSV feeds

Source precedence and provenance fields are used to support deterministic dedupe/merge behavior across sources.

## Security model

- Local-first storage by default
- At-rest encryption for sensitive text fields (ADR-010)
- Key modes:
  - macOS Keychain (default)
  - user passphrase (Argon2id-derived key)
- AI features are optional and key-gated

See [Security & Encryption](/security) for full details.

## ADR coverage

Architecture decisions live in [ADR Index](/adr/), including:

- Foundational app design (ADR-001)
- Multi-source ingest direction (ADR-002, ADR-009)
- Dashboard completion milestones (ADR-006)
- Encryption at rest (ADR-010)
