from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import asyncio

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
except ImportError:
    pass

from .database import init_db, SessionLocal
from .routers import accounts, imports, prices, real_estate, snapshots, insights, settings, watcher, debt
from .routers import retirement, taxes, news, backups
from .routers.prices import refresh_prices
from .routers.snapshots import record_snapshots
from .watchers.folder_watcher import start_watcher

app = FastAPI(title="Libertas", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(accounts.router)
app.include_router(imports.router)
app.include_router(prices.router)
app.include_router(real_estate.router)
app.include_router(retirement.router)
app.include_router(snapshots.router)
app.include_router(insights.router)
app.include_router(settings.router)
app.include_router(watcher.router)
app.include_router(debt.router)
app.include_router(taxes.router)
app.include_router(news.router)
app.include_router(backups.router)

WATCH_FOLDER = Path(__file__).parent.parent / "data" / "watch"


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.on_event("startup")
async def on_startup():
    init_db()
    start_watcher(str(WATCH_FOLDER))
    # Mount built frontend AFTER all API routes are registered
    frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
    if frontend_dist.is_dir():
        app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")
    # Refresh prices and snapshot after startup ingest (runs in background)
    asyncio.ensure_future(_post_startup_refresh())


async def _post_startup_refresh():
    """Fetch live prices and record snapshots after the server is fully up."""
    await asyncio.sleep(1)  # let the server finish starting
    db = SessionLocal()
    try:
        result = await refresh_prices(db)
        updated = result.get("updated", 0)
        if updated > 0:
            record_snapshots(db)
            import logging
            logging.getLogger(__name__).info(f"Startup price refresh: {updated} prices updated")
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Startup price refresh failed: {e}")
    finally:
        db.close()
