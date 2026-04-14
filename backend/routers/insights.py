from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
import json
import math

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Account, BalanceSnapshot, DebtDetail, RealEstate, Setting, Transaction
from ..services.snapshots import DEBT_TYPES, compute_account_balance

router = APIRouter(prefix="/api/insights", tags=["insights"])


def _get_setting(db: Session, key: str, default=None):
    setting = db.query(Setting).get(key)
    if setting and setting.value:
        return json.loads(setting.value)
    return default


def _priority(score: float, high: float, medium: float, invert: bool = False) -> str:
    if invert:
        if score <= high:
            return "high"
        if score <= medium:
            return "medium"
        return "low"

    if score >= high:
        return "high"
    if score >= medium:
        return "medium"
    return "low"


def _aggregate_context(db: Session) -> dict:
    accounts = db.query(Account).all()
    properties = db.query(RealEstate).all()

    assets_by_type: dict[str, float] = defaultdict(float)
    total_assets = 0.0
    total_debt = 0.0
    total_minimum_payment = 0.0
    weighted_debt_apr_numerator = 0.0

    holdings_rows: list[dict] = []

    for account in accounts:
        balance = compute_account_balance(db, account)
        if account.type in DEBT_TYPES:
            total_debt += balance
            detail = db.query(DebtDetail).filter(DebtDetail.account_id == account.id).first()
            if detail:
                total_minimum_payment += float(detail.minimum_payment or 0)
                weighted_debt_apr_numerator += float(detail.interest_rate or 0) * balance
            continue

        assets_by_type[account.type] += balance
        total_assets += balance

        for holding in account.holdings:
            qty = holding.quantity or 0
            mv = (holding.last_price * qty) if holding.last_price is not None else (holding.cost_basis or 0)
            cost_total = holding.cost_basis if holding.cost_basis is not None else mv
            holdings_rows.append(
                {
                    "symbol": holding.symbol,
                    "market_value": float(mv or 0),
                    "cost_basis": float(cost_total or 0),
                    "account_type": account.type,
                }
            )

    real_estate_value = 0.0
    mortgage_total = 0.0
    for prop in properties:
        value = float(prop.effective_value or 0)
        mortgage = float(prop.mortgage_balance or 0)
        equity = value - mortgage
        assets_by_type["real_estate"] += equity
        total_assets += equity
        real_estate_value += value
        mortgage_total += mortgage

    net_worth = total_assets - total_debt

    income_w2 = float(_get_setting(db, "income_w2", 0) or 0)
    income_1099 = float(_get_setting(db, "income_1099", 0) or 0)
    annual_income = income_w2 + income_1099
    monthly_income = annual_income / 12 if annual_income > 0 else 0

    monthly_expenses = float(_get_setting(db, "monthly_expenses", 5000) or 0)
    monthly_contribution = float(_get_setting(db, "monthly_contribution", 0) or 0)
    risk_profile = str(_get_setting(db, "risk_profile", "moderate") or "moderate")

    retirement_target = _get_setting(db, "retirement_target_amount", None)
    if retirement_target is None:
        retirement_target = monthly_expenses * 12 * 25
    retirement_target = float(retirement_target or 0)

    snapshots = db.query(BalanceSnapshot).order_by(BalanceSnapshot.date).all()
    by_date: dict[str, float] = defaultdict(float)
    for snap in snapshots:
        by_date[snap.date.isoformat()] += float(snap.balance)

    return {
        "accounts": accounts,
        "holdings": holdings_rows,
        "assets_by_type": dict(assets_by_type),
        "total_assets": total_assets,
        "total_debt": total_debt,
        "total_minimum_payment": total_minimum_payment,
        "avg_debt_apr": (weighted_debt_apr_numerator / total_debt) if total_debt > 0 else 0.0,
        "net_worth": net_worth,
        "annual_income": annual_income,
        "monthly_income": monthly_income,
        "monthly_expenses": monthly_expenses,
        "monthly_contribution": monthly_contribution,
        "risk_profile": risk_profile,
        "retirement_target": retirement_target,
        "snapshots_by_date": dict(sorted(by_date.items())),
        "real_estate_value": real_estate_value,
        "mortgage_total": mortgage_total,
        "properties": properties,
    }


