# Phase 5: Plaid Integration (Post-V1) - Research

**Researched:** 2026-04-11
**Domain:** Optional bank sync architecture, OAuth/link flow, deduplicated ingestion
**Confidence:** MEDIUM-HIGH (designed as post-V1 with compatibility-first constraints)

## Summary

Plaid is intentionally post-V1 and must remain optional. The codebase already includes CSV and manual workflows; the integration must not degrade local-first behavior or introduce mandatory cloud coupling.

Critical constraints:
- Users who do not connect Plaid should never see blocking Plaid UX
- CSV/manual workflows remain first-class and can coexist per account
- Sync data must deduplicate with existing import hash patterns
- Credentials and tokens stay local in SQLite settings/tables

<phase_requirements>
## Phase Requirements

| ID | Description |
|----|-------------|
| FR-8.1 | Optional Plaid Link + OAuth token exchange |
| FR-8.2 | Account and transaction sync from Plaid |
| FR-8.3 | Debt/liability data mapping where available |
| FR-8.4 | Pricing/alternative guidance and explicit optionality |
| NFR-4 | Reuse external_id/sync_source extensibility without breaking CSV |
</phase_requirements>

## Execution Recommendation

1. Data model and feature-flag foundation
2. Link-token/public-token backend flow
3. Accounts + transactions sync and dedup rules
4. Debt mapping and sync refresh strategy
5. Frontend optional connect/manage UI
6. ADR, pricing guidance, and validation sign-off
