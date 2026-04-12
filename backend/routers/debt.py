import math
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import date

from ..database import get_db
from ..models import Account, BalanceSnapshot, DebtDetail

router = APIRouter(prefix="/api/debt", tags=["debt"])

DEBT_TYPES = {"credit_card", "student_loan", "auto_loan", "personal_loan"}


class DebtDetailUpdate(BaseModel):
    interest_rate: Optional[float] = None
    minimum_payment: Optional[float] = None
    payoff_date: Optional[date] = None


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
    import json
    debts = _get_debt_accounts(db)
    total_balance = sum(d["balance"] for d in debts)
    total_min = sum(d["minimum_payment"] for d in debts)
    highest_rate = max((d["interest_rate"] for d in debts), default=0.0)
    total_interest = sum(d["total_interest"] for d in debts if d["total_interest"] is not None)

    # DTI
    from ..models import Setting
    s = db.query(Setting).get("annual_income")
    annual_income = json.loads(s.value) if s and s.value else None
    dti = (total_balance / annual_income * 100) if annual_income and annual_income > 0 else None

    return {
        "debts": debts,
        "summary": {
            "total_balance": total_balance,
            "total_minimum_payment": total_min,
            "highest_rate": highest_rate,
            "total_interest_if_minimums": total_interest,
            "debt_to_income": round(dti, 1) if dti is not None else None,
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
    return {
        "ok": True,
        "payoff_date": detail.payoff_date.isoformat() if getattr(detail, "payoff_date", None) else None,
    }


@router.get("/strategies")
def get_strategies(db: Session = Depends(get_db)):
    """Avalanche (highest rate first) and snowball (lowest balance first) payoff strategies."""
    debts = _get_debt_accounts(db)
    active = [d for d in debts if d["balance"] > 0 and d["minimum_payment"] > 0]
    if not active:
        return {"avalanche": [], "snowball": [], "summary": {}}

    def _simulate(order: list[dict]) -> dict:
        """Simulate paying minimum on all + extra on priority debt."""
        total_min = sum(d["minimum_payment"] for d in active)
        extra = 0  # pay minimums only for comparison
        states = {d["account_id"]: {"balance": d["balance"], "rate": d["interest_rate"] / 100 / 12} for d in active}
        order_ids = [d["account_id"] for d in order]
        month = 0
        total_paid = 0.0
        total_interest_paid = 0.0
        while any(v["balance"] > 0.01 for v in states.values()) and month < 600:
            month += 1
            # Apply interest
            for aid, s in states.items():
                s["balance"] += s["balance"] * s["rate"]
            # Pay minimums + extra toward priority
            payment_pool = total_min + extra
            for aid in order_ids:
                s = states[aid]
                if s["balance"] <= 0:
                    continue
                d = next(x for x in active if x["account_id"] == aid)
                pay = min(payment_pool, s["balance"] + 0.01)
                interest = s["balance"] * s["rate"]  # already applied
                principal = pay - interest
                total_interest_paid += interest
                s["balance"] = max(0, s["balance"] - pay)
                total_paid += pay
                payment_pool -= pay
                if payment_pool <= 0:
                    break
        return {"months": month, "total_interest": round(total_interest_paid, 2), "total_paid": round(total_paid, 2)}

    avalanche_order = sorted(active, key=lambda d: d["interest_rate"], reverse=True)
    snowball_order = sorted(active, key=lambda d: d["balance"])

    avalanche_result = _simulate(avalanche_order)
    snowball_result = _simulate(snowball_order)

    return {
        "avalanche": [{"account_id": d["account_id"], "name": d["name"], "interest_rate": d["interest_rate"], "balance": d["balance"]} for d in avalanche_order],
        "snowball": [{"account_id": d["account_id"], "name": d["name"], "interest_rate": d["interest_rate"], "balance": d["balance"]} for d in snowball_order],
        "avalanche_result": avalanche_result,
        "snowball_result": snowball_result,
    }


@router.post("/{account_id}/extra-payment")
def extra_payment_impact(account_id: int, extra: float = 0, db: Session = Depends(get_db)):
    """Calculate how an extra monthly payment changes payoff time and total interest."""
    account = db.query(Account).get(account_id)
    if not account or account.type not in DEBT_TYPES:
        raise HTTPException(404, "Debt account not found")

    snap = (
        db.query(BalanceSnapshot)
        .filter(BalanceSnapshot.account_id == account_id)
        .order_by(BalanceSnapshot.date.desc())
        .first()
    )
    balance = snap.balance if snap else 0.0
    detail = db.query(DebtDetail).filter(DebtDetail.account_id == account_id).first()
    rate = detail.interest_rate if detail else 0.0
    min_pay = detail.minimum_payment if detail else 0.0

    base_months = _months_to_payoff(balance, rate, min_pay)
    base_interest = _total_interest(balance, rate, min_pay, base_months) if base_months else None

    new_pay = min_pay + extra
    new_months = _months_to_payoff(balance, rate, new_pay)
    new_interest = _total_interest(balance, rate, new_pay, new_months) if new_months else None

    return {
        "account_id": account_id,
        "balance": balance,
        "interest_rate": rate,
        "minimum_payment": min_pay,
        "extra_payment": extra,
        "base": {"months": base_months, "total_interest": base_interest},
        "with_extra": {"months": new_months, "total_interest": new_interest},
        "months_saved": (base_months - new_months) if base_months and new_months else None,
        "interest_saved": round((base_interest - new_interest), 2) if base_interest and new_interest else None,
    }


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
