from datetime import date
import json
from typing import Any, Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Account, BalanceSnapshot, Holding, Setting, Transaction

router = APIRouter(prefix="/api/retirement", tags=["retirement"])

DEBT_TYPES = {"credit_card", "student_loan", "auto_loan", "personal_loan", "mortgage"}
RETIREMENT_TYPES = {"401k", "ira", "traditional_ira", "roth_ira", "pension"}
TAXABLE_TYPES = {"brokerage", "crypto"}
CASH_TYPES = {"checking", "savings"}
FIRE_TYPES = {"lean", "regular", "fat", "coast", "barista"}


def _get_setting(db: Session, key: str, default=None):
    row = db.query(Setting).get(key)
    if not row or row.value is None:
        return default
    try:
        return json.loads(row.value)
    except (TypeError, json.JSONDecodeError):
        return default


def _latest_snapshot(db: Session, account_id: int):
    return (
        db.query(BalanceSnapshot)
        .filter(BalanceSnapshot.account_id == account_id)
        .order_by(BalanceSnapshot.date.desc())
        .first()
    )


def _account_balance(db: Session, account: Account) -> float:
    if account.holdings:
        return sum((h.last_price or 0.0) * (h.quantity or 0.0) for h in account.holdings)
    snap = _latest_snapshot(db, account.id)
    return float(snap.balance) if snap else 0.0


def _portfolio_totals(db: Session) -> dict[str, float]:
    totals = {"investable": 0.0, "debt": 0.0, "retirement": 0.0, "tax_advantaged": 0.0, "taxable": 0.0, "cash": 0.0, "other": 0.0}
    accounts = db.query(Account).all()
    for a in accounts:
        bal = _account_balance(db, a)
        if a.type in DEBT_TYPES:
            totals["debt"] += bal
            continue
        totals["investable"] += bal
        if a.type in RETIREMENT_TYPES:
            totals["retirement"] += bal
            totals["tax_advantaged"] += bal
        elif a.type in TAXABLE_TYPES:
            totals["taxable"] += bal
        elif a.type in CASH_TYPES:
            totals["cash"] += bal
        else:
            totals["other"] += bal
    return totals


def _monthly_income(db: Session) -> float:
    monthly_income = _get_setting(db, "monthly_income", None)
    if monthly_income:
        return float(monthly_income)
    income_w2 = float(_get_setting(db, "income_w2", 0) or 0)
    income_1099 = float(_get_setting(db, "income_1099", 0) or 0)
    return (income_w2 + income_1099) / 12 if (income_w2 + income_1099) > 0 else 0.0


def _fire_target(
    fire_type: str,
    monthly_expenses: float,
    annual_lean_expenses: float,
    annual_fat_expenses: float,
    part_time_income: float,
    safe_withdrawal_rate: float,
    expected_return: float,
    current_age: int,
    target_retirement_age: int,
) -> float:
    regular_annual = monthly_expenses * 12
    if fire_type == "lean":
        annual = annual_lean_expenses if annual_lean_expenses > 0 else regular_annual * 0.75
        return annual / safe_withdrawal_rate
    if fire_type == "fat":
        annual = annual_fat_expenses if annual_fat_expenses > 0 else regular_annual * 1.5
        return annual / safe_withdrawal_rate
    if fire_type == "barista":
        annual = max(0.0, regular_annual - part_time_income)
        return annual / safe_withdrawal_rate
    if fire_type == "coast":
        years = max(0, target_retirement_age - current_age)
        regular_target = regular_annual / safe_withdrawal_rate
        return regular_target / ((1 + expected_return) ** years) if years > 0 else regular_target
    return regular_annual / safe_withdrawal_rate


def _time_to_target(current_balance: float, yearly_contribution: float, annual_return: float, target: float) -> dict[str, Any]:
    if target <= 0:
        return {"years": 0, "projected_balance": current_balance}
    if current_balance >= target:
        return {"years": 0, "projected_balance": current_balance}

    balance = current_balance
    for year in range(1, 101):
        balance = balance * (1 + annual_return) + yearly_contribution
        if balance >= target:
            return {"years": year, "projected_balance": balance}
    return {"years": None, "projected_balance": balance}


