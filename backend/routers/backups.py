from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..database import DB_PATH, get_db
from ..models import Account, Backup, Institution, NewsCache, QuoteCache, Setting

router = APIRouter(prefix="/api/backups", tags=["backups"])

BACKUP_DIR = Path(__file__).parent.parent.parent / "data" / "backups"


def _safe_parse_setting(raw: str | None):
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except Exception:
        return raw


@router.get("")
def list_backups(db: Session = Depends(get_db)):
    backups = db.query(Backup).order_by(Backup.created_at.desc()).limit(20).all()
    return [
        {
            "id": b.id,
            "filename": b.filename,
            "size_bytes": b.size_bytes,
            "created_at": b.created_at.isoformat() if b.created_at else None,
        }
        for b in backups
    ]


@router.post("")
def create_backup(db: Session = Depends(get_db)):
    """Create a JSON backup + SQLite snapshot (includes caches)."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    accounts = db.query(Account).all()
    institutions = db.query(Institution).all()
    settings = db.query(Setting).all()
    news_cache = db.query(NewsCache).order_by(NewsCache.fetched_at.desc()).limit(2000).all()
    quote_cache = db.query(QuoteCache).all()

    data = {
        "created_at": datetime.utcnow().isoformat(),
        "version": "1",
        "institutions": [
            {
                "id": i.id, "name": i.name, "export_url": i.export_url,
                "file_pattern": i.file_pattern, "column_mapping": i.column_mapping,
                "importer_preset": i.importer_preset, "notes": i.notes,
            }
            for i in institutions
        ],
        "accounts": [
            {
                "id": a.id, "name": a.name, "type": a.type,
                "institution_id": a.institution_id, "currency": a.currency,
            }
            for a in accounts
        ],
        "settings": {s.key: _safe_parse_setting(s.value) for s in settings},
        "cache": {
            "news": [
                {
                    "id": n.id,
                    "source": n.source,
                    "title": n.title,
                    "url": n.url,
                    "published_at": n.published_at.isoformat() if n.published_at else None,
                    "fetched_at": n.fetched_at.isoformat() if n.fetched_at else None,
                    "summary": n.summary,
                    "category": n.category,
                }
                for n in news_cache
            ],
            "quotes": [
                {
                    "symbol": q.symbol,
                    "price": q.price,
                    "day_change_pct": q.day_change_pct,
                    "source": q.source,
                    "fetched_at": q.fetched_at.isoformat() if q.fetched_at else None,
                    "expires_at": q.expires_at.isoformat() if q.expires_at else None,
                }
                for q in quote_cache
            ],
        },
    }

    filename = f"libertas-backup-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.json"
    filepath = BACKUP_DIR / filename
    content = json.dumps(data, indent=2)
    filepath.write_text(content)

    # DB-level snapshot backup so the full SQLite state persists and is recoverable.
    sqlite_filename = f"libertas-db-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.sqlite3"
    sqlite_path = BACKUP_DIR / sqlite_filename
    src = sqlite3.connect(DB_PATH)
    dst = sqlite3.connect(str(sqlite_path))
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()

    size = len(content.encode()) + (sqlite_path.stat().st_size if sqlite_path.exists() else 0)
    record = Backup(filename=filename, size_bytes=size)
    db.add(record)
    db.commit()
    db.refresh(record)

    return {"id": record.id, "filename": filename, "sqlite_filename": sqlite_filename, "size_bytes": size}


@router.get("/{backup_id}/download")
def download_backup(backup_id: int, db: Session = Depends(get_db)):
    from fastapi import HTTPException
    backup = db.query(Backup).get(backup_id)
    if not backup:
        raise HTTPException(404, "Backup not found")
    filepath = BACKUP_DIR / backup.filename
    if not filepath.exists():
        raise HTTPException(404, "Backup file missing from disk")
    return FileResponse(str(filepath), filename=backup.filename, media_type="application/json")