def _generate_insights(db: Session) -> list[dict]:
    ctx = _aggregate_context(db)

    if ctx["total_assets"] <= 0 and ctx["total_debt"] <= 0:
        return [
            {
                "title": "Add your first account",
                "description": "Import or manually add account balances to unlock the dashboard insights engine.",
                "category": "Behavioral",
                "priority": "high",
                "action": "Go to Accounts and add at least one cash or investment account.",
                "why": "Insights are deterministic and local-only, but they need portfolio data to evaluate your position.",
            }
        ]

    insights: list[dict] = []
    total_assets = max(ctx["total_assets"], 0.0)
    monthly_expenses = max(ctx["monthly_expenses"], 1.0)
    annual_income = ctx["annual_income"]
    monthly_income = ctx["monthly_income"]
    total_debt = ctx["total_debt"]
    monthly_contribution = ctx["monthly_contribution"]

    holdings = ctx["holdings"]
    assets_by_type = ctx["assets_by_type"]

    # 1) Concentration risk
    top_holding = max(holdings, key=lambda h: h["market_value"], default=None)
    concentration_pct = (top_holding["market_value"] / total_assets * 100) if top_holding and total_assets else 0.0
    concentration_priority = _priority(concentration_pct, high=40, medium=25)
    insights.append(
        {
            "title": "Concentration Risk",
            "description": (
                f"Largest position is {top_holding['symbol']} at {concentration_pct:.1f}% of assets."
                if top_holding
                else "No concentrated single-name positions detected in tracked holdings."
            ),
            "category": "Risk",
            "priority": concentration_priority,
            "action": "Keep any single position below 40% by trimming outsized winners over time.",
            "why": "High concentration increases unsystematic risk and can dominate portfolio volatility.",
        }
    )

    # 2) Liquidity ratio
    liquid_assets = assets_by_type.get("checking", 0) + assets_by_type.get("savings", 0)
    runway_months = liquid_assets / monthly_expenses if monthly_expenses > 0 else 0
    insights.append(
        {
            "title": "Liquidity Ratio (Emergency Fund)",
            "description": f"Liquid runway is {runway_months:.1f} months ({liquid_assets:,.0f} vs {monthly_expenses:,.0f} monthly expenses).",
            "category": "Liquidity",
            "priority": _priority(runway_months, high=0, medium=3, invert=True),
            "action": "Target 3–6 months of expenses in checking/savings before increasing risk.",
            "why": "Liquidity protects against forced selling during emergencies and market drawdowns.",
        }
    )

    # 3) Allocation drift
    bucket_map = {
        "equities": {"brokerage", "401k", "roth_ira", "hsa"},
        "crypto": {"crypto"},
        "cash": {"checking", "savings"},
        "real_estate": {"real_estate"},
    }
    bucket_totals = {
        bucket: sum(assets_by_type.get(t, 0) for t in types)
        for bucket, types in bucket_map.items()
    }

    targets = {
        "conservative": {"equities": 35, "crypto": 3, "cash": 35, "real_estate": 27},
        "moderate": {"equities": 50, "crypto": 8, "cash": 20, "real_estate": 22},
        "aggressive": {"equities": 62, "crypto": 12, "cash": 10, "real_estate": 16},
    }.get(ctx["risk_profile"], {"equities": 50, "crypto": 8, "cash": 20, "real_estate": 22})

    drift = 0.0
    drift_parts = []
    for bucket, target in targets.items():
        actual = (bucket_totals[bucket] / total_assets * 100) if total_assets else 0.0
        delta = abs(actual - target)
        drift += delta
        drift_parts.append(f"{bucket}: {actual:.0f}% (target {target:.0f}%)")

    insights.append(
        {
            "title": "Allocation Drift",
            "description": "; ".join(drift_parts),
            "category": "Allocation",
            "priority": _priority(drift, high=35, medium=20),
            "action": "Rebalance the most off-target bucket first, then reassess monthly.",
            "why": "Drift compounds over time and can move your risk profile away from intent.",
        }
    )

    # 4) Debt-to-income ratio
    dti = (ctx["total_minimum_payment"] / monthly_income * 100) if monthly_income > 0 else 0.0
    insights.append(
        {
            "title": "Debt-to-Income Ratio",
            "description": (
                f"Estimated DTI is {dti:.1f}% using minimum payments ({ctx['total_minimum_payment']:,.0f}/mo)."
                if monthly_income > 0
                else "Set W-2 and 1099 income in Settings to compute DTI accurately."
            ),
            "category": "Debt",
            "priority": _priority(dti, high=36, medium=20),
            "action": "Keep DTI below 36% and prioritize high-interest balances if above threshold.",
            "why": "DTI is a core affordability and credit-health metric used by lenders.",
        }
    )

    # 5) Asset class diversification
    active_classes = sum(1 for v in bucket_totals.values() if v > 0)
    insights.append(
        {
            "title": "Asset Class Diversification",
            "description": f"You currently hold {active_classes} active asset classes.",
            "category": "Risk",
            "priority": "high" if active_classes < 3 else ("medium" if active_classes == 3 else "low"),
            "action": "Aim for exposure across at least three classes: equities, cash, and one diversifier.",
            "why": "Diversification lowers dependency on a single market regime.",
        }
    )

    # 6) Net worth growth rate
    date_keys = list(ctx["snapshots_by_date"].keys())
    growth_monthly = 0.0
    if len(date_keys) >= 2:
        first_val = ctx["snapshots_by_date"][date_keys[0]]
        last_val = ctx["snapshots_by_date"][date_keys[-1]]
        months = max((date.fromisoformat(date_keys[-1]) - date.fromisoformat(date_keys[0])).days / 30.44, 1)
        growth_monthly = (last_val - first_val) / months

    insights.append(
        {
            "title": "Net Worth Growth Rate",
            "description": f"Estimated net worth trend is {growth_monthly:,.0f} per month based on your snapshot history.",
            "category": "Trends",
            "priority": "high" if growth_monthly < 0 else ("medium" if growth_monthly < 1000 else "low"),
            "action": "Maintain positive monthly net worth momentum through savings consistency and debt reduction.",
            "why": "Growth rate is a leading indicator for timeline-based planning.",
        }
    )

    # 7) Retirement readiness / FIRE timeline
    retirement_target = max(ctx["retirement_target"], 1.0)
    investable = max(total_assets - assets_by_type.get("checking", 0) - assets_by_type.get("savings", 0), 0)
    monthly_progress = monthly_contribution if monthly_contribution > 0 else max(monthly_income - monthly_expenses, 0)
    years_to_fire = None
    if monthly_progress > 0 and investable < retirement_target:
        years_to_fire = (retirement_target - investable) / (monthly_progress * 12)

    readiness_pct = investable / retirement_target * 100
    insights.append(
        {
            "title": "Retirement Readiness / FIRE Timeline",
            "description": (
                f"You are at {readiness_pct:.1f}% of target; projected timeline is {years_to_fire:.1f} years."
                if years_to_fire is not None
                else f"You are at {readiness_pct:.1f}% of target. Increase monthly contributions to project a timeline."
            ),
            "category": "Retirement",
            "priority": "high" if readiness_pct < 25 else ("medium" if readiness_pct < 60 else "low"),
            "action": "Increase recurring monthly contributions to compress your expected FIRE date.",
            "why": "Timeline projection translates static net worth into actionable pace-to-goal.",
        }
    )

    # 8) 401k/IRA contribution rate
    contribution_accounts = {"401k", "roth_ira"}
    year_start = date(date.today().year, 1, 1)
    retirement_contrib = (
        db.query(Transaction)
        .join(Account, Account.id == Transaction.account_id)
        .filter(Account.type.in_(contribution_accounts), Transaction.date >= year_start)
        .all()
    )
    contributed = sum(abs(float(t.amount or 0)) for t in retirement_contrib if (t.amount or 0) > 0)
    # Use settings contribution as fallback when transactions are sparse.
    if contributed == 0 and monthly_contribution > 0:
        contributed = monthly_contribution * max(date.today().month, 1)

    annual_limit_proxy = 23_500 + 7_000
    contribution_pct = (contributed / annual_limit_proxy * 100) if annual_limit_proxy > 0 else 0.0
    insights.append(
        {
            "title": "401k / IRA Contribution Rate",
            "description": f"Estimated retirement contributions are {contributed:,.0f} YTD ({contribution_pct:.1f}% of annual limits proxy).",
            "category": "Retirement",
            "priority": "high" if contribution_pct < 25 else ("medium" if contribution_pct < 60 else "low"),
            "action": "Set auto-contributions that pace toward annual limits by year-end.",
            "why": "Retirement tax-advantaged space is use-it-or-lose-it each calendar year.",
        }
    )

    # 9) Compound growth projection
    projection_10y = investable * (1.06 ** 10) + (monthly_progress * 12) * ((1.06 ** 10 - 1) / 0.06)
    insights.append(
        {
            "title": "Compound Growth Projection",
            "description": f"At 6% annual growth, 10-year projection is {projection_10y:,.0f}.",
            "category": "Retirement",
            "priority": "low",
            "action": "Focus on contribution consistency first; compounding amplifies disciplined deposits.",
            "why": "Long-term outcomes are most sensitive to time in market and sustained contributions.",
        }
    )

    # 10) Debt payoff trajectory
    payoff_months = (total_debt / ctx["total_minimum_payment"]) if ctx["total_minimum_payment"] > 0 else None
    payoff_priority = "high" if (payoff_months and payoff_months > 120) else ("medium" if (payoff_months and payoff_months > 48) else "low")
    insights.append(
        {
            "title": "Debt Payoff Trajectory",
            "description": (
                f"At current minimum payments, debt payoff is ~{payoff_months:.0f} months."
                if payoff_months is not None and total_debt > 0
                else "No active debt payoff schedule detected from minimum-payment data."
            ),
            "category": "Debt",
            "priority": payoff_priority,
            "action": "Add targeted extra principal to the highest APR balance to shorten payoff duration.",
            "why": "Trajectory highlights whether debt is shrinking at a pace aligned with wealth goals.",
        }
    )

    # 11) Total interest burden
    annual_interest = total_debt * (ctx["avg_debt_apr"] / 100)
    insights.append(
        {
            "title": "Total Interest Burden",
            "description": f"Estimated annual interest cost is {annual_interest:,.0f} at {ctx['avg_debt_apr']:.1f}% weighted APR.",
            "category": "Debt",
            "priority": "high" if annual_interest > 5000 else ("medium" if annual_interest > 1500 else "low"),
            "action": "Prioritize debt principal payments where APR materially exceeds expected portfolio return.",
            "why": "Interest drag directly reduces investable cash flow and slows net worth growth.",
        }
    )

    # 12) Mortgage affordability (LTV)
    avg_ltv = (ctx["mortgage_total"] / ctx["real_estate_value"] * 100) if ctx["real_estate_value"] > 0 else 0.0
    insights.append(
        {
            "title": "Mortgage Affordability (LTV)",
            "description": (
                f"Portfolio real-estate LTV is {avg_ltv:.1f}% across {len(ctx['properties'])} properties."
                if ctx["properties"]
                else "No mortgage-backed real-estate positions detected."
            ),
            "category": "Risk",
            "priority": "high" if avg_ltv > 85 else ("medium" if avg_ltv > 70 else "low"),
            "action": "Aim to keep LTV below 80% to improve refinancing options and reduce risk.",
            "why": "Lower LTV generally improves borrowing resilience and reduces payment pressure.",
        }
    )

    # 13) Savings rate trend
    savings_rate = ((annual_income - (monthly_expenses * 12)) / annual_income * 100) if annual_income > 0 else 0.0
    insights.append(
        {
            "title": "Savings Rate Trend",
            "description": (
                f"Estimated savings rate is {savings_rate:.1f}% from income minus expense settings."
                if annual_income > 0
                else "Add income settings to compute savings-rate trend."
            ),
            "category": "Behavioral",
            "priority": "high" if savings_rate < 10 else ("medium" if savings_rate < 20 else "low"),
            "action": "Keep savings rate above 20% to accelerate financial freedom planning.",
            "why": "Savings rate is a controllable input with outsized effect on timeline outcomes.",
        }
    )

    # 14) Income stability / volatility
    six_month_start = date.today() - timedelta(days=183)
    income_rows = (
        db.query(Transaction)
        .filter(Transaction.date >= six_month_start)
        .all()
    )

    monthly_income_buckets: dict[str, float] = defaultdict(float)
    income_types = {"income", "salary", "paycheck", "bonus", "freelance", "deposit", "rental_income"}
    for row in income_rows:
        if (row.type or "").lower() not in income_types:
            continue
        if row.amount is None or row.amount <= 0:
            continue
        key = row.date.strftime("%Y-%m")
        monthly_income_buckets[key] += float(row.amount)

    monthly_income_samples = list(monthly_income_buckets.values())
    if len(monthly_income_samples) >= 3:
        mean_income = sum(monthly_income_samples) / len(monthly_income_samples)
        variance = sum((value - mean_income) ** 2 for value in monthly_income_samples) / len(monthly_income_samples)
        cv = math.sqrt(variance) / mean_income if mean_income > 0 else 0
    else:
        cv = 0.05 if annual_income > 0 else 0

    insights.append(
        {
            "title": "Income Stability / Volatility",
            "description": f"Income volatility coefficient is {cv:.2f} (lower is more stable).",
            "category": "Trends",
            "priority": "high" if cv > 0.35 else ("medium" if cv > 0.2 else "low"),
            "action": "Maintain a larger emergency buffer when monthly income swings are elevated.",
            "why": "Income volatility increases planning uncertainty and required liquidity.",
        }
    )

    # 15) Passive vs earned income
    passive_types = {"dividend", "interest", "rental_income", "passive_income"}
    passive_income = 0.0
    earned_income = 0.0
    twelve_month_start = date.today() - timedelta(days=365)
    last_year_rows = db.query(Transaction).filter(Transaction.date >= twelve_month_start).all()
    for row in last_year_rows:
        if row.amount is None or row.amount <= 0:
            continue
        ttype = (row.type or "").lower()
        if ttype in passive_types:
            passive_income += float(row.amount)
        elif ttype in income_types:
            earned_income += float(row.amount)

    if earned_income == 0 and annual_income > 0:
        earned_income = annual_income

    passive_pct = (passive_income / (passive_income + earned_income) * 100) if (passive_income + earned_income) > 0 else 0.0
    insights.append(
        {
            "title": "Passive vs Earned Income",
            "description": f"Passive income represents {passive_pct:.1f}% of tracked income flows.",
            "category": "Performance",
            "priority": "low" if passive_pct >= 10 else ("medium" if passive_pct >= 3 else "high"),
            "action": "Increase compounding assets and yield sources to reduce reliance on earned income.",
            "why": "A higher passive-income share improves financial flexibility and downside resilience.",
        }
    )

    return insights


