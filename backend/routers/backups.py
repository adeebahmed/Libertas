import json
import os
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Account, Institution, Setting, Backup

router = APIRouter(prefix="/api/backups", tags=["backups"])

BACKUP_DIR = Path(__file__).parent.parent.parent / "data" / "backups"


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
    """Create a JSON backup of accounts, institutions, and settings."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    accounts = db.query(Account).all()
    institutions = db.query(Institution).all()
    settings = db.query(Setting).all()

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
        "settings": {s.key: json.loads(s.value) if s.value else None for s in settings},
    }

    filename = f"libertas-backup-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.json"
    filepath = BACKUP_DIR / filename
    content = json.dumps(data, indent=2)
    filepath.write_text(content)

    size = len(content.encode())
    record = Backup(filename=filename, size_bytes=size)
    db.add(record)
    db.commit()
    db.refresh(record)

    return {"id": record.id, "filename": filename, "size_bytes": size}


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
