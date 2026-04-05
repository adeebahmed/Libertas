import os
import tempfile
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..importers.ingest import ingest_file, read_file
from ..importers.analyzer import auto_detect_columns
from ..models import ImportLog, Transaction, BalanceSnapshot

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
            "id": log.id,
            "status": log.status,
            "institution": log.institution_name,
            "account_id": log.account_id,
            "rows_imported": log.rows_imported,
            "rows_skipped": log.rows_skipped,
            "error": log.error_message,
        }
    finally:
        os.unlink(tmp_path)


@router.post("/{import_id}/rollback")
def rollback_import(import_id: int, db: Session = Depends(get_db)):
    """
    Rolls back a specific import: deletes all transactions tagged with this
    import_log_id, rebuilds holdings, and re-snapshots the account.
    """
    from ..importers.ingest import _rebuild_holdings, _take_snapshot

    log = db.query(ImportLog).get(import_id)
    if not log:
        raise HTTPException(404, "Import log not found")
    if log.status == "rolled_back":
        raise HTTPException(400, "Import already rolled back")

    account_id = log.account_id
    if not account_id:
        raise HTTPException(400, "Import has no associated account — nothing to roll back")

    # Delete transactions from this specific import
    deleted = (
        db.query(Transaction)
        .filter(Transaction.import_log_id == import_id)
        .delete(synchronize_session=False)
    )

    # Also delete today's snapshot (will be rebuilt)
    from datetime import date
    db.query(BalanceSnapshot).filter(
        BalanceSnapshot.account_id == account_id,
        BalanceSnapshot.date == date.today(),
    ).delete(synchronize_session=False)

    db.flush()

    # Rebuild holdings and snapshot from remaining transactions
    _rebuild_holdings(account_id, db)
    _take_snapshot(account_id, db)

    log.status = "rolled_back"
    db.commit()

    return {"ok": True, "deleted_transactions": deleted}


@router.post("/preview")
async def preview_import(file: UploadFile = File(...)):
    """Return headers + sample rows so the user can verify column detection."""
    content = await file.read()
    ext = os.path.splitext(file.filename or ".csv")[1]

    with tempfile.NamedTemporaryFile(delete=False, suffix=ext, prefix="preview_") as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        headers, rows = read_file(tmp_path)
        sample = rows[:5]
        mapping = auto_detect_columns(headers, rows) if headers else {}
        return {
            "headers": headers,
            "sample_rows": sample,
            "detected_mapping": mapping,
        }
    finally:
        os.unlink(tmp_path)
