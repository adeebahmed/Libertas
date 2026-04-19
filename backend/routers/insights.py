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


def _usd(value: float) -> str:
    return f"${value:,.0f}"


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
                "title": "Add your first account to get started",
                "description": "Import or manually add account balances to unlock personalized insights.",
                "category": "Behavioral",
                "priority": "high",
                "action": "Go to Accounts and add at least one cash or investment account.",
                "why": "Insights are local-only and need portfolio data to give you meaningful guidance.",
                "icon": "sparkle",
                "institution_hint": None,
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
    trim_needed = max((top_holding["market_value"] - (0.40 * total_assets)), 0.0) if top_holding else 0.0
    if top_holding and concentration_pct > 40:
        conc_title = f"{top_holding['symbol']} makes up {concentration_pct:.0f}% of your portfolio"
        conc_desc = f"That's a lot in one stock. Spreading out {_usd(trim_needed)} would bring it under 40% and reduce your risk."
        conc_action = f"Trim {top_holding['symbol']} by {_usd(trim_needed)} and move it into other holdings."
    elif top_holding and concentration_pct > 25:
        conc_title = f"{top_holding['symbol']} is {concentration_pct:.0f}% of your portfolio"
        conc_desc = "Worth watching — if this stock drops sharply it'll have an outsized effect on your balance."
        conc_action = "Direct new contributions to other holdings until this drops below 25%."
    else:
        conc_title = "No single investment dominates your portfolio"
        conc_desc = "Your largest position is well below 25% of assets — good spread."
        conc_action = "Keep new deposits spread across your holdings."
    insights.append(
        {
            "title": conc_title,
            "description": conc_desc,
            "category": "Risk",
            "priority": concentration_priority,
            "action": conc_action,
            "why": "Putting too much in one stock means a single bad day can hurt your whole portfolio.",
            "icon": "shield",
            "institution_hint": "brokerage",
        }
    )

    # 2) Liquidity ratio
    liquid_assets = assets_by_type.get("checking", 0) + assets_by_type.get("savings", 0)
    runway_months = liquid_assets / monthly_expenses if monthly_expenses > 0 else 0
    target_runway = 3 if runway_months < 3 else 6
    liquidity_gap = max((target_runway * monthly_expenses) - liquid_assets, 0.0)
    if liquidity_gap > 0:
        liq_title = f"Your emergency fund covers {runway_months:.1f} months of expenses"
        liq_desc = f"You have {_usd(liquid_assets)} in cash. Most people aim for {target_runway}–6 months. You're about {_usd(liquidity_gap)} short."
        liq_action = f"Add {_usd(liquidity_gap)} to savings to reach a {target_runway}-month cushion."
    else:
        liq_title = f"Your emergency fund covers {runway_months:.1f} months — you're set"
        liq_desc = "Your cash cushion is healthy. Keep it steady while you invest new surplus."
        liq_action = "No action needed. Invest any extra cash above your target buffer."
    insights.append(
        {
            "title": liq_title,
            "description": liq_desc,
            "category": "Liquidity",
            "priority": _priority(runway_months, high=0, medium=3, invert=True),
            "action": liq_action,
            "why": "A cash cushion means you never have to sell investments in an emergency.",
            "icon": "umbrella",
            "institution_hint": "savings",
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
    for bucket, target in targets.items():
        actual = (bucket_totals[bucket] / total_assets * 100) if total_assets else 0.0
        drift += abs(actual - target)

    bucket_diffs = {
        bucket: ((bucket_totals[bucket] / total_assets * 100) - target) if total_assets else 0.0
        for bucket, target in targets.items()
    }
    over_bucket = max(bucket_diffs.items(), key=lambda item: item[1], default=("cash", 0.0))
    under_bucket = min(bucket_diffs.items(), key=lambda item: item[1], default=("equities", 0.0))
    shift_pct = min(max(over_bucket[1], 0.0), max(-under_bucket[1], 0.0))
    shift_amount = (shift_pct / 100) * total_assets

    over_actual = (bucket_totals[over_bucket[0]] / total_assets * 100) if total_assets else 0.0
    under_actual = (bucket_totals[under_bucket[0]] / total_assets * 100) if total_assets else 0.0

    if shift_amount > 0:
        alloc_title = f"Your mix has drifted — {over_bucket[0].replace('_', ' ')} is {over_actual:.0f}%, target {targets[over_bucket[0]]:.0f}%"
        alloc_desc = f"{under_bucket[0].replace('_', ' ').capitalize()} is low at {under_actual:.0f}% vs your {targets[under_bucket[0]]:.0f}% goal. Moving {_usd(shift_amount)} would rebalance you."
        alloc_action = f"Move {_usd(shift_amount)} from {over_bucket[0].replace('_', ' ')} into {under_bucket[0].replace('_', ' ')}."
    else:
        alloc_title = "Your investment mix is close to your target"
        alloc_desc = f"Allocation looks good for a {ctx['risk_profile']} profile. Keep directing new money to your lowest bucket."
        alloc_action = "No rebalance needed. Direct new contributions to your lowest bucket."
    insights.append(
        {
            "title": alloc_title,
            "description": alloc_desc,
            "category": "Allocation",
            "priority": _priority(drift, high=35, medium=20),
            "action": alloc_action,
            "why": "Drift happens naturally as some investments grow faster than others. Rebalancing keeps your risk level where you want it.",
            "icon": "pie",
            "institution_hint": "brokerage",
        }
    )

    # 4) Debt-to-income ratio
    dti = (ctx["total_minimum_payment"] / monthly_income * 100) if monthly_income > 0 else 0.0
    target_min_payment = monthly_income * 0.36 if monthly_income > 0 else 0.0
    dti_excess_payment = max(ctx["total_minimum_payment"] - target_min_payment, 0.0)
    if monthly_income <= 0:
        dti_title = "Add your income to see your debt load"
        dti_desc = "We can't calculate how much of your income goes to debt payments without knowing what you earn."
        dti_action = "Go to Settings and add your annual income."
    elif dti > 36:
        dti_title = f"Debt payments take up {dti:.0f}% of your income"
        dti_desc = f"You're above the 36% guideline. Reducing minimum payments by {_usd(dti_excess_payment)}/mo would bring you into a healthier range."
        dti_action = f"Focus on paying down the highest-interest debt to free up {_usd(dti_excess_payment)}/mo."
    else:
        dti_title = f"Debt payments use {dti:.0f}% of your income — within the healthy range"
        dti_desc = "Under 36% is considered manageable. Avoid taking on new high-interest debt."
        dti_action = "Keep debt payments stable and avoid new high-interest balances."
    insights.append(
        {
            "title": dti_title,
            "description": dti_desc,
            "category": "Debt",
            "priority": _priority(dti, high=36, medium=20),
            "action": dti_action,
            "why": "The lower your debt payments relative to income, the more you have to save and invest.",
            "icon": "credit",
            "institution_hint": "credit_card",
        }
    )

    # 5) Asset class diversification
    active_classes = sum(1 for v in bucket_totals.values() if v > 0)
    missing_classes = [name.replace("_", " ") for name, value in bucket_totals.items() if value <= 0]
    if active_classes < 3 and missing_classes:
        div_title = f"Your money is only spread across {active_classes} of 4 asset types"
        div_desc = f"You're missing {', '.join(missing_classes[:2])}. Broader diversification reduces the impact of any one market going down."
        div_action = f"Open a starter position in {missing_classes[0]} to add a third asset type."
    else:
        div_title = "You're invested across multiple asset types"
        div_desc = f"You hold {active_classes} out of 4 major asset classes. That's a solid base."
        div_action = "Keep balancing position sizes as you add new money."
    insights.append(
        {
            "title": div_title,
            "description": div_desc,
            "category": "Risk",
            "priority": "high" if active_classes < 3 else ("medium" if active_classes == 3 else "low"),
            "action": div_action,
            "why": "Different asset types tend to move independently — owning a mix softens the blow when one drops.",
            "icon": "grid",
            "institution_hint": "brokerage",
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

    growth_floor = 1000.0
    growth_gap = max(growth_floor - growth_monthly, 0.0)
    if growth_monthly < 0:
        growth_title = f"Net worth dropped {_usd(abs(growth_monthly))}/mo on average"
        growth_desc = "Your balance has been shrinking. That's usually spending outpacing income or market losses."
        growth_action = "Identify the biggest spending leak and cut it this month."
    elif growth_monthly < growth_floor:
        growth_title = f"Net worth grew {_usd(growth_monthly)}/mo on average"
        growth_desc = f"Progress, but there's room to grow. Adding {_usd(growth_gap)}/mo in savings or debt payoff would get you over {_usd(growth_floor)}/mo."
        growth_action = f"Increase monthly saving or debt payoff by {_usd(growth_gap)} to hit {_usd(growth_floor)}/mo growth."
    else:
        growth_title = f"Net worth is growing {_usd(growth_monthly)}/mo — solid pace"
        growth_desc = "You're building wealth consistently. Keep the momentum."
        growth_action = "Keep current saving and debt payoff pace."
    insights.append(
        {
            "title": growth_title,
            "description": growth_desc,
            "category": "Trends",
            "priority": "high" if growth_monthly < 0 else ("medium" if growth_monthly < 1000 else "low"),
            "action": growth_action,
            "why": "Net worth growth rate is your single best measure of financial progress.",
            "icon": "trending",
            "institution_hint": None,
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
    target_horizon_years = 20
    needed_monthly_for_horizon = max((retirement_target - investable) / (target_horizon_years * 12), 0.0)
    monthly_shortfall = max(needed_monthly_for_horizon - monthly_progress, 0.0)

    if readiness_pct >= 100:
        ret_title = "You've hit your retirement savings goal"
        ret_desc = "Your investable assets have reached your target. Consider your withdrawal strategy."
        ret_action = "Meet with a fee-only advisor to plan distributions."
    elif years_to_fire is not None:
        ret_title = f"You're {readiness_pct:.0f}% to your retirement goal — {years_to_fire:.1f} years away"
        ret_desc = f"At your current pace you'll reach {_usd(retirement_target)} in about {years_to_fire:.1f} years."
        ret_action = (
            f"Add {_usd(monthly_shortfall)}/mo to hit your goal in {target_horizon_years} years."
            if monthly_shortfall > 0
            else "Current pace supports your timeline. Keep it up."
        )
    else:
        ret_title = f"You're {readiness_pct:.0f}% to your retirement goal"
        ret_desc = "Start contributing monthly to project a retirement timeline."
        ret_action = f"Add {_usd(needed_monthly_for_horizon)}/mo to target a {target_horizon_years}-year timeline."
    insights.append(
        {
            "title": ret_title,
            "description": ret_desc,
            "category": "Retirement",
            "priority": "high" if readiness_pct < 25 else ("medium" if readiness_pct < 60 else "low"),
            "action": ret_action,
            "why": "Knowing your progress and pace helps you make concrete decisions now.",
            "icon": "flag",
            "institution_hint": "401k",
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
    if contributed == 0 and monthly_contribution > 0:
        contributed = monthly_contribution * max(date.today().month, 1)

    annual_limit_proxy = 23_500 + 7_000
    contribution_pct = (contributed / annual_limit_proxy * 100) if annual_limit_proxy > 0 else 0.0
    months_remaining = max(12 - date.today().month + 1, 1)
    remaining_to_limit = max(annual_limit_proxy - contributed, 0.0)
    required_monthly = remaining_to_limit / months_remaining if months_remaining > 0 else 0.0
    monthly_increase = max(required_monthly - monthly_contribution, 0.0)

    if remaining_to_limit <= 0:
        contrib_title = "You've maxed out this year's tax-free retirement space"
        contrib_desc = "Great discipline. Your 401(k) and IRA contributions are at the annual limit."
        contrib_action = "Keep auto-contributions at their current level for next year."
    else:
        contrib_title = f"You've used {contribution_pct:.0f}% of this year's tax-free retirement space"
        contrib_desc = f"You've put in {_usd(contributed)} so far. {_usd(remaining_to_limit)} left to contribute across {months_remaining} months."
        if monthly_contribution > 0:
            contrib_action = (
                f"Bump auto-contributions to {_usd(required_monthly)}/mo "
                f"(+{_usd(monthly_increase)}/mo from your current {_usd(monthly_contribution)}/mo) to max out by year-end."
            )
        else:
            contrib_action = f"Set auto-contributions to {_usd(required_monthly)}/mo to max out by year-end."
    insights.append(
        {
            "title": contrib_title,
            "description": contrib_desc,
            "category": "Retirement",
            "priority": "high" if contribution_pct < 25 else ("medium" if contribution_pct < 60 else "low"),
            "action": contrib_action,
            "why": "Tax-free retirement space is use-it-or-lose-it each year. Every unused dollar is a missed tax break.",
            "icon": "piggy",
            "institution_hint": "401k",
        }
    )

    # 9) Compound growth projection
    projection_10y = investable * (1.06 ** 10) + (monthly_progress * 12) * ((1.06 ** 10 - 1) / 0.06)
    projection_plus_100 = investable * (1.06 ** 10) + ((monthly_progress + 100) * 12) * ((1.06 ** 10 - 1) / 0.06)
    gain_from_100 = max(projection_plus_100 - projection_10y, 0.0)
    insights.append(
        {
            "title": f"At this pace, your investments could reach {_usd(projection_10y)} in 10 years",
            "description": f"Assuming 6% average annual growth. Adding just $100/mo more would add {_usd(gain_from_100)} to that number.",
            "category": "Retirement",
            "priority": "low",
            "action": f"Add $100/mo to auto-investing — it's worth {_usd(gain_from_100)} over 10 years.",
            "why": "Small consistent increases compound significantly over time.",
            "icon": "chart",
            "institution_hint": "brokerage",
        }
    )

    # 10) Debt payoff trajectory
    payoff_months = (total_debt / ctx["total_minimum_payment"]) if ctx["total_minimum_payment"] > 0 else None
    payoff_priority = "high" if (payoff_months and payoff_months > 120) else ("medium" if (payoff_months and payoff_months > 48) else "low")
    target_payoff_months = 48
    needed_monthly_payment = (total_debt / target_payoff_months) if total_debt > 0 else 0.0
    extra_to_48 = max(needed_monthly_payment - ctx["total_minimum_payment"], 0.0)
    if total_debt <= 0:
        payoff_title = "No debt tracked — or you're debt-free"
        payoff_desc = "No active debt payoff schedule detected."
        payoff_action = "Keep it up. If you have debt, add it in Accounts to track payoff progress."
    elif payoff_months and payoff_months > target_payoff_months:
        payoff_title = f"At this rate, you'll be debt-free in {payoff_months:.0f} months ({payoff_months / 12:.1f} years)"
        payoff_desc = f"Adding {_usd(extra_to_48)}/mo to principal would cut that to {target_payoff_months} months."
        payoff_action = f"Add {_usd(extra_to_48)}/mo to your highest-interest debt payment."
    else:
        payoff_title = f"Debt payoff pace looks reasonable — {(payoff_months or 0):.0f} months to go"
        payoff_desc = "Keep directing extra cash to your highest-rate balance."
        payoff_action = "Direct any extra cash to your highest-APR balance first."
    insights.append(
        {
            "title": payoff_title,
            "description": payoff_desc,
            "category": "Debt",
            "priority": payoff_priority,
            "action": payoff_action,
            "why": "Getting out of debt faster frees up cash to invest and build wealth.",
            "icon": "clock",
            "institution_hint": "credit_card",
        }
    )

    # 11) Total interest burden
    annual_interest = total_debt * (ctx["avg_debt_apr"] / 100)
    apr_reduction_savings = total_debt * 0.01
    if annual_interest > 0:
        interest_title = f"You're paying about {_usd(annual_interest)}/yr in interest"
        interest_desc = f"At a {ctx['avg_debt_apr']:.1f}% average rate. Each 1% rate reduction saves you {_usd(apr_reduction_savings)}/yr."
        interest_action = "Refinance or aggressively pay the highest-rate debt first."
    else:
        interest_title = "No interest burden detected"
        interest_desc = "No debt with interest rate data found. Add debt details to track interest costs."
        interest_action = "Add interest rate details to your debt accounts in Settings."
    insights.append(
        {
            "title": interest_title,
            "description": interest_desc,
            "category": "Debt",
            "priority": "high" if annual_interest > 5000 else ("medium" if annual_interest > 1500 else "low"),
            "action": interest_action,
            "why": "Interest is money that goes to lenders instead of your savings.",
            "icon": "percent",
            "institution_hint": "credit_card",
        }
    )

    # 12) Mortgage affordability (LTV)
    avg_ltv = (ctx["mortgage_total"] / ctx["real_estate_value"] * 100) if ctx["real_estate_value"] > 0 else 0.0
    ltv_paydown_need = max(ctx["mortgage_total"] - (0.80 * ctx["real_estate_value"]), 0.0) if ctx["real_estate_value"] > 0 else 0.0
    if not ctx["properties"]:
        ltv_title = "No real estate tracked"
        ltv_desc = "Add a property in Accounts to track your mortgage and home equity."
        ltv_action = "Add real estate in Accounts to see your home equity and LTV."
        ltv_priority = "low"
    elif avg_ltv > 80 and ltv_paydown_need > 0:
        ltv_title = f"You owe {avg_ltv:.0f}% of your home's value"
        ltv_desc = f"Above 80% means you're likely paying PMI. Paying down {_usd(ltv_paydown_need)} would bring you under 80%."
        ltv_action = f"Make a lump-sum payment of {_usd(ltv_paydown_need)} to cancel PMI and save on monthly costs."
        ltv_priority = "high" if avg_ltv > 85 else "medium"
    else:
        ltv_title = f"Your mortgage is at {avg_ltv:.0f}% of your home's value"
        ltv_desc = "Under 80% is healthy — you have solid equity and likely no PMI."
        ltv_action = "Keep paying principal and avoid cash-out refinancing for non-essential expenses."
        ltv_priority = "low"
    insights.append(
        {
            "title": ltv_title,
            "description": ltv_desc,
            "category": "Risk",
            "priority": ltv_priority,
            "action": ltv_action,
            "why": "Lower LTV means more equity, better borrowing rates, and no PMI payments.",
            "icon": "house",
            "institution_hint": "mortgage",
        }
    )

    # 13) Savings rate trend
    savings_rate = ((annual_income - (monthly_expenses * 12)) / annual_income * 100) if annual_income > 0 else 0.0
    target_savings_rate = 20.0
    monthly_savings_gap = max(((target_savings_rate / 100) * annual_income - (annual_income - monthly_expenses * 12)) / 12, 0.0) if annual_income > 0 else 0.0
    if annual_income <= 0:
        savings_title = "Add your income to see your savings rate"
        savings_desc = "We need your income to calculate how much of it you're keeping."
        savings_action = "Go to Settings and add your annual income."
        savings_priority = "medium"
    elif savings_rate < 10:
        savings_title = f"You're saving {savings_rate:.0f}% of your income — room to improve"
        savings_desc = f"Most financial plans target 20%+. Freeing up {_usd(monthly_savings_gap)}/mo would get you there."
        savings_action = f"Cut {_usd(monthly_savings_gap)}/mo in spending or increase income to hit a 20% savings rate."
        savings_priority = "high"
    elif savings_rate < 20:
        savings_title = f"You're saving {savings_rate:.0f}% of your income — getting there"
        savings_desc = f"Almost at the 20% goal. {_usd(monthly_savings_gap)}/mo more would get you there."
        savings_action = f"Find {_usd(monthly_savings_gap)}/mo in spending to cut to hit 20%."
        savings_priority = "medium"
    else:
        savings_title = f"You're saving {savings_rate:.0f}% of your income — great discipline"
        savings_desc = "Above 20% means you're building wealth faster than most. Keep it up."
        savings_action = "Keep this margin. Raise it when income increases."
        savings_priority = "low"
    insights.append(
        {
            "title": savings_title,
            "description": savings_desc,
            "category": "Behavioral",
            "priority": savings_priority,
            "action": savings_action,
            "why": "Savings rate is the single most controllable factor in how quickly you build wealth.",
            "icon": "wallet",
            "institution_hint": "savings",
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

    stability_buffer_target = 6 if cv > 0.35 else (4 if cv > 0.2 else 3)
    stability_buffer_gap = max((stability_buffer_target * monthly_expenses) - liquid_assets, 0.0)
    if cv > 0.35:
        stab_title = "Your income varies a lot month to month"
        stab_desc = f"Variable income means you need a bigger cash cushion. You're about {_usd(stability_buffer_gap)} short of a {stability_buffer_target}-month buffer."
        stab_action = f"Build {_usd(stability_buffer_gap)} more cash to reach a {stability_buffer_target}-month buffer."
    elif cv > 0.2:
        stab_title = "Your income is somewhat variable"
        stab_desc = f"A {stability_buffer_target}-month cash buffer is safer given the variability. Aim to add {_usd(stability_buffer_gap)} more." if stability_buffer_gap > 0 else "Your buffer looks adequate for your income variability."
        stab_action = f"Keep a {stability_buffer_target}-month cash buffer as your income fluctuates."
    else:
        stab_title = "Your income looks steady and predictable"
        stab_desc = "Low variability means a standard 3-month emergency fund is probably enough for you."
        stab_action = "Maintain a 3-month buffer. Any extra cash can go toward investing."
    insights.append(
        {
            "title": stab_title,
            "description": stab_desc,
            "category": "Trends",
            "priority": "high" if cv > 0.35 else ("medium" if cv > 0.2 else "low"),
            "action": stab_action,
            "why": "Variable income means you need a bigger safety net to avoid being forced into bad financial decisions.",
            "icon": "pulse",
            "institution_hint": "savings",
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
    target_passive_pct = 10.0
    target_passive_annual = ((passive_income + earned_income) * target_passive_pct / 100)
    passive_gap_annual = max(target_passive_annual - passive_income, 0.0)
    if passive_pct >= 10:
        pass_title = f"{passive_pct:.0f}% of your income comes in without active work"
        pass_desc = "That's a strong passive income base. Reinvesting it keeps that number growing."
        pass_action = "Reinvest passive income to keep growing this ratio."
    elif passive_income > 0:
        pass_title = f"{passive_pct:.0f}% of your income is passive — growing nicely"
        pass_desc = f"You're earning {_usd(passive_income)}/yr passively. Adding {_usd(passive_gap_annual / 12)}/mo more in dividend or rental income would get you to 10%."
        pass_action = f"Add {_usd(passive_gap_annual / 12)}/mo in dividend stocks or REITs to reach 10% passive income."
    else:
        pass_title = "No passive income tracked yet"
        pass_desc = "Dividend stocks, REITs, and interest income are ways to start. Even small amounts add up over time."
        pass_action = "Open a brokerage account and buy a dividend ETF to start building passive income."
    insights.append(
        {
            "title": pass_title,
            "description": pass_desc,
            "category": "Performance",
            "priority": "low" if passive_pct >= 10 else ("medium" if passive_pct >= 3 else "high"),
            "action": pass_action,
            "why": "Passive income that doesn't depend on your time is the foundation of financial independence.",
            "icon": "leaf",
            "institution_hint": "brokerage",
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

    try:
        reply = await ai.chat([{"role": "user", "content": question}], system=system)
    except ValueError as exc:
        from fastapi import HTTPException
        raise HTTPException(502, str(exc))
    except Exception as exc:
        from fastapi import HTTPException
        raise HTTPException(502, f"Claude API unreachable: {exc}")
    return {"reply": reply}
