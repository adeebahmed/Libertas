from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
import json

from ..database import get_db
from ..models import Account, Setting

router = APIRouter(prefix="/api/settings", tags=["settings"])


class SettingValue(BaseModel):
    value: object


KNOWN_KEYS = {
    "monthly_expenses",
    "risk_profile",
    "claude_api_key",
    "watch_folder_path",
    "projection_return_rates",
    "income_w2",
    "income_1099",
    "tax_filing_status",
    "birth_year",
    "retirement_age",
    "monthly_contribution",
    "retirement_target_amount",
    "fire_type",
    "monthly_income",
    "annual_lean_expenses",
    "annual_fat_expenses",
    "part_time_income",
    "onboarding_complete",
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


@router.get("/onboarding/status")
def onboarding_status(db: Session = Depends(get_db)):
    account_count = db.query(Account).count()
    onboarding_row = db.query(Setting).get("onboarding_complete")

    onboarding_complete = False
    if onboarding_row and onboarding_row.value:
        try:
            onboarding_complete = bool(json.loads(onboarding_row.value))
        except (json.JSONDecodeError, TypeError):
            onboarding_complete = str(onboarding_row.value).strip().lower() == "true"

    return {
        "has_accounts": account_count > 0,
        "account_count": account_count,
        "onboarding_complete": onboarding_complete,
        "should_run_onboarding": (account_count == 0) or (not onboarding_complete),
    }
