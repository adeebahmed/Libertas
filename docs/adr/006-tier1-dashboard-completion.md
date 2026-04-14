# ADR-006: Tier-1 Net Worth Dashboard Completion

- Status: Accepted
- Date: 2026-04-12

## Context

Phase 2 required Libertas to ship a complete Tier-1 net worth experience: range-aware history, grouped account depth, deterministic offline insights, and measurable local performance.

Prior implementation gaps:
- `/api/snapshots/net-worth` had no range controls.
- Month-end continuity was not guaranteed.
- Dashboard account scan and recommendation UX were incomplete.
- Account details lacked search/filter depth and benchmark context.
- Insights were rule-based but not aligned to a deterministic 15-rule model.

## Decision

1. Introduce `backend/services/snapshots.py` as the canonical snapshot computation layer.
2. Extend snapshot API contract:
- `GET /api/snapshots/net-worth?range=1M|3M|6M|YTD|1Y|ALL`
- `POST /api/snapshots/record-month-end`
- `GET /api/snapshots/current` includes 30-day delta and timestamp metadata.
3. Keep insights fully local/offline and standardize to 15 deterministic rule cards.
4. Expand account depth:
- transaction search/filter query params
- holdings gain/loss and account-weight visibility
- S&P baseline comparison in account performance
- real-estate account detail blocks (value, mortgage, LTV, equity)
5. Add a performance guardrail test (`test_dashboard_perf.py`) enforcing a sub-500ms snapshot path in local test conditions.

## Consequences

Positive:
- Dashboard behavior now maps directly to Phase 2 functional requirements.
- Core data path is tested across history, insights, account depth, and performance.
- UI supports fast scanning and drill-in workflows without cloud dependencies.

Trade-offs:
- S&P comparison is a deterministic baseline approximation (8% annualized), not live index tracking.
- Month-end backfill uses local snapshot continuity rather than new persistence models.

## Follow-ups

- Phase 3 will layer onboarding and FIRE wizard workflows on top of this data model.
- Phase 4 will replace single-provider chat assumptions with multi-model provider selection and prompt orchestration.
