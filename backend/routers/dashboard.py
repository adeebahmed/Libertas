from __future__ import annotations

from datetime import datetime, timedelta, timezone
import re
import threading
import time
import random
import os
import math
import csv
from collections import deque
from typing import Any

import httpx

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Holding, QuoteCache, RealEstate, Setting
from .news import _build_ranked_payload

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

MAX_NEWS_ITEMS = 120
MAX_TICKERS = 20
DEFAULT_STOCK_REQUESTS_PER_HOUR = 4
DEFAULT_CRYPTO_REQUESTS_PER_MINUTE = 6
FMP_SYMBOLS_PER_REQUEST = 1
RECENT_NEWS_MEMORY = 120

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
    "BTC": ["bitcoin", "bitcoin etf", "btc", "crypto"],
    "ETH": ["ethereum", "ethereum etf", "eth", "crypto"],
    "SOL": ["solana", "crypto"],
    "VTI": ["vanguard total stock market", "total stock market", "us equities"],
    "VOO": ["vanguard s&p 500", "s&p 500", "sp500", "large cap"],
    "FXAIX": ["fidelity 500", "s&p 500", "sp500", "large cap"],
    "SPY": ["spy etf", "s&p 500", "sp500", "large cap"],
    "QQQ": ["nasdaq 100", "qqq etf", "large cap growth", "tech stocks"],
}

DERIVATIVE_SYMBOL_GROUPS = {
    # Crypto spot + major proxies
    "BTC": {"BTC", "IBIT", "GBTC", "BITB", "ARKB", "FBTC", "MSTR", "COIN"},
    "ETH": {"ETH", "ETHE", "ETHA", "COIN"},
    # Broad US index ecosystem
    "SPY": {"SPY", "VOO", "IVV", "FXAIX", "VTI"},
    "QQQ": {"QQQ", "ONEQ"},
}

