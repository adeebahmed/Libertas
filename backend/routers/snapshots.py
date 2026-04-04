from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import date

from ..database import get_db
from ..models import Account, Holding, BalanceSnapshot, RealEstate

router = APIRouter(prefix="/api/snapshots", tags=["snapshots"])


@router.post("/record")
def record_snapshots(db: Session = Depends(get_db)):
    """Record a net worth snapshot for all accounts for today."""
    accounts = db.query(Account).all()
    today = date.today()
    recorded = 0

    for a in accounts:
        if a.holdings:
            balance = sum(
                (h.last_price * h.quantity) if h.last_price and h.quantity else (h.cost_basis or 0)
                for h in a.holdings
            )
        else:
            # Cash account — use most recent snapshot balance
            last_snap = (
                db.query(BalanceSnapshot)
                .filter(BalanceSnapshot.account_id == a.id)
                .order_by(BalanceSnapshot.date.desc())
                .first()
            )
            balance = last_snap.balance if last_snap else 0

        # Add real estate equity
        for re in a.real_estate:
            value = re.effective_value or 0
            mortgage = re.mortgage_balance or 0
            balance += value - mortgage

        existing = (
            db.query(BalanceSnapshot)
            .filter(BalanceSnapshot.account_id == a.id, BalanceSnapshot.date == today)
            .first()
        )
        if existing:
            # Never overwrite a good snapshot with $0
            if balance > 0 or existing.balance == 0:
                existing.balance = balance
        else:
            db.add(BalanceSnapshot(account_id=a.id, date=today, balance=balance))
        recorded += 1

    db.commit()
    return {"recorded": recorded, "date": today.isoformat()}


@router.get("/net-worth")
def net_worth_history(db: Session = Depends(get_db)):
    """Get net worth over time (aggregated across all accounts)."""
    snapshots = (
        db.query(BalanceSnapshot)
        .order_by(BalanceSnapshot.date)
        .all()
    )
    by_date: dict[str, float] = {}
    for s in snapshots:
        d = s.date.isoformat()
        by_date[d] = by_date.get(d, 0) + s.balance

    return [{"date": d, "net_worth": round(v, 2)} for d, v in sorted(by_date.items())]


@router.get("/current")
def current_net_worth(db: Session = Depends(get_db)):
    """Get current net worth calculated from holdings + real estate."""
    accounts = db.query(Account).all()
    total = 0
    by_type: dict[str, float] = {}

    today = date.today()
    for a in accounts:
        if a.holdings:
            account_balance = sum(
                (h.last_price * h.quantity) if h.last_price and h.quantity else (h.cost_basis or 0)
                for h in a.holdings
            )
        else:
            # Cash account — use most recent snapshot balance
            last_snap = (
                db.query(BalanceSnapshot)
                .filter(BalanceSnapshot.account_id == a.id)
                .order_by(BalanceSnapshot.date.desc())
                .first()
            )
            account_balance = last_snap.balance if last_snap else 0

        for re in a.real_estate:
            account_balance += (re.effective_value or 0) - (re.mortgage_balance or 0)
        total += account_balance
        by_type[a.type] = by_type.get(a.type, 0) + account_balance

    # Delta: compare against most recent snapshot from a PRIOR date (not today)
    prior_snap = (
        db.query(BalanceSnapshot)
        .filter(BalanceSnapshot.date < today)
        .order_by(BalanceSnapshot.date.desc())
        .first()
    )
    previous_total = 0
    if prior_snap:
        snaps = (
            db.query(BalanceSnapshot)
            .filter(BalanceSnapshot.date == prior_snap.date)
            .all()
        )
        previous_total = sum(s.balance for s in snaps)

    return {
        "net_worth": round(total, 2),
        "previous": round(previous_total, 2),
        "delta": round(total - previous_total, 2),
        "by_type": {k: round(v, 2) for k, v in by_type.items()},
    }
