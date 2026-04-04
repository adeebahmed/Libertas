from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import ImportLog

router = APIRouter(prefix="/api/watcher", tags=["watcher"])


@router.get("/log")
def import_log(limit: int = 50, db: Session = Depends(get_db)):
    logs = (
        db.query(ImportLog)
        .order_by(ImportLog.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": l.id,
            "filename": l.filename,
            "institution_name": l.institution_name,
            "account_id": l.account_id,
            "rows_imported": l.rows_imported,
            "rows_skipped": l.rows_skipped,
            "status": l.status,
            "error_message": l.error_message,
            "created_at": l.created_at.isoformat() if l.created_at else None,
        }
        for l in logs
    ]
