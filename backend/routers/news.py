from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import logging
import time
from urllib.parse import quote_plus
from urllib.parse import urlparse
from typing import Optional
import httpx

from ..database import get_db
from ..models import NewsCache, Holding, Account

router = APIRouter(prefix="/api/news", tags=["news"])
logger = logging.getLogger(__name__)

GENERIC_FINANCE_FEEDS = [
    ("Morning Brew", "https://www.morningbrew.com/feed.xml"),
    ("Yahoo Finance", "https://finance.yahoo.com/rss/"),
    ("Reuters", "https://feeds.reuters.com/reuters/businessNews"),
    ("Financial Times", "https://www.ft.com/rss/home"),
    ("MarketWatch", "https://feeds.marketwatch.com/marketwatch/topstories/"),
    ("CNBC", "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114"),
]

CACHE_TTL_HOURS = 2
MAX_SYMBOL_FEEDS = 10
MIN_NEWS_ITEMS = 6

ACCOUNT_TYPE_NEWS_QUERIES = {
    "crypto": "bitcoin OR ethereum OR crypto regulation OR crypto etf",
    "checking": "federal reserve interest rates OR consumer spending OR inflation",
    "savings": "high yield savings rates OR federal reserve",
    "credit_card": "credit card interest rates OR household debt OR delinquencies",
    "student_loan": "student loan rates OR repayment policy OR refinancing",
    "auto_loan": "auto loan rates OR used car prices OR delinquencies",
    "personal_loan": "personal loan rates OR consumer credit",
    "real_estate": "mortgage rates OR housing market OR home prices",
    "brokerage": "stock market outlook OR earnings season OR fed policy",
    "roth_ira": "retirement investing OR index funds OR long term investing",
    "401k": "401k investing OR retirement outlook OR target date funds",
    "hsa": "hsa investing OR healthcare costs OR tax planning",
}

DEMO_NEWS_SOURCES = {"DemoWire", "Synthetic Journal", "Mock Finance", "Test Reuters"}
PAYWALL_DOMAINS = {
    "wsj.com",
    "barrons.com",
    "bloomberg.com",
    "ft.com",
    "economist.com",
    "theinformation.com",
}
SOURCE_PRIORITY = {
    "Morning Brew": 0,
    "Yahoo Finance": 1,
    "Reuters": 2,
    "Financial Times": 3,
    "MarketWatch": 4,
    "CNBC": 5,
    "Portfolio Briefing": 99,
}
BLOCKED_SOURCES = {"The Economist", "Bloomberg"}


@router.get("")
def get_news(limit: int = 20, db: Session = Depends(get_db)):
    """Return cached news, auto-refreshing if stale."""
    cutoff = datetime.utcnow() - timedelta(hours=CACHE_TTL_HOURS)
    latest = db.query(NewsCache).order_by(NewsCache.fetched_at.desc()).first()
    has_only_demo_news = (
        db.query(NewsCache)
        .filter(NewsCache.source.in_(DEMO_NEWS_SOURCES))
        .count() > 0
        and db.query(NewsCache).filter(~NewsCache.source.in_(DEMO_NEWS_SOURCES)).count() == 0
    )

    if not latest or latest.fetched_at < cutoff or has_only_demo_news:
        _fetch_and_cache(db)
        _purge_invalid_news_links(db)
        _ensure_minimum_news_entries(db, min_count=MIN_NEWS_ITEMS)
    else:
        _purge_invalid_news_links(db)
        _ensure_minimum_news_entries(db, min_count=MIN_NEWS_ITEMS)

    articles = (
        db.query(NewsCache)
        .filter(~NewsCache.source.in_(BLOCKED_SOURCES))
        .order_by(NewsCache.published_at.desc().nullslast())
        .limit(limit * 3)
        .all()
    )
    payload = [
        {
            "id": a.id,
            "source": a.source,
            "title": a.title,
            "url": a.url,
            "published_at": a.published_at.isoformat() if a.published_at else None,
            "summary": a.summary,
            "category": a.category,
        }
        for a in articles
    ]
    payload.sort(key=lambda a: a["published_at"] or "", reverse=True)
    payload.sort(key=lambda a: SOURCE_PRIORITY.get(a["source"], 99))
    filtered_payload = [
        p for p in payload
        if p["source"] == "Financial Times" or not _is_paywalled_url(p.get("url") or "")
    ]
    return filtered_payload[:limit]


