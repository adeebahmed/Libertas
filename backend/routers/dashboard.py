from __future__ import annotations

from datetime import date, datetime, timezone
import json

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Account, BalanceSnapshot, DebtDetail, Holding, Setting
from ..services.snapshots import compute_account_balance, net_worth_overview
from .insights import _generate_insights
from .news import _build_ranked_payload

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

MAX_NEWS_ITEMS = 80
MAX_TICKERS = 5
MAX_PERSONAL = 4
NEWS_BLOCK_SIZE = 8
PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}


def _get_setting(db: Session, key: str, default):
    row = db.query(Setting).get(key)
    if not row or row.value is None:
        return default
    try:
        return json.loads(row.value)
    except Exception:
        return row.value


def _money(value: float) -> str:
    sign = "-" if value < 0 else ""
    return f"{sign}${abs(value):,.0f}"


def _pct(value: float) -> str:
    return f"{'+' if value >= 0 else ''}{value:.1f}%"


def _build_news_segment(db: Session) -> list[dict]:
    ranked = _build_ranked_payload(db, MAX_NEWS_ITEMS)
    items: list[dict] = []
    for article in ranked:
        title = str(article.get("title") or "").strip()
        url = str(article.get("url") or "").strip()
        if not title or not url:
            continue
        raw_id = article.get("id")
        item_id = f"news-{raw_id}" if raw_id is not None else f"news-{len(items)}"
        items.append(
            {
                "id": item_id,
                "label": title,
                "url": url,
                "source": article.get("source"),
                "published_at": article.get("published_at"),
            }
        )
        if len(items) >= MAX_NEWS_ITEMS:
            break
    return items


def _build_ticker_segment(db: Session) -> list[dict]:
    rows = db.query(Holding).all()
    if not rows:
        return []

    symbols: dict[str, dict] = {}
    for holding in rows:
        symbol = str(holding.symbol or "").strip().upper()
        if not symbol:
            continue
        quantity = float(holding.quantity or 0.0)
        if holding.last_price is not None:
            market_value = float(holding.last_price) * quantity
        else:
            market_value = float(holding.cost_basis or 0.0)

        agg = symbols.setdefault(
            symbol,
            {
                "symbol": symbol,
                "market_value": 0.0,
                "price": None,
                "last_updated": None,
            },
        )
        agg["market_value"] += market_value

        if holding.last_price is not None:
            current_ts = agg["last_updated"]
            incoming_ts = holding.last_updated
            if current_ts is None or (incoming_ts is not None and incoming_ts > current_ts):
                agg["price"] = float(holding.last_price)
                agg["last_updated"] = incoming_ts

    all_positive = [entry for entry in symbols.values() if entry["market_value"] > 0]
    ordered = sorted(
        all_positive,
        key=lambda entry: (-entry["market_value"], entry["symbol"]),
    )[:MAX_TICKERS]

    portfolio_total = sum(entry["market_value"] for entry in all_positive)
    if portfolio_total <= 0:
        portfolio_total = 0.0

    items: list[dict] = []
    for entry in ordered:
        weight = (entry["market_value"] / portfolio_total * 100.0) if portfolio_total > 0 else 0.0
        last_updated = entry["last_updated"].isoformat() if entry["last_updated"] else None
        items.append(
            {
                "id": f"sym-{entry['symbol']}",
                "symbol": entry["symbol"],
                "price": round(entry["price"], 4) if entry["price"] is not None else None,
                "market_value": round(entry["market_value"], 2),
                "portfolio_weight_pct": round(weight, 2),
                "last_updated": last_updated,
            }
        )
    return items


def _stale_account_count(db: Session, accounts: list[Account], stale_days: int = 7) -> tuple[int, int]:
    latest_by_account = {
        account_id: snap_date
        for account_id, snap_date in (
            db.query(BalanceSnapshot.account_id, func.max(BalanceSnapshot.date))
            .group_by(BalanceSnapshot.account_id)
            .all()
        )
    }

    today = date.today()
    stale = 0
    for account in accounts:
        latest = latest_by_account.get(account.id)
        if latest is None or (today - latest).days > stale_days:
            stale += 1
    return stale, len(accounts)


