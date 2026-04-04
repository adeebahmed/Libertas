from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime
import httpx

from ..database import get_db
from ..models import Holding

router = APIRouter(prefix="/api/prices", tags=["prices"])


async def fetch_stock_prices(symbols: list[str]) -> dict[str, float]:
    """Fetch stock prices via yfinance."""
    if not symbols:
        return {}
    try:
        import yfinance as yf
        tickers = yf.Tickers(" ".join(symbols))
        prices = {}
        for sym in symbols:
            try:
                info = tickers.tickers[sym].fast_info
                prices[sym] = info.get("lastPrice") or info.get("regularMarketPrice", 0)
            except Exception:
                continue
        return prices
    except Exception:
        return {}


async def fetch_crypto_prices(coin_ids: list[str]) -> dict[str, float]:
    """Fetch crypto prices from CoinGecko free API."""
    if not coin_ids:
        return {}
    try:
        async with httpx.AsyncClient() as client:
            ids_param = ",".join(coin_ids)
            resp = await client.get(
                "https://api.coingecko.com/api/v3/simple/price",
                params={"ids": ids_param, "vs_currencies": "usd"},
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            return {cid: data[cid]["usd"] for cid in data if "usd" in data[cid]}
    except Exception:
        return {}


# Common crypto symbol -> CoinGecko ID mapping
CRYPTO_MAP = {
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


def classify_symbol(symbol: str) -> str:
    """Guess if a symbol is crypto or stock."""
    upper = symbol.upper()
    if upper in CRYPTO_MAP:
        return "crypto"
    # Heuristic: crypto symbols are usually short and all caps without dots
    if len(upper) <= 5 and "." not in upper and "-" not in upper:
        return "unknown"
    return "stock"


@router.post("/refresh")
async def refresh_prices(db: Session = Depends(get_db)):
    holdings = db.query(Holding).all()
    if not holdings:
        return {"updated": 0}

    symbols = list({h.symbol.upper() for h in holdings if h.symbol})

    stock_symbols = []
    crypto_symbols = []

    for sym in symbols:
        cls = classify_symbol(sym)
        if cls == "crypto":
            crypto_symbols.append(sym)
        else:
            stock_symbols.append(sym)

    # Fetch prices
    stock_prices = await fetch_stock_prices(stock_symbols)

    coin_ids = [CRYPTO_MAP[s] for s in crypto_symbols if s in CRYPTO_MAP]
    crypto_prices_raw = await fetch_crypto_prices(coin_ids)
    # Map back to ticker symbols
    reverse_crypto = {v: k for k, v in CRYPTO_MAP.items()}
    crypto_prices = {reverse_crypto[cid]: price for cid, price in crypto_prices_raw.items() if cid in reverse_crypto}

    all_prices = {**stock_prices, **crypto_prices}

    updated = 0
    now = datetime.utcnow()
    for h in holdings:
        sym = h.symbol.upper() if h.symbol else ""
        if sym in all_prices:
            h.last_price = all_prices[sym]
            h.last_updated = now
            updated += 1

    db.commit()
    return {"updated": updated, "prices": all_prices}


@router.get("/status")
def price_status(db: Session = Depends(get_db)):
    holdings = db.query(Holding).all()
    return [
        {
            "symbol": h.symbol,
            "last_price": h.last_price,
            "last_updated": h.last_updated.isoformat() if h.last_updated else None,
        }
        for h in holdings
    ]
