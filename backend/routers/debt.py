import math
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from ..database import get_db
from ..models import Account, BalanceSnapshot, DebtDetail

router = APIRouter(prefix="/api/debt", tags=["debt"])

DEBT_TYPES = {"credit_card", "student_loan", "auto_loan", "personal_loan"}


class DebtDetailUpdate(BaseModel):
    interest_rate: Optional[float] = None
    minimum_payment: Optional[float] = None


def _months_to_payoff(balance: float, annual_rate: float, monthly_payment: float) -> Optional[int]:
    if balance <= 0:
        return 0
    if annual_rate == 0:
        return math.ceil(balance / monthly_payment) if monthly_payment > 0 else None
    r = annual_rate / 100 / 12
    if monthly_payment <= balance * r:
        return None  # never paid off at this payment
    months = -math.log(1 - (balance * r / monthly_payment)) / math.log(1 + r)
    return math.ceil(months)


def _total_interest(balance: float, annual_rate: float, monthly_payment: float, months: int) -> float:
    return max(0.0, monthly_payment * months - balance)


def _get_debt_accounts(db: Session):
    accounts = db.query(Account).filter(Account.type.in_(DEBT_TYPES)).all()
    result = []
    for a in accounts:
        snap = (
            db.query(BalanceSnapshot)
            .filter(BalanceSnapshot.account_id == a.id)
            .order_by(BalanceSnapshot.date.desc())
            .first()
        )
        balance = snap.balance if snap else 0.0
        detail = db.query(DebtDetail).filter(DebtDetail.account_id == a.id).first()
        rate = detail.interest_rate if detail else 0.0
        min_pay = detail.minimum_payment if detail else 0.0
        months = _months_to_payoff(balance, rate, min_pay)
        interest = _total_interest(balance, rate, min_pay, months) if months is not None else None
        result.append({
            "account_id": a.id,
            "name": a.name,
            "type": a.type,
            "balance": balance,
            "interest_rate": rate,
            "minimum_payment": min_pay,
            "months_to_payoff": months,
            "total_interest": interest,
            "last_updated": snap.date.isoformat() if snap else None,
        })
    return result


@router.get("")
def get_debts(db: Session = Depends(get_db)):
    debts = _get_debt_accounts(db)
    total_balance = sum(d["balance"] for d in debts)
    total_min = sum(d["minimum_payment"] for d in debts)
    highest_rate = max((d["interest_rate"] for d in debts), default=0.0)
    total_interest = sum(d["total_interest"] for d in debts if d["total_interest"] is not None)
    return {
        "debts": debts,
        "summary": {
            "total_balance": total_balance,
            "total_minimum_payment": total_min,
            "highest_rate": highest_rate,
            "total_interest_if_minimums": total_interest,
        },
    }


@router.patch("/{account_id}")
def update_debt_detail(account_id: int, data: DebtDetailUpdate, db: Session = Depends(get_db)):
    account = db.query(Account).get(account_id)
    if not account or account.type not in DEBT_TYPES:
        raise HTTPException(404, "Debt account not found")
    detail = db.query(DebtDetail).filter(DebtDetail.account_id == account_id).first()
    if not detail:
        detail = DebtDetail(account_id=account_id)
        db.add(detail)
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(detail, k, v)
    db.commit()
    db.refresh(detail)
    return {"ok": True}


@router.get("/payoff-chart")
def payoff_chart(db: Session = Depends(get_db)):
    """Month-by-month remaining balance for each debt at minimum payments."""
    debts = _get_debt_accounts(db)
    max_months = 0
    for d in debts:
        if d["months_to_payoff"] is not None:
            max_months = max(max_months, d["months_to_payoff"])
    if max_months == 0 or max_months > 600:
        max_months = min(max_months or 0, 600)

    series = []
    for d in debts:
        if d["balance"] <= 0:
            continue
        r = d["interest_rate"] / 100 / 12
        pay = d["minimum_payment"]
        bal = d["balance"]
        points = []
        for m in range(max_months + 1):
            points.append({"month": m, "balance": round(max(bal, 0), 2)})
            if bal <= 0:
                break
            interest = bal * r
            principal = pay - interest
            bal -= principal
        series.append({"name": d["name"], "type": d["type"], "points": points})

    return {"months": max_months, "series": series}
