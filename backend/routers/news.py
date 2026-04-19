from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import logging
import json
import os
import re
import time
import threading
from urllib.parse import quote_plus, urlparse
from typing import Optional
import httpx

from ..database import get_db, SessionLocal
from ..models import NewsCache, Holding, Account, Setting

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
AI_NEWS_FEEDS = [
    ("AI News", "artificial intelligence OR generative ai OR llm OR model release"),
    ("AI Chips", "nvidia OR amd OR tsmc OR ai chips OR gpu demand"),
    ("AI Policy", "ai regulation OR openai OR anthropic OR google deepmind"),
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
    "AI News": 0,
    "AI Chips": 1,
    "AI Policy": 2,
    "NewsAPI": 3,
    "Morning Brew": 3,
    "Yahoo Finance": 4,
    "Reuters": 5,
    "Financial Times": 6,
    "MarketWatch": 7,
    "CNBC": 8,
    "Portfolio Briefing": 99,
}
BLOCKED_SOURCES = {"The Economist", "Bloomberg"}
AI_RELEVANCE_KEYWORDS = {
    "ai", "artificial intelligence", "generative", "llm", "model",
    "openai", "anthropic", "deepmind", "inference", "training",
    "gpu", "nvidia", "amd", "semiconductor", "datacenter", "chip",
}
_refresh_lock = threading.Lock()
_refresh_inflight = False


def _strip_html(text: str) -> str:
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'&nbsp;', ' ', text)
    text = re.sub(r'&amp;', '&', text)
    text = re.sub(r'&lt;', '<', text)
    text = re.sub(r'&gt;', '>', text)
    text = re.sub(r'&quot;', '"', text)
    text = re.sub(r'&#\d+;', '', text)
    return re.sub(r'\s+', ' ', text).strip()


def _clean_html_summaries(db: Session):
    """Strip HTML from any cached summaries that weren't cleaned at ingest time."""
    dirty = False
    for row in db.query(NewsCache).filter(NewsCache.summary.isnot(None)).all():
        if '<' in (row.summary or ''):
            row.summary = _strip_html(row.summary)
            dirty = True
    if dirty:
        db.commit()


@router.get("")
def get_news(limit: int = 20, refresh: bool = False, db: Session = Depends(get_db)):
    """Return cached news quickly. Optionally trigger async refresh."""
    cutoff = datetime.utcnow() - timedelta(hours=CACHE_TTL_HOURS)
    latest = db.query(NewsCache).order_by(NewsCache.fetched_at.desc()).first()
    has_only_demo_news = (
        db.query(NewsCache)
        .filter(NewsCache.source.in_(DEMO_NEWS_SOURCES))
        .count() > 0
        and db.query(NewsCache).filter(~NewsCache.source.in_(DEMO_NEWS_SOURCES)).count() == 0
    )

    if refresh or not latest or latest.fetched_at < cutoff or has_only_demo_news:
        _trigger_async_refresh()

    boosted_payload = _build_ranked_payload(db, limit)
    required_ai = min(2, limit)

    # If we still don't have enough AI articles near the top, do a quick
    # synchronous AI-only fetch and re-rank once so users immediately see AI.
    if _count_ai_articles(boosted_payload[:required_ai]) < required_ai:
        _fetch_ai_only(db)
        _purge_invalid_news_links(db)
        _ensure_minimum_news_entries(db, min_count=MIN_NEWS_ITEMS)
        boosted_payload = _build_ranked_payload(db, limit)

    return boosted_payload[:limit]


@router.post("/refresh")
def refresh_news(db: Session = Depends(get_db)):
    """Immediately strip any HTML from cached summaries, then trigger a background refresh."""
    _clean_html_summaries(db)
    started = _trigger_async_refresh(force=True)
    return {"started": started, "inflight": _is_refresh_inflight()}


def _is_refresh_inflight() -> bool:
    with _refresh_lock:
        return _refresh_inflight


def _trigger_async_refresh(force: bool = False) -> bool:
    global _refresh_inflight
    with _refresh_lock:
        if _refresh_inflight:
            return False
        _refresh_inflight = True

    t = threading.Thread(target=_refresh_worker, daemon=True)
    t.start()
    return True