def _recommend_fire_type(db: Session) -> dict[str, Any]:
    totals = _portfolio_totals(db)
    birth_year = int(_get_setting(db, "birth_year", date.today().year - 30) or date.today().year - 30)
    age = max(18, date.today().year - birth_year)
    monthly_income = _monthly_income(db)
    monthly_expenses = float(_get_setting(db, "monthly_expenses", 0) or 0)
    savings_rate = ((monthly_income - monthly_expenses) / monthly_income * 100) if monthly_income > 0 else 0.0

    if age < 30 and savings_rate < 20:
        return {"recommended_fire_type": "coast", "reason": "Time horizon long and savings rate low; Coast FIRE gives realistic near-term target."}
    if 25 <= age <= 35 and savings_rate > 30 and monthly_expenses > 6000:
        return {"recommended_fire_type": "fat", "reason": "Savings strong and spending high; Fat FIRE better matches desired lifestyle."}
    if 25 <= age <= 35 and savings_rate > 30:
        return {"recommended_fire_type": "regular", "reason": "Savings rate supports standard FIRE without extreme lifestyle compression."}
    if 30 <= age <= 40 and 15 <= savings_rate <= 30 and totals["debt"] > 50000:
        return {"recommended_fire_type": "barista", "reason": "Debt load plus moderate savings rate suggests hybrid part-time glide path."}
    if monthly_expenses > 0 and monthly_expenses < 3000:
        return {"recommended_fire_type": "lean", "reason": "Expense baseline low; Lean FIRE reachable earlier with current habits."}
    return {"recommended_fire_type": "regular", "reason": "Regular FIRE is best default baseline using current expenses."}


@router.get("")
def get_projections(
    monthly_contribution: float = 0,
    years: int = 10,
    conservative_rate: float = 0.04,
    moderate_rate: float = 0.07,
    aggressive_rate: float = 0.10,
    db: Session = Depends(get_db),
):
    current_balance = _portfolio_totals(db)["investable"]
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


@router.get("/overview")
def retirement_overview(db: Session = Depends(get_db)):
    totals = _portfolio_totals(db)
    accounts = db.query(Account).all()
    birth_year = int(_get_setting(db, "birth_year", date.today().year - 30) or date.today().year - 30)
    target_retirement_age = int(_get_setting(db, "retirement_age", 65) or 65)
    monthly_expenses = float(_get_setting(db, "monthly_expenses", 0) or 0)
    target = float(_get_setting(db, "retirement_target_amount", 0) or 0)
    if target <= 0 and monthly_expenses > 0:
        target = monthly_expenses * 12 * 25

    current_age = max(18, date.today().year - birth_year)
    readiness = (totals["investable"] / target * 100) if target > 0 else 0
    monthly_contribution = float(_get_setting(db, "monthly_contribution", 0) or 0)

    current_year_start = date(date.today().year, 1, 1)
    account_rows = []
    contrib_by_type = {"401k": 0.0, "ira": 0.0, "roth_ira": 0.0}
    for a in accounts:
        bal = _account_balance(db, a)
        if a.type in RETIREMENT_TYPES:
            account_rows.append({"id": a.id, "name": a.name, "type": a.type, "balance": round(bal, 2)})
            txs = (
                db.query(Transaction)
                .filter(Transaction.account_id == a.id, Transaction.date >= current_year_start)
                .all()
            )
            contrib_amount = sum(max(0.0, float(t.amount or 0.0)) for t in txs if (t.type or "").lower() in {"deposit", "contribution", "buy"})
            if a.type in contrib_by_type:
                contrib_by_type[a.type] += contrib_amount

    limits = {"401k": 23500.0, "ira": 7000.0, "roth_ira": 7000.0}
    contribution_utilization = {
        key: {
            "limit": value,
            "contributed": round(contrib_by_type.get(key, 0.0), 2),
            "utilization_pct": round((contrib_by_type.get(key, 0.0) / value) * 100, 2) if value > 0 else 0,
        }
        for key, value in limits.items()
    }

    return {
        "retirement_accounts": account_rows,
        "total_retirement_assets": round(totals["retirement"], 2),
        "retirement_pct_of_net_worth": round((totals["retirement"] / totals["investable"]) * 100, 2) if totals["investable"] > 0 else 0,
        "tax_split": {
            "tax_advantaged": round(totals["tax_advantaged"], 2),
            "taxable": round(totals["taxable"], 2),
            "cash": round(totals["cash"], 2),
            "other": round(totals["other"], 2),
        },
        "contribution_utilization": contribution_utilization,
        "readiness": {"target": round(target, 2), "percent": round(readiness, 2)},
        "age_milestones": {
            "current_age": current_age,
            "target_retirement_age": target_retirement_age,
            "milestones": [{"label": "Roth/401k access", "age": 59.5}, {"label": "Social Security earliest", "age": 62}, {"label": "Medicare", "age": 65}, {"label": "Social Security full", "age": 67}],
        },
        "monthly_needed_delta": round(monthly_contribution, 2),
    }


