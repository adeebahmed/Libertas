from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
import json

from ..database import get_db
from ..models import Setting

router = APIRouter(prefix="/api/settings", tags=["settings"])


class SettingValue(BaseModel):
    value: object


KNOWN_KEYS = {
    "monthly_expenses",
    "risk_profile",
    "claude_api_key",
    "watch_folder_path",
    "projection_return_rates",
}


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
    s = db.query(Setting).get(key)
    if not s:
        return {"key": key, "value": None}
    try:
        return {"key": key, "value": json.loads(s.value)}
    except (json.JSONDecodeError, TypeError):
        return {"key": key, "value": s.value}


@router.put("/{key}")
def set_setting(key: str, body: SettingValue, db: Session = Depends(get_db)):
    s = db.query(Setting).get(key)
    serialized = json.dumps(body.value)
    if s:
        s.value = serialized
    else:
        db.add(Setting(key=key, value=serialized))
    db.commit()
    return {"key": key, "value": body.value}


@router.delete("/{key}")
def delete_setting(key: str, db: Session = Depends(get_db)):
    s = db.query(Setting).get(key)
    if s:
        db.delete(s)
        db.commit()
    return {"ok": True}
