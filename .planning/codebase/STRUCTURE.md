# Codebase Structure

**Analysis Date:** 2026-04-11

## Directory Layout

```
/Libertas (root)
├── backend/                    # Python FastAPI backend
│   ├── main.py                 # FastAPI app entry point, router registration, startup
│   ├── database.py             # SQLAlchemy setup, session factory, migrations
│   ├── models.py               # ORM table definitions (Account, Holding, etc.)
│   ├── ai.py                   # Claude API integration for insights chat (optional)
│   ├── routers/                # REST endpoint handlers organized by domain
│   │   ├── accounts.py         # GET/POST/PATCH accounts + institutions CRUD
│   │   ├── imports.py          # POST /upload, preview, rollback for CSV ingestion
│   │   ├── prices.py           # POST /refresh (yfinance + CoinGecko), symbol mapping
│   │   ├── snapshots.py        # POST /record, GET /net-worth, GET /current (balance history)
│   │   ├── insights.py         # GET /list (rule-based insights engine)
│   │   ├── real_estate.py      # CRUD for properties, Zillow scraping, manual valuation
│   │   ├── settings.py         # GET/POST user preferences (expenses, risk profile, API keys)
│   │   ├── projections.py      # GET scenarios (future net worth)
│   │   ├── retirement.py       # FIRE calculations (savings rate, FI number, etc.)
│   │   ├── debt.py             # Debt account tracking, interest/minimum payment
│   │   ├── taxes.py            # Tax optimization insights, gain harvesting
│   │   ├── news.py             # GET /list (dual-source: RSS + NewsAPI)
│   │   ├── watcher.py          # Folder watcher status, file processing logs
│   │   ├── backups.py          # JSON export, versioned backup management
│   │   └── __init__.py
│   ├── importers/              # CSV/Excel ingestion pipeline
│   │   ├── ingest.py           # Main ingest_file() orchestrator, holding rebuild, snapshots
│   │   ├── analyzer.py         # Column auto-detection, field type inference
│   │   ├── filename_parser.py  # Institution + account type extraction from filename
│   │   └── __init__.py
│   ├── watchers/               # File system monitoring
│   │   ├── folder_watcher.py   # Watchdog-based /data/watch/ monitor, auto-ingest trigger
│   │   └── __init__.py
│   ├── requirements.txt        # Python dependencies (fastapi, uvicorn, sqlalchemy, etc.)
│   └── __pycache__
│
├── frontend/                   # Vite + React 18 TypeScript SPA
│   ├── src/
│   │   ├── main.tsx            # React entry point (ReactDOM.createRoot)
│   │   ├── App.tsx             # Root component, React Router, sidebar nav
│   │   ├── index.css           # Global styles, CSS variables (--text, --bg, --border, etc.)
│   │   ├── pages/              # Page components (one file per route)
│   │   │   ├── Dashboard.tsx   # Hero net worth, allocation pie, history chart, news feed
│   │   │   ├── Accounts.tsx    # List all accounts with balances, click-in holdings
│   │   │   ├── Import.tsx      # Drag-drop CSV, institution selector, column mapping preview
│   │   │   ├── RealEstate.tsx  # Property cards, Zillow estimate, equity chart
│   │   │   ├── Retirement.tsx  # FIRE goals, savings rate, projection curves
│   │   │   ├── Debt.tsx        # Debt balance, interest rate, payoff plan
│   │   │   ├── Taxes.tsx       # Tax lot tracking, gain harvesting, asset location
│   │   │   ├── Insights.tsx    # Insight card grid, optional Claude chat
│   │   │   └── Settings.tsx    # Institution config, account mgmt, watch folder, preferences
│   │   ├── api/
│   │   │   └── client.ts       # Typed fetch wrapper (api.get, api.post, api.upload)
│   │   ├── hooks/
│   │   │   └── useApi.ts       # Custom hook for data fetching + loading/error states
│   │   ├── components/         # Reusable UI components
│   │   │   └── Icons.tsx       # SVG icon set (Grid, Wallet, TrendDown, etc.)
│   │   ├── types/
│   │   │   └── index.ts        # TypeScript interfaces (Account, Holding, NetWorth, etc.)
│   │   └── vite-env.d.ts       # Vite environment type definitions
│   ├── vite.config.ts          # Vite config (React plugin, dev proxy to :8000)
│   ├── tsconfig.json           # TypeScript config
│   ├── package.json            # Node dependencies (react, react-router-dom, recharts, etc.)
│   ├── bun.lock                # Bun package lock
│   ├── dist/                   # Built output (generated, not committed)
│   └── node_modules/           # Dependencies (not committed)
│
├── docs/                       # VitePress documentation site
│   ├── index.md                # Landing page with feature overview
│   ├── adr/                    # Architectural Decision Records
│   │   ├── 001-finance-dashboard-design.md    # Founding spec, tech stack, pages
│   │   ├── 002-data-ingestion-strategy.md     # Multi-source support (CSV, manual, Plaid)
│   │   ├── 003-news-feed.md                   # RSS + NewsAPI dual-source
│   │   ├── 004-user-profile-and-ai-guidance.md
│   │   ├── 005-versioned-backups.md
│   │   └── 002-taxes-page.md                  # Tax lot tracking, harvesting
│   ├── guide/                  # User documentation
│   │   ├── getting-started.md
│   │   ├── importing-data.md
│   │   ├── real-estate.md
│   │   ├── insights.md
│   │   └── projections.md
│   ├── reference/              # Reference docs
│   │   ├── accounts.md
│   │   └── faq.md
│   └── .vitepress/
│       └── config.ts           # VitePress theme and site config
│
├── data/                       # Local data and watch folder
│   ├── libertas.db             # SQLite database (all user data, generated on first run)
│   ├── watch/                  # Drop exported CSVs here for auto-import
│   │   └── processed/          # Auto-archive of imported files
│   └── backups/                # Versioned JSON backups of full database export
│
├── .github/
│   └── workflows/
│       └── docs.yml            # GitHub Actions: build VitePress and deploy to Pages
│
├── .planning/                  # GSD planning documents
│   └── codebase/               # Architecture, structure, conventions, concerns
│       ├── ARCHITECTURE.md     # System design, layers, data flow
│       ├── STRUCTURE.md        # Directory layout (this file)
│       ├── CONVENTIONS.md      # Coding style, naming, patterns
│       └── CONCERNS.md         # Technical debt, fragile areas
│
├── .superpowers/               # Superpowers agent work (phase plans, specs)
├── .codex/                     # Codex cache (build artifacts)
├── .claude/                    # Claude memory for persistence
├── .venv/                      # Python virtual environment (git-ignored)
├── memory/                     # User memory index for conversation persistence
│
├── CLAUDE.md                   # Project instructions, stack, design decisions
├── AGENTS.md                   # Agent runtime notes, known issues
├── README.md                   # Public readme
├── start.sh                    # Dev launcher: starts backend (:8000) + frontend (:5173) concurrently
├── start-docs.sh               # VitePress dev server launcher
├── .env                        # Environment secrets (NEWS_API_KEY, CLAUDE_API_KEY, gitignored)
├── .env.example                # Template showing required env vars
├── .gitignore                  # Ignores .env, .venv, node_modules, *.db
└── README.md                   # Project overview
```