@router.get("/fire/recommend")
def recommend_fire(db: Session = Depends(get_db)):
    return _recommend_fire_type(db)


@router.get("/fire")
def fire_projection(
    fire_type: str = "regular",
    safe_withdrawal_rate: float = 0.04,
    expected_return: float = 0.07,
    monthly_contribution: Optional[float] = None,
    monthly_income: Optional[float] = None,
    monthly_expenses: Optional[float] = None,
    annual_lean_expenses: Optional[float] = None,
    annual_fat_expenses: Optional[float] = None,
    part_time_income: Optional[float] = None,
    target_retirement_age: Optional[int] = None,
    db: Session = Depends(get_db),
):
    f_type = fire_type if fire_type in FIRE_TYPES else "regular"
    birth_year = int(_get_setting(db, "birth_year", date.today().year - 30) or date.today().year - 30)
    current_age = max(18, date.today().year - birth_year)
    retirement_age = int(target_retirement_age or _get_setting(db, "retirement_age", 65) or 65)
    m_income = float(monthly_income if monthly_income is not None else _monthly_income(db))
    m_expenses = float(monthly_expenses if monthly_expenses is not None else (_get_setting(db, "monthly_expenses", 0) or 0))
    m_contribution = float(monthly_contribution if monthly_contribution is not None else (_get_setting(db, "monthly_contribution", 0) or 0))
    lean_annual = float(annual_lean_expenses if annual_lean_expenses is not None else (_get_setting(db, "annual_lean_expenses", 0) or 0))
    fat_annual = float(annual_fat_expenses if annual_fat_expenses is not None else (_get_setting(db, "annual_fat_expenses", 0) or 0))
    barista_income = float(part_time_income if part_time_income is not None else (_get_setting(db, "part_time_income", 0) or 0))
    current_balance = _portfolio_totals(db)["investable"]

    fire_number = _fire_target(
        fire_type=f_type,
        monthly_expenses=m_expenses,
        annual_lean_expenses=lean_annual,
        annual_fat_expenses=fat_annual,
        part_time_income=barista_income,
        safe_withdrawal_rate=safe_withdrawal_rate,
        expected_return=expected_return,
        current_age=current_age,
        target_retirement_age=retirement_age,
    )
    progress_pct = (current_balance / fire_number * 100) if fire_number > 0 else 0
    savings_rate = ((m_income - m_expenses) / m_income * 100) if m_income > 0 else 0
    timing = _time_to_target(current_balance, m_contribution * 12, expected_return, fire_number)
    years_to_fire = timing["years"]

    rec = _recommend_fire_type(db)
    nudges = []
    if f_type == "coast":
        gap = max(0.0, fire_number - current_balance)
        nudges.append(f"Coast gap: ${gap:,.0f}")
    if savings_rate >= 30:
        nudges.append(f"Savings rate {savings_rate:.0f}% is strong for FIRE timeline.")
    if years_to_fire is not None:
        nudges.append(f"At current pace: ~{years_to_fire} years to {f_type.title()} FIRE.")
    if not nudges:
        nudges.append("Increase monthly contribution to shorten timeline.")

    return {
        "fire_type": f_type,
        "fire_number": round(fire_number, 2),
        "current_balance": round(current_balance, 2),
        "progress_pct": round(progress_pct, 2),
        "savings_rate": round(savings_rate, 2),
        "time_to_fire_years": years_to_fire,
        "projected_balance_at_target": round(timing["projected_balance"], 2),
        "recommended_fire_type": rec["recommended_fire_type"],
        "recommendation_reason": rec["reason"],
        "inputs": {
            "safe_withdrawal_rate": safe_withdrawal_rate,
            "expected_return": expected_return,
            "monthly_contribution": m_contribution,
            "monthly_income": m_income,
            "monthly_expenses": m_expenses,
            "annual_lean_expenses": lean_annual,
            "annual_fat_expenses": fat_annual,
            "part_time_income": barista_income,
            "current_age": current_age,
            "target_retirement_age": retirement_age,
        },
        "nudges": nudges,
    }


