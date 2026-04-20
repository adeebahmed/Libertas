from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import asyncio
import logging
import os

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
except ImportError:
    pass

from .database import init_db, SessionLocal
from .services.encryption import load_key_on_startup
from .importers.ingest import ingest_file
from .models import Account, ImportLog
from .routers import accounts, imports, prices, real_estate, snapshots, insights, settings, watcher, debt
from .routers import retirement, taxes, news, backups
from .routers import integrations
from .routers import dashboard
from .routers.prices import refresh_prices
from .routers.snapshots import record_snapshots
from .services.integration_scheduler import daily_sync_loop
from .watchers.folder_watcher import start_watcher

app = FastAPI(title="Libertas", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
    ],
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
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
app.include_router(integrations.router)
app.include_router(dashboard.router)

WATCH_FOLDER = Path(__file__).parent.parent / "data" / "watch"
DEMO_FILENAMES = [
    "Chase_Checking_Activity_2025.csv",
    "Chase_Sapphire_CreditCard_2025.csv",
    "Coinbase_crypto_2025.csv",
    "Fidelity_Brokerage_2025.csv",
    "Fidelity_Roth_IRA_2025.csv",
    "Marcus_Savings_2025.csv",
    "Navient_StudentLoan_2025.csv",
    "ToyotaFinancial_AutoLoan_2025.csv",
    "Vanguard_401k_2025.csv",
]
logger = logging.getLogger(__name__)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.on_event("startup")
async def on_startup():
    init_db()
    _clean_stale_demo_import_errors()
    db = SessionLocal()
    try:
        load_key_on_startup(db)
        loaded = dashboard.load_quote_cache(db)
        logger.info(f"Startup quote cache load: {loaded}")
    finally:
        db.close()
    is_test = bool(os.getenv("PYTEST_CURRENT_TEST"))
    disable_watcher = os.getenv("LIBERTAS_DISABLE_WATCHER") == "1" or is_test
    disable_scheduler = os.getenv("LIBERTAS_DISABLE_INTEGRATION_SCHEDULER") == "1" or is_test
    if not disable_watcher:
        try:
            start_watcher(str(WATCH_FOLDER))
        except Exception as e:
            logger.warning(f"File watcher disabled due to startup error: {e}")
    _bootstrap_demo_data_if_empty()
    # Mount built frontend AFTER all API routes are registered
    frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
    if frontend_dist.is_dir():
        app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")
    # Refresh prices and snapshot after startup ingest (runs in background)
    asyncio.ensure_future(_post_startup_refresh())
    asyncio.ensure_future(_market_tape_refresh_loop())
    if not disable_scheduler:
        asyncio.ensure_future(daily_sync_loop())


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

        # Warm all quote cache rows (stocks + crypto) and persist into SQLite-backed cache.
        quote_cache = dashboard.refresh_quote_cache(db, only="all")
        logging.getLogger(__name__).info(f"Startup quote cache warmup: {quote_cache}")
        try:
            news._trigger_async_refresh()
        except Exception:
            pass
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Startup price refresh failed: {e}")
    finally:
        db.close()


async def _market_tape_refresh_loop():
    """
    Lightweight live-refresh loop for tape freshness.
    - Quote cache refresh cadence derives from provider rate limits.
    - News refresh remains async and lock-protected.
    """
    news_interval_seconds = int(os.getenv("LIBERTAS_NEWS_REFRESH_INTERVAL_SECONDS", "900"))
    sleep_tick_seconds = 15
    last_stock_refresh_ts = 0.0
    last_crypto_refresh_ts = 0.0
    last_news_ts = 0.0

    await asyncio.sleep(20)
    while True:
        now = asyncio.get_running_loop().time()
        db = SessionLocal()
        try:
            plan = dashboard.quote_refresh_plan(db)
            stock_interval_seconds = max(60, int(plan.get("stock_interval_seconds", 900)))
            crypto_interval_seconds = max(30, int(plan.get("crypto_interval_seconds", 60)))
        except Exception as e:
            logging.getLogger(__name__).warning(f"Quote refresh plan computation failed: {e}")
            stock_interval_seconds = 900
            crypto_interval_seconds = 60
        finally:
            db.close()

        if now - last_stock_refresh_ts >= stock_interval_seconds:
            db = SessionLocal()
            try:
                result = dashboard.refresh_quote_cache(db, only="stocks")
                logging.getLogger(__name__).info(f"Background stock quote cache refresh: {result}")
            except Exception as e:
                logging.getLogger(__name__).warning(f"Background stock quote cache refresh failed: {e}")
            finally:
                db.close()
            last_stock_refresh_ts = now

        if now - last_crypto_refresh_ts >= crypto_interval_seconds:
            db = SessionLocal()
            try:
                result = dashboard.refresh_quote_cache(db, only="crypto")
                logging.getLogger(__name__).info(f"Background crypto quote cache refresh: {result}")
            except Exception as e:
                logging.getLogger(__name__).warning(f"Background crypto quote cache refresh failed: {e}")
            finally:
                db.close()
            last_crypto_refresh_ts = now

        if now - last_news_ts >= max(news_interval_seconds, 300):
            try:
                news._trigger_async_refresh()
            except Exception as e:
                logging.getLogger(__name__).warning(f"Background news refresh trigger failed: {e}")
            last_news_ts = now

        await asyncio.sleep(sleep_tick_seconds)


def _bootstrap_demo_data_if_empty():
    """
    If the DB has no accounts, import bundled fake fixtures from watch/ or
    watch/processed/ so first-run dashboards are not blank.
    """
    db = SessionLocal()
    try:
        if db.query(Account).count() > 0:
            return

        root = Path(__file__).parent.parent
        search_dirs = [
            root / "data" / "watch",
            root / "data" / "watch" / "processed",
        ]
        imported_rows = 0
        found_files = 0

        for filename in DEMO_FILENAMES:
            for folder in search_dirs:
                candidate = folder / filename
                if candidate.is_file():
                    found_files += 1
                    log = ingest_file(str(candidate), db)
                    imported_rows += log.rows_imported or 0
                    break

        if found_files:
            logger.info(
                "Bootstrapped fake demo data on empty DB: files=%s imported_rows=%s",
                found_files,
                imported_rows,
            )
    except Exception as e:
        logger.warning(f"Demo bootstrap failed: {e}")
    finally:
        db.close()


def _clean_stale_demo_import_errors():
    """
    Remove noisy historical demo fixture errors from Import History so users
    only see actionable import failures for their own files.
    """
    db = SessionLocal()
    try:
        stale_rows = (
            db.query(ImportLog)
            .filter(
                ImportLog.status == "error",
                ImportLog.filename.in_(DEMO_FILENAMES),
                ImportLog.filepath.isnot(None),
                ImportLog.filepath.ilike("%/data/watch/%"),
            )
        )
        removed = stale_rows.count()
        if removed > 0:
            stale_rows.delete(synchronize_session=False)
            db.commit()
            logger.info("Removed %s stale demo import ENOENT log rows", removed)
    except Exception as e:
        logger.warning(f"Cleanup of stale demo import errors failed: {e}")
    finally:
        db.close()