## Directory Purposes

**`backend/`:**
- Purpose: FastAPI REST API server
- Contains: Route handlers, ORM models, database setup, importers, file watcher
- Key files: `main.py` (entry point), `models.py` (schema), `database.py` (setup)
- Runs on: localhost:8000

**`frontend/src/`:**
- Purpose: React SPA source code
- Contains: Pages, components, hooks, API client, TypeScript types
- Key structure: `pages/` (one file per route), `api/` (fetch wrapper), `components/` (UI kit)
- Runs on: localhost:5173 (dev) or served by backend (prod)

**`routers/`:**
- Purpose: Organize REST endpoints by domain
- Pattern: One Python file per router (accounts.py, imports.py, prices.py, etc.)
- Each router has a FastAPI `APIRouter` with prefix (e.g., `/api/accounts`)
- Routers included in `main.py:app.include_router()`

**`importers/`:**
- Purpose: CSV/Excel ingestion pipeline
- Files:
  - `ingest.py`: Main orchestrator (read file → analyze → map → import transactions → rebuild holdings)
  - `analyzer.py`: Auto-detect column roles (Date, Symbol, Quantity, Price, etc.)
  - `filename_parser.py`: Extract institution name and account type from filename
- Used by: Folder watcher and `/api/imports/upload` route

