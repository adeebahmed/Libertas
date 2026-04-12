# Technology Stack

**Analysis Date:** 2026-04-11

## Languages

**Primary:**
- Python 3.12 - Backend API and data processing
- TypeScript 5.5.3 - Frontend application and type safety
- JavaScript - Package management and tooling

**Secondary:**
- SQL (SQLite) - Database queries and migrations
- Bash - Development scripts and automation

## Runtime

**Environment:**
- Python 3.12 - Specified in `./start.sh` via `uv venv --python 3.12`
- Node.js 24 - CI/CD (GitHub Actions deployment)
- Bun - Frontend package manager (primary runtime, installed via `bun install`)

**Package Manager:**
- Backend: `uv` - Fast Python package installer (see `./start.sh`)
- Frontend: Bun - JavaScript package manager (see `frontend/package.json`)
- Docs: npm - JavaScript packages for VitePress

## Frameworks

**Core Backend:**
- FastAPI 0.111.0 - REST API framework
- SQLAlchemy 2.0.30 - ORM for database models and queries
- Uvicorn 0.30.1 - ASGI server for FastAPI

**Frontend:**
- React 18.3.1 - UI component library
- React Router 6.23.1 - Client-side routing
- Vite 5.3.4 - Build tool and dev server
- TypeScript 5.5.3 - Static type checking

**Documentation:**
- VitePress 1.6.3 - Markdown-based documentation site

**Testing/Dev Tools:**
- @vitejs/plugin-react 4.3.1 - React integration for Vite
- @types/react 18.3.3, @types/react-dom 18.3.0 - TypeScript definitions

## Key Dependencies

**Critical Backend:**
- yfinance 0.2.40 - Stock and crypto price data fetching
- aiosqlite 0.20.0 - Async SQLite driver
- httpx 0.27.0 - Async HTTP client (for yfinance, CoinGecko, Zillow, Claude API calls)
- watchdog 4.0.1 - File system monitoring for CSV import watch folder
- beautifulsoup4 4.12.3 - HTML parsing (Zillow scraping)
- pandas 2.2.2 - Data processing and DataFrame manipulation
- feedparser 6.0.11 - RSS feed parsing for news aggregation
- openpyxl 3.1.5 - Excel file support for imports
- python-multipart 0.0.9 - Multipart form parsing for file uploads

**Frontend:**
- recharts 2.12.7 - React charts and data visualization

## Configuration

**Environment:**
- Backend environment configured via:
  - Optional `.env` file (see `backend/main.py` lines 8-12)
  - Database location: `/data/libertas.db` (SQLite)
  - Port: 8000 (FastAPI/Uvicorn)
- Frontend environment:
  - Development: Vite dev server at `localhost:5173`
  - API proxy: `/api/*` routed to `http://127.0.0.1:8000`

**Build:**
- Frontend build: TypeScript compilation then Vite bundling (`npm run build`)
  - Output: `frontend/dist/` (mounted as static files at startup)
- Backend: No build step (Python modules loaded directly)

**Database:**
- SQLite with WAL (Write-Ahead Logging) mode enabled
- Foreign key constraints enabled at connection time
- Location: `/data/libertas.db`
- Migrations: Lightweight approach in `backend/database.py` (check column existence before ALTER TABLE)

## Platform Requirements

**Development:**
- Python 3.12+ (via uv)
- Bun (JavaScript runtime)
- Bash shell
- curl (for health check in `./start.sh`)
- SQLite (bundled with Python)

**Production:**
- Python 3.12 runtime
- No external database server required (SQLite is embedded)
- HTTP server (Uvicorn) on port 8000
- Compiled frontend static assets served by FastAPI
- Optional: reverse proxy (nginx, etc.) for HTTPS and routing

## CI/CD & Deployment

**Documentation Deployment:**
- GitHub Actions workflow: `.github/workflows/deploy-docs.yml`
- Trigger: Push to `main` branch in `docs/` directory
- Build: VitePress build (`npm run build`)
- Deploy: GitHub Pages
- Node.js: 24 (as specified in workflow)

## Runtime Startup

**Development:**
- Execute `./start.sh` which:
  1. Ensures Python 3.12 virtualenv via `uv venv` (line 27)
  2. Installs backend dependencies via `uv pip install` (line 37)
  3. Ensures frontend node_modules via `bun install` (line 49)
  4. Starts Uvicorn backend at `127.0.0.1:8000` (line 66)
  5. Starts Vite dev server via `bun run dev` at port 5173+ (line 98)
  6. Verifies backend health via health check endpoint (lines 75-94)

**Production:**
- Compile frontend: `npm run build --prefix frontend`
- Run Uvicorn: `python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000`
- Static assets served from `frontend/dist/` mounted to `/` in FastAPI

---

*Stack analysis: 2026-04-11*
