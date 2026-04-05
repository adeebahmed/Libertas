from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import json
from datetime import date

from ..database import get_db
from ..models import Account, Holding, Transaction, Setting

router = APIRouter(prefix="/api/taxes", tags=["taxes"])

DEBT_TYPES = {"credit_card", "student_loan", "auto_loan", "personal_loan"}


def _get_setting(db: Session, key: str, default=None):
    s = db.query(Setting).get(key)
    if s and s.value:
        return json.loads(s.value)
    return default


# 2024 tax brackets (MFJ and single)
_BRACKETS = {
    "single": [
        (11600, 0.10),
        (47150, 0.12),
        (100525, 0.22),
        (191950, 0.24),
        (243725, 0.32),
        (609350, 0.35),
        (float("inf"), 0.37),
    ],
    "married_filing_jointly": [
        (23200, 0.10),
        (94300, 0.12),
        (201050, 0.22),
        (383900, 0.24),
        (487450, 0.32),
        (731200, 0.35),
        (float("inf"), 0.37),
    ],
    "married_filing_separately": [
        (11600, 0.10),
        (47150, 0.12),
        (100525, 0.22),
        (191950, 0.24),
        (243725, 0.32),
        (365600, 0.35),
        (float("inf"), 0.37),
    ],
    "head_of_household": [
        (16550, 0.10),
        (63100, 0.12),
        (100500, 0.22),
        (191950, 0.24),
        (243700, 0.32),
        (609350, 0.35),
        (float("inf"), 0.37),
    ],
}

_STANDARD_DEDUCTIONS = {
    "single": 14600,
    "married_filing_jointly": 29200,
    "married_filing_separately": 14600,
    "head_of_household": 21900,
}

# Long-term capital gains brackets (single / MFJ)
_LTCG_BRACKETS = {
    "single": [(47025, 0.0), (518900, 0.15), (float("inf"), 0.20)],
    "married_filing_jointly": [(94050, 0.0), (583750, 0.15), (float("inf"), 0.20)],
    "married_filing_separately": [(47025, 0.0), (291850, 0.15), (float("inf"), 0.20)],
    "head_of_household": [(63000, 0.0), (551350, 0.15), (float("inf"), 0.20)],
}


def _calc_ordinary_tax(income: float, filing_status: str) -> float:
    brackets = _BRACKETS.get(filing_status, _BRACKETS["single"])
    tax = 0.0
    prev = 0.0
    for limit, rate in brackets:
        if income <= prev:
            break
        taxable = min(income, limit) - prev
        tax += taxable * rate
        prev = limit
    return tax


def _calc_ltcg_tax(gains: float, ordinary_income: float, filing_status: str) -> float:
    brackets = _LTCG_BRACKETS.get(filing_status, _LTCG_BRACKETS["single"])
    tax = 0.0
    prev = 0.0
    for limit, rate in brackets:
        # Capital gains stack on top of ordinary income
        effective_lower = max(prev, ordinary_income) - ordinary_income
        effective_upper = limit - ordinary_income
        if gains <= effective_lower or effective_upper <= 0:
            prev = limit
            continue
        taxable = min(gains, max(0, effective_upper)) - max(0, effective_lower)
        if taxable > 0:
            tax += taxable * rate
        prev = limit
    return max(0, tax)


@router.get("/estimate")
def tax_estimate(db: Session = Depends(get_db)):
    """Estimate current year tax liability from settings."""
    income_w2 = _get_setting(db, "income_w2", 0) or 0
    income_1099 = _get_setting(db, "income_1099", 0) or 0
    filing_status = _get_setting(db, "tax_filing_status", "single") or "single"

    total_income = income_w2 + income_1099
    se_tax = income_1099 * 0.9235 * 0.153  # self-employment tax (both halves)
    se_deduction = se_tax / 2  # above-the-line deduction

    standard_deduction = _STANDARD_DEDUCTIONS.get(filing_status, 14600)
    agi = total_income - se_deduction
    taxable_income = max(0, agi - standard_deduction)

    ordinary_tax = _calc_ordinary_tax(taxable_income, filing_status)

    # Realized capital gains this year
    current_year = date.today().year
    realized_gains = 0.0
    realized_losses = 0.0
    accounts = db.query(Account).filter(~Account.type.in_(DEBT_TYPES)).all()
    for a in accounts:
        sell_txns = (
            db.query(Transaction)
            .filter(
                Transaction.account_id == a.id,
                Transaction.type == "sell",
                Transaction.date >= date(current_year, 1, 1),
            )
            .all()
        )
        for tx in sell_txns:
            if tx.amount and tx.price and tx.quantity:
                proceeds = tx.quantity * tx.price
                cost = tx.cost_basis * tx.quantity if hasattr(tx, "cost_basis") and tx.cost_basis else proceeds
                gain = proceeds - cost
                if gain > 0:
                    realized_gains += gain
                else:
                    realized_losses += abs(gain)

    net_gains = max(0, realized_gains - realized_losses)
    ltcg_tax = _calc_ltcg_tax(net_gains, taxable_income, filing_status)

    total_tax = ordinary_tax + se_tax + ltcg_tax
    effective_rate = total_tax / total_income * 100 if total_income > 0 else 0

    return {
        "income_w2": income_w2,
        "income_1099": income_1099,
        "total_income": total_income,
        "filing_status": filing_status,
        "agi": round(agi, 2),
        "standard_deduction": standard_deduction,
        "taxable_income": round(taxable_income, 2),
        "ordinary_tax": round(ordinary_tax, 2),
        "self_employment_tax": round(se_tax, 2),
        "realized_gains": round(realized_gains, 2),
        "realized_losses": round(realized_losses, 2),
        "net_capital_gains": round(net_gains, 2),
        "ltcg_tax": round(ltcg_tax, 2),
        "total_estimated_tax": round(total_tax, 2),
        "effective_rate": round(effective_rate, 2),
        "quarterly_payment": round(total_tax / 4, 2),
    }


