from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import base64
import json
import os

from ..database import get_db
from ..models import Setting
from ..services.encryption import (
    derive_passphrase_key,
    init_keychain_key,
    set_active_key,
)

router = APIRouter(prefix="/api/settings", tags=["settings"])


class SettingValue(BaseModel):
    value: object


class UnlockRequest(BaseModel):
    passphrase: str


KNOWN_KEYS = {
    "monthly_expenses",
    "risk_profile",
    "claude_api_key",
    "claude_model",
    "plaid_client_id",
    "plaid_secret",
    "news_api_key",
    "watch_folder_path",
    "projection_return_rates",
    "encryption_mode",
    "encryption_passphrase_set",
    "encryption_salt",
}


def _get_raw(db: Session, key: str) -> Optional[str]:
    row = db.query(Setting).filter(Setting.key == key).first()
    return row.value if row else None


def _set_raw(db: Session, key: str, value: str) -> None:
    row = db.query(Setting).filter(Setting.key == key).first()
    if row:
        row.value = value
    else:
        db.add(Setting(key=key, value=value))
    db.commit()


@router.get("")
def list_settings(db: Session = Depends(get_db)):
    settings = db.query(Setting).all()
    result = {}
    for s in settings:
        try:
            result[s.key] = json.loads(s.value)
        except (json.JSONDecodeError, TypeError):
            result[s.key] = s.value
    return result


@router.get("/{key}")
def get_setting(key: str, db: Session = Depends(get_db)):
    s = db.query(Setting).filter(Setting.key == key).first()
    if not s:
        return {"key": key, "value": None}
    try:
        return {"key": key, "value": json.loads(s.value)}
    except (json.JSONDecodeError, TypeError):
        return {"key": key, "value": s.value}


@router.put("/{key}")
def set_setting(key: str, body: SettingValue, db: Session = Depends(get_db)):
    if key == "encryption_mode":
        mode = str(body.value).strip('"')
        if mode == "keychain":
            try:
                key_bytes = init_keychain_key()
                set_active_key(key_bytes)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Keychain unavailable: {e}")
        # store mode unencrypted — needed at startup before key is loaded
        _set_raw(db, key, json.dumps(body.value))
        return {"key": key, "value": body.value}

    s = db.query(Setting).filter(Setting.key == key).first()
    serialized = json.dumps(body.value)
    if s:
        s.value = serialized
    else:
        db.add(Setting(key=key, value=serialized))
    db.commit()
    return {"key": key, "value": body.value}


@router.post("/encryption_unlock")
def encryption_unlock(body: UnlockRequest, db: Session = Depends(get_db)):
    salt_b64 = _get_raw(db, "encryption_salt")
    if salt_b64:
        salt = base64.b64decode(salt_b64.strip('"'))
    else:
        salt = os.urandom(16)
        _set_raw(db, "encryption_salt", json.dumps(base64.b64encode(salt).decode()))

    key_bytes = derive_passphrase_key(body.passphrase, salt)
    set_active_key(key_bytes)
    _set_raw(db, "encryption_passphrase_set", json.dumps(True))
    return {"ok": True}


@router.delete("/{key}")
def delete_setting(key: str, db: Session = Depends(get_db)):
    s = db.query(Setting).filter(Setting.key == key).first()
    if s:
        db.delete(s)
        db.commit()
    return {"ok": True}
