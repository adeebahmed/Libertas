"""
Smart CSV analyzer. Figures out what each column contains by inspecting actual
cell values — not header names. Works with any export format from any institution.
"""
import re
from datetime import datetime
from typing import Optional

# Date formats we try, ordered by commonality
DATE_FORMATS = [
    "%m/%d/%Y", "%Y-%m-%d", "%m-%d-%Y", "%m/%d/%y", "%Y/%m/%d",
    "%d/%m/%Y", "%b %d, %Y", "%B %d, %Y", "%m/%d/%Y %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S", "%m/%d/%Y %I:%M:%S %p",
]

TICKER_PATTERN = re.compile(r"^[A-Z]{1,5}$")
CRYPTO_LONG_NAMES = {
    "bitcoin", "ethereum", "solana", "cardano", "polkadot", "dogecoin",
    "avalanche", "chainlink", "uniswap", "ripple", "litecoin", "cosmos",
    "algorand", "polygon", "matic",
}
CRYPTO_SYMBOL_MAP = {
    "bitcoin": "BTC", "ethereum": "ETH", "solana": "SOL", "cardano": "ADA",
    "polkadot": "DOT", "dogecoin": "DOGE", "avalanche": "AVAX",
    "chainlink": "LINK", "uniswap": "UNI", "ripple": "XRP", "litecoin": "LTC",
    "cosmos": "ATOM", "algorand": "ALGO", "polygon": "MATIC", "matic": "MATIC",
}

BUY_WORDS = {"buy", "bought", "purchase", "deposit", "receive", "received", "credit",
             "reinvest", "reinvestment", "dividend reinvestment", "contribution",
             "transfer in", "incoming"}
SELL_WORDS = {"sell", "sold", "sale", "withdrawal", "withdraw", "send", "sent",
              "debit", "distribution", "transfer out", "outgoing", "fee", "tax"}
SKIP_WORDS = {"interest", "dividend", "div", "adr fee", "journal"}

MONEY_PATTERN = re.compile(r"^[($\s]*-?\$?\s*[\d,]+\.?\d*[)\s]*$")


def try_parse_date(val: str) -> Optional[datetime]:
    s = val.strip()
    if not s:
        return None
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def try_parse_number(val: str) -> Optional[float]:
    s = val.strip().replace("$", "").replace(",", "").replace("(", "-").replace(")", "").replace("+", "")
    if not s or s in ("--", "N/A", "n/a", ""):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def looks_like_ticker(val: str) -> bool:
    s = val.strip()
    if TICKER_PATTERN.match(s):
        return True
    if s.lower() in CRYPTO_LONG_NAMES:
        return True
    return False


def normalize_symbol(val: str) -> str:
    """Turn 'Bitcoin' -> 'BTC', 'AAPL' -> 'AAPL'."""
    s = val.strip()
    if s.lower() in CRYPTO_SYMBOL_MAP:
        return CRYPTO_SYMBOL_MAP[s.lower()]
    return s.upper()


def classify_transaction_type(val: str) -> str:
    """Normalize a transaction type string to 'buy', 'sell', or 'other'."""
    s = val.strip().lower()
    if any(w in s for w in BUY_WORDS):
        return "buy"
    if any(w in s for w in SELL_WORDS):
        return "sell"
    if any(w in s for w in SKIP_WORDS):
        return "other"
    return "other"


class ColumnRole:
    DATE = "date"
    SYMBOL = "symbol"
    QUANTITY = "quantity"
    PRICE = "price"
    AMOUNT = "amount"
    TYPE = "type"
    DESCRIPTION = "description"
    UNKNOWN = "unknown"


