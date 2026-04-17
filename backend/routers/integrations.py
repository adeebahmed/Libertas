from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Account, IntegrationConnection, IntegrationRun, Setting
from ..services.integration_scheduler import run_daily_sync_once
from ..services.integration_security import encrypt_secret
from ..services.plaid_client import PlaidClient
from ..services.plaid_sync import sync_all_plaid, sync_plaid_connection
from ..services.sheets_sync import sync_all_sheets, sync_sheets_connection, validate_feed

router = APIRouter(prefix="/api/integrations", tags=["integrations"])


def _plaid_client(db: Session) -> PlaidClient:
    import json

    def _get(key: str) -> str:
        row = db.query(Setting).get(key)
        if not row:
            return ""
        try:
            return str(json.loads(row.value))
        except Exception:
            return str(row.value)

    client_id = _get("plaid_client_id")
    secret = _get("plaid_secret")
    env = _get("plaid_env") or None
    return PlaidClient(client_id=client_id or None, secret=secret or None, env=env)


class PlaidExchangeBody(BaseModel):
    public_token: str
    name: Optional[str] = None


class PlaidLinkBody(BaseModel):
    user_id: str = "local-user"
    redirect_uri: Optional[str] = None


class PlaidConnectionBody(BaseModel):
    connection_id: Optional[int] = None


class SheetsAddBody(BaseModel):
    name: str
    csv_url: str
    account_id: int
    mapping: Optional[dict[str, str]] = None


class SheetsValidateBody(BaseModel):
    csv_url: str


class SheetsConnectionBody(BaseModel):
    connection_id: int


@router.get("/status")
def integrations_status(db: Session = Depends(get_db)):
    conns = db.query(IntegrationConnection).order_by(IntegrationConnection.created_at.desc()).all()
    latest_runs = {}
    for run in (
        db.query(IntegrationRun)
        .order_by(IntegrationRun.started_at.desc())
        .limit(200)
        .all()
    ):
        if run.connection_id not in latest_runs:
            latest_runs[run.connection_id] = run

    rows = []
    for c in conns:
        run = latest_runs.get(c.id)
        rows.append(
            {
                "id": c.id,
                "provider": c.provider,
                "name": c.name,
                "status": c.status,
                "config": c.config_json,
                "external_item_id": c.external_item_id,
                "last_sync_at": c.last_sync_at.isoformat() if c.last_sync_at else None,
                "last_error": c.last_error,
                "last_run": {
                    "status": run.status,
                    "trigger": run.trigger,
                    "started_at": run.started_at.isoformat() if run and run.started_at else None,
                    "finished_at": run.finished_at.isoformat() if run and run.finished_at else None,
                    "details": run.details,
                }
                if run
                else None,
            }
        )
    return {"connections": rows}


@router.post("/sync/daily")
async def trigger_daily_sync():
    return await run_daily_sync_once(trigger="manual")


@router.post("/plaid/create-link-token")
async def plaid_create_link_token(body: PlaidLinkBody, db: Session = Depends(get_db)):
    try:
        client = _plaid_client(db)
        data = await client.create_link_token(user_id=body.user_id, redirect_uri=body.redirect_uri)
    except Exception as exc:
        raise HTTPException(400, str(exc))
    return {"link_token": data.get("link_token"), "expiration": data.get("expiration")}


@router.post("/plaid/exchange-public-token")
async def plaid_exchange_public_token(body: PlaidExchangeBody, db: Session = Depends(get_db)):
    try:
        client = _plaid_client(db)
        payload = await client.exchange_public_token(body.public_token)
    except Exception as exc:
        raise HTTPException(400, str(exc))

    access_token = payload.get("access_token")
    item_id = payload.get("item_id")
    if not access_token:
        raise HTTPException(400, "Plaid exchange did not return access_token")

    connection = IntegrationConnection(
        provider="plaid",
        name=body.name or f"Plaid {item_id or datetime.utcnow().date().isoformat()}",
        status="active",
        encrypted_secret=encrypt_secret(access_token),
        external_item_id=item_id,
        config_json={"products": ["transactions", "liabilities"]},
    )
    db.add(connection)
    db.commit()
    db.refresh(connection)

    return {
        "id": connection.id,
        "provider": connection.provider,
        "status": connection.status,
        "item_id": item_id,
    }


@router.post("/plaid/sync-now")
async def plaid_sync_now(body: Optional[PlaidConnectionBody] = None, db: Session = Depends(get_db)):
    if body and body.connection_id:
        conn = db.get(IntegrationConnection, body.connection_id)
        if not conn or conn.provider != "plaid":
            raise HTTPException(404, "Plaid connection not found")
        return await sync_plaid_connection(db, conn, trigger="manual")

    return await sync_all_plaid(db, trigger="manual")