**`watchers/`:**
- Purpose: Background file system monitoring
- Files: `folder_watcher.py` (watchdog-based monitor of `/data/watch/`)
- Lifecycle: Started on app startup, runs in background thread

**`pages/` (frontend):**
- Pattern: One TypeScript file per route
- Each page is a React component exported as default
- Pages use `useApi()` hook for data fetching
- Routed in `App.tsx` via React Router

**`data/`:**
- Purpose: Local data storage
- `libertas.db`: SQLite database (all financial data)
- `watch/`: Drop exported CSVs here for auto-import
- `watch/processed/`: Archive of successfully imported files
- `backups/`: Versioned JSON exports of entire database

**`docs/`:**
- Purpose: VitePress documentation site (deployed to GitHub Pages)
- Structure: ADRs in `adr/`, user guides in `guide/`, reference in `reference/`
- Built and deployed via GitHub Actions on push to `main`
- Public URL: `https://<username>.github.io/libertas`

**`.planning/codebase/`:**
- Purpose: GSD codebase mapping documents
- Contains: ARCHITECTURE.md, STRUCTURE.md, CONVENTIONS.md, CONCERNS.md
- Updated by: GSD agents when exploring the codebase

## Key File Locations

**Entry Points:**
- `backend/main.py`: FastAPI app initialization, router registration, startup hooks
- `frontend/src/main.tsx`: React root mount point
- `frontend/src/App.tsx`: Route definitions and sidebar navigation
- `./start.sh`: Development launcher script

**Configuration:**
- `CLAUDE.md`: Project instructions, design decisions, stack overview
- `AGENTS.md`: Agent runtime notes and known issues
- `backend/requirements.txt`: Python dependencies
- `frontend/vite.config.ts`: Vite dev server config (API proxy)
- `frontend/tsconfig.json`: TypeScript configuration

**Core Logic:**
- `backend/models.py`: ORM definitions for all tables (10 models)
- `backend/database.py`: SQLite engine setup, session factory, migrations
- `backend/importers/ingest.py`: CSV ingestion orchestrator
- `backend/routers/snapshots.py`: Balance snapshot calculation and history
- `backend/routers/insights.py`: Rule-based insight generation engine

**Testing:**
- No test files present in codebase (untested currently)

## Naming Conventions

**Files:**

**Backend:**
- Route handlers: `snake_case.py` (e.g., `accounts.py`, `real_estate.py`)
- Modules: `snake_case.py` (e.g., `ingest.py`, `analyzer.py`)
- ORM models: PascalCase class names (e.g., `Account`, `Holding`)

**Frontend:**
- Page components: PascalCase.tsx (e.g., `Dashboard.tsx`, `RealEstate.tsx`)
- Reusable components: PascalCase.tsx
- Hooks: `use{Name}.ts` (e.g., `useApi.ts`)
- Types: `index.ts` in types folder
- API: `client.ts`
- Icons: `Icons.tsx`

**Directories:**

**Backend:**
- Feature routers: `/routers/` (grouped by domain, not by HTTP method)
- Ingestion: `/importers/` (column analysis, filename parsing, transaction import)
- Background tasks: `/watchers/` (file system monitoring)

**Frontend:**
- Pages: `/pages/` (one file per route)
- UI: `/components/` (reusable, no page-specific logic)
- Data fetching: `/hooks/`, `/api/`
- Type definitions: `/types/`

## Where to Add New Code