def _refresh_worker():
    global _refresh_inflight
    db = SessionLocal()
    try:
        _fetch_and_cache(db)
        _purge_invalid_news_links(db)
        _ensure_minimum_news_entries(db, min_count=MIN_NEWS_ITEMS)
    except Exception as e:
        logger.warning(f"Background news refresh failed: {e}")
    finally:
        db.close()
        with _refresh_lock:
            _refresh_inflight = False


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

    _clean_html_summaries(db)

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

                summary = _strip_html((entry.get("summary") or entry.get("description") or "").strip())
                text = f"{title} {summary}".lower()
                ai_hit = any(keyword in text for keyword in AI_RELEVANCE_KEYWORDS)
                if strict_relevance and not _is_relevant(text, context):
                    continue

                article_url = (entry.get("link") or "").strip()
                if _is_paywalled_url(article_url):
                    # Keep FT headlines/summaries even when full article is paywalled.
                    if source == "Financial Times":
                        article_url = ""
                    else:
                        continue
                if article_url and not _is_direct_article_url(article_url):
                    continue
                if article_url and not _url_is_live(article_url):
                    continue

                published = _parse_entry_datetime(entry)
                if len(summary) > 400:
                    summary = summary[:397] + "…"

                db.add(NewsCache(
                    source=source,
                    title=title,
                    url=article_url,
                    published_at=published,
                    summary=summary or None,
                    category="ai" if ai_hit else category,
                ))
                existing_titles.add(title)
                added += 1
        except Exception as e:
            logger.warning(f"News fetch failed for {source}: {e}")

    # Optional premium feed: NewsAPI (user-provided key in Settings).
    try:
        added += _fetch_newsapi(db, existing_titles, strict_relevance=strict_relevance)
    except Exception as e:
        logger.warning(f"NewsAPI fetch failed: {e}")

    if added > 0:
        db.commit()
    return added


def _get_news_api_key(db: Session) -> str:
    env_key = (os.getenv("NEWS_API_KEY") or "").strip()
    if env_key:
        return env_key
    row = db.query(Setting).get("news_api_key")
    if not row or row.value is None:
        return ""
    try:
        return str(json.loads(row.value) or "").strip()
    except Exception:
        return str(row.value).strip()


def _parse_iso_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


def _fetch_newsapi(db: Session, existing_titles: set[str], strict_relevance: bool = True) -> int:
    key = _get_news_api_key(db)
    if not key:
        return 0

    context = _portfolio_context(db)
    queries: list[tuple[str, dict[str, str]]] = [
        ("NewsAPI", {"country": "us", "category": "business", "pageSize": "20"}),
        ("NewsAPI", {"q": "markets OR investing OR inflation OR federal reserve", "language": "en", "sortBy": "publishedAt", "pageSize": "20"}),
        ("NewsAPI", {"q": "artificial intelligence OR openai OR anthropic OR nvidia", "language": "en", "sortBy": "publishedAt", "pageSize": "20"}),
    ]

    added = 0
    headers = {"X-Api-Key": key, "User-Agent": "Libertas-NewsBot/1.0 (+local)"}
    timeout = httpx.Timeout(8.0, connect=4.0)
    with httpx.Client(timeout=timeout, headers=headers) as client:
        for source, params in queries:
            try:
                response = client.get("https://newsapi.org/v2/top-headlines" if "country" in params else "https://newsapi.org/v2/everything", params=params)
                if response.status_code in {401, 403}:
                    logger.warning("NewsAPI key rejected (401/403). Check news_api_key in Settings.")
                    return added
                response.raise_for_status()
                payload = response.json()
                for article in payload.get("articles", [])[:18]:
                    title = (article.get("title") or "").strip()
                    if not title or title in existing_titles:
                        continue
                    url = (article.get("url") or "").strip()
                    if not url or _is_paywalled_url(url) or not _is_direct_article_url(url):
                        continue
                    summary = _strip_html((article.get("description") or "").strip())
                    text = f"{title} {summary}".lower()
                    ai_hit = any(keyword in text for keyword in AI_RELEVANCE_KEYWORDS)
                    if strict_relevance and not _is_relevant(text, context):
                        continue

                    if len(summary) > 400:
                        summary = summary[:397] + "…"

                    db.add(NewsCache(
                        source=source,
                        title=title,
                        url=url,
                        published_at=_parse_iso_datetime(article.get("publishedAt")),
                        summary=summary or None,
                        category="ai" if ai_hit else "markets",
                    ))
                    existing_titles.add(title)
                    added += 1
            except Exception as exc:
                logger.warning(f"NewsAPI request failed for params {params}: {exc}")
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
    for source, query in AI_NEWS_FEEDS:
        feeds.append((source, _google_news_rss_url(query), "ai"))

    return feeds


