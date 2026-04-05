from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Optional
import json
import math
from datetime import date

from ..database import get_db
from ..models import Account, Holding, RealEstate, Setting, BalanceSnapshot

router = APIRouter(prefix="/api/insights", tags=["insights"])

DEBT_TYPES = {"credit_card", "student_loan", "auto_loan", "personal_loan"}


def _get_setting(db: Session, key: str, default=None):
    s = db.query(Setting).get(key)
    if s and s.value:
        return json.loads(s.value)
    return default


def _generate_insights(db: Session) -> list[dict]:
    insights = []
    accounts = db.query(Account).all()

    # Collect all holdings and balances
    all_holdings: list[dict] = []
    total_assets = 0.0
    total_debt = 0.0
    by_type: dict[str, float] = {}

    for a in accounts:
        if a.type in DEBT_TYPES:
            snap = (
                db.query(BalanceSnapshot)
                .filter(BalanceSnapshot.account_id == a.id)
                .order_by(BalanceSnapshot.date.desc())
                .first()
            )
            total_debt += snap.balance if snap else 0.0
            continue

        for h in a.holdings:
            mv = (h.last_price or 0) * (h.quantity or 0)
            all_holdings.append({
                "symbol": h.symbol,
                "market_value": mv,
                "cost_basis": (h.cost_basis or 0) * (h.quantity or 0),
                "account_name": a.name,
                "account_type": a.type,
            })
            total_assets += mv
            by_type[a.type] = by_type.get(a.type, 0) + mv

        if not a.holdings:
            snap = (
                db.query(BalanceSnapshot)
                .filter(BalanceSnapshot.account_id == a.id)
                .order_by(BalanceSnapshot.date.desc())
                .first()
            )
            bal = snap.balance if snap else 0.0
            total_assets += bal
            by_type[a.type] = by_type.get(a.type, 0) + bal

    # Add real estate equity
    properties = db.query(RealEstate).all()
    for p in properties:
        equity = (p.effective_value or 0) - (p.mortgage_balance or 0)
        total_assets += equity
        by_type["real_estate"] = by_type.get("real_estate", 0) + equity

    total_net_worth = total_assets - total_debt

    if total_assets <= 0:
        return [{"title": "Add Data", "category": "info", "description": "Import account data to see insights.", "why": "Insights need portfolio data to analyze."}]

    monthly_expenses = _get_setting(db, "monthly_expenses", 5000)
    annual_expenses = monthly_expenses * 12
    risk_profile = _get_setting(db, "risk_profile", "moderate")
    birth_year = _get_setting(db, "birth_year", None)
    annual_income = _get_setting(db, "annual_income", None)
    retirement_age = _get_setting(db, "retirement_age", 65)

    # ── CONCENTRATION ────────────────────────────────────────────────────────
    for h in all_holdings:
        if total_assets > 0:
            pct = h["market_value"] / total_assets * 100
            if pct > 20:
                insights.append({
                    "title": f"High Concentration: {h['symbol']}",
                    "category": "Risk",
                    "priority": "high",
                    "action": f"Consider trimming {h['symbol']} and reinvesting proceeds into diversified funds.",
                    "description": f"{h['symbol']} is {pct:.1f}% of your portfolio in {h['account_name']}.",
                    "why": "Single-stock concentration above 20% increases unsystematic risk. Consider diversifying.",
                })

    # ── ALLOCATION ───────────────────────────────────────────────────────────
    targets = {
        "conservative": {"brokerage": 30, "crypto": 5, "real_estate": 30, "savings": 20, "roth_ira": 10, "401k": 5},
        "moderate":     {"brokerage": 40, "crypto": 10, "real_estate": 25, "savings": 10, "roth_ira": 10, "401k": 5},
        "aggressive":   {"brokerage": 50, "crypto": 20, "real_estate": 15, "savings": 5, "roth_ira": 5, "401k": 5},
    }.get(risk_profile, {})

    for atype, target_pct in targets.items():
        actual_pct = by_type.get(atype, 0) / total_assets * 100 if total_assets else 0
        deviation = actual_pct - target_pct
        if abs(deviation) > 10:
            direction = "overweight" if deviation > 0 else "underweight"
            label = atype.replace('_', ' ').title()
            action = (
                f"Reduce {label} exposure by rebalancing into underweight categories."
                if direction == "overweight"
                else f"Increase {label} allocation toward your {target_pct}% target."
            )
            insights.append({
                "title": f"{label} {direction.title()}",
                "category": "Allocation",
                "priority": "medium",
                "action": action,
                "description": f"{label} is {actual_pct:.1f}% (target: {target_pct}% for {risk_profile} profile).",
                "why": f"Your {risk_profile} risk profile targets {target_pct}% in this category.",
            })

    # ── LIQUIDITY ────────────────────────────────────────────────────────────
    liquid = by_type.get("savings", 0) + by_type.get("checking", 0)
    months_runway = liquid / monthly_expenses if monthly_expenses > 0 else 0
    if months_runway < 6:
        insights.append({
            "title": "Low Liquidity",
            "category": "Liquidity",
            "priority": "high",
            "action": f"Build cash reserves to ${monthly_expenses * 6:,.0f} (6 months of expenses) before investing more.",
            "description": f"You have {months_runway:.1f} months of expenses in liquid accounts (${liquid:,.0f}).",
            "why": "Financial advisors recommend 3–6 months of expenses in easily accessible accounts.",
        })
    elif months_runway > 12:
        insights.append({
            "title": "Excess Cash",
            "category": "Liquidity",
            "priority": "low",
            "action": "Consider investing the excess cash above 6 months of expenses into a diversified portfolio.",
            "description": f"You have {months_runway:.1f} months of expenses sitting in cash (${liquid:,.0f}).",
            "why": "Cash above 12 months of expenses may be better deployed in investments.",
        })

    # ── REAL ESTATE LTV ──────────────────────────────────────────────────────
    for p in properties:
        if p.effective_value and p.mortgage_balance:
            ltv = p.mortgage_balance / p.effective_value * 100
            if ltv > 80:
                insights.append({
                    "title": f"High LTV: {p.address[:30]}",
                    "category": "Risk",
                    "priority": "medium",
                    "action": "Make extra principal payments to get below 80% LTV and eliminate PMI.",
                    "description": f"Loan-to-value is {ltv:.1f}% on this property.",
                    "why": "LTV above 80% typically requires PMI and increases risk in a downturn.",
                })
            elif ltv < 50:
                insights.append({
                    "title": f"Refinance Opportunity: {p.address[:30]}",
                    "category": "Performance",
                    "priority": "low",
                    "action": "Contact lenders to compare current rates — your LTV qualifies you for the best pricing.",
                    "description": f"LTV is only {ltv:.1f}%. You may qualify for better rates.",
                    "why": "Low LTV properties often qualify for the best mortgage rates.",
                })

    # ── NET WORTH TREND ──────────────────────────────────────────────────────
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
                    "priority": "low",
                    "action": "Keep importing data regularly to maintain an accurate growth picture.",
                    "description": f"Net worth has {'grown' if growth > 0 else 'declined'} {abs(growth):.1f}% since tracking began.",
                    "why": f"From ${first:,.0f} to ${last:,.0f} over {len(dates)} data points.",
                })

        # Declining streak (3+ consecutive months down)
        if len(dates) >= 4:
            recent = [by_date[d] for d in dates[-4:]]
            if all(recent[i] > recent[i + 1] for i in range(3)):
                insights.append({
                    "title": "Net Worth Declining 3+ Months",
                    "category": "Behavioral",
                    "priority": "high",
                    "action": "Review your monthly spending and investment contributions for the past quarter.",
                    "description": "Your net worth has declined for at least three consecutive months.",
                    "why": "A sustained downward trend warrants a review of spending, contributions, and asset performance.",
                })

    # ── 401k ─────────────────────────────────────────────────────────────────
    k401_accounts = [a for a in accounts if a.type == "401k"]
    k401_balance = by_type.get("401k", 0)

    if not k401_accounts and total_assets > 10_000:
        insights.append({
            "title": "No 401k Detected",
            "category": "Retirement",
            "priority": "high",
            "action": "Enroll in your employer's 401k and contribute at least enough to capture any match.",
            "description": "You have no 401k account tracked. The 2024 contribution limit is $23,000 ($30,500 if 50+).",
            "why": "401k contributions reduce taxable income and grow tax-deferred. Employer match is free money.",
        })
    elif k401_accounts and k401_balance / total_assets < 0.05 and total_assets > 50_000:
        insights.append({
            "title": "401k Appears Underutilized",
            "category": "Retirement",
            "priority": "high",
            "action": "Increase your 401k contribution rate — aim for $23,000/yr or at minimum the full employer match.",
            "description": f"Your 401k is ${k401_balance:,.0f} — only {k401_balance / total_assets * 100:.1f}% of total assets.",
            "why": "Maximizing 401k contributions (up to $23,000/yr) is one of the highest-impact tax moves available.",
        })

    # ── RETIREMENT READINESS (4% rule) ───────────────────────────────────────
    fire_target = annual_expenses * 25
    investable = total_assets - by_type.get("real_estate", 0) - by_type.get("savings", 0) - by_type.get("checking", 0)
    if fire_target > 0 and investable > 0:
        pct_to_fire = investable / fire_target * 100
        if pct_to_fire < 100:
            insights.append({
                "title": f"Retirement Readiness: {pct_to_fire:.0f}%",
                "category": "Retirement",
                "priority": "medium",
                "action": f"Increase monthly contributions and check the Retirement page for a personalized plan.",
                "description": f"At ${monthly_expenses:,.0f}/mo expenses, your FIRE number is ${fire_target:,.0f}. You're at ${investable:,.0f} ({pct_to_fire:.0f}%).",
                "why": "The 4% rule: you need 25× annual expenses invested to retire safely with a 4% withdrawal rate.",
            })

    # ── DEBT ─────────────────────────────────────────────────────────────────
    if total_debt > 0:
        from ..models import DebtDetail
        debt_accounts = [a for a in accounts if a.type in DEBT_TYPES]
        for da in debt_accounts:
            detail = db.query(DebtDetail).filter(DebtDetail.account_id == da.id).first()
            if detail and detail.interest_rate > 15:
                snap = (
                    db.query(BalanceSnapshot)
                    .filter(BalanceSnapshot.account_id == da.id)
                    .order_by(BalanceSnapshot.date.desc())
                    .first()
                )
                bal = snap.balance if snap else 0
                if bal > 0:
                    insights.append({
                        "title": f"High-Interest Debt: {da.name}",
                        "category": "Debt",
                        "priority": "high",
                        "action": f"Pay more than the minimum on {da.name} — every extra dollar saves {detail.interest_rate:.0f}¢ in interest.",
                        "description": f"{da.name} carries {detail.interest_rate:.1f}% APR with ${bal:,.0f} balance.",
                        "why": "High-interest debt (>15%) costs more than most investments earn. Pay this down before investing further.",
                    })

        if annual_income and annual_income > 0:
            dti = total_debt / annual_income * 100
            if dti > 36:
                insights.append({
                    "title": f"High Debt-to-Income: {dti:.0f}%",
                    "category": "Debt",
                    "priority": "high",
                    "action": "Focus extra income on debt payoff before taking on new credit or large purchases.",
                    "description": f"Total debt of ${total_debt:,.0f} is {dti:.0f}% of your annual income.",
                    "why": "Lenders use 36% DTI as a threshold. Above this, borrowing becomes harder and financial flexibility shrinks.",
                })

        re_pct = by_type.get("real_estate", 0) / total_assets * 100 if total_assets else 0
        if re_pct > 50:
            insights.append({
                "title": "Real Estate Illiquidity Risk",
                "category": "Risk",
                "priority": "medium",
                "action": "Build liquid savings and diversify into financial assets to reduce concentration in real estate.",
                "description": f"Real estate is {re_pct:.0f}% of your assets (${by_type.get('real_estate', 0):,.0f}).",
                "why": "Heavy real estate concentration creates liquidity risk — property can't be sold quickly in a downturn.",
            })

    # ── TAX ──────────────────────────────────────────────────────────────────
    tlh_candidates = []
    for h in all_holdings:
        if h["cost_basis"] > 0 and h["market_value"] > 0:
            loss_pct = (h["market_value"] - h["cost_basis"]) / h["cost_basis"] * 100
            if loss_pct < -20:
                tlh_candidates.append((h["symbol"], loss_pct, h["market_value"] - h["cost_basis"]))

    if tlh_candidates:
        worst = min(tlh_candidates, key=lambda x: x[1])
        total_loss = sum(x[2] for x in tlh_candidates)
        insights.append({
            "title": "Tax-Loss Harvesting Opportunity",
            "category": "Tax",
            "priority": "medium",
            "action": f"Sell {worst[0]} to realize the loss, then repurchase a similar (not identical) fund after 30 days.",
            "description": f"{len(tlh_candidates)} position(s) are down 20%+. {worst[0]} is down {abs(worst[1]):.0f}% (${abs(total_loss):,.0f} in unrealized losses).",
            "why": "Selling losing positions to offset capital gains can reduce your tax bill. Repurchase after 30 days to maintain exposure.",
        })

    bond_keywords = {"BND", "AGG", "TLT", "IEF", "SHY", "BOND", "VBTLX", "FXNAX", "LQD", "HYG", "TIPS"}
    misplaced = [
        h for h in all_holdings
        if h["account_type"] == "brokerage"
        and any(kw in h["symbol"].upper() for kw in bond_keywords)
    ]
    if misplaced:
        symbols = ", ".join(h["symbol"] for h in misplaced[:3])
        insights.append({
            "title": "Asset Location: Bonds in Taxable Account",
            "category": "Tax",
            "priority": "medium",
            "action": f"Move {symbols} into your IRA or 401k, and hold equities in the taxable account instead.",
            "description": f"{symbols} appear to be bond funds held in a taxable brokerage account.",
            "why": "Bonds generate ordinary-income dividends. Holding them in a tax-deferred account (IRA, 401k) shields that income from annual taxes.",
        })

    # ── BEHAVIORAL ───────────────────────────────────────────────────────────
    today = date.today()
    for a in accounts:
        if a.type in DEBT_TYPES:
            continue
        snap = (
            db.query(BalanceSnapshot)
            .filter(BalanceSnapshot.account_id == a.id)
            .order_by(BalanceSnapshot.date.desc())
            .first()
        )
        if snap:
            days_old = (today - snap.date).days
            if days_old > 30:
                insights.append({
                    "title": f"Stale Data: {a.name}",
                    "category": "Behavioral",
                    "priority": "low",
                    "action": f"Download a fresh CSV from your {a.name} institution and drop it into Import.",
                    "description": f"{a.name} hasn't been updated in {days_old} days.",
                    "why": "Stale data leads to inaccurate net worth calculations. Import a fresh CSV to stay current.",
                })

    crypto_pct = by_type.get("crypto", 0) / total_assets * 100 if total_assets else 0
    if crypto_pct > 20:
        insights.append({
            "title": f"High Crypto Allocation: {crypto_pct:.0f}%",
            "category": "Risk",
            "priority": "medium",
            "action": "Consider gradually rebalancing crypto gains into less volatile assets.",
            "description": f"Crypto is {crypto_pct:.0f}% of your portfolio (${by_type.get('crypto', 0):,.0f}).",
            "why": "Crypto is highly volatile. Most advisors suggest limiting it to 5–10% of a portfolio unless you have high risk tolerance.",
        })

    # ── ESTATE ───────────────────────────────────────────────────────────────
    if total_net_worth > 500_000:
        insights.append({
            "title": "Estate Plan Review",
            "category": "Estate",
            "priority": "medium",
            "action": "Review or create a will and update beneficiary designations on all accounts.",
            "description": f"With a net worth of ${total_net_worth:,.0f}, an outdated or missing estate plan creates risk.",
            "why": "Above $500k, a will and updated beneficiary designations become critical. Dying intestate can delay distribution and increase taxes.",
        })
    if total_net_worth > 1_000_000:
        insights.append({
            "title": "Consider a Trust",
            "category": "Estate",
            "priority": "low",
            "action": "Consult an estate attorney about a revocable living trust to streamline asset transfer.",
            "description": f"At ${total_net_worth:,.0f}, a revocable living trust may help avoid probate.",
            "why": "Trusts allow assets to pass directly to heirs, bypass probate court, and offer more control than a will alone.",
        })

    # ── INSURANCE (commented out — data not yet tracked) ─────────────────────
    # if total_net_worth > 500_000:
    #     insights.append({
    #         "title": "Umbrella Insurance",
    #         "category": "Insurance",
    #         "description": f"Net worth of ${total_net_worth:,.0f} may warrant a personal umbrella policy.",
    #         "why": "Umbrella policies add $1M+ of liability coverage above auto/home limits, typically for ~$200/yr. High net worth makes you a target for lawsuits.",
    #     })
    # if annual_income:
    #     insights.append({
    #         "title": "Disability Insurance Check",
    #         "category": "Insurance",
    #         "description": "Disability insurance is the most commonly overlooked coverage gap.",
    #         "why": "A 35-year-old has a 1 in 4 chance of becoming disabled before retirement. Short-term disability rarely covers more than 3 months.",
    #     })

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

    # Build context from current portfolio state
    insights = _generate_insights(db)

    from ..models import Account, BalanceSnapshot
    accounts = db.query(Account).all()
    total_assets = 0.0
    by_type: dict[str, float] = {}
    for a in accounts:
        for h in a.holdings:
            mv = (h.last_price or 0) * (h.quantity or 0)
            total_assets += mv
            by_type[a.type] = by_type.get(a.type, 0) + mv
        if not a.holdings:
            snap = (
                db.query(BalanceSnapshot)
                .filter(BalanceSnapshot.account_id == a.id)
                .order_by(BalanceSnapshot.date.desc())
                .first()
            )
            bal = snap.balance if snap else 0.0
            total_assets += bal
            by_type[a.type] = by_type.get(a.type, 0) + bal

    monthly_expenses = _get_setting(db, "monthly_expenses", 5000)

    allocation_summary = ", ".join(
        f"{k.replace('_',' ')}: {v/total_assets*100:.1f}%"
        for k, v in sorted(by_type.items(), key=lambda x: -x[1])
        if v > 0 and total_assets > 0
    )

    active_insights = [
        f"[{ins['priority'].upper()}] {ins['title']}: {ins['description']}"
        for ins in insights
        if ins.get("priority") in ("high", "medium")
    ][:8]

    system = f"""You are a personal finance advisor for a locally-hosted finance app called Libertas.
The user's portfolio summary:
- Total assets: ${total_assets:,.0f}
- Monthly expenses: ${monthly_expenses:,.0f}
- Allocation: {allocation_summary or 'no data'}
- Active insights: {'; '.join(active_insights) if active_insights else 'none'}

Give concise, actionable advice. Be direct. No disclaimers about not being a licensed advisor — the user knows this is an AI tool. Max 3 paragraphs."""

    reply = await ai.chat([{"role": "user", "content": question}], system=system)
    return {"reply": reply}
