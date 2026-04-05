# ADR-003: News Feed Integration

**Date:** 2026-04-05
**Status:** Accepted

---

## Context

The Dashboard should surface news articles relevant to the user's holdings and interests (Tech, Politics, Markets, Crypto). This requires an external data source. The app's privacy-first constraint means no mandatory cloud accounts.

## Decision

Dual-source news feed:

- **RSS feeds** (Reuters, AP, Yahoo Finance) — always available, no API key required, fetched server-side
- **NewsAPI** — richer filtering by ticker/topic, requires a free API key stored in `.env` as `NEWS_API_KEY`

When both sources are configured, results are merged and deduplicated. Holdings-based results (articles mentioning symbols the user holds) rank above category-based results.

If `NEWS_API_KEY` is absent, the app falls back to RSS silently — no error shown to the user.

## Caching

News is cached in a `news_cache` table (see spec for schema) to avoid repeated API calls. Cache TTL: 30 minutes. Backend fetches on dashboard load if cache is stale.

## Privacy

- No user data is sent to NewsAPI beyond ticker symbols and category keywords
- API key stored in `.env`, gitignored, never committed
- Settings page shows masked key status only

## Consequences

- New `news` router in backend
- `news_cache` table added to DB
- `NEWS_API_KEY` documented in `.env.example` (no actual key committed)
- RSS parsing library needed (`feedparser` or equivalent)
