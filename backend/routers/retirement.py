from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import date
import json

from ..database import get_db
from ..models import Account, Holding, Setting, BalanceSnapshot

router = APIRouter(prefix="/api/retirement", tags=["retirement"])


def _get_setting(db: Session, key: str, default=None):
    s = db.query(Setting).get(key)
    if s and s.value:
        return json.loads(s.value)
    return default


def _current_investable(db: Session) -> float:
    EXCLUDE = {"credit_card", "student_loan", "auto_loan", "personal_loan"}
    accounts = db.query(Account).all()
    total = 0.0
    for a in accounts:
        if a.type in EXCLUDE:
            continue
        if a.holdings:
            total += sum((h.last_price or 0) * (h.quantity or 0) for h in a.holdings)
        else:
            snap = (
                db.query(BalanceSnapshot)
                .filter(BalanceSnapshot.account_id == a.id)
                .order_by(BalanceSnapshot.date.desc())
                .first()
            )
            total += snap.balance if snap else 0.0
    return total


@router.get("")
def get_projections(
    monthly_contribution: float = 0,
    years: int = 10,
    conservative_rate: float = 0.04,
    moderate_rate: float = 0.07,
    aggressive_rate: float = 0.10,
    db: Session = Depends(get_db),
):
    current_balance = _current_investable(db)
    scenarios = {}
    for name, rate in [
        ("conservative", conservative_rate),
        ("moderate", moderate_rate),
        ("aggressive", aggressive_rate),
    ]:
        points = []
        balance = current_balance
        for year in range(years + 1):
            points.append({"year": year, "value": round(balance, 2)})
            balance = balance * (1 + rate) + monthly_contribution * 12
        scenarios[name] = points

    return {
        "current_balance": round(current_balance, 2),
        "params": {
            "monthly_contribution": monthly_contribution,
            "years": years,
            "conservative_rate": conservative_rate,
            "moderate_rate": moderate_rate,
            "aggressive_rate": aggressive_rate,
        },
        "scenarios": scenarios,
    }


@router.get("/plan")
def get_retirement_plan(db: Session = Depends(get_db)):
    """Personalized retirement plan using saved settings."""
    investable = _current_investable(db)

    monthly_expenses = _get_setting(db, "monthly_expenses", 5000)
    birth_year = _get_setting(db, "birth_year", None)
    retirement_age = _get_setting(db, "retirement_age", 65)
    monthly_contribution = _get_setting(db, "monthly_contribution", 2000)
    target = _get_setting(db, "retirement_target_amount", None)

    if not target:
        target = (monthly_expenses or 5000) * 12 * 25  # 4% rule

    rate = 0.07  # moderate assumption

    # Years to retirement
    current_year = date.today().year
    years_to_retire = None
    on_track = None
    if birth_year:
        current_age = current_year - birth_year
        years_to_retire = max(0, (retirement_age or 65) - current_age)
        balance = investable
        for _ in range(years_to_retire):
            balance = balance * (1 + rate) + (monthly_contribution or 0) * 12
        on_track = {
            "projected_at_retirement": round(balance, 2),
            "target": round(target, 2),
            "on_track": balance >= target,
            "shortfall": round(max(0, target - balance), 2),
            "surplus": round(max(0, balance - target), 2),
            "years_to_retire": years_to_retire,
        }

    # Years to hit target at current pace
    years_to_target = None
    if monthly_contribution and target and investable < target:
        balance = investable
        for y in range(1, 101):
            balance = balance * (1 + rate) + monthly_contribution * 12
            if balance >= target:
                years_to_target = y
                break

    # Monthly contribution needed to hit target by retirement age
    needed_monthly = None
    if years_to_retire and years_to_retire > 0 and target > investable:
        # FV = PV*(1+r)^n + PMT * ((1+r)^n - 1) / r  =>  solve for PMT
        n = years_to_retire
        r = rate
        fv_pv = investable * ((1 + r) ** n)
        needed_monthly = max(0, (target - fv_pv) / (((1 + r) ** n - 1) / r) / 12)

    # Scenarios for chart
    y_range = years_to_retire or 30
    scenarios = {}
    for name, r in [("conservative", 0.04), ("moderate", 0.07), ("aggressive", 0.10)]:
        points = []
        balance = investable
        for year in range(y_range + 1):
            points.append({"year": year, "value": round(balance, 2)})
            balance = balance * (1 + r) + (monthly_contribution or 0) * 12
        scenarios[name] = points

    return {
        "current_balance": round(investable, 2),
        "target": round(target, 2),
        "monthly_contribution": monthly_contribution or 0,
        "years_to_target": years_to_target,
        "needed_monthly_contribution": round(needed_monthly, 2) if needed_monthly else None,
        "on_track": on_track,
        "scenarios": scenarios,
        "settings": {
            "birth_year": birth_year,
            "retirement_age": retirement_age,
            "monthly_expenses": monthly_expenses,
        },
    }
