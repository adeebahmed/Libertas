from __future__ import annotations

from datetime import datetime, timezone
import re

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Holding, RealEstate
from .news import _build_ranked_payload

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

MAX_NEWS_ITEMS = 120
MAX_TICKERS = 20

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
    "BTC": ["bitcoin", "bitcoin etf"],
    "ETH": ["ethereum", "ethereum etf"],
    "SOL": ["solana"],
    "VTI": ["vanguard total stock market", "total stock market", "us equities"],
    "VOO": ["vanguard s&p 500", "s&p 500", "sp500", "large cap"],
    "FXAIX": ["fidelity 500", "s&p 500", "sp500", "large cap"],
    "SPY": ["spy etf", "s&p 500", "sp500", "large cap"],
    "QQQ": ["nasdaq 100", "qqq etf", "large cap growth", "tech stocks"],
}

BROAD_MARKET_SYMBOLS = {"VTI", "VOO", "FXAIX", "SPY", "QQQ", "IVV", "DIA"}
BROAD_MARKET_KEYWORDS = {
    "stock market", "s&p 500", "sp500", "nasdaq", "dow",
    "treasury yields", "federal reserve", "inflation", "earnings",
}

STATE_NAMES = {
    "AL": "alabama", "AK": "alaska", "AZ": "arizona", "AR": "arkansas", "CA": "california",
    "CO": "colorado", "CT": "connecticut", "DE": "delaware", "FL": "florida", "GA": "georgia",
    "HI": "hawaii", "ID": "idaho", "IL": "illinois", "IN": "indiana", "IA": "iowa",
    "KS": "kansas", "KY": "kentucky", "LA": "louisiana", "ME": "maine", "MD": "maryland",
    "MA": "massachusetts", "MI": "michigan", "MN": "minnesota", "MS": "mississippi", "MO": "missouri",
    "MT": "montana", "NE": "nebraska", "NV": "nevada", "NH": "new hampshire", "NJ": "new jersey",
    "NM": "new mexico", "NY": "new york", "NC": "north carolina", "ND": "north dakota", "OH": "ohio",
    "OK": "oklahoma", "OR": "oregon", "PA": "pennsylvania", "RI": "rhode island", "SC": "south carolina",
    "SD": "south dakota", "TN": "tennessee", "TX": "texas", "UT": "utah", "VT": "vermont",
    "VA": "virginia", "WA": "washington", "WV": "west virginia", "WI": "wisconsin", "WY": "wyoming",
}

REAL_ESTATE_POLICY_KEYWORDS = {
    "property tax", "tax credit", "tax law", "state tax", "depreciation",
    "bonus depreciation", "section 179", "housing law", "zoning",
    "landlord", "rental law", "homestead", "assessment", "parcel tax",
}


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


def _extract_state_code(address: str) -> str | None:
    addr = (address or "").strip()
    if not addr:
        return None

    # Typical US format: "... City, ST 12345"
    m = re.search(r",\s*([A-Z]{2})\s+\d{5}(?:-\d{4})?\b", addr.upper())
    if m and m.group(1) in STATE_NAMES:
        return m.group(1)

    lower_addr = addr.lower()
    for code, state_name in STATE_NAMES.items():
        if state_name in lower_addr:
            return code
    return None


def _build_ticker_segment(db: Session) -> list[dict]:
    symbols: dict[str, dict] = {}

    for holding in db.query(Holding).all():
        symbol = str(holding.symbol or "").strip().upper()
        if not symbol:
            continue

        quantity = float(holding.quantity or 0.0)
        market_value = float(holding.last_price or 0.0) * quantity if holding.last_price is not None else float(holding.cost_basis or 0.0)
        if market_value <= 0:
            continue

        agg = symbols.setdefault(
            symbol,
            {"symbol": symbol, "market_value": 0.0, "cost_basis_total": 0.0, "price": None, "last_updated": None},
        )
        agg["market_value"] += market_value
        agg["cost_basis_total"] += float(holding.cost_basis or 0.0)

        if holding.last_price is not None:
            current_ts = agg["last_updated"]
            incoming_ts = holding.last_updated
            if current_ts is None or (incoming_ts is not None and incoming_ts > current_ts):
                agg["price"] = float(holding.last_price)
                agg["last_updated"] = incoming_ts

    # Add real-estate state buckets so state/local law headlines can be paired.
    for prop in db.query(RealEstate).all():
        state_code = _extract_state_code(str(prop.address or "")) or "US"
        symbol = f"RE-{state_code}"
        effective_value = float(prop.manual_override if prop.manual_override is not None else (prop.zillow_estimate if prop.zillow_estimate is not None else (prop.purchase_price or 0.0)))
        equity = effective_value - float(prop.mortgage_balance or 0.0)
        if equity <= 0:
            continue

        agg = symbols.setdefault(
            symbol,
            {"symbol": symbol, "market_value": 0.0, "price": None, "last_updated": None},
        )
        agg["market_value"] += equity
        if prop.last_updated is not None:
            current_ts = agg["last_updated"]
            if current_ts is None or prop.last_updated > current_ts:
                agg["last_updated"] = prop.last_updated

    all_entries = [entry for entry in symbols.values() if entry["market_value"] > 0]
    all_entries.sort(key=lambda entry: (-entry["market_value"], entry["symbol"]))
    top_entries = all_entries[:MAX_TICKERS]

    portfolio_total = sum(entry["market_value"] for entry in all_entries)
    portfolio_total = portfolio_total if portfolio_total > 0 else 0.0

    items: list[dict] = []
    for entry in top_entries:
        weight = (entry["market_value"] / portfolio_total * 100.0) if portfolio_total > 0 else 0.0
        last_updated = entry["last_updated"].isoformat() if entry["last_updated"] else None
        items.append(
            {
                "id": f"sym-{entry['symbol']}",
                "symbol": entry["symbol"],
                "price": round(entry["price"], 4) if entry["price"] is not None else None,
                "market_value": round(entry["market_value"], 2),
                "portfolio_weight_pct": round(weight, 2),
                "performance_pct": round(((entry["market_value"] - entry["cost_basis_total"]) / entry["cost_basis_total"] * 100.0), 2)
                if entry.get("cost_basis_total", 0) and entry["cost_basis_total"] > 0
                else None,
                "last_updated": last_updated,
            }
        )
    return items


