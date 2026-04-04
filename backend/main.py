from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from .database import init_db
from .routers import accounts, imports, prices, real_estate, projections, snapshots, insights, settings, watcher
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
app.include_router(projections.router)
app.include_router(snapshots.router)
app.include_router(insights.router)
app.include_router(settings.router)
app.include_router(watcher.router)

WATCH_FOLDER = Path(__file__).parent.parent / "data" / "watch"


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.on_event("startup")
def on_startup():
    init_db()
    start_watcher(str(WATCH_FOLDER))
    # Mount built frontend AFTER all API routes are registered
    frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
    if frontend_dist.is_dir():
        app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")