**New Feature (Page):**
- Create `/frontend/src/pages/MyFeature.tsx` with React component
- Add route in `/frontend/src/App.tsx` (Routes section)
- Add nav item in `/frontend/src/App.tsx` (NAV array)
- Create corresponding backend router at `/backend/routers/my_feature.py`
- Include router in `/backend/main.py:app.include_router()`

**New API Endpoint:**
- Add function to existing router in `/backend/routers/[domain].py`
- Use `@router.get()`, `@router.post()`, etc. with appropriate prefix
- Define Pydantic request model if POST/PATCH body needed
- Depends on: `db: Session = Depends(get_db)` for database access
- Call from frontend with: `api.get('/api/[domain]/[endpoint')`

**New Database Model:**
- Add class in `/backend/models.py` extending `Base`
- Define columns and relationships
- If adding new table, update any migrations in `/backend/database.py:_apply_sqlite_migrations()`

**New Component:**
- Create `/frontend/src/components/MyComponent.tsx`
- Use TypeScript and follow Recharts/React patterns from existing components
- Import in page component and use like any React component

**New Utility Function (Backend):**
- Backend utilities live alongside routers or in `/backend/importers/`
- Example: Column analysis in `importers/analyzer.py`
- Import and call from routers or watchers

**New Utility Function (Frontend):**
- Shared helpers in `/frontend/src/hooks/` if data-fetching related
- Otherwise as standalone `.ts` file in `/frontend/src/`
- Import and use in components/pages

## Special Directories

**`./data/watch/`:**
- Purpose: Auto-import folder for CSVs
- User behavior: Export CSV from institution, save to `data/watch/`, file auto-detected
- Folder watcher: Monitors for new files, auto-ingests, moves to `processed/`
- Generated: Yes (created on first file drop)
- Committed: No (.gitignore excludes `data/`)

**`./data/watch/processed/`:**
- Purpose: Archive of imported files
- Auto-created by folder watcher after successful import
- Files named: `[original_filename]` or `[original]_[timestamp].[ext]` if collision
- Committed: No

**`.planning/codebase/`:**
- Purpose: GSD mapping documents (architecture, structure, conventions, concerns)
- Generated: By GSD agents during analysis
- Committed: Yes (for team reference)
- Not user-facing

**`.superpowers/`:**
- Purpose: Superpowers agent working directory (phase plans, specs)
- Generated: By Superpowers agents during planning
- Committed: Varies (implementation plans should be committed)

**`.github/workflows/`:**
- Purpose: GitHub Actions automation
- `docs.yml`: Builds VitePress and deploys to GitHub Pages on push to `main`
- Committed: Yes

**`.venv/`:**
- Purpose: Python virtual environment
- Created: By `./start.sh` if missing (using `uv venv`)
- Committed: No (.gitignore)

**`node_modules/`:**
- Purpose: Node package dependencies
- Created: By `bun install` if missing (or `npm install`)
- Committed: No (.gitignore)

## Frontend File Organization Rationale

The frontend is organized by **feature (pages) and components (UI)**, not by architecture layer:

- `pages/`: Each page maps to a route. Full responsibility for that route's logic and data fetching
- `components/`: Reusable across multiple pages. No page-specific business logic
- `hooks/`: Data fetching and state management helpers
- `api/`: Thin wrapper around fetch, centralized endpoint access
- `types/`: Shared TypeScript interfaces

This avoids deep folder nesting and makes it easy to find "where does Dashboard live?" (`pages/Dashboard.tsx`).

## Backend File Organization Rationale

The backend is organized by **domain** (routers) and **function** (importers, watchers):

- `routers/`: REST endpoints grouped by entity (accounts, imports, prices, etc.)
- `importers/`: CSV ingestion pipeline (separate because it's multi-step and reused)
- `watchers/`: Background tasks (separate because they're async and lifecycle-managed)
- `models.py`: All ORM definitions in one file for quick navigation
- `database.py`: Connection and setup in one place

This keeps related endpoints together (accounts + institutions in same file) and complex processes isolated (ingest pipeline in importers/).

---

*Structure analysis: 2026-04-11*
