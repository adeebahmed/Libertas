from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from ..database import get_db
from ..models import Account, Institution, Holding, BalanceSnapshot

router = APIRouter(prefix="/api/accounts", tags=["accounts"])


class InstitutionCreate(BaseModel):
    name: str
    export_url: Optional[str] = None
    file_pattern: Optional[str] = None
    column_mapping: Optional[dict] = None
    importer_preset: str = "generic"
    notes: Optional[str] = None


class InstitutionUpdate(BaseModel):
    name: Optional[str] = None
    export_url: Optional[str] = None
    file_pattern: Optional[str] = None
    column_mapping: Optional[dict] = None
    importer_preset: Optional[str] = None
    notes: Optional[str] = None


class AccountCreate(BaseModel):
    name: str
    type: str
    institution_id: Optional[int] = None
    currency: str = "USD"


class AccountUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    institution_id: Optional[int] = None
    currency: Optional[str] = None


# --- Institutions ---

@router.get("/institutions")
def list_institutions(db: Session = Depends(get_db)):
    return db.query(Institution).all()


@router.post("/institutions")
def create_institution(data: InstitutionCreate, db: Session = Depends(get_db)):
    inst = Institution(**data.model_dump())
    db.add(inst)
    db.commit()
    db.refresh(inst)
    return inst


@router.get("/institutions/{institution_id}")
def get_institution(institution_id: int, db: Session = Depends(get_db)):
    inst = db.query(Institution).get(institution_id)
    if not inst:
        raise HTTPException(404, "Institution not found")
    return inst


@router.patch("/institutions/{institution_id}")
def update_institution(institution_id: int, data: InstitutionUpdate, db: Session = Depends(get_db)):
    inst = db.query(Institution).get(institution_id)
    if not inst:
        raise HTTPException(404, "Institution not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(inst, k, v)
    db.commit()
    db.refresh(inst)
    return inst


@router.delete("/institutions/{institution_id}")
def delete_institution(institution_id: int, db: Session = Depends(get_db)):
    inst = db.query(Institution).get(institution_id)
    if not inst:
        raise HTTPException(404, "Institution not found")
    db.delete(inst)
    db.commit()
    return {"ok": True}


# --- Accounts ---

@router.get("")
def list_accounts(db: Session = Depends(get_db)):
    accounts = db.query(Account).all()
    result = []
    for a in accounts:
        balance = sum(
            (h.last_price or 0) * (h.quantity or 0) for h in a.holdings
        )
        last_snap = (
            db.query(BalanceSnapshot)
            .filter(BalanceSnapshot.account_id == a.id)
            .order_by(BalanceSnapshot.date.desc())
            .first()
        )
        result.append({
            "id": a.id,
            "name": a.name,
            "type": a.type,
            "institution_id": a.institution_id,
            "institution_name": a.institution.name if a.institution else None,
            "currency": a.currency,
            "created_at": a.created_at.isoformat() if a.created_at else None,
            "balance": balance,
            "last_updated": last_snap.date.isoformat() if last_snap else None,
        })
    return result


@router.post("")
def create_account(data: AccountCreate, db: Session = Depends(get_db)):
    account = Account(**data.model_dump())
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@router.get("/{account_id}")
def get_account(account_id: int, db: Session = Depends(get_db)):
    account = db.query(Account).get(account_id)
    if not account:
        raise HTTPException(404, "Account not found")
    holdings = [
        {
            "id": h.id,
            "symbol": h.symbol,
            "quantity": h.quantity,
            "cost_basis": h.cost_basis,
            "last_price": h.last_price,
            "last_updated": h.last_updated.isoformat() if h.last_updated else None,
            "market_value": (h.last_price or 0) * (h.quantity or 0),
        }
        for h in account.holdings
    ]
    return {
        "id": account.id,
        "name": account.name,
        "type": account.type,
        "institution_id": account.institution_id,
        "institution_name": account.institution.name if account.institution else None,
        "currency": account.currency,
        "created_at": account.created_at.isoformat() if account.created_at else None,
        "holdings": holdings,
        "balance": sum(h["market_value"] for h in holdings),
    }


@router.patch("/{account_id}")
def update_account(account_id: int, data: AccountUpdate, db: Session = Depends(get_db)):
    account = db.query(Account).get(account_id)
    if not account:
        raise HTTPException(404, "Account not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(account, k, v)
    db.commit()
    db.refresh(account)
    return account


@router.delete("/{account_id}")
def delete_account(account_id: int, db: Session = Depends(get_db)):
    account = db.query(Account).get(account_id)
    if not account:
        raise HTTPException(404, "Account not found")
    db.delete(account)
    db.commit()
    return {"ok": True}
