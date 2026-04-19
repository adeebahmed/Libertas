# ADR-009: Optional Plaid + Sheets Integration with Canonical Multi-Source Ingest

- Date: 2026-04-14
- Status: Accepted

## Context

Libertas is local-first and must keep CSV/Excel/manual workflows fully first-class. We need expanded source coverage for household cashflow and liabilities without introducing blocking cloud coupling.

## Decision

1. Add optional integrations under Settings only:
- Plaid link/exchange/sync/relink/disconnect
- Google Sheets CSV-export feeds (no Google OAuth)

2. Route all sources through one canonical ingest precedence model:
- `plaid external_id` > `csv/excel import hash` > `sheets row id` > `manual`

3. Persist provenance + conflict metadata on accounts and transactions for debugging.

4. Encrypt provider secrets at rest locally.

5. Default sync cadence:
- User-triggered manual sync anytime
- Daily background sync loop

## Consequences

Positive:
- Better source coverage while preserving local-first usage
- Deterministic dedup and clearer merge behavior
- Optionality preserved: users ignoring integrations retain existing UX

Trade-offs:
- Plaid connectivity depends on external credentials/network
- Sheets feeds depend on stable CSV URLs and column mapping quality

## Out of Scope

- PDF parsing/OCR (explicitly deferred)
- Google OAuth Sheets API integration
- Mandatory onboarding connect flows