@router.post("/refresh")
def refresh_news(db: Session = Depends(get_db)):
    """Force a news refresh."""
    count = _fetch_and_cache(db)
    _purge_invalid_news_links(db)
    _ensure_minimum_news_entries(db, min_count=MIN_NEWS_ITEMS)
    return {"fetched": count}


def _fetch_and_cache(db: Session, strict_relevance: bool = True) -> int:
    """Fetch RSS feeds and upsert into news_cache. Returns count of new articles."""
    try:
        import feedparser
    except ImportError:
        logger.warning("feedparser not installed — skipping news fetch")
        return 0

    # Clear articles older than 7 days
    cutoff = datetime.utcnow() - timedelta(days=7)
    db.query(NewsCache).filter(NewsCache.fetched_at < cutoff).delete()

    # Clean out locally inserted fake/demo rows before adding live data.
    db.query(NewsCache).filter(NewsCache.source.in_(DEMO_NEWS_SOURCES)).delete()

    context = _portfolio_context(db)
    feeds = _build_feeds(context)
    existing_titles = {r.title for r in db.query(NewsCache.title).all()}
    added = 0

    for source, url, category in feeds:
        if source in BLOCKED_SOURCES:
            continue
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:12]:
                title = (entry.get("title") or "").strip()
                if not title or title in existing_titles:
                    continue

                summary = (entry.get("summary") or entry.get("description") or "").strip()
                text = f"{title} {summary}".lower()
                if strict_relevance and not _is_relevant(text, context):
                    continue

                raw_url = entry.get("link") or ""
                url = raw_url.strip()
                if _is_paywalled_url(url):
                    # Keep FT headlines/summaries even when full article is paywalled.
                    if source == "Financial Times":
                        url = ""
                    else:
                        continue
                if url and not _is_direct_article_url(url):
                    continue
                if url and not _url_is_live(url):
                    continue

                published = _parse_entry_datetime(entry)
                if len(summary) > 400:
                    summary = summary[:397] + "…"

                db.add(NewsCache(
                    source=source,
                    title=title,
                    url=url,
                    published_at=published,
                    summary=summary or None,
                    category=category,
                ))
                existing_titles.add(title)
                added += 1
        except Exception as e:
            logger.warning(f"News fetch failed for {source}: {e}")

    if added > 0:
        db.commit()
    return added


def _ensure_minimum_news_entries(db: Session, min_count: int = MIN_NEWS_ITEMS):
    db.query(NewsCache).filter(NewsCache.source.in_(DEMO_NEWS_SOURCES)).delete()
    db.query(NewsCache).filter(NewsCache.source == "Portfolio Briefing").delete()
    db.commit()

    existing = db.query(NewsCache).filter(NewsCache.url.isnot(None)).count()
    if existing >= min_count:
        return

    # Fill from live feeds, but relax relevance filtering so we can reliably
    # maintain a minimum count of direct article links.
    _fetch_and_cache(db, strict_relevance=False)
    _purge_invalid_news_links(db)


