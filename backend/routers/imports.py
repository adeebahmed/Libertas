import os
import tempfile
from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.orm import Session

from ..database import get_db
from ..importers.ingest import ingest_file

router = APIRouter(prefix="/api/imports", tags=["imports"])


@router.post("/upload")
async def upload_import(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Upload a file directly via the UI. Same smart ingest as the watch folder."""
    content = await file.read()
    ext = os.path.splitext(file.filename or ".csv")[1]

    with tempfile.NamedTemporaryFile(delete=False, suffix=ext, prefix=file.filename or "upload_") as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        log = ingest_file(tmp_path, db)
        return {
            "status": log.status,
            "institution": log.institution_name,
            "account_id": log.account_id,
            "rows_imported": log.rows_imported,
            "rows_skipped": log.rows_skipped,
            "error": log.error_message,
        }
    finally:
        os.unlink(tmp_path)