@router.get("/plan")
def get_retirement_plan(db: Session = Depends(get_db)):
    investable = _portfolio_totals(db)["investable"]
    monthly_expenses = float(_get_setting(db, "monthly_expenses", 5000) or 5000)
    birth_year = _get_setting(db, "birth_year", None)
    retirement_age = int(_get_setting(db, "retirement_age", 65) or 65)
    monthly_contribution = float(_get_setting(db, "monthly_contribution", 2000) or 2000)
    target = float(_get_setting(db, "retirement_target_amount", 0) or 0)
    if target <= 0:
        target = monthly_expenses * 12 * 25

    rate = 0.07
    current_year = date.today().year
    years_to_retire = None
    on_track = None
    if birth_year:
        current_age = current_year - int(birth_year)
        years_to_retire = max(0, retirement_age - current_age)
        balance = investable
        for _ in range(years_to_retire):
            balance = balance * (1 + rate) + monthly_contribution * 12
        on_track = {
            "projected_at_retirement": round(balance, 2),
            "target": round(target, 2),
            "on_track": balance >= target,
            "shortfall": round(max(0, target - balance), 2),
            "surplus": round(max(0, balance - target), 2),
            "years_to_retire": years_to_retire,
        }

    years_to_target = None
    if monthly_contribution and target and investable < target:
        balance = investable
        for y in range(1, 101):
            balance = balance * (1 + rate) + monthly_contribution * 12
            if balance >= target:
                years_to_target = y
                break

    needed_monthly = None
    if years_to_retire and years_to_retire > 0 and target > investable:
        n = years_to_retire
        r = rate
        fv_pv = investable * ((1 + r) ** n)
        needed_monthly = max(0, (target - fv_pv) / (((1 + r) ** n - 1) / r) / 12)

    y_range = years_to_retire or 30
    scenarios = {}
    for name, r in [("conservative", 0.04), ("moderate", 0.07), ("aggressive", 0.10)]:
        points = []
        balance = investable
        for year in range(y_range + 1):
            points.append({"year": year, "value": round(balance, 2)})
            balance = balance * (1 + r) + monthly_contribution * 12
        scenarios[name] = points

    fire_context = _recommend_fire_type(db)
    return {
        "current_balance": round(investable, 2),
        "target": round(target, 2),
        "monthly_contribution": monthly_contribution,
        "years_to_target": years_to_target,
        "needed_monthly_contribution": round(needed_monthly, 2) if needed_monthly else None,
        "on_track": on_track,
        "scenarios": scenarios,
        "settings": {"birth_year": birth_year, "retirement_age": retirement_age, "monthly_expenses": monthly_expenses},
        "fire_context": fire_context,
    }