BROAD_MARKET_SYMBOLS = {"VTI", "VOO", "FXAIX", "SPY", "QQQ", "IVV", "DIA"}
BROAD_CRYPTO_SYMBOLS = {"BTC", "ETH", "SOL", "ADA", "DOT", "DOGE", "AVAX", "MATIC", "LINK", "UNI", "XRP", "LTC"}
BROAD_MARKET_KEYWORDS = {
    "stock market", "s&p 500", "sp500", "nasdaq", "dow",
    "treasury yields", "federal reserve", "inflation", "earnings",
}
BROAD_CRYPTO_KEYWORDS = {
    "bitcoin", "btc", "ethereum", "eth", "crypto", "digital asset",
    "crypto etf", "spot etf", "sec", "crypto regulation",
    "stablecoin", "coinbase", "blockchain",
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
REAL_ESTATE_GENERAL_KEYWORDS = {
    "real estate", "housing market", "home prices", "mortgage rates",
    "rental market", "rent", "property market",
}

_quote_cache_lock = threading.Lock()
_quote_cache: dict[str, tuple[float | None, float | None, float]] = {}
_fmp_limit_cooldown_until = 0.0
_recent_tape_lock = threading.Lock()
_recent_news_ids: deque[str] = deque(maxlen=RECENT_NEWS_MEMORY)
_tape_cache_lock = threading.Lock()
_tape_cache_payload: dict[str, Any] | None = None
_tape_cache_generated_at_ts = 0.0

CRYPTO_SYMBOLS = {"BTC", "ETH", "SOL", "ADA", "DOT", "DOGE", "AVAX", "MATIC", "LINK", "UNI", "XRP", "LTC", "ATOM", "ALGO", "USDC", "USDT"}


def _dashboard_tape_cache_ttl_seconds() -> int:
    raw = str(os.getenv("LIBERTAS_DASHBOARD_TAPE_CACHE_TTL_SECONDS", "30")).strip()
    try:
        parsed = int(raw)
    except Exception:
        parsed = 30
    return max(5, min(parsed, 300))


def _normalize_symbol(symbol: str) -> str:
    raw = (symbol or "").strip().upper()
    if not raw:
        return raw
    if raw.startswith("RE-"):
        return raw
    for suffix in ("-USD", "/USD", "USD", "-USDT", "/USDT", "USDT"):
        if raw.endswith(suffix):
            trimmed = raw[: -len(suffix)].strip("-/ ")
            if trimmed:
                return trimmed
    return raw


def _to_yahoo_symbol(symbol: str) -> str:
    """Convert local symbol format to Yahoo-friendly format."""
    normalized = _normalize_symbol(symbol)
    if normalized.startswith("RE-"):
        return normalized
    return normalized.replace(".", "-")


def _to_stooq_symbol(symbol: str) -> str:
    """Convert local symbol format to Stooq format."""
    normalized = _normalize_symbol(symbol)
    if normalized.startswith("RE-"):
        return normalized
    return f"{normalized.replace('.', '-').lower()}.us"


def _symbol_family(symbol: str) -> set[str]:
    base = _normalize_symbol(symbol)
    if not base:
        return set()
    family = {base}
    for anchor, members in DERIVATIVE_SYMBOL_GROUPS.items():
        norm_members = {_normalize_symbol(m) for m in members}
        if base == _normalize_symbol(anchor) or base in norm_members:
            family.update(norm_members)
            family.add(_normalize_symbol(anchor))
    return {s for s in family if s}


def _parse_published_at(value: Any) -> datetime | None:
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except Exception:
        return None


def _compact_headline(title: str, source: Any = None, max_len: int = 88) -> str:
    text = str(title or "").strip()
    if not text:
        return ""

    # Remove anything in parentheses to keep tape labels compact.
    text = re.sub(r"\s*\([^)]*\)\s*", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    # Keep only the lead clause for tape readability.
    text = re.split(r"\s+\|\s+|\s+[-—–]\s+", text, maxsplit=1)[0].strip()

    source_names = {
        "forbes",
        "reuters",
        "cnbc",
        "bloomberg",
        "marketwatch",
        "financial times",
        "the wall street journal",
        "wall street journal",
        "wsj",
        "yahoo finance",
        "associated press",
        "ap",
    }
    src = str(source or "").strip().lower()
    if src:
        source_names.add(src)

    # Remove trailing source suffixes (e.g., " - Reuters", "| CNBC", "• Bloomberg").
    for name in source_names:
        if not name:
            continue
        text = re.sub(
            rf"\s*(?:[-|—–•·:]\s*)?{re.escape(name)}\s*$",
            "",
            text,
            flags=re.IGNORECASE,
        ).strip()

    text = text.strip(" -|—–•·:")
    if not text:
        return ""

    # Keep only the first sentence for compact tape readability.
    first_sentence = re.split(r"(?<=[.!?])\s+", text, maxsplit=1)[0].strip()
    if first_sentence:
        text = first_sentence.rstrip(".!?").strip()

    if len(text) <= max_len:
        return text

    clipped = text[: max_len - 1].rstrip()
    if " " in clipped:
        clipped = clipped.rsplit(" ", 1)[0]
    return clipped.rstrip(" ,;:-") + "…"


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    raw = str(value).strip().replace("%", "").replace(",", "")
    raw = raw.strip("()")
    if not raw:
        return None
    try:
        return float(raw)
    except Exception:
        return None


def _get_setting_str(db: Session, key: str) -> str:
    row = db.query(Setting).filter(Setting.key == key).first()
    if not row or row.value is None:
        return ""
    return str(row.value).strip().strip('"')


def _stock_requests_per_hour(db: Session) -> int:
    rate_raw = (
        _get_setting_str(db, "stock_data_requests_per_hour")
        or os.getenv("STOCK_DATA_REQUESTS_PER_HOUR")
        or os.getenv("LIBERTAS_STOCK_REQUESTS_PER_HOUR")
        or str(DEFAULT_STOCK_REQUESTS_PER_HOUR)
    )
    try:
        return max(1, int(float(rate_raw)))
    except Exception:
        return DEFAULT_STOCK_REQUESTS_PER_HOUR


def _stock_refresh_interval_seconds(db: Session, symbol_count: int | None = None) -> int:
    explicit = os.getenv("LIBERTAS_PRICE_REFRESH_INTERVAL_SECONDS")
    if explicit:
        try:
            return max(60, int(explicit))
        except Exception:
            pass

    requests_per_hour = _stock_requests_per_hour(db)
    stocks = max(1, int(symbol_count or 1))
    requests_per_cycle = max(1, math.ceil(stocks / FMP_SYMBOLS_PER_REQUEST))
    return max(60, int(math.ceil(3600 * requests_per_cycle / requests_per_hour)))


def _crypto_requests_per_minute(db: Session) -> int:
    rpm_raw = (
        _get_setting_str(db, "crypto_data_requests_per_minute")
        or os.getenv("COINGECKO_REQUESTS_PER_MINUTE")
        or os.getenv("LIBERTAS_CRYPTO_REQUESTS_PER_MINUTE")
        or str(DEFAULT_CRYPTO_REQUESTS_PER_MINUTE)
    )
    try:
        return max(1, int(float(rpm_raw)))
    except Exception:
        return DEFAULT_CRYPTO_REQUESTS_PER_MINUTE


def _crypto_refresh_interval_seconds(db: Session) -> int:
    explicit = os.getenv("LIBERTAS_CRYPTO_REFRESH_INTERVAL_SECONDS")
    if explicit:
        try:
            return max(30, int(explicit))
        except Exception:
            pass

    requests_per_minute = _crypto_requests_per_minute(db)
    return max(30, int(60 / requests_per_minute))


def _chunked(items: list[str], size: int) -> list[list[str]]:
    if size <= 0:
        return [items]
    return [items[i:i + size] for i in range(0, len(items), size)]


def _fetch_premium_stock_quotes(symbols: list[str], db: Session) -> dict[str, dict[str, float]]:
    """
    Premium provider: Financial Modeling Prep batch quote endpoint.
    Uses `FMP_API_KEY` env or `stock_data_api_key` setting.
    """
    global _fmp_limit_cooldown_until
    if not symbols:
        return {}
    now_ts = time.time()
    if now_ts < _fmp_limit_cooldown_until:
        return {}

    api_key = (
        os.getenv("FMP_API_KEY")
        or _get_setting_str(db, "fmp_api_key")
        or _get_setting_str(db, "stock_data_api_key")
    ).strip()
    if not api_key:
        return {}

    out: dict[str, dict[str, float]] = {}
    provider_symbols = [s.replace(".", "-") for s in symbols]
    reverse = {p.upper(): s for p, s in zip(provider_symbols, symbols)}
    try:
        with httpx.Client(timeout=6.0, headers={"User-Agent": "Libertas/1.0"}) as client:
            # Use stable endpoint. This account tier supports one symbol per call.
            for provider_symbol in provider_symbols:
                resp = client.get(
                    "https://financialmodelingprep.com/stable/quote",
                    params={"symbol": provider_symbol, "apikey": api_key},
                )
                if resp.status_code != 200:
                    continue
                payload = resp.json()
                if isinstance(payload, dict):
                    msg = str(payload.get("Error Message") or payload.get("message") or payload.get("error") or "").lower()
                    if "limit" in msg and "reach" in msg:
                        cooldown = max(300, int(3600 / max(1, _stock_requests_per_hour(db))))
                        _fmp_limit_cooldown_until = now_ts + cooldown
                        break
                if isinstance(payload, list):
                    rows = payload
                elif isinstance(payload, dict) and payload.get("symbol"):
                    rows = [payload]
                else:
                    continue
                for row in rows:
                    if not isinstance(row, dict):
                        continue
                    provider_symbol = str(row.get("symbol") or "").strip().upper()
                    symbol = reverse.get(provider_symbol)
                    if not symbol:
                        continue
                    price = _safe_float(row.get("price"))
                    if price is None:
                        continue
                    change_pct = _safe_float(row.get("changePercentage"))
                    if change_pct is None:
                        change_pct = _safe_float(row.get("changesPercentage"))
                    if change_pct is None:
                        change = _safe_float(row.get("change"))
                        prev_close = _safe_float(row.get("previousClose"))
                        if change is not None and prev_close not in (None, 0):
                            change_pct = (change / prev_close) * 100.0
                    if change_pct is None:
                        continue
                    out[symbol] = {"price": float(price), "day_change_pct": float(change_pct)}
    except Exception:
        return out
    return out


def _fetch_stock_from_stooq(symbols: list[str]) -> dict[str, dict[str, float | None]]:
    """
    Fallback stock provider using Stooq quote CSV.
    Provides last-trading-day close and previous close for daily % move.
    """
    out: dict[str, dict[str, float | None]] = {}
    if not symbols:
        return out

    symbol_candidates: dict[str, list[tuple[int, str, bool]]] = {}
    all_provider_symbols: list[str] = []
    seen_provider_symbols: set[str] = set()

    for raw_symbol in symbols:
        symbol = _normalize_symbol(raw_symbol)
        if not symbol or symbol.startswith("RE-") or symbol in CRYPTO_SYMBOLS:
            continue
        candidates: list[tuple[int, str, bool]] = [(0, symbol, False)]
        # For some funds (e.g., FXAIX), use family proxies for move only.
        family = sorted(_symbol_family(symbol))
        rank = 1
        for fam_symbol in family:
            fam_symbol = _normalize_symbol(fam_symbol)
            if fam_symbol == symbol or fam_symbol.startswith("RE-") or fam_symbol in CRYPTO_SYMBOLS:
                continue
            candidates.append((rank, fam_symbol, True))
            rank += 1
        symbol_candidates[symbol] = candidates
        for _, candidate_symbol, _ in candidates:
            provider_symbol = _to_stooq_symbol(candidate_symbol)
            if provider_symbol not in seen_provider_symbols:
                seen_provider_symbols.add(provider_symbol)
                all_provider_symbols.append(provider_symbol)

    if not all_provider_symbols:
        return out

    provider_to_targets: dict[str, list[tuple[str, int, bool]]] = {}
    for target_symbol, candidates in symbol_candidates.items():
        for rank, candidate_symbol, is_proxy in candidates:
            provider_symbol = _to_stooq_symbol(candidate_symbol).upper()
            provider_to_targets.setdefault(provider_symbol, []).append((target_symbol, rank, is_proxy))

    best_rank: dict[str, int] = {}
    chunks = _chunked(all_provider_symbols, 20)
    try:
        with httpx.Client(timeout=6.0, headers={"User-Agent": "Libertas/1.0"}) as client:
            for chunk in chunks:
                query = "+".join(chunk)
                # Stooq requires raw `+` symbol separators; URL-encoding plus breaks batching.
                resp = client.get(f"https://stooq.com/q/l/?s={query}&f=sd2t2cp&h&e=csv")
                if resp.status_code != 200 or not resp.text:
                    continue
                lines = resp.text.splitlines()
                if not lines or not lines[0].lower().startswith("symbol"):
                    continue
                reader = csv.DictReader(lines)
                for row in reader:
                    provider_symbol = str(row.get("Symbol") or "").strip().upper()
                    if not provider_symbol:
                        continue
                    close = _safe_float(row.get("Close"))
                    prev = _safe_float(row.get("Prev"))
                    if close is None or prev in (None, 0):
                        continue
                    day_change_pct = ((float(close) - float(prev)) / float(prev)) * 100.0
                    for target_symbol, rank, is_proxy in provider_to_targets.get(provider_symbol, []):
                        existing_rank = best_rank.get(target_symbol)
                        if existing_rank is not None and existing_rank <= rank:
                            continue
                        out[target_symbol] = {
                            "price": None if is_proxy else float(close),
                            "day_change_pct": float(day_change_pct),
                        }
                        best_rank[target_symbol] = rank
    except Exception:
        return out

    return out


def has_fmp_api_key(db: Session) -> bool:
    key = (
        os.getenv("FMP_API_KEY")
        or _get_setting_str(db, "fmp_api_key")
        or _get_setting_str(db, "stock_data_api_key")
    )
    return bool(str(key or "").strip())


def _dt_to_timestamp(dt: datetime | None) -> float:
    if dt is None:
        return 0.0
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt.timestamp()


def _hydrate_quote_cache_from_db(db: Session, symbols: list[str]) -> None:
    if not symbols:
        return
    rows = db.query(QuoteCache).filter(QuoteCache.symbol.in_(symbols)).all()
    if not rows:
        return
    with _quote_cache_lock:
        for row in rows:
            symbol = _normalize_symbol(str(row.symbol or ""))
            if not symbol or row.day_change_pct is None:
                continue
            ts = _dt_to_timestamp(row.fetched_at) or time.time()
            _quote_cache[symbol] = (
                float(row.price) if row.price is not None else None,
                float(row.day_change_pct),
                ts,
            )


def _upsert_quote_cache_row(
    db: Session,
    *,
    symbol: str,
    price: float | None,
    day_change_pct: float | None,
    now_ts: float,
    stock_ttl_seconds: int,
    crypto_ttl_seconds: int,
    source: str,
) -> bool:
    if not symbol or day_change_pct is None:
        return False

    with _quote_cache_lock:
        _quote_cache[symbol] = (price, day_change_pct, now_ts)

    fetched_at = datetime.fromtimestamp(now_ts, tz=timezone.utc)
    ttl_seconds = crypto_ttl_seconds if symbol in CRYPTO_SYMBOLS else stock_ttl_seconds
    expires_at = fetched_at + timedelta(seconds=max(30, int(ttl_seconds)))
    row = db.query(QuoteCache).filter(QuoteCache.symbol == symbol).first()
    if row:
        row.price = price
        row.day_change_pct = day_change_pct
        row.source = source
        row.fetched_at = fetched_at
        row.expires_at = expires_at
    else:
        db.add(
            QuoteCache(
                symbol=symbol,
                price=price,
                day_change_pct=day_change_pct,
                source=source,
                fetched_at=fetched_at,
                expires_at=expires_at,
            )
        )
    return True


def load_quote_cache(db: Session) -> dict[str, int]:
    rows = db.query(QuoteCache).all()
    loaded = 0
    now_ts = time.time()
    with _quote_cache_lock:
        _quote_cache.clear()
        for row in rows:
            symbol = _normalize_symbol(str(row.symbol or ""))
            if not symbol or row.day_change_pct is None:
                continue
            ts = _dt_to_timestamp(row.fetched_at) or now_ts
            _quote_cache[symbol] = (
                float(row.price) if row.price is not None else None,
                float(row.day_change_pct),
                ts,
            )
            loaded += 1
    return {"rows_loaded": loaded, "rows_total": len(rows)}


def purge_quote_cache(db: Session, max_age_days: int = 14) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(days=max(1, int(max_age_days)))
    deleted = db.query(QuoteCache).filter(QuoteCache.fetched_at < cutoff).delete()
    if deleted:
        db.commit()
    return int(deleted or 0)


def _fetch_stock_from_yahoo_html(symbols: list[str]) -> dict[str, dict[str, float]]:
    """Fallback parser for Yahoo quote web page when API endpoints are rate-limited."""
    out: dict[str, dict[str, float]] = {}
    if not symbols:
        return out
    try:
        with httpx.Client(timeout=7.0, headers={"User-Agent": "Mozilla/5.0"}) as client:
            for symbol in symbols:
                provider_symbol = _to_yahoo_symbol(symbol)
                try:
                    resp = client.get(f"https://finance.yahoo.com/quote/{provider_symbol}?p={provider_symbol}")
                    if resp.status_code != 200 or not resp.text:
                        continue
                    html = resp.text
                    # Prefer visible quote fields rendered for the requested symbol page.
                    price_match = re.search(r'data-testid="qsp-price"[^>]*>([^<]+)<', html)
                    pct_match = re.search(r'data-testid="qsp-price-change-percent"[^>]*>([^<]+)<', html)
                    change_match = re.search(r'data-testid="qsp-price-change"[^>]*>([^<]+)<', html)

                    price = _safe_float(price_match.group(1) if price_match else None)
                    change_pct = _safe_float(pct_match.group(1) if pct_match else None)
                    if change_pct is None and price is not None:
                        change_abs = _safe_float(change_match.group(1) if change_match else None)
                        if change_abs is not None:
                            prev_close = price - change_abs
                            if prev_close != 0:
                                change_pct = (change_abs / prev_close) * 100.0

                    if price is None or change_pct is None:
                        continue
                    out[symbol] = {"price": float(price), "day_change_pct": float(change_pct)}
                except Exception:
                    continue
    except Exception:
        return out
    return out


def _fetch_stock_last_day_with_yfinance(symbols: list[str]) -> dict[str, dict[str, float]]:
    """
    Fallback for stocks/ETFs when Yahoo quote/chart endpoints are rate-limited.
    Returns last trading-day close and % move from previous close.
    """
    if not symbols:
        return {}
    try:
        import yfinance as yf  # type: ignore
    except Exception:
        return {}

    request_symbol_map = {symbol: _to_yahoo_symbol(symbol) for symbol in symbols}
    requested = list(request_symbol_map.values())
    if not requested:
        return {}

    out: dict[str, dict[str, float]] = {}
    try:
        data = yf.download(
            tickers=" ".join(requested),
            period="15d",
            interval="1d",
            auto_adjust=False,
            progress=False,
            threads=False,
            group_by="ticker",
        )
    except Exception:
        return {}

    if data is None or getattr(data, "empty", True):
        return out

    reverse_map = {v: k for k, v in request_symbol_map.items()}
    try:
        cols = getattr(data, "columns", None)
        if cols is None:
            return out
        is_multi = getattr(cols, "nlevels", 1) > 1
    except Exception:
        return out

    def _extract_close_series(frame, ticker_col: str | None = None):
        try:
            if ticker_col:
                series = frame[ticker_col]["Close"]
            else:
                series = frame["Close"]
            cleaned = [float(x) for x in series.dropna().tolist()]
            return cleaned
        except Exception:
            return []

    if is_multi:
        for request_symbol in requested:
            closes = _extract_close_series(data, request_symbol)
            if len(closes) < 2:
                continue
            prev_close = closes[-2]
            last_close = closes[-1]
            if prev_close == 0:
                continue
            symbol = reverse_map.get(request_symbol, request_symbol)
            out[symbol] = {
                "price": float(last_close),
                "day_change_pct": float((last_close - prev_close) / prev_close * 100.0),
            }
    else:
        closes = _extract_close_series(data, None)
        if len(closes) >= 2:
            prev_close = closes[-2]
            last_close = closes[-1]
            if prev_close != 0:
                symbol = reverse_map.get(requested[0], requested[0])
                out[symbol] = {
                    "price": float(last_close),
                    "day_change_pct": float((last_close - prev_close) / prev_close * 100.0),
                }
    return out


def _recent_news_snapshot() -> set[str]:
    with _recent_tape_lock:
        return set(_recent_news_ids)


def _remember_sequence(sequence: list[dict]):
    shown_news: list[str] = []
    for block in sequence:
        if str(block.get("kind") or "") == "news":
            news_id = str(block.get("ref_id") or "").strip()
            if news_id:
                shown_news.append(news_id)
    if not shown_news:
        return
    with _recent_tape_lock:
        _recent_news_ids.extend(shown_news)


def _build_news_segment(db: Session) -> list[dict]:
    ranked = _build_ranked_payload(db, MAX_NEWS_ITEMS)
    items: list[dict] = []
    for article in ranked:
        title = _compact_headline(article.get("title"), article.get("source"))
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


def _fetch_live_quote_snapshot(db: Session, symbols: list[str], force_refresh: bool = False) -> dict[str, dict[str, float]]:
    """Fetch current price + day % change with cache-first semantics."""
    now_ts = time.time()
    unique_symbols = sorted({_normalize_symbol(s) for s in symbols if s and not _normalize_symbol(s).startswith("RE-")})
    if not unique_symbols:
        return {}

    _hydrate_quote_cache_from_db(db, unique_symbols)
    stock_cache_ttl_seconds = _stock_refresh_interval_seconds(db, symbol_count=len(unique_symbols))
    crypto_cache_ttl_seconds = _crypto_refresh_interval_seconds(db)
    stale_symbols: list[str] = []
    snapshot: dict[str, dict[str, float]] = {}
    stale_cache_backup: dict[str, tuple[float | None, float]] = {}
    db_dirty = False

    with _quote_cache_lock:
        for symbol in unique_symbols:
            cached = _quote_cache.get(symbol)
            cached_is_usable = (
                not force_refresh
                and cached is not None
                and now_ts - cached[2] < (crypto_cache_ttl_seconds if symbol in CRYPTO_SYMBOLS else stock_cache_ttl_seconds)
                and cached[1] is not None
            )
            if cached_is_usable:
                price, day_change_pct, _ = cached
                snapshot[symbol] = {"price": price, "day_change_pct": day_change_pct}
            else:
                if cached is not None and cached[1] is not None:
                    cached_price = float(cached[0]) if cached[0] is not None else None
                    stale_cache_backup[symbol] = (cached_price, float(cached[1]))
                stale_symbols.append(symbol)

    stale_stocks = [s for s in stale_symbols if s not in CRYPTO_SYMBOLS]
    stale_crypto = [s for s in stale_symbols if s in CRYPTO_SYMBOLS]

    # Premium provider first for stocks/ETFs/funds.
    if stale_stocks:
        premium = _fetch_premium_stock_quotes(stale_stocks, db)
        if premium:
            for symbol, row in premium.items():
                price = row.get("price")
                day_change_pct = row.get("day_change_pct")
                if price is None or day_change_pct is None:
                    continue
                changed = _upsert_quote_cache_row(
                    db,
                    symbol=symbol,
                    price=float(price),
                    day_change_pct=float(day_change_pct),
                    now_ts=now_ts,
                    stock_ttl_seconds=stock_cache_ttl_seconds,
                    crypto_ttl_seconds=crypto_cache_ttl_seconds,
                    source="fmp",
                )
                db_dirty = db_dirty or changed
                snapshot[symbol] = {"price": float(price), "day_change_pct": float(day_change_pct)}

    # Stooq fallback for stock symbols still missing.
    stock_still_missing = [s for s in stale_stocks if s not in snapshot or snapshot[s].get("day_change_pct") is None]
    if stock_still_missing:
        stooq_fallback = _fetch_stock_from_stooq(stock_still_missing)
        if stooq_fallback:
            with _quote_cache_lock:
                existing_prices = {symbol: _quote_cache.get(symbol) for symbol in stooq_fallback.keys()}
            for symbol, row in stooq_fallback.items():
                day_change_pct = row.get("day_change_pct")
                if day_change_pct is None:
                    continue
                price = row.get("price")
                previous = existing_prices.get(symbol)
                cached_price = previous[0] if previous else None
                effective_price = float(price) if price is not None else cached_price
                changed = _upsert_quote_cache_row(
                    db,
                    symbol=symbol,
                    price=effective_price,
                    day_change_pct=float(day_change_pct),
                    now_ts=now_ts,
                    stock_ttl_seconds=stock_cache_ttl_seconds,
                    crypto_ttl_seconds=crypto_cache_ttl_seconds,
                    source="stooq",
                )
                db_dirty = db_dirty or changed
                snapshot[symbol] = {"price": effective_price, "day_change_pct": float(day_change_pct)}

    # Optional Yahoo API fallback for stock symbols still missing.
    # Disabled by default because Yahoo endpoints are frequently rate-limited and can stall tape latency.
    stock_still_missing = [s for s in stale_stocks if s not in snapshot or snapshot[s].get("day_change_pct") is None]
    if stock_still_missing and os.getenv("LIBERTAS_ENABLE_YAHOO_FALLBACK", "0") == "1":
        try:
            with httpx.Client(timeout=4.0, headers={"User-Agent": "Libertas/1.0"}) as client:
                request_symbol_map = {symbol: _to_yahoo_symbol(symbol) for symbol in stock_still_missing}
                quote_resp = client.get(
                    "https://query1.finance.yahoo.com/v7/finance/quote",
                    params={"symbols": ",".join(request_symbol_map.values())},
                )
                if quote_resp.status_code == 200:
                    payload = quote_resp.json()
                    results = payload.get("quoteResponse", {}).get("result", [])
                    quote_map: dict[str, dict[str, Any]] = {
                        str(item.get("symbol") or "").upper(): item for item in results
                    }
                    quote_price_by_symbol: dict[str, float] = {}
                    quote_change_by_symbol: dict[str, float] = {}
                    for symbol in stock_still_missing:
                        request_symbol = request_symbol_map.get(symbol, symbol)
                        row = quote_map.get(request_symbol, {}) or quote_map.get(symbol, {})
                        price = (
                            row.get("regularMarketPrice")
                            or row.get("postMarketPrice")
                            or row.get("preMarketPrice")
                            or row.get("navPrice")
                        )
                        change = row.get("regularMarketChangePercent")
                        if change is None and price is not None:
                            prev_close = row.get("regularMarketPreviousClose") or row.get("previousClose")
                            if prev_close not in (None, 0):
                                try:
                                    change = ((float(price) - float(prev_close)) / float(prev_close)) * 100.0
                                except Exception:
                                    change = None
                        price_float = float(price) if price is not None else None
                        change_float = float(change) if change is not None else None
                        if price_float is not None:
                            quote_price_by_symbol[symbol] = price_float
                        if change_float is not None:
                            quote_change_by_symbol[symbol] = change_float

                    # Last trading-day move from daily candles.
                    for symbol in stock_still_missing:
                        try:
                            request_symbol = request_symbol_map.get(symbol, symbol)
                            chart_resp = client.get(
                                f"https://query2.finance.yahoo.com/v8/finance/chart/{request_symbol}",
                                params={"interval": "1d", "range": "15d", "includePrePost": "false"},
                            )
                            if chart_resp.status_code != 200:
                                continue
                            chart = chart_resp.json()
                            result = ((chart.get("chart") or {}).get("result") or [None])[0] or {}
                            indicators = result.get("indicators") or {}
                            quote_list = indicators.get("quote") or []
                            quote_block = quote_list[0] if quote_list else {}
                            closes = quote_block.get("close") or []
                            clean_closes = [float(c) for c in closes if c is not None]
                            if len(clean_closes) < 2:
                                continue
                            prev_close = clean_closes[-2]
                            last_close = clean_closes[-1]
                            if prev_close == 0:
                                continue
                            last_day_pct = ((last_close - prev_close) / prev_close) * 100.0
                            effective_price = quote_price_by_symbol.get(symbol, last_close)
                            changed = _upsert_quote_cache_row(
                                db,
                                symbol=symbol,
                                price=float(effective_price),
                                day_change_pct=float(last_day_pct),
                                now_ts=now_ts,
                                stock_ttl_seconds=stock_cache_ttl_seconds,
                                crypto_ttl_seconds=crypto_cache_ttl_seconds,
                                source="yahoo-chart",
                            )
                            db_dirty = db_dirty or changed
                            snapshot[symbol] = {"price": effective_price, "day_change_pct": last_day_pct}
                        except Exception:
                            if symbol in quote_price_by_symbol and symbol in quote_change_by_symbol:
                                changed = _upsert_quote_cache_row(
                                    db,
                                    symbol=symbol,
                                    price=float(quote_price_by_symbol[symbol]),
                                    day_change_pct=float(quote_change_by_symbol[symbol]),
                                    now_ts=now_ts,
                                    stock_ttl_seconds=stock_cache_ttl_seconds,
                                    crypto_ttl_seconds=crypto_cache_ttl_seconds,
                                    source="yahoo-quote",
                                )
                                db_dirty = db_dirty or changed
                                snapshot[symbol] = {
                                    "price": quote_price_by_symbol[symbol],
                                    "day_change_pct": quote_change_by_symbol[symbol],
                                }
        except Exception:
            pass

    # Optional yfinance fallback for stock symbols still unresolved.
    # Disabled by default to keep tape rendering predictable/low-latency.
    stock_still_missing = [s for s in stale_stocks if s not in snapshot or snapshot[s].get("day_change_pct") is None]
    if stock_still_missing and os.getenv("LIBERTAS_ENABLE_YFINANCE_FALLBACK", "0") == "1":
        fallback = _fetch_stock_last_day_with_yfinance(stock_still_missing)
        if fallback:
            for symbol, row in fallback.items():
                price = row.get("price")
                day_change_pct = row.get("day_change_pct")
                if price is None or day_change_pct is None:
                    continue
                changed = _upsert_quote_cache_row(
                    db,
                    symbol=symbol,
                    price=float(price),
                    day_change_pct=float(day_change_pct),
                    now_ts=now_ts,
                    stock_ttl_seconds=stock_cache_ttl_seconds,
                    crypto_ttl_seconds=crypto_cache_ttl_seconds,
                    source="yfinance",
                )
                db_dirty = db_dirty or changed
                snapshot[symbol] = {"price": float(price), "day_change_pct": float(day_change_pct)}

    # Optional final stock fallback: parse Yahoo quote page.
    stock_still_missing = [s for s in stale_stocks if s not in snapshot or snapshot[s].get("day_change_pct") is None]
    if stock_still_missing and os.getenv("LIBERTAS_ENABLE_YAHOO_HTML_FALLBACK", "0") == "1":
        html_fallback = _fetch_stock_from_yahoo_html(stock_still_missing)
        if html_fallback:
            for symbol, row in html_fallback.items():
                price = row.get("price")
                day_change_pct = row.get("day_change_pct")
                if price is None or day_change_pct is None:
                    continue
                changed = _upsert_quote_cache_row(
                    db,
                    symbol=symbol,
                    price=float(price),
                    day_change_pct=float(day_change_pct),
                    now_ts=now_ts,
                    stock_ttl_seconds=stock_cache_ttl_seconds,
                    crypto_ttl_seconds=crypto_cache_ttl_seconds,
                    source="yahoo-html",
                )
                db_dirty = db_dirty or changed
                snapshot[symbol] = {"price": float(price), "day_change_pct": float(day_change_pct)}

    # Crypto overlay (CoinGecko) for stale symbols only.
    crypto_map = {
        "BTC": "bitcoin",
        "ETH": "ethereum",
        "SOL": "solana",
        "ADA": "cardano",
        "DOT": "polkadot",
        "DOGE": "dogecoin",
        "AVAX": "avalanche-2",
        "MATIC": "matic-network",
        "LINK": "chainlink",
        "UNI": "uniswap",
        "XRP": "ripple",
        "LTC": "litecoin",
        "ATOM": "cosmos",
        "ALGO": "algorand",
        "USDC": "usd-coin",
        "USDT": "tether",
    }
    crypto_symbols = [s for s in stale_crypto if s in crypto_map]
    if crypto_symbols:
        try:
            coin_ids = ",".join(crypto_map[s] for s in crypto_symbols)
            with httpx.Client(timeout=4.0, headers={"User-Agent": "Libertas/1.0"}) as client:
                cg_resp = client.get(
                    "https://api.coingecko.com/api/v3/simple/price",
                    params={
                        "ids": coin_ids,
                        "vs_currencies": "usd",
                        "include_24hr_change": "true",
                    },
                )
                if cg_resp.status_code == 200:
                    data = cg_resp.json()
                    reverse_map = {v: k for k, v in crypto_map.items()}
                    for coin_id, values in data.items():
                        symbol = reverse_map.get(coin_id)
                        if not symbol:
                            continue
                        usd = values.get("usd")
                        change_24h = values.get("usd_24h_change")
                        usd_float = float(usd) if usd is not None else None
                        change_float = float(change_24h) if change_24h is not None else None
                        if usd_float is None or change_float is None:
                            continue
                        changed = _upsert_quote_cache_row(
                            db,
                            symbol=symbol,
                            price=usd_float,
                            day_change_pct=change_float,
                            now_ts=now_ts,
                            stock_ttl_seconds=stock_cache_ttl_seconds,
                            crypto_ttl_seconds=crypto_cache_ttl_seconds,
                            source="coingecko",
                        )
                        db_dirty = db_dirty or changed
                        snapshot[symbol] = {"price": usd_float, "day_change_pct": change_float}
        except Exception:
            pass

    # If refresh fails for a symbol, keep rendering last-known cached move values.
    for symbol, (price, day_change_pct) in stale_cache_backup.items():
        if symbol in snapshot:
            continue
        snapshot[symbol] = {"price": price, "day_change_pct": day_change_pct}

    if db_dirty:
        try:
            db.commit()
        except Exception:
            db.rollback()

    return snapshot


def _build_ticker_segment(db: Session) -> list[dict]:
    symbols: dict[str, dict] = {}

    for holding in db.query(Holding).all():
        symbol = _normalize_symbol(str(holding.symbol or ""))
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
    quote_snapshot = _fetch_live_quote_snapshot(db, [entry["symbol"] for entry in top_entries])

    portfolio_total = sum(entry["market_value"] for entry in all_entries)
    portfolio_total = portfolio_total if portfolio_total > 0 else 0.0

    items: list[dict] = []
    for entry in top_entries:
        weight = (entry["market_value"] / portfolio_total * 100.0) if portfolio_total > 0 else 0.0
        symbol = _normalize_symbol(str(entry["symbol"]))
        live = quote_snapshot.get(symbol, {})
        live_price = live.get("price")
        daily_move = live.get("day_change_pct")
        effective_price = live_price if live_price is not None else entry["price"]
        effective_last_updated = datetime.now(timezone.utc) if live_price is not None else entry["last_updated"]
        last_updated = effective_last_updated.isoformat() if effective_last_updated else None
        items.append(
            {
                "id": f"sym-{entry['symbol']}",
                "symbol": entry["symbol"],
                "price": round(effective_price, 4) if effective_price is not None else None,
                "market_value": round(entry["market_value"], 2),
                "portfolio_weight_pct": round(weight, 2),
                # Daily move (%) used by the tape UI for color + arrow direction.
                "performance_pct": round(float(daily_move), 2) if daily_move is not None else None,
                "last_updated": last_updated,
            }
        )
    return items


def _tracked_quote_symbols(db: Session) -> list[str]:
    symbols = {
        _normalize_symbol(str(h.symbol or ""))
        for h in db.query(Holding).all()
        if h.symbol
    }
    return sorted([s for s in symbols if s and not s.startswith("RE-")])


def quote_refresh_plan(db: Session) -> dict[str, int]:
    symbols = _tracked_quote_symbols(db)
    stock_symbols = [s for s in symbols if s not in CRYPTO_SYMBOLS]
    crypto_symbols = [s for s in symbols if s in CRYPTO_SYMBOLS]
    return {
        "stock_symbols": len(stock_symbols),
        "crypto_symbols": len(crypto_symbols),
        "stock_requests_per_hour": _stock_requests_per_hour(db),
        "crypto_requests_per_minute": _crypto_requests_per_minute(db),
        "stock_interval_seconds": _stock_refresh_interval_seconds(db, symbol_count=len(stock_symbols)),
        "crypto_interval_seconds": _crypto_refresh_interval_seconds(db),
    }


def refresh_quote_cache(db: Session, only: str = "all") -> dict[str, int]:
    symbols = _tracked_quote_symbols(db)
    if only == "stocks":
        symbols = [s for s in symbols if s not in CRYPTO_SYMBOLS]
    elif only == "crypto":
        symbols = [s for s in symbols if s in CRYPTO_SYMBOLS]

    snapshot = _fetch_live_quote_snapshot(db, symbols, force_refresh=True)
    stock_symbols = [s for s in symbols if s not in CRYPTO_SYMBOLS]
    crypto_symbols = [s for s in symbols if s in CRYPTO_SYMBOLS]
    stock_with_moves = sum(1 for s in stock_symbols if snapshot.get(s, {}).get("day_change_pct") is not None)
    crypto_with_moves = sum(1 for s in crypto_symbols if snapshot.get(s, {}).get("day_change_pct") is not None)
    purged = purge_quote_cache(db, max_age_days=14)
    persisted = db.query(QuoteCache).count()
    return {
        "tracked_symbols": len(symbols),
        "stock_symbols": len(stock_symbols),
        "crypto_symbols": len(crypto_symbols),
        "stock_with_moves": stock_with_moves,
        "crypto_with_moves": crypto_with_moves,
        "persisted_rows": persisted,
        "purged_rows": purged,
    }


def _symbol_news_keywords(symbol: str) -> list[str]:
    normalized = _normalize_symbol(symbol)

    if normalized.startswith("RE-"):
        state_code = normalized.split("-", 1)[1]
        state_name = STATE_NAMES.get(state_code, "")
        keys = [state_code.lower(), state_name]
        keys.extend(REAL_ESTATE_POLICY_KEYWORDS)
        keys.extend(REAL_ESTATE_GENERAL_KEYWORDS)
    else:
        keys = [normalized.lower(), normalized.replace(".", "").lower()]
        for family_symbol in _symbol_family(normalized):
            keys.append(family_symbol.lower())
            keys.append(family_symbol.replace(".", "").lower())
            keys.extend(TICKER_ALIASES.get(family_symbol, []))

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

    normalized_symbol = _normalize_symbol(symbol)

    if normalized_symbol.startswith("RE-"):
        has_state = False
        has_policy_or_re = False
        for kw in keys:
            if kw in REAL_ESTATE_POLICY_KEYWORDS or kw in REAL_ESTATE_GENERAL_KEYWORDS:
                if kw in text:
                    has_policy_or_re = True
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

        if has_state and has_policy_or_re:
            score += 8
        elif has_state or has_policy_or_re:
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


def _pick_news_for_symbol(
    symbol: str,
    news_items: list[dict],
    used_news_ids: set[str],
    recent_news_ids: set[str],
    rng: random.Random,
) -> str | None:
    normalized_symbol = _normalize_symbol(symbol)
    candidates: list[tuple[dict, int]] = []
    for pass_idx in (0, 1):
        candidates = []
        for news in news_items:
            news_id = str(news.get("id") or "")
            if not news_id or news_id in used_news_ids:
                continue
            if pass_idx == 0 and news_id in recent_news_ids:
                continue
            score = _news_relevance_score(normalized_symbol, news)
            if score > 0:
                candidates.append((news, score))
        if candidates:
            break

    if candidates:
        # Prefer high relevance + recency, but rotate between top matches.
        now = datetime.now(timezone.utc)
        weighted_pool: list[tuple[str, float]] = []
        for news, score in candidates:
            published = _parse_published_at(news.get("published_at"))
            age_hours = max((now - published).total_seconds() / 3600.0, 0.0) if published else 48.0
            recency_boost = 1.0 / (1.0 + (age_hours / 36.0))
            weight = float(score) * (0.8 + recency_boost) * rng.uniform(0.92, 1.12)
            news_id = str(news.get("id") or "")
            if weight > 0 and news_id:
                weighted_pool.append((news_id, weight))

        if weighted_pool:
            # Keep focus on best options while still rotating.
            weighted_pool.sort(key=lambda item: item[1], reverse=True)
            shortlist = weighted_pool[: min(7, len(weighted_pool))]
            total = sum(w for _, w in shortlist)
            if total > 0:
                pick = rng.uniform(0, total)
                running = 0.0
                for news_id, weight in shortlist:
                    running += weight
                    if running >= pick:
                        return news_id
                return shortlist[0][0]

    # Fallback for broad-market ETFs/funds when symbol-specific mentions are sparse.
    if normalized_symbol in BROAD_MARKET_SYMBOLS:
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

    # Fallback for crypto macro news when symbol-specific mentions are sparse.
    if normalized_symbol in BROAD_CRYPTO_SYMBOLS or any(s in BROAD_CRYPTO_SYMBOLS for s in _symbol_family(normalized_symbol)):
        crypto_id: str | None = None
        crypto_score = 0
        for news in news_items:
            news_id = str(news.get("id") or "")
            if not news_id or news_id in used_news_ids:
                continue
            text = f"{news.get('label') or ''} {news.get('summary') or ''}".lower()
            score = sum(1 for kw in BROAD_CRYPTO_KEYWORDS if kw in text)
            if score > crypto_score:
                crypto_score = score
                crypto_id = news_id
        if crypto_score > 0:
            return crypto_id

    return None


def _build_sequence(news_items: list[dict], ticker_items: list[dict], rng: random.Random) -> list[dict]:
    sequence: list[dict] = []
    used_news_ids: set[str] = set()
    recent_news_ids = _recent_news_snapshot()
    ticker_queue = list(ticker_items)
    rng.shuffle(ticker_queue)

    for ticker in ticker_queue:
        symbol = _normalize_symbol(str(ticker.get("symbol") or ""))
        ticker_id = str(ticker.get("id") or "")
        if not symbol or not ticker_id:
            continue

        news_id = _pick_news_for_symbol(symbol, news_items, used_news_ids, recent_news_ids, rng)
        if not news_id:
            continue

        used_news_ids.add(news_id)
        sequence.append({"kind": "ticker", "ref_id": ticker_id})
        sequence.append({"kind": "news", "ref_id": news_id})

    # Fallback: keep stream alive with top-ranked pairs if relevance matching is sparse.
    if not sequence:
        news_pool = [n for n in news_items if str(n.get("id") or "") not in recent_news_ids] or news_items
        rng.shuffle(news_pool)
        pair_count = min(len(ticker_queue), len(news_pool))
        for idx in range(pair_count):
            sequence.append({"kind": "ticker", "ref_id": ticker_queue[idx]["id"]})
            sequence.append({"kind": "news", "ref_id": news_pool[idx]["id"]})

    _remember_sequence(sequence)

    return sequence


def _build_dashboard_tape_payload(db: Session) -> dict[str, Any]:
    # Randomize order on refresh while still honoring relevance + recent-memory guards.
    rng = random.SystemRandom()
    news_items = _build_news_segment(db)
    ticker_items = _build_ticker_segment(db)
    sequence = _build_sequence(news_items, ticker_items, rng)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "segments": {
            "news": news_items,
            "tickers": ticker_items,
            "personal": [],
        },
        "sequence": sequence,
    }


@router.get("/tape")
def get_dashboard_tape(db: Session = Depends(get_db)):
    global _tape_cache_payload, _tape_cache_generated_at_ts
    now_ts = time.time()
    ttl_seconds = _dashboard_tape_cache_ttl_seconds()

    with _tape_cache_lock:
        cache_is_fresh = (
            _tape_cache_payload is not None
            and (now_ts - _tape_cache_generated_at_ts) < ttl_seconds
        )
        if cache_is_fresh:
            return _tape_cache_payload

    payload = _build_dashboard_tape_payload(db)

    with _tape_cache_lock:
        _tape_cache_payload = payload
        _tape_cache_generated_at_ts = now_ts

    return payload
