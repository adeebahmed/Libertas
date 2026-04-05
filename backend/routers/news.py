from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import logging

from ..database import get_db
from ..models import NewsCache

router = APIRouter(prefix="/api/news", tags=["news"])
logger = logging.getLogger(__name__)

FINANCE_FEEDS = [
    ("MarketWatch", "https://feeds.marketwatch.com/marketwatch/topstories/"),
    ("Yahoo Finance", "https://finance.yahoo.com/rss/"),
    ("Seeking Alpha", "https://seekingalpha.com/feed.xml"),
    ("CNBC", "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114"),
    ("Reuters", "https://feeds.reuters.com/reuters/businessNews"),
]

CACHE_TTL_HOURS = 2


@router.get("")
def get_news(limit: int = 20, db: Session = Depends(get_db)):
    """Return cached news, auto-refreshing if stale."""
    cutoff = datetime.utcnow() - timedelta(hours=CACHE_TTL_HOURS)
    latest = db.query(NewsCache).order_by(NewsCache.fetched_at.desc()).first()

    if not latest or latest.fetched_at < cutoff:
        _fetch_and_cache(db)

    articles = (
        db.query(NewsCache)
        .order_by(NewsCache.published_at.desc().nullslast())
        .limit(limit)
        .all()
    )
    return [
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


@router.post("/refresh")
def refresh_news(db: Session = Depends(get_db)):
    """Force a news refresh."""
    count = _fetch_and_cache(db)
    return {"fetched": count}


def _fetch_and_cache(db: Session) -> int:
    """Fetch RSS feeds and upsert into news_cache. Returns count of new articles."""
    try:
        import feedparser
    except ImportError:
        logger.warning("feedparser not installed — skipping news fetch")
        return 0

    # Clear articles older than 7 days
    cutoff = datetime.utcnow() - timedelta(days=7)
    db.query(NewsCache).filter(NewsCache.fetched_at < cutoff).delete()

    existing_titles = {r.title for r in db.query(NewsCache.title).all()}
    added = 0

    for source, url in FINANCE_FEEDS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:10]:
                title = (entry.get("title") or "").strip()
                if not title or title in existing_titles:
                    continue

                published = None
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    try:
                        import time as _time
                        published = datetime.fromtimestamp(_time.mktime(entry.published_parsed))
                    except Exception:
                        pass

                summary = (entry.get("summary") or "").strip()
                if len(summary) > 400:
                    summary = summary[:397] + "…"

                db.add(NewsCache(
                    source=source,
                    title=title,
                    url=entry.get("link") or "",
                    published_at=published,
                    summary=summary or None,
                    category="markets",
                ))
                existing_titles.add(title)
                added += 1
        except Exception as e:
            logger.warning(f"News fetch failed for {source}: {e}")

    if added > 0:
        db.commit()
    return added
