from __future__ import annotations

import csv
import hashlib
import io
from datetime import datetime, date
from typing import Any, Optional
from urllib.parse import urlparse

import httpx
from sqlalchemy.orm import Session

from ..models import Account, IntegrationConnection, IntegrationRun
from .source_ingest import upsert_transaction


def _validate_feed_url(url: str) -> tuple[bool, str]:
    try:
        parsed = urlparse(url)
    except Exception:
        return False, "Invalid URL"
    if parsed.scheme not in {"http", "https"}:
        return False, "URL must be http(s)"
    if "docs.google.com" in parsed.netloc and "output=csv" not in (parsed.query or ""):
        return False, "Google Sheets URLs must include output=csv"
    return True, "ok"


def _normalize_date(value: Optional[str]) -> date:
    if not value:
        return date.today()
    value = value.strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m-%d-%Y"):
        try:
            from datetime import datetime as dt

            return dt.strptime(value, fmt).date()
        except Exception:
            continue
    try:
        return datetime.fromisoformat(value).date()
    except Exception:
        return date.today()


def _normalize_amount(value: Optional[str]) -> float | None:
    if value is None:
        return None
    raw = str(value).strip().replace(",", "")
    if not raw:
        return None
    if raw.startswith("(") and raw.endswith(")"):
        raw = "-" + raw[1:-1]
    try:
        return float(raw)
    except ValueError:
        return None


async def validate_feed(url: str) -> dict[str, Any]:
    valid, msg = _validate_feed_url(url)
    if not valid:
        return {"ok": False, "error": msg}

    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.get(url)
    if r.status_code >= 400:
        return {"ok": False, "error": f"Could not fetch sheet CSV ({r.status_code})"}

    rows = list(csv.DictReader(io.StringIO(r.text)))
    if not rows:
        return {"ok": False, "error": "No rows found"}

    return {
        "ok": True,
        "headers": list(rows[0].keys()),
        "sample_rows": rows[:3],
        "row_count": len(rows),
    }


async def sync_sheets_connection(db: Session, connection: IntegrationConnection, trigger: str = "manual") -> dict[str, Any]:
    run = IntegrationRun(connection_id=connection.id, trigger=trigger, status="running", details={})
    db.add(run)
    db.flush()

    created = 0
    updated = 0
    cfg = connection.config_json or {}

    try:
        url = cfg.get("csv_url")
        account_id = cfg.get("account_id")
        if not url or not account_id:
            raise ValueError("Sheets feed requires csv_url and account_id")

        account = db.get(Account, int(account_id))
        if not account:
            raise ValueError("Bound account not found")

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url)
        if response.status_code >= 400:
            raise ValueError(f"Could not fetch sheet CSV ({response.status_code})")

        rows = list(csv.DictReader(io.StringIO(response.text)))
        mapping = cfg.get("mapping") or {}
        date_col = mapping.get("date", "date")
        amount_col = mapping.get("amount", "amount")
        type_col = mapping.get("type", "type")
        desc_col = mapping.get("description", "description")
        symbol_col = mapping.get("symbol", "symbol")
        row_id_col = mapping.get("row_id", "row_id")

        for idx, row in enumerate(rows, start=1):
            amount = _normalize_amount(row.get(amount_col))
            tx_type = (row.get(type_col) or "").strip().lower()
            if not tx_type:
                tx_type = "buy" if (amount or 0) < 0 else "sell" if (amount or 0) > 0 else "other"

            source_record_id = row.get(row_id_col)
            if not source_record_id:
                digest = hashlib.sha256(
                    f"{idx}|{row.get(date_col)}|{row.get(amount_col)}|{row.get(desc_col)}".encode()
                ).hexdigest()
                source_record_id = digest

            _, was_created, _ = upsert_transaction(
                db,
                account_id=account.id,
                tx_date=_normalize_date(row.get(date_col)),
                tx_type=tx_type,
                symbol=(row.get(symbol_col) or "").strip().upper() or None,
                quantity=_normalize_amount(row.get(mapping.get("quantity", "quantity"))),
                price=_normalize_amount(row.get(mapping.get("price", "price"))),
                amount=amount,
                description=row.get(desc_col),
                source_kind="sheets",
                source_record_id=str(source_record_id),
                raw_row=row,
            )
            if was_created:
                created += 1
            else:
                updated += 1

        connection.last_sync_at = datetime.utcnow()
        connection.last_error = None
        connection.status = "active"
        run.status = "success"
        run.details = {"created": created, "updated": updated, "rows": len(rows)}
    except Exception as exc:
        connection.status = "error"
        connection.last_error = str(exc)
        run.status = "error"
        run.details = {"error": str(exc)}
    finally:
        run.finished_at = datetime.utcnow()
        db.add(connection)
        db.add(run)
        db.commit()

    return {"status": run.status, "created": created, "updated": updated, "error": connection.last_error}


async def sync_all_sheets(db: Session, trigger: str = "scheduled") -> dict[str, Any]:
    feeds = db.query(IntegrationConnection).filter(
        IntegrationConnection.provider == "sheets",
        IntegrationConnection.status.in_(["active", "error"]),
    ).all()
    runs = []
    for feed in feeds:
        runs.append(await sync_sheets_connection(db, feed, trigger=trigger))
    return {"count": len(feeds), "runs": runs}
