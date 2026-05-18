from __future__ import annotations

import logging
from typing import Any, Optional

import keyring
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import IntegrationConnection, IntegrationRun
from ..services.ofx_sync import sync_all_ofx, sync_ofx_connection

router = APIRouter(prefix="/api/ofx", tags=["ofx"])
logger = logging.getLogger(__name__)


class OFXConnectionCreate(BaseModel):
    name: str
    url: str
    fi_id: str
    org: str
    account_number: str
    account_type: str
    is_investment: bool = False
    broker_id: Optional[str] = None
    account_id: int
    username: str
    password: str


class OFXSyncBody(BaseModel):
    connection_id: Optional[int] = None


def _serialize_connection(conn: IntegrationConnection, latest_run: Optional[IntegrationRun]) -> dict[str, Any]:
    cfg = conn.config_json or {}
    return {
        "id": conn.id,
        "name": conn.name,
        "provider": conn.provider,
        "status": conn.status,
        "account_id": cfg.get("account_id"),
        "fi_id": cfg.get("fi_id"),
        "org": cfg.get("org"),
        "account_number": cfg.get("account_number"),
        "account_type": cfg.get("account_type"),
        "is_investment": cfg.get("is_investment", False),
        "last_sync_at": conn.last_sync_at.isoformat() if conn.last_sync_at else None,
        "last_error": conn.last_error,
        "last_run": {
            "status": latest_run.status,
            "trigger": latest_run.trigger,
            "started_at": latest_run.started_at.isoformat() if latest_run.started_at else None,
            "finished_at": latest_run.finished_at.isoformat() if latest_run.finished_at else None,
            "details": latest_run.details,
        } if latest_run else None,
    }


def _latest_run(db: Session, connection_id: int) -> Optional[IntegrationRun]:
    return (
        db.query(IntegrationRun)
        .filter(IntegrationRun.connection_id == connection_id)
        .order_by(IntegrationRun.started_at.desc())
        .first()
    )


@router.get("/connections")
def list_ofx_connections(db: Session = Depends(get_db)):
    conns = db.query(IntegrationConnection).filter(IntegrationConnection.provider == "ofx").all()
    return [_serialize_connection(c, _latest_run(db, c.id)) for c in conns]


@router.post("/connections")
def add_ofx_connection(body: OFXConnectionCreate, db: Session = Depends(get_db)):
    keychain_service = f"libertas-ofx-{body.fi_id}-{body.account_number}"
    keyring.set_password(keychain_service, body.username, body.password)

    conn = IntegrationConnection(
        provider="ofx",
        name=body.name,
        status="active",
        config_json={
            "url": body.url,
            "fi_id": body.fi_id,
            "org": body.org,
            "account_number": body.account_number,
            "account_type": body.account_type,
            "is_investment": body.is_investment,
            "broker_id": body.broker_id,
            "account_id": body.account_id,
            "username": body.username,
            "keychain_service": keychain_service,
        },
    )
    db.add(conn)
    db.commit()
    db.refresh(conn)
    return _serialize_connection(conn, None)


@router.delete("/connections/{connection_id}")
def delete_ofx_connection(connection_id: int, db: Session = Depends(get_db)):
    conn = db.query(IntegrationConnection).filter(IntegrationConnection.id == connection_id).first()
    if not conn or conn.provider != "ofx":
        raise HTTPException(404, "OFX connection not found")
    cfg = conn.config_json or {}
    try:
        keyring.delete_password(cfg.get("keychain_service", ""), cfg.get("username", "ofx"))
    except Exception:
        pass
    db.delete(conn)
    db.commit()
    return {"ok": True}


@router.post("/sync")
async def sync_now(body: Optional[OFXSyncBody] = None, db: Session = Depends(get_db)):
    if body and body.connection_id:
        conn = db.query(IntegrationConnection).filter(IntegrationConnection.id == body.connection_id).first()
        if not conn or conn.provider != "ofx":
            raise HTTPException(404, "OFX connection not found")
        result = sync_ofx_connection(db, conn, trigger="manual")
        db.commit()
        return result
    return await sync_all_ofx(db, trigger="manual")


@router.get("/status")
def ofx_status(db: Session = Depends(get_db)):
    conns = db.query(IntegrationConnection).filter(IntegrationConnection.provider == "ofx").all()
    return {"connections": [_serialize_connection(c, _latest_run(db, c.id)) for c in conns]}
