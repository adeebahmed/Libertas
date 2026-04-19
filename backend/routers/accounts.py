from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional
from datetime import date, datetime

from ..database import get_db
from ..models import Account, Institution, Holding, BalanceSnapshot, Transaction
from ..services.source_ingest import upsert_transaction

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


class BalanceUpdate(BaseModel):
    balance: float
    as_of: Optional[date] = Field(default=None, alias="date")


class TransactionCreate(BaseModel):
    date: date
    type: str
    symbol: Optional[str] = None
    quantity: Optional[float] = None
    price: Optional[float] = None
    amount: Optional[float] = None
    description: Optional[str] = None


class HoldingCreate(BaseModel):
    symbol: str
    quantity: float
    cost_basis: Optional[float] = None
    last_price: Optional[float] = None
    last_updated: Optional[datetime] = None


class HoldingUpdate(BaseModel):
    symbol: Optional[str] = None
    quantity: Optional[float] = None
    cost_basis: Optional[float] = None
    last_price: Optional[float] = None
    last_updated: Optional[datetime] = None


def _get_latest_snapshot(db: Session, account_id: int) -> Optional[BalanceSnapshot]:
    return (
        db.query(BalanceSnapshot)
        .filter(BalanceSnapshot.account_id == account_id)
        .order_by(BalanceSnapshot.date.desc())
        .first()
    )


def _serialize_holding(h: Holding) -> dict:
    qty = h.quantity or 0
    market_value = (h.last_price * qty) if h.last_price and qty else (h.cost_basis or 0)
    return {
        "id": h.id,
        "symbol": h.symbol,
        "quantity": h.quantity,
        "cost_basis": h.cost_basis,
        "last_price": h.last_price,
        "last_updated": h.last_updated.isoformat() if h.last_updated else None,
        "market_value": market_value,
    }