def _build_personal_segment(db: Session) -> list[dict]:
    accounts = db.query(Account).all()
    items: list[dict] = []

    insights = _generate_insights(db)
    if insights:
        top = sorted(
            insights,
            key=lambda insight: PRIORITY_ORDER.get(str(insight.get("priority")), 3),
        )[0]
        insight_title = str(top.get("title") or "").strip()
        insight_priority = str(top.get("priority") or "medium")
        if insight_title:
            tone = "negative" if insight_priority == "high" else ("neutral" if insight_priority == "medium" else "positive")
            items.append(
                {
                    "id": "p-top-insight",
                    "label": f"Insight: {insight_title}",
                    "tone": tone,
                    "route": "/insights",
                }
            )

    overview = net_worth_overview(db)
    delta_30 = overview.get("delta_30d")
    delta_30_pct = overview.get("delta_30d_pct")
    if delta_30 is not None:
        tone = "positive" if delta_30 > 0 else ("negative" if delta_30 < 0 else "neutral")
        pct_suffix = f" ({_pct(float(delta_30_pct))})" if delta_30_pct is not None else ""
        items.append(
            {
                "id": "p-networth-30d",
                "label": f"Net worth 30d {'+' if delta_30 >= 0 else ''}{_money(float(delta_30))}{pct_suffix}",
                "tone": tone,
                "route": "/insights",
            }
        )

    stale_count, total_accounts = _stale_account_count(db, accounts)
    if total_accounts > 0:
        if stale_count == 0:
            stale_label = "Account freshness: all balances updated in the last 7 days."
            stale_tone = "positive"
        elif stale_count == total_accounts:
            stale_label = f"Account freshness: {stale_count}/{total_accounts} accounts may be stale (7d+)."
            stale_tone = "negative"
        else:
            stale_label = f"Account freshness: {stale_count}/{total_accounts} accounts may be stale (7d+)."
            stale_tone = "neutral"
        items.append(
            {
                "id": "p-stale-accounts",
                "label": stale_label,
                "tone": stale_tone,
                "route": "/accounts",
            }
        )

    monthly_expenses = float(_get_setting(db, "monthly_expenses", 5000) or 5000)
    monthly_expenses = monthly_expenses if monthly_expenses > 0 else 5000.0
    liquid_assets = sum(
        compute_account_balance(db, account)
        for account in accounts
        if account.type in {"checking", "savings"}
    )
    runway = liquid_assets / monthly_expenses if monthly_expenses > 0 else 0.0

    income_w2 = float(_get_setting(db, "income_w2", 0) or 0)
    income_1099 = float(_get_setting(db, "income_1099", 0) or 0)
    monthly_income = (income_w2 + income_1099) / 12.0 if (income_w2 + income_1099) > 0 else 0.0
    min_payments = float(db.query(func.coalesce(func.sum(DebtDetail.minimum_payment), 0.0)).scalar() or 0.0)
    dti_pct = (min_payments / monthly_income * 100.0) if monthly_income > 0 else None

    if runway < 3:
        nudge_label = f"Emergency runway: {runway:.1f} months. Target 3-6 months of expenses."
        nudge_tone = "negative"
    elif dti_pct is not None and dti_pct > 36:
        nudge_label = f"Debt load check: minimum payments are {_pct(dti_pct)} of monthly income."
        nudge_tone = "negative"
    elif runway < 6:
        nudge_label = f"Emergency runway: {runway:.1f} months. Build toward a 6-month cushion."
        nudge_tone = "neutral"
    else:
        nudge_label = f"Liquidity looks healthy at {runway:.1f} months of expenses."
        nudge_tone = "positive"

    items.append(
        {
            "id": "p-liquidity-debt",
            "label": nudge_label,
            "tone": nudge_tone,
            "route": "/insights",
        }
    )

    return items[:MAX_PERSONAL]


def _chunk(items: list[str], size: int):
    for i in range(0, len(items), size):
        yield items[i:i + size]


def _build_sequence(news_items: list[dict], ticker_items: list[dict], personal_items: list[dict]) -> list[dict]:
    news_ids = [item["id"] for item in news_items]
    ticker_ids = [item["id"] for item in ticker_items]
    personal_ids = [item["id"] for item in personal_items]

    sequence: list[dict] = []
    if news_ids:
        for news_chunk in _chunk(news_ids, NEWS_BLOCK_SIZE):
            for item_id in news_chunk:
                sequence.append({"kind": "news", "ref_id": item_id})
            for item_id in ticker_ids:
                sequence.append({"kind": "ticker", "ref_id": item_id})
            for item_id in personal_ids:
                sequence.append({"kind": "personal", "ref_id": item_id})
    else:
        for item_id in ticker_ids:
            sequence.append({"kind": "ticker", "ref_id": item_id})
        for item_id in personal_ids:
            sequence.append({"kind": "personal", "ref_id": item_id})

    return sequence


@router.get("/tape")
def get_dashboard_tape(db: Session = Depends(get_db)):
    news_items = _build_news_segment(db)
    ticker_items = _build_ticker_segment(db)
    personal_items = _build_personal_segment(db)
    sequence = _build_sequence(news_items, ticker_items, personal_items)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "segments": {
            "news": news_items,
            "tickers": ticker_items,
            "personal": personal_items,
        },
        "sequence": sequence,
    }