@router.get("/plaid/status")
def plaid_status(db: Session = Depends(get_db)):
    conns = db.query(IntegrationConnection).filter(IntegrationConnection.provider == "plaid").all()
    return {
        "connections": [
            {
                "id": c.id,
                "name": c.name,
                "status": c.status,
                "external_item_id": c.external_item_id,
                "last_sync_at": c.last_sync_at.isoformat() if c.last_sync_at else None,
                "last_error": c.last_error,
            }
            for c in conns
        ]
    }


@router.post("/plaid/relink")
def plaid_relink(body: PlaidConnectionBody, db: Session = Depends(get_db)):
    if not body.connection_id:
        raise HTTPException(400, "connection_id is required")
    conn = db.get(IntegrationConnection, body.connection_id)
    if not conn or conn.provider != "plaid":
        raise HTTPException(404, "Plaid connection not found")
    conn.status = "relink_required"
    conn.last_error = "Relink requested by user"
    db.add(conn)
    db.commit()
    return {"ok": True, "id": conn.id, "status": conn.status}


@router.post("/plaid/disconnect")
def plaid_disconnect(body: PlaidConnectionBody, db: Session = Depends(get_db)):
    if not body.connection_id:
        raise HTTPException(400, "connection_id is required")
    conn = db.get(IntegrationConnection, body.connection_id)
    if not conn or conn.provider != "plaid":
        raise HTTPException(404, "Plaid connection not found")
    conn.status = "disabled"
    conn.encrypted_secret = None
    conn.last_error = None
    db.add(conn)
    db.commit()
    return {"ok": True, "id": conn.id, "status": conn.status}


@router.post("/sheets/validate-feed")
async def sheets_validate_feed(body: SheetsValidateBody):
    result = await validate_feed(body.csv_url)
    if not result.get("ok"):
        raise HTTPException(400, result.get("error", "Could not validate feed"))
    return result


@router.post("/sheets/add-feed")
def sheets_add_feed(body: SheetsAddBody, db: Session = Depends(get_db)):
    # Validate URL up-front for clearer user feedback.
    # Network validation stays in /validate-feed to keep this endpoint quick.
    if not body.csv_url.startswith("http://") and not body.csv_url.startswith("https://"):
        raise HTTPException(400, "CSV URL must start with http:// or https://")
    if "docs.google.com" in body.csv_url and "output=csv" not in body.csv_url:
        raise HTTPException(400, "Google Sheets URL must include output=csv")

    account = db.get(Account, body.account_id)
    if not account:
        raise HTTPException(404, "Bound account not found")

    feed = IntegrationConnection(
        provider="sheets",
        name=body.name,
        status="active",
        config_json={
            "csv_url": body.csv_url,
            "account_id": body.account_id,
            "mapping": body.mapping or {},
        },
    )
    db.add(feed)
    db.commit()
    db.refresh(feed)
    return {
        "id": feed.id,
        "provider": feed.provider,
        "status": feed.status,
    }


@router.post("/sheets/sync-now")
async def sheets_sync_now(body: Optional[SheetsConnectionBody] = None, db: Session = Depends(get_db)):
    if body and body.connection_id:
        feed = db.get(IntegrationConnection, body.connection_id)
        if not feed or feed.provider != "sheets":
            raise HTTPException(404, "Sheets feed not found")
        return await sync_sheets_connection(db, feed, trigger="manual")

    return await sync_all_sheets(db, trigger="manual")


@router.post("/sheets/disable-feed")
def sheets_disable_feed(body: SheetsConnectionBody, db: Session = Depends(get_db)):
    feed = db.get(IntegrationConnection, body.connection_id)
    if not feed or feed.provider != "sheets":
        raise HTTPException(404, "Sheets feed not found")
    feed.status = "disabled"
    db.add(feed)
    db.commit()
    return {"ok": True, "id": feed.id, "status": feed.status}


@router.get("/sheets/status")
def sheets_status(db: Session = Depends(get_db)):
    feeds = db.query(IntegrationConnection).filter(IntegrationConnection.provider == "sheets").all()
    return {
        "feeds": [
            {
                "id": f.id,
                "name": f.name,
                "status": f.status,
                "config": f.config_json,
                "last_sync_at": f.last_sync_at.isoformat() if f.last_sync_at else None,
                "last_error": f.last_error,
            }
            for f in feeds
        ]
    }
