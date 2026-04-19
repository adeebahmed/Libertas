# ADR-011: Overview Collapsed Market Tape

- Status: Accepted
- Date: 2026-04-19

## Context

Libertas needs a fast-scanning, market-style information strip that helps users stay oriented without turning the dashboard into a noisy feed.

The requirement is to show three signal types in one strip:

1. Clickable news headlines from the existing news cache
2. Top invested symbols with live-ish price context from locally stored holdings data
3. Personal finance signals derived from user data, while preserving privacy on shared screens

This must fit the existing dashboard hero behavior and remain readable in both `onyx` and `retro` themes.

## Decision

1. Add a backend aggregation endpoint: `GET /api/dashboard/tape`.
2. Compose tape content from local/cached sources only:
   - News: ranked cached news (`/api/news` source logic reused), URL-backed rows only, capped at 80.
   - Tickers: top 5 symbols by aggregated market value (`last_price * quantity`, fallback `cost_basis`).
   - Personal: up to 4 aggregate actionable signals (top insight summary, 30d net worth momentum, stale-account count, liquidity/debt nudge).
3. Use a deterministic sequence rule for the tape stream:
   - `8 news -> up to 5 ticker -> up to 4 personal`, then repeat for additional news blocks.
4. Render the tape only on Overview and only when the hero is collapsed.
5. Keep personal tape content aggregate-only (no account or institution names).
6. Add motion/accessibility safeguards:
   - Pause on hover/focus
   - Respect `prefers-reduced-motion` with static horizontal scroll fallback

## Consequences

Positive:
- Adds a high-signal “at-a-glance” layer without requiring new external services.
- Preserves Libertas’ local-first and privacy-first mission.
- Reuses existing ranking/insight logic and keeps API fan-out to one frontend call.

Trade-offs:
- Tape freshness depends on existing background refresh cadence for prices/news.
- Personal signals are intentionally less specific (aggregate-only) to avoid exposing sensitive labels.

## Follow-ups

- Add optional user controls in Settings (speed, density, segment toggles).
- Consider optional pinning for custom symbols beyond top-invested holdings.
