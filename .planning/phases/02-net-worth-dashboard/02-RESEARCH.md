# Phase 2: Net Worth Dashboard - Research

**Researched:** 2026-04-11
**Domain:** Dashboard correctness, history ranges, account depth views, rule-based insight quality
**Confidence:** HIGH (validated against current backend/frontend code)

---

## Summary

Phase 2 should convert the existing dashboard into a complete Tier-1 net worth experience with explicit range controls, grouped account depth, and stronger correctness/performance guarantees.

What already exists:
- Hero net worth and delta (`/api/snapshots/current`)
- Allocation donut and timeline chart (`/api/snapshots/net-worth`)
- Account cards and market news in `Dashboard.tsx`
- Rule-based insights endpoint (`/api/insights`)

Key gaps to close for FR-2 / FR-3 / FR-4:
- No time range selector for net-worth history (1M/3M/6M/YTD/1Y/All)
- No monthly snapshot scheduler/command to guarantee month-end continuity
- Dashboard accounts are not grouped by type and have no quick-add entry point
- Account transaction/holding depth exists partially but lacks robust search/filter UX
- Insight engine has useful rules but needs deterministic tests and explicit offline-mode contract checks

---

<phase_requirements>
## Phase Requirements

| ID | Description |
|----|-------------|
| FR-2.1 | Hero net worth, 30-day change %, last-updated timestamp |
| FR-2.2 | Allocation donut by asset class incl. liabilities |
| FR-2.3 | Time-range net-worth chart + month-end snapshots |
| FR-2.4 | Grouped account list + quick-add + account detail navigation |
| FR-3.1 | Per-account searchable/filterable transactions |
| FR-3.2 | Holdings breakdown with gain/loss and benchmark comparison |
| FR-3.3 | Real estate detail with value, mortgage, LTV, equity |
| FR-4.1 | Rule-based insight cards (risk/liquidity/drift/emergency/debt-to-income) |
| FR-4.2 | Insights work offline without AI dependency |
| NFR-1 | Dashboard query path <500ms on local SQLite |
</phase_requirements>

---

## Execution Recommendation

Split phase into five plans:
1. Backend history + snapshot cadence APIs
2. Dashboard hero/allocation/range UX and grouped account panel
3. Account depth views (transactions, holdings, real-estate detail)
4. Insight engine hardening with tests and offline contract checks
5. Final polish + performance profiling + ADR