def analyze_column(header: str, values: list[str]) -> tuple[str, float]:
    """
    Analyze a column's values to determine its role. Returns (role, confidence).
    We score each possible role and pick the best.
    """
    if not values:
        return ColumnRole.UNKNOWN, 0.0

    sample = [v for v in values[:20] if v and v.strip()]
    if not sample:
        return ColumnRole.UNKNOWN, 0.0

    n = len(sample)
    h = header.lower().strip()

    # --- Date detection: try parsing as dates ---
    date_hits = sum(1 for v in sample if try_parse_date(v) is not None)
    date_score = date_hits / n if n else 0

    # --- Ticker detection ---
    ticker_hits = sum(1 for v in sample if looks_like_ticker(v))
    ticker_score = ticker_hits / n if n else 0

    # --- Numeric detection ---
    num_values = []
    for v in sample:
        p = try_parse_number(v)
        if p is not None:
            num_values.append(p)
    num_score = len(num_values) / n if n else 0

    # --- Money (has $ or parens) ---
    money_hits = sum(1 for v in sample if MONEY_PATTERN.match(v.strip()))
    money_score = money_hits / n if n else 0

    # --- Transaction type detection ---
    type_words = BUY_WORDS | SELL_WORDS | SKIP_WORDS
    type_hits = sum(1 for v in sample if any(w in v.lower() for w in type_words))
    type_score = type_hits / n if n else 0

    # --- Long text (description) ---
    avg_len = sum(len(v) for v in sample) / n if n else 0

    # Now decide with header hints boosting scores
    scores: dict[str, float] = {}

    # Date
    scores[ColumnRole.DATE] = date_score * 0.9
    if any(k in h for k in ("date", "time", "timestamp", "when")):
        scores[ColumnRole.DATE] += 0.3

    # Symbol
    scores[ColumnRole.SYMBOL] = ticker_score * 0.9
    if any(k in h for k in ("symbol", "ticker", "asset", "coin", "security", "instrument")):
        scores[ColumnRole.SYMBOL] += 0.3

    # Type
    scores[ColumnRole.TYPE] = type_score * 0.8
    if any(k in h for k in ("type", "action", "trans code", "transaction type", "activity")):
        scores[ColumnRole.TYPE] += 0.3

    # Numeric columns — distinguish by header hints and value magnitude
    if num_score > 0.5:
        if any(k in h for k in ("qty", "quantity", "shares", "units")):
            scores[ColumnRole.QUANTITY] = num_score * 0.8 + 0.3
        elif any(k in h for k in ("price", "cost per share", "share price", "unit price", "spot price")):
            scores[ColumnRole.PRICE] = num_score * 0.8 + 0.3
        elif any(k in h for k in ("amount", "total", "net amount", "value", "market value", "principal")):
            scores[ColumnRole.AMOUNT] = num_score * 0.8 + 0.3
        elif money_score > 0.3:
            # Has $ signs — likely amount
            scores[ColumnRole.AMOUNT] = num_score * 0.7 + money_score * 0.2
        else:
            # Pure numbers with no header hint. Use magnitude heuristic:
            # quantities tend to be smaller or whole, prices moderate, amounts larger
            if num_values:
                median = sorted(num_values)[len(num_values) // 2]
                abs_median = abs(median)
                if abs_median < 100:
                    scores[ColumnRole.QUANTITY] = num_score * 0.5
                elif abs_median < 10000:
                    scores[ColumnRole.PRICE] = num_score * 0.4
                else:
                    scores[ColumnRole.AMOUNT] = num_score * 0.4

    # Description
    if any(k in h for k in ("description", "memo", "notes", "details", "name", "investment name")):
        scores[ColumnRole.DESCRIPTION] = 0.7
    elif avg_len > 20 and num_score < 0.3 and date_score < 0.3 and ticker_score < 0.3:
        scores[ColumnRole.DESCRIPTION] = 0.4

    if not scores:
        return ColumnRole.UNKNOWN, 0.0

    best_role = max(scores, key=scores.get)
    return best_role, scores[best_role]


def auto_detect_columns(headers: list[str], rows: list[dict]) -> dict[str, str]:
    """
    Analyze all columns and assign roles. Returns {header_name: role}.
    Ensures each role is assigned at most once, picking the highest confidence.
    """
    # Score every column for every role
    all_scores: list[tuple[str, str, float]] = []  # (header, role, score)

    for header in headers:
        values = [row.get(header, "") for row in rows[:20]]
        role, score = analyze_column(header, values)
        if role != ColumnRole.UNKNOWN and score > 0.2:
            all_scores.append((header, role, score))

    # Greedy assignment: highest score first, no role or header reused
    all_scores.sort(key=lambda x: -x[2])
    assigned_roles: set[str] = set()
    assigned_headers: set[str] = set()
    mapping: dict[str, str] = {}

    for header, role, score in all_scores:
        if role in assigned_roles or header in assigned_headers:
            continue
        mapping[header] = role
        assigned_roles.add(role)
        assigned_headers.add(header)

    return mapping