def _portfolio_context(db: Session) -> dict:
    rows = (
        db.query(Holding.symbol, Account.type)
        .join(Account, Holding.account_id == Account.id)
        .all()
    )
    account_types = {r[1] for r in rows if r[1]}
    # Keep symbol list stable and bounded.
    symbols: list[str] = []
    seen = set()
    for symbol, _atype in rows:
        if not symbol:
            continue
        sym = symbol.strip().upper()
        if sym and sym not in seen:
            seen.add(sym)
            symbols.append(sym)
    symbols = symbols[:MAX_SYMBOL_FEEDS]

    keywords = set(sym.lower() for sym in symbols)
    for atype in account_types:
        keywords.update(str(atype).lower().replace("_", " ").split())
        if atype in ACCOUNT_TYPE_NEWS_QUERIES:
            keywords.update(ACCOUNT_TYPE_NEWS_QUERIES[atype].lower().replace("or", " ").split())

    # Remove tiny/noisy tokens
    keywords = {k for k in keywords if len(k) > 2 and k not in {"and", "the", "for", "with"}}

    return {
        "symbols": symbols,
        "account_types": sorted(account_types),
        "keywords": keywords,
        "has_portfolio": len(symbols) > 0 or len(account_types) > 0,
    }


def _build_feeds(context: dict) -> list[tuple[str, str, str]]:
    feeds: list[tuple[str, str, str]] = [(name, url, "markets") for name, url in GENERIC_FINANCE_FEEDS]

    return feeds


def _is_relevant(text: str, context: dict) -> bool:
    # If no portfolio context exists, keep broad market coverage.
    if not context["has_portfolio"]:
        return True
    return any(keyword in text for keyword in context["keywords"])


def _parse_entry_datetime(entry) -> Optional[datetime]:
    for field in ("published_parsed", "updated_parsed"):
        parsed = getattr(entry, field, None)
        if parsed:
            try:
                return datetime.fromtimestamp(time.mktime(parsed))
            except Exception:
                continue
    return None


def _google_news_rss_url(query: str) -> str:
    return f"https://news.google.com/rss/search?q={quote_plus(query + ' when:7d')}&hl=en-US&gl=US&ceid=US:en"


def _google_news_search_url(query: str) -> str:
    return f"https://news.google.com/search?q={quote_plus(query)}&hl=en-US&gl=US&ceid=US:en"


def _is_paywalled_url(url: str) -> bool:
    if not url:
        return False
    try:
        host = (urlparse(url).hostname or "").lower()
    except Exception:
        return False
    if host.startswith("www."):
        host = host[4:]
    return any(host == d or host.endswith(f".{d}") for d in PAYWALL_DOMAINS)


def _is_direct_article_url(url: str) -> bool:
    if not url:
        return False
    try:
        parsed = urlparse(url)
    except Exception:
        return False
    if parsed.scheme not in {"http", "https"}:
        return False
    if not parsed.netloc:
        return False

    host = parsed.netloc.lower()
    path = parsed.path or ""
    query = (parsed.query or "").lower()

    if "news.google.com" in host:
        return False
    if path in {"", "/"}:
        return False
    if "/search" in path.lower():
        return False
    if "q=" in query and ("search" in query or "query" in query):
        return False
    return True


def _url_is_live(url: str) -> bool:
    # Avoid 404 links in the UI. We accept 2xx and common anti-bot statuses.
    # Some sites block HEAD; fallback to GET.
    timeout = httpx.Timeout(5.0, connect=3.0)
    headers = {"User-Agent": "Libertas-NewsBot/1.0 (+local)"}
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True, headers=headers) as client:
            r = client.head(url)
            if r.status_code in {200, 201, 202, 301, 302, 307, 308, 401, 403, 405, 429}:
                return True
            if r.status_code == 404:
                return False
            if r.status_code >= 500:
                return False
            g = client.get(url)
            return g.status_code != 404 and g.status_code < 500
    except Exception:
        return False


def _purge_invalid_news_links(db: Session):
    rows = db.query(NewsCache).all()
    removed = 0
    for row in rows:
        if row.source in BLOCKED_SOURCES:
            db.delete(row)
            removed += 1
            continue
        url = (row.url or "").strip()
        if row.source == "Financial Times":
            # Keep FT headline/summary rows even when no direct free URL is available.
            continue
        if not _is_direct_article_url(url):
            db.delete(row)
            removed += 1
            continue
        if _is_paywalled_url(url):
            db.delete(row)
            removed += 1
            continue
        if not _url_is_live(url):
            db.delete(row)
            removed += 1
    if removed > 0:
        db.commit()