def _symbol_news_keywords(symbol: str) -> list[str]:
    normalized = symbol.strip().upper()

    if normalized.startswith("RE-"):
        state_code = normalized.split("-", 1)[1]
        state_name = STATE_NAMES.get(state_code, "")
        keys = [state_code.lower(), state_name]
        keys.extend(REAL_ESTATE_POLICY_KEYWORDS)
    else:
        keys = [normalized.lower(), normalized.replace(".", "").lower()]
        keys.extend(TICKER_ALIASES.get(normalized, []))

    deduped: list[str] = []
    seen = set()
    for key in keys:
        key = str(key or "").strip().lower()
        if key and key not in seen:
            seen.add(key)
            deduped.append(key)
    return deduped


def _news_relevance_score(symbol: str, news_item: dict) -> int:
    text = f"{news_item.get('label') or ''} {news_item.get('summary') or ''}".lower()
    score = 0
    keys = _symbol_news_keywords(symbol)

    if symbol.startswith("RE-"):
        has_state = False
        has_policy = False
        for kw in keys:
            if kw in REAL_ESTATE_POLICY_KEYWORDS:
                if kw in text:
                    has_policy = True
                    score += 4
                continue

            if len(kw) <= 2:
                pattern = rf"(?<![a-z0-9]){re.escape(kw)}(?![a-z0-9])"
                if re.search(pattern, text):
                    has_state = True
                    score += 6
            elif kw in text:
                has_state = True
                score += 6

        if has_state and has_policy:
            score += 8
        elif has_state or has_policy:
            score += 1
        return score

    for kw in keys:
        if len(kw) <= 5:
            pattern = rf"(?<![a-z0-9]){re.escape(kw)}(?![a-z0-9])"
            if re.search(pattern, text):
                score += 7
        elif kw in text:
            score += 4
    return score


def _pick_news_for_symbol(symbol: str, news_items: list[dict], used_news_ids: set[str]) -> str | None:
    best_id: str | None = None
    best_score = 0
    for news in news_items:
        news_id = str(news.get("id") or "")
        if not news_id or news_id in used_news_ids:
            continue
        score = _news_relevance_score(symbol, news)
        if score > best_score:
            best_score = score
            best_id = news_id

    if best_score > 0:
        return best_id

    # Fallback for broad-market ETFs/funds when symbol-specific mentions are sparse.
    if symbol in BROAD_MARKET_SYMBOLS:
        broad_id: str | None = None
        broad_score = 0
        for news in news_items:
            news_id = str(news.get("id") or "")
            if not news_id or news_id in used_news_ids:
                continue
            text = f"{news.get('label') or ''} {news.get('summary') or ''}".lower()
            score = sum(1 for kw in BROAD_MARKET_KEYWORDS if kw in text)
            if score > broad_score:
                broad_score = score
                broad_id = news_id
        if broad_score > 0:
            return broad_id

    return None


def _build_sequence(news_items: list[dict], ticker_items: list[dict]) -> list[dict]:
    sequence: list[dict] = []
    used_news_ids: set[str] = set()

    for ticker in ticker_items:
        symbol = str(ticker.get("symbol") or "").strip().upper()
        ticker_id = str(ticker.get("id") or "")
        if not symbol or not ticker_id:
            continue

        news_id = _pick_news_for_symbol(symbol, news_items, used_news_ids)
        if not news_id:
            continue

        used_news_ids.add(news_id)
        sequence.append({"kind": "ticker", "ref_id": ticker_id})
        sequence.append({"kind": "news", "ref_id": news_id})

    # Fallback: keep stream alive with top-ranked pairs if relevance matching is sparse.
    if not sequence:
        pair_count = min(len(ticker_items), len(news_items))
        for idx in range(pair_count):
            sequence.append({"kind": "ticker", "ref_id": ticker_items[idx]["id"]})
            sequence.append({"kind": "news", "ref_id": news_items[idx]["id"]})

    return sequence


@router.get("/tape")
def get_dashboard_tape(db: Session = Depends(get_db)):
    news_items = _build_news_segment(db)
    ticker_items = _build_ticker_segment(db)
    sequence = _build_sequence(news_items, ticker_items)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "segments": {
            "news": news_items,
            "tickers": ticker_items,
            "personal": [],
        },
        "sequence": sequence,
    }