def _serialize_transaction(t: Transaction) -> dict:
    return {
        "id": t.id,
        "date": t.date.isoformat(),
        "type": t.type,
        "symbol": t.symbol,
        "quantity": t.quantity,
        "price": t.price,
        "amount": t.amount,
        "description": t.description,
        "import_log_id": t.import_log_id,
        "import_hash": t.import_hash,
        "sync_source": t.sync_source,
        "source_kind": t.source_kind,
        "source_record_id": t.source_record_id,
        "source_priority": t.source_priority,
        "canonical_key": t.canonical_key,
        "provenance": t.provenance,
        "merge_conflict": bool(t.merge_conflict),
    }


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
        last_snap = _get_latest_snapshot(db, a.id)

        def holding_value(h):
            qty = h.quantity or 0
            if h.last_price:
                return h.last_price * qty
            return h.cost_basis or 0

        if a.holdings:
            balance = sum(holding_value(h) for h in a.holdings)
        else:
            # Cash/checking account — use last snapshot balance
            balance = last_snap.balance if last_snap else 0
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
            "sync_source": a.sync_source,
            "source_kind": a.source_kind,
            "source_record_id": a.source_record_id,
            "source_priority": a.source_priority,
            "provenance": a.provenance,
            "merge_conflict": bool(a.merge_conflict),
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
    last_snap = _get_latest_snapshot(db, account_id)
    holdings = [_serialize_holding(h) for h in account.holdings]
    balance = sum(h["market_value"] for h in holdings) if holdings else (last_snap.balance if last_snap else 0)
    return {
        "id": account.id,
        "name": account.name,
        "type": account.type,
        "institution_id": account.institution_id,
        "institution_name": account.institution.name if account.institution else None,
        "currency": account.currency,
        "created_at": account.created_at.isoformat() if account.created_at else None,
        "holdings": holdings,
        "balance": balance,
        "last_updated": last_snap.date.isoformat() if last_snap else None,
        "sync_source": account.sync_source,
        "source_kind": account.source_kind,
        "source_record_id": account.source_record_id,
        "source_priority": account.source_priority,
        "provenance": account.provenance,
        "merge_conflict": bool(account.merge_conflict),
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


@router.post("/{account_id}/balance")
def set_account_balance(account_id: int, data: BalanceUpdate, db: Session = Depends(get_db)):
    account = db.query(Account).get(account_id)
    if not account:
        raise HTTPException(404, "Account not found")

    snap_date = data.as_of or date.today()
    snapshot = (
        db.query(BalanceSnapshot)
        .filter(BalanceSnapshot.account_id == account_id, BalanceSnapshot.date == snap_date)
        .first()
    )
    if snapshot:
        snapshot.balance = data.balance
    else:
        snapshot = BalanceSnapshot(account_id=account_id, date=snap_date, balance=data.balance)
        db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return {
        "ok": True,
        "snapshot": {
            "id": snapshot.id,
            "account_id": snapshot.account_id,
            "date": snapshot.date.isoformat(),
            "balance": snapshot.balance,
        },
    }


@router.get("/{account_id}/transactions")
def get_account_transactions(
    account_id: int,
    limit: int = 200,
    search: Optional[str] = Query(default=None),
    tx_type: Optional[str] = Query(default=None, alias="type"),
    date_from: Optional[date] = Query(default=None),
    date_to: Optional[date] = Query(default=None),
    min_amount: Optional[float] = Query(default=None),
    max_amount: Optional[float] = Query(default=None),
    db: Session = Depends(get_db),
):
    account = db.query(Account).get(account_id)
    if not account:
        raise HTTPException(404, "Account not found")
    query = db.query(Transaction).filter(Transaction.account_id == account_id)

    if search:
        pattern = f"%{search.strip()}%"
        query = query.filter(
            (Transaction.symbol.ilike(pattern)) |
            (Transaction.description.ilike(pattern))
        )
    if tx_type:
        query = query.filter(Transaction.type == tx_type.strip().lower())
    if date_from:
        query = query.filter(Transaction.date >= date_from)
    if date_to:
        query = query.filter(Transaction.date <= date_to)
    if min_amount is not None:
        query = query.filter(Transaction.amount >= min_amount)
    if max_amount is not None:
        query = query.filter(Transaction.amount <= max_amount)

    txns = query.order_by(Transaction.date.desc()).limit(limit).all()
    return [_serialize_transaction(t) for t in txns]


@router.post("/{account_id}/transactions")
def create_account_transaction(account_id: int, data: TransactionCreate, db: Session = Depends(get_db)):
    account = db.query(Account).get(account_id)
    if not account:
        raise HTTPException(404, "Account not found")

    symbol = data.symbol.strip().upper() if data.symbol else None
    tx, _, _ = upsert_transaction(
        db,
        account_id=account_id,
        tx_date=data.date,
        tx_type=data.type.strip().lower(),
        symbol=symbol,
        quantity=data.quantity,
        price=data.price,
        amount=data.amount,
        description=data.description,
        source_kind="manual",
        source_record_id=None,
        raw_row=None,
    )
    db.commit()
    db.refresh(tx)
    return _serialize_transaction(tx)


@router.delete("/{account_id}/transactions/{tx_id}")
def delete_account_transaction(account_id: int, tx_id: int, db: Session = Depends(get_db)):
    account = db.query(Account).get(account_id)
    if not account:
        raise HTTPException(404, "Account not found")

    tx = db.query(Transaction).get(tx_id)
    if not tx or tx.account_id != account_id:
        raise HTTPException(404, "Transaction not found")
    if tx.import_log_id is not None or tx.import_hash is not None:
        raise HTTPException(400, "CSV transactions cannot be deleted")

    db.delete(tx)
    db.commit()
    return {"ok": True}


@router.post("/{account_id}/holdings")
def create_account_holding(account_id: int, data: HoldingCreate, db: Session = Depends(get_db)):
    account = db.query(Account).get(account_id)
    if not account:
        raise HTTPException(404, "Account not found")

    holding = Holding(
        account_id=account_id,
        symbol=data.symbol.strip().upper(),
        quantity=data.quantity,
        cost_basis=data.cost_basis,
        last_price=data.last_price,
        last_updated=data.last_updated or datetime.utcnow(),
    )
    db.add(holding)
    db.commit()
    db.refresh(holding)
    return _serialize_holding(holding)


@router.patch("/{account_id}/holdings/{holding_id}")
def update_account_holding(account_id: int, holding_id: int, data: HoldingUpdate, db: Session = Depends(get_db)):
    account = db.query(Account).get(account_id)
    if not account:
        raise HTTPException(404, "Account not found")

    holding = db.query(Holding).get(holding_id)
    if not holding or holding.account_id != account_id:
        raise HTTPException(404, "Holding not found")

    payload = data.model_dump(exclude_unset=True)
    if "symbol" in payload and payload["symbol"] is not None:
        payload["symbol"] = payload["symbol"].strip().upper()
    for key, value in payload.items():
        setattr(holding, key, value)
    if "last_updated" not in payload:
        holding.last_updated = datetime.utcnow()

    db.commit()
    db.refresh(holding)
    return _serialize_holding(holding)


@router.delete("/{account_id}/holdings/{holding_id}")
def delete_account_holding(account_id: int, holding_id: int, db: Session = Depends(get_db)):
    account = db.query(Account).get(account_id)
    if not account:
        raise HTTPException(404, "Account not found")

    holding = db.query(Holding).get(holding_id)
    if not holding or holding.account_id != account_id:
        raise HTTPException(404, "Holding not found")

    db.delete(holding)
    db.commit()
    return {"ok": True}


@router.get("/{account_id}/performance")
def get_account_performance(account_id: int, db: Session = Depends(get_db)):
    """Balance history snapshots for charting."""
    account = db.query(Account).get(account_id)
    if not account:
        raise HTTPException(404, "Account not found")
    snaps = (
        db.query(BalanceSnapshot)
        .filter(BalanceSnapshot.account_id == account_id)
        .order_by(BalanceSnapshot.date)
        .all()
    )
    if len(snaps) < 2:
        return {
            "snapshots": [{"date": s.date.isoformat(), "balance": s.balance} for s in snaps],
            "gain_pct": None,
            "benchmark_gain_pct": None,
            "relative_gain_pct": None,
        }

    first = snaps[0].balance
    last = snaps[-1].balance
    gain_pct = (last - first) / first * 100 if first > 0 else None

    # Simple S&P 500 baseline using 8% annualized return over the same span.
    day_span = max((snaps[-1].date - snaps[0].date).days, 1)
    years = day_span / 365.0
    benchmark_gain_pct = (((1.08 ** years) - 1) * 100) if years > 0 else 0.0
    relative_gain_pct = (gain_pct - benchmark_gain_pct) if gain_pct is not None else None

    return {
        "snapshots": [{"date": s.date.isoformat(), "balance": s.balance} for s in snaps],
        "gain_pct": round(gain_pct, 2) if gain_pct is not None else None,
        "benchmark_gain_pct": round(benchmark_gain_pct, 2),
        "relative_gain_pct": round(relative_gain_pct, 2) if relative_gain_pct is not None else None,
        "first_balance": first,
        "last_balance": last,
    }