def _is_relevant(text: str, context: dict) -> bool:
    # If no portfolio context exists, keep broad market coverage.
    if not context["has_portfolio"]:
        return True
    return any(keyword in text for keyword in context["keywords"]) or any(keyword in text for keyword in AI_RELEVANCE_KEYWORDS)


def _build_ranked_payload(db: Session, limit: int) -> list[dict]:
    articles = (
        db.query(NewsCache)
        .filter(~NewsCache.source.in_(BLOCKED_SOURCES))
        .order_by(NewsCache.published_at.desc().nullslast())
        .limit(max(limit * 4, 24))
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
    return _enforce_ai_mix(filtered_payload, top_n=min(2, limit), min_ai=min(2, limit))


def _count_ai_articles(articles: list[dict]) -> int:
    return sum(1 for item in articles if _is_ai_article(item))


def _fetch_ai_only(db: Session) -> int:
    """Quickly fetch only AI feeds to improve top-card relevance."""
    try:
        import feedparser
    except ImportError:
        logger.warning("feedparser not installed — skipping AI-only fetch")
        return 0

    added = 0
    existing_titles = {r.title for r in db.query(NewsCache.title).all()}
    for source, query in AI_NEWS_FEEDS:
        url = _google_news_rss_url(query)
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:16]:
                title = (entry.get("title") or "").strip()
                if not title or title in existing_titles:
                    continue
                summary = _strip_html((entry.get("summary") or entry.get("description") or "").strip())
                text = f"{title} {summary}".lower()
                if not any(keyword in text for keyword in AI_RELEVANCE_KEYWORDS):
                    continue

                raw_url = (entry.get("link") or "").strip()
                if not raw_url or _is_paywalled_url(raw_url):
                    continue
                if not _is_direct_article_url(raw_url):
                    continue

                published = _parse_entry_datetime(entry)
                if len(summary) > 400:
                    summary = summary[:397] + "…"

                db.add(NewsCache(
                    source=source,
                    title=title,
                    url=raw_url,
                    published_at=published,
                    summary=summary or None,
                    category="ai",
                ))
                existing_titles.add(title)
                added += 1
        except Exception as e:
            logger.warning(f"AI-only news fetch failed for {source}: {e}")

    if added > 0:
        db.commit()
    return added


def _is_ai_article(article: dict) -> bool:
    if article.get("category") == "ai":
        return True
    source = (article.get("source") or "").strip()
    if source in {"AI News", "AI Chips", "AI Policy"}:
        return True
    text = f"{article.get('title') or ''} {article.get('summary') or ''}".lower()
    return any(keyword in text for keyword in AI_RELEVANCE_KEYWORDS)


def _enforce_ai_mix(payload: list[dict], top_n: int = 6, min_ai: int = 2) -> list[dict]:
    if len(payload) <= top_n:
        return payload

    top = payload[:top_n]
    ai_in_top = sum(1 for item in top if _is_ai_article(item))
    if ai_in_top >= min_ai:
        return payload

    needed = min_ai - ai_in_top
    ai_candidates = [item for item in payload[top_n:] if _is_ai_article(item)]
    if not ai_candidates:
        return payload

    selected = ai_candidates[:needed]
    # Replace from the bottom of top_n, preferring non-AI slots.
    replace_positions = [i for i in range(top_n - 1, -1, -1) if not _is_ai_article(top[i])]
    if not replace_positions:
        return payload

    new_top = top[:]
    used_ids = set()
    for candidate in selected:
        if not replace_positions:
            break
        pos = replace_positions.pop(0)
        new_top[pos] = candidate
        if candidate.get("id") is not None:
            used_ids.add(candidate["id"])

    remainder = []
    for item in payload[top_n:]:
        item_id = item.get("id")
        if item_id is not None and item_id in used_ids:
            continue
        # fallback compare by object for rows without ids
        if item_id is None and item in selected:
            continue
        remainder.append(item)

    return new_top + remainder


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
        # Google News article redirect URLs are still article-specific.
        return "/articles/" in path.lower() or "/rss/articles/" in path.lower()
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
        # Network hiccups should not nuke cached rows.
        return True


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
        # Only remove if it's clearly dead; keep rows on transient network failures.
        if not _url_is_live(url):
            db.delete(row)
            removed += 1
    if removed > 0:
        db.commit()