@router.get("/harvesting")
def tax_loss_harvesting(db: Session = Depends(get_db)):
    """Detailed tax-loss harvesting opportunities across all taxable accounts."""
    accounts = db.query(Account).filter(
        Account.type.in_(["brokerage"])
    ).all()

    opportunities = []
    total_harvestable = 0.0

    for a in accounts:
        for h in a.holdings:
            if not h.cost_basis or not h.last_price or not h.quantity:
                continue
            avg_cost = h.cost_basis / h.quantity if h.quantity else 0
            market_value = h.last_price * h.quantity
            cost_total = h.cost_basis
            gain = market_value - cost_total
            gain_pct = (gain / cost_total * 100) if cost_total > 0 else 0

            if gain < -500:  # only meaningful losses
                opportunities.append({
                    "symbol": h.symbol,
                    "account": a.name,
                    "quantity": round(h.quantity, 4),
                    "avg_cost": round(avg_cost, 4),
                    "current_price": round(h.last_price, 4),
                    "market_value": round(market_value, 2),
                    "cost_basis": round(cost_total, 2),
                    "unrealized_loss": round(gain, 2),
                    "loss_pct": round(gain_pct, 1),
                })
                total_harvestable += abs(gain)

    opportunities.sort(key=lambda x: x["unrealized_loss"])

    filing_status = _get_setting(db, "tax_filing_status", "single") or "single"
    income_w2 = _get_setting(db, "income_w2", 0) or 0
    income_1099 = _get_setting(db, "income_1099", 0) or 0
    total_income = income_w2 + income_1099
    # Rough marginal rate for gain offset estimate
    marginal = 0.15  # default LTCG rate
    if total_income > 583750 if filing_status == "married_filing_jointly" else total_income > 518900:
        marginal = 0.20

    return {
        "opportunities": opportunities,
        "total_harvestable_loss": round(total_harvestable, 2),
        "estimated_tax_savings": round(total_harvestable * marginal, 2),
        "note": "Wash-sale rule: wait 30 days before repurchasing the same security.",
    }


@router.get("/entity-recommendations")
def entity_recommendations(db: Session = Depends(get_db)):
    """Recommend account types and strategies based on income and current holdings."""
    income_w2 = _get_setting(db, "income_w2", 0) or 0
    income_1099 = _get_setting(db, "income_1099", 0) or 0
    filing_status = _get_setting(db, "tax_filing_status", "single") or "single"
    total_income = income_w2 + income_1099

    recs = []

    # Traditional vs Roth IRA
    roth_limit = 161000 if filing_status == "single" else 240000
    trad_deductible_limit = 77000 if filing_status == "single" else 123000
    if total_income < roth_limit:
        recs.append({
            "type": "Roth IRA",
            "priority": "high",
            "reason": f"At ${total_income:,.0f} income you qualify for Roth IRA ({filing_status}). Contributions grow tax-free.",
            "limit_2024": 7000,
        })
    elif total_income > roth_limit:
        recs.append({
            "type": "Backdoor Roth IRA",
            "priority": "medium",
            "reason": "Income exceeds Roth limit. Consider backdoor Roth via non-deductible Traditional IRA conversion.",
            "limit_2024": 7000,
        })

    # Traditional IRA deductibility
    accounts = db.query(Account).all()
    has_401k = any(a.type == "401k" for a in accounts)
    if total_income < trad_deductible_limit and has_401k:
        recs.append({
            "type": "Traditional IRA",
            "priority": "medium",
            "reason": "You may be able to deduct Traditional IRA contributions, reducing taxable income now.",
            "limit_2024": 7000,
        })

    # 401k
    if has_401k:
        recs.append({
            "type": "401k Max",
            "priority": "high",
            "reason": "Maximize 401k contributions ($23,000/yr) before taxable investing. Pre-tax reduces your bill now.",
            "limit_2024": 23000,
        })

    # HSA
    recs.append({
        "type": "HSA",
        "priority": "medium",
        "reason": "If on a High Deductible Health Plan, HSA is the only triple-tax-advantaged account (deductible, grows tax-free, tax-free withdrawals for medical).",
        "limit_2024": 4150 if filing_status == "single" else 8300,
    })

    # Self-employed accounts
    if income_1099 > 0:
        sep_limit = min(income_1099 * 0.25, 69000)
        recs.append({
            "type": "SEP-IRA or Solo 401k",
            "priority": "high",
            "reason": f"With ${income_1099:,.0f} in 1099 income, a SEP-IRA allows up to ${sep_limit:,.0f} in deductible contributions.",
            "limit_2024": round(sep_limit),
        })

    return {"recommendations": recs, "total_income": total_income, "filing_status": filing_status}
