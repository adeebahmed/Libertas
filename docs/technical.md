# Technical Docs

This section is intentionally secondary to the product experience.

If you want implementation details, architecture decisions, and engineering context, start here.

## Architecture Decision Records

- [ADR-001 — Finance Dashboard Design](/adr/001-finance-dashboard-design)
- [ADR-002 — Data Ingestion Strategy](/adr/002-data-ingestion-strategy)
- [ADR-002 — Taxes Page](/adr/002-taxes-page)
- [ADR-003 — News Feed Integration](/adr/003-news-feed)
- [ADR-004 — User Profile and AI-Powered Guidance](/adr/004-user-profile-and-ai-guidance)
- [ADR-005 — Versioned Backups and Rollback](/adr/005-versioned-backups)

## Runtime Overview

- Backend: FastAPI + SQLAlchemy + SQLite
- Frontend: Vite + React + TypeScript
- Docs: VitePress deployed via GitHub Pages
- Local run: `./start.sh`

## API Surface (High-Level)

Primary routers are mounted under `/api` and include:

- accounts
- snapshots
- imports
- watcher
- debt
- retirement
- taxes
- insights
- news
- backups
- settings
- prices
- real-estate

## Product-First Note

If you are evaluating Libertas as a user, start at the [home page](/) for value and feature overview.