@router.get("")
def get_insights(db: Session = Depends(get_db)):
    return _generate_insights(db)


@router.post("/chat")
async def insights_chat(body: dict, db: Session = Depends(get_db)):
    """Ask Claude a question about your portfolio. Requires Claude API key in Settings."""
    from .. import ai

    if not ai.is_configured():
        from fastapi import HTTPException

        raise HTTPException(400, "Claude API key not configured. Add it in Settings.")

    question = (body.get("message") or "").strip()
    if not question:
        from fastapi import HTTPException

        raise HTTPException(400, "message is required")

    insights = _generate_insights(db)
    ctx = _aggregate_context(db)

    allocation_summary = ", ".join(
        f"{k.replace('_', ' ')}: {(v / ctx['total_assets'] * 100):.1f}%"
        for k, v in sorted(ctx["assets_by_type"].items(), key=lambda item: -item[1])
        if ctx["total_assets"] > 0 and v > 0
    )

    active_insights = [
        f"[{ins['priority'].upper()}] {ins['title']}: {ins['description']}"
        for ins in insights
        if ins.get("priority") in {"high", "medium"}
    ][:8]

    system = f"""You are a personal finance advisor for a locally-hosted finance app called Libertas.
The user's portfolio summary:
- Net worth: ${ctx['net_worth']:,.0f}
- Monthly expenses: ${ctx['monthly_expenses']:,.0f}
- Allocation: {allocation_summary or 'no data'}
- Active insights: {'; '.join(active_insights) if active_insights else 'none'}

Give concise, actionable advice. Be direct. Max 3 paragraphs."""

    reply = await ai.chat([{"role": "user", "content": question}], system=system)
    return {"reply": reply}
