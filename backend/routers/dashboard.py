from __future__ import annotations

from datetime import datetime, timezone
import json
import re

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Account, DebtDetail, Holding, Setting
from ..services.snapshots import compute_account_balance
from .insights import _generate_insights
from .news import _build_ranked_payload

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

MAX_NEWS_ITEMS = 80
MAX_TICKERS = 5
MAX_PERSONAL = 5
NEWS_BLOCK_SIZE = 8
PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}
TICKER_ALIASES = {
    "AAPL": ["apple", "iphone", "ipad", "mac"],
    "MSFT": ["microsoft", "azure", "windows"],
    "NVDA": ["nvidia", "gpu", "ai chips"],
    "GOOGL": ["alphabet", "google"],
    "GOOG": ["alphabet", "google"],
    "AMZN": ["amazon", "aws"],
    "META": ["meta", "facebook", "instagram"],
    "TSLA": ["tesla", "elon musk"],
    "AMD": ["amd", "advanced micro devices"],
    "NFLX": ["netflix"],
    "JPM": ["jpmorgan", "jp morgan"],
    "BAC": ["bank of america"],
    "BRK.B": ["berkshire", "warren buffett"],
}


def _get_setting(db: Session, key: str, default):
    row = db.query(Setting).get(key)
    if not row or row.value is None:
        return default
    try:
        return json.loads(row.value)
    except Exception:
        return row.value


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
                "summary": article.get("summary"),
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


def _build_position_signals(ticker_items: list[dict]) -> list[dict]:
    items: list[dict] = []
    for ticker in ticker_items[:MAX_PERSONAL]:
        symbol = str(ticker.get("symbol") or "").strip().upper()
        if not symbol:
            continue

        weight = float(ticker.get("portfolio_weight_pct") or 0.0)
        last_updated_raw = ticker.get("last_updated")
        stale_days = None
        if isinstance(last_updated_raw, str) and last_updated_raw:
            try:
                ts = datetime.fromisoformat(last_updated_raw.replace("Z", "+00:00"))
                now = datetime.now(ts.tzinfo or timezone.utc)
                stale_days = max(0, (now - ts).days)
            except Exception:
                stale_days = None

        if stale_days is not None and stale_days >= 3:
            tone = "negative"
            label = f"{symbol} signal: price is {stale_days}d old. Action: refresh pricing before making moves."
        elif weight >= 20:
            tone = "negative"
            label = f"{symbol} signal: {weight:.1f}% concentration. Action: consider trimming or rebalancing."
        elif weight >= 10:
            tone = "neutral"
            label = f"{symbol} signal: {weight:.1f}% core position. Action: monitor catalyst risk around headlines."
        else:
            tone = "positive"
            label = f"{symbol} signal: {weight:.1f}% position sizing is controlled. Action: stay disciplined on entries."

        items.append(
            {
                "id": f"p-pos-{symbol}",
                "symbol": symbol,
                "label": label,
                "tone": tone,
                "route": "/accounts",
            }
        )
    return items


def _build_personal_segment(db: Session, ticker_items: list[dict]) -> list[dict]:
    accounts = db.query(Account).all()
    items: list[dict] = _build_position_signals(ticker_items)

    if items:
        return items[:MAX_PERSONAL]

    # Fallback when no invested symbols are available.
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


def _symbol_news_keywords(symbol: str) -> list[str]:
    normalized = symbol.strip().upper()
    keys = [normalized.lower(), normalized.replace(".", "").lower()]
    for alias in TICKER_ALIASES.get(normalized, []):
        keys.append(alias.lower())
    # Keep deterministic order while removing duplicates.
    deduped: list[str] = []
    seen = set()
    for key in keys:
        if key and key not in seen:
            seen.add(key)
            deduped.append(key)
    return deduped


def _news_relevance_score(symbol: str, news_item: dict) -> int:
    text = f"{news_item.get('label') or ''} {news_item.get('summary') or ''}".lower()
    score = 0
    for kw in _symbol_news_keywords(symbol):
        # Use boundary checks for short tokens like ticker symbols.
        if len(kw) <= 5:
            pattern = rf"(?<![a-z0-9]){re.escape(kw)}(?![a-z0-9])"
            if re.search(pattern, text):
                score += 6
        elif kw in text:
            score += 3
    return score


def _pick_news_for_symbol(symbol: str, news_items: list[dict], used_news_ids: set[str]) -> str | None:
    best_id = None
    best_score = -1
    for news in news_items:
        news_id = str(news.get("id") or "")
        if not news_id or news_id in used_news_ids:
            continue
        score = _news_relevance_score(symbol, news)
        if score > best_score:
            best_score = score
            best_id = news_id

    # Fallback to next available headline if no explicit match.
    if best_id is None:
        for news in news_items:
            news_id = str(news.get("id") or "")
            if news_id and news_id not in used_news_ids:
                return news_id
    return best_id


def _build_sequence(news_items: list[dict], ticker_items: list[dict], personal_items: list[dict]) -> list[dict]:
    ticker_by_symbol = {
        str(item.get("symbol") or "").strip().upper(): item
        for item in ticker_items
    }
    personal_by_symbol = {
        str(item.get("symbol") or "").strip().upper(): item
        for item in personal_items
        if item.get("symbol")
    }

    sequence: list[dict] = []
    used_news_ids: set[str] = set()

    for symbol in [str(item.get("symbol") or "").strip().upper() for item in ticker_items]:
        ticker = ticker_by_symbol.get(symbol)
        if not ticker:
            continue
        ticker_id = str(ticker.get("id") or "")
        if not ticker_id:
            continue

        sequence.append({"kind": "ticker", "ref_id": ticker_id})

        news_id = _pick_news_for_symbol(symbol, news_items, used_news_ids)
        if news_id:
            used_news_ids.add(news_id)
            sequence.append({"kind": "news", "ref_id": news_id})

        personal = personal_by_symbol.get(symbol)
        if personal:
            personal_id = str(personal.get("id") or "")
            if personal_id:
                sequence.append({"kind": "personal", "ref_id": personal_id})

    # Fallback when no ticker-specific groups could be built.
    if not sequence:
        for item in news_items[:NEWS_BLOCK_SIZE]:
            sequence.append({"kind": "news", "ref_id": item["id"]})
        for item in ticker_items:
            sequence.append({"kind": "ticker", "ref_id": item["id"]})
        for item in personal_items:
            sequence.append({"kind": "personal", "ref_id": item["id"]})

    return sequence


@router.get("/tape")
def get_dashboard_tape(db: Session = Depends(get_db)):
    news_items = _build_news_segment(db)
    ticker_items = _build_ticker_segment(db)
    personal_items = _build_personal_segment(db, ticker_items)
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
