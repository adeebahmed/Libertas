from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import keyring
from sqlalchemy.orm import Session

from ..models import Account, IntegrationConnection, IntegrationRun
from .ofx_client import OFXConnectionConfig, fetch_ofx_statement
from .source_ingest import upsert_transaction

logger = logging.getLogger(__name__)

_OFX_TYPE_MAP: dict[str, str] = {
    "DEBIT": "debit",
    "CREDIT": "credit",
    "INT": "interest",
    "DIV": "dividend",
    "FEE": "fee",
    "SRVCHG": "fee",
    "DEP": "deposit",
    "ATM": "atm",
    "POS": "debit",
    "XFER": "transfer",
    "CHECK": "check",
    "PAYMENT": "payment",
    "CASH": "cash",
    "DIRECTDEP": "direct_deposit",
    "DIRECTDEBIT": "debit",
    "REPEATPMT": "payment",
    "OTHER": "other",
    "BUY": "buy",
    "SELL": "sell",
    "REINVEST": "reinvest",
    "INCOME": "income",
}


def _trntype_to_internal(trntype: str) -> str:
    return _OFX_TYPE_MAP.get((trntype or "").upper(), "other")


def _json_safe(obj: Any) -> Any:
    """Recursively convert non-JSON-serializable values (e.g. datetime) to strings."""
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_json_safe(v) for v in obj]
    if isinstance(obj, (datetime,)):
        return obj.isoformat()
    return obj


def sync_ofx_connection(
    db: Session,
    conn: IntegrationConnection,
    trigger: str = "manual",
    days_back: int = 90,
) -> dict[str, Any]:
    cfg_json = conn.config_json or {}
    account_id: int | None = cfg_json.get("account_id")
    keychain_service: str = cfg_json.get("keychain_service", f"libertas-ofx-{conn.id}")

    run = IntegrationRun(
        connection_id=conn.id,
        trigger=trigger,
        status="running",
    )
    db.add(run)
    db.flush()

    def _fail(msg: str) -> dict[str, Any]:
        run.status = "error"
        run.details = {"error": msg}
        run.finished_at = datetime.utcnow()
        conn.status = "error"
        conn.last_error = msg
        db.flush()
        logger.warning("OFX sync failed for connection %s: %s", conn.id, msg)
        return {"status": "error", "error": msg, "connection_id": conn.id}

    if not account_id:
        return _fail("No account_id configured for OFX connection")
    account = db.get(Account, account_id)
    if not account:
        return _fail(f"Linked account {account_id} not found")

    username = cfg_json.get("username")
    password = keyring.get_password(keychain_service, username or "ofx")
    if not password:
        return _fail(f"No credentials found in keychain for service '{keychain_service}'")

    cfg = OFXConnectionConfig(
        url=cfg_json["url"],
        fi_id=cfg_json["fi_id"],
        org=cfg_json["org"],
        account_number=cfg_json["account_number"],
        account_type=cfg_json.get("account_type", "CHECKING"),
        is_investment=cfg_json.get("is_investment", False),
        broker_id=cfg_json.get("broker_id"),
    )

    try:
        raw_txs = fetch_ofx_statement(cfg, username or "ofx", password, days_back=days_back)
    except Exception as exc:
        return _fail(f"OFX fetch failed: {exc}")

    imported = 0
    skipped = 0
    for raw in raw_txs:
        fitid = raw["fitid"]
        tx_date = raw["date"].date() if hasattr(raw["date"], "date") else raw["date"]
        tx_type = _trntype_to_internal(raw.get("trntype", "other"))
        description = raw.get("description") or raw.get("memo") or ""
        amount = raw.get("amount")

        _, created, _ = upsert_transaction(
            db,
            account_id=account_id,
            tx_date=tx_date,
            tx_type=tx_type,
            symbol=None,
            quantity=None,
            price=None,
            amount=amount,
            description=description,
            source_kind="ofx",
            external_id=fitid,
            source_record_id=fitid,
            raw_row=_json_safe(raw),
        )
        if created:
            imported += 1
        else:
            skipped += 1

    conn.last_sync_at = datetime.utcnow()
    conn.last_error = None
    conn.status = "active"
    run.status = "success"
    run.details = {"imported": imported, "skipped": skipped}
    run.finished_at = datetime.utcnow()
    db.flush()

    logger.info("OFX sync connection=%s imported=%s skipped=%s", conn.id, imported, skipped)
    return {
        "status": "success",
        "connection_id": conn.id,
        "imported": imported,
        "skipped": skipped,
    }


async def sync_all_ofx(db: Session, trigger: str = "scheduled") -> dict[str, Any]:
    conns = (
        db.query(IntegrationConnection)
        .filter(
            IntegrationConnection.provider == "ofx",
            IntegrationConnection.status.in_(["active", "error"]),
        )
        .all()
    )
    results = []
    errors = []
    for conn in conns:
        result = sync_ofx_connection(db, conn, trigger=trigger)
        results.append(result)
        if result.get("status") == "error":
            errors.append({"connection_id": conn.id, "name": conn.name, "error": result["error"]})
    db.commit()
    return {"synced": len(results), "errors": errors, "results": results}
