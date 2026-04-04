from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Optional
import json

from ..database import get_db
from ..models import Account, Holding, RealEstate, Setting, BalanceSnapshot

router = APIRouter(prefix="/api/insights", tags=["insights"])


def _get_setting(db: Session, key: str, default=None):
    s = db.query(Setting).get(key)
    if s and s.value:
        return json.loads(s.value)
    return default


def _generate_insights(db: Session) -> list[dict]:
    insights = []
    accounts = db.query(Account).all()

    # Collect all holdings
    all_holdings: list[dict] = []
    total_value = 0
    by_type: dict[str, float] = {}

    for a in accounts:
        for h in a.holdings:
            mv = (h.last_price or 0) * (h.quantity or 0)
            all_holdings.append({
                "symbol": h.symbol,
                "market_value": mv,
                "account_name": a.name,
                "account_type": a.type,
            })
            total_value += mv
            by_type[a.type] = by_type.get(a.type, 0) + mv

    # Add real estate
    properties = db.query(RealEstate).all()
    for p in properties:
        equity = (p.effective_value or 0) - (p.mortgage_balance or 0)
        total_value += equity
        by_type["real_estate"] = by_type.get("real_estate", 0) + equity

    if total_value <= 0:
        return [{"title": "Add Data", "category": "info", "description": "Import account data to see insights.", "why": "Insights need portfolio data to analyze."}]

    # --- Concentration ---
    for h in all_holdings:
        if total_value > 0:
            pct = h["market_value"] / total_value * 100
            if pct > 20:
                insights.append({
                    "title": f"High Concentration: {h['symbol']}",
                    "category": "Risk",
                    "description": f"{h['symbol']} is {pct:.1f}% of your portfolio in {h['account_name']}.",
                    "why": "Single-stock concentration above 20% increases unsystematic risk. Consider diversifying.",
                })

    # --- Allocation ---
    risk_profile = _get_setting(db, "risk_profile", "moderate")
    targets = {
        "conservative": {"brokerage": 30, "crypto": 5, "real_estate": 30, "savings": 20, "roth_ira": 10, "401k": 5},
        "moderate": {"brokerage": 40, "crypto": 10, "real_estate": 25, "savings": 10, "roth_ira": 10, "401k": 5},
        "aggressive": {"brokerage": 50, "crypto": 20, "real_estate": 15, "savings": 5, "roth_ira": 5, "401k": 5},
    }.get(risk_profile, {})

    for atype, target_pct in targets.items():
        actual_pct = by_type.get(atype, 0) / total_value * 100 if total_value else 0
        deviation = actual_pct - target_pct
        if abs(deviation) > 10:
            direction = "overweight" if deviation > 0 else "underweight"
            insights.append({
                "title": f"{atype.replace('_', ' ').title()} {direction.title()}",
                "category": "Allocation",
                "description": f"{atype.replace('_', ' ').title()} is {actual_pct:.1f}% (target: {target_pct}% for {risk_profile} profile).",
                "why": f"Your {risk_profile} risk profile targets {target_pct}% in this category.",
            })

    # --- Liquidity ---
    monthly_expenses = _get_setting(db, "monthly_expenses", 5000)
    liquid = by_type.get("savings", 0) + by_type.get("checking", 0)
    months_runway = liquid / monthly_expenses if monthly_expenses > 0 else 0
    if months_runway < 6:
        insights.append({
            "title": "Low Liquidity",
            "category": "Liquidity",
            "description": f"You have {months_runway:.1f} months of expenses in liquid accounts (${liquid:,.0f}).",
            "why": "Financial advisors recommend 3-6 months of expenses in easily accessible accounts.",
        })
    elif months_runway > 12:
        insights.append({
            "title": "Excess Cash",
            "category": "Liquidity",
            "description": f"You have {months_runway:.1f} months of expenses sitting in cash (${liquid:,.0f}).",
            "why": "Cash above 12 months of expenses may be better deployed in investments.",
        })

    # --- Real Estate LTV ---
    for p in properties:
        if p.effective_value and p.mortgage_balance:
            ltv = p.mortgage_balance / p.effective_value * 100
            if ltv > 80:
                insights.append({
                    "title": f"High LTV: {p.address[:30]}",
                    "category": "Risk",
                    "description": f"Loan-to-value is {ltv:.1f}% on this property.",
                    "why": "LTV above 80% typically requires PMI and increases risk in a downturn.",
                })
            elif ltv < 50:
                insights.append({
                    "title": f"Refinance Opportunity: {p.address[:30]}",
                    "category": "Performance",
                    "description": f"LTV is only {ltv:.1f}%. You may qualify for better rates.",
                    "why": "Low LTV properties often qualify for the best mortgage rates.",
                })

    # --- Net Worth Trend ---
    snapshots = db.query(BalanceSnapshot).order_by(BalanceSnapshot.date).all()
    if len(snapshots) >= 2:
        by_date: dict[str, float] = {}
        for s in snapshots:
            d = s.date.isoformat()
            by_date[d] = by_date.get(d, 0) + s.balance
        dates = sorted(by_date.keys())
        if len(dates) >= 2:
            first = by_date[dates[0]]
            last = by_date[dates[-1]]
            if first > 0:
                growth = (last - first) / first * 100
                insights.append({
                    "title": "Net Worth Trend",
                    "category": "Trends",
                    "description": f"Net worth has {'grown' if growth > 0 else 'declined'} {abs(growth):.1f}% since tracking began.",
                    "why": f"From ${first:,.0f} to ${last:,.0f} over {len(dates)} data points.",
                })

    return insights


@router.get("")
def get_insights(db: Session = Depends(get_db)):
    return _generate_insights(db)
