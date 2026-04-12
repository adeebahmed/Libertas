# ADR-002 — Data Ingestion Strategy: Multi-Source Support
**Status: Accepted | 2026-04-11**

---

## Context

ADR-001 established CSV/Excel file import as the sole data ingestion method, citing privacy as a first-class feature:

> *"CSV/Excel import only — no direct institution API links (privacy trade-off, intentional)"*

This was the right call for the initial prototype. However, as Libertas evolves toward a genuine financial freedom planning tool, the friction of manual CSV exports has become a real barrier to usefulness:

- Users won't maintain accurate data if the update flow is tedious
- Debt balances and cash accounts are especially painful to track via CSV exports
- Manual entry for simple values (salary, savings balance) shouldn't require a file at all
- Real-time accuracy matters for FIRE planning — stale data produces wrong retirement projections

The goal is to support all three data paths, with privacy preserved as a default and any third-party connectivity remaining **explicitly opt-in**.

---

## Decision

Libertas will support three data ingestion methods, ordered by friction (lowest to highest):

### 1. Manual User Input (new)
Direct in-app entry for any financial value: account balances, debt balances, income, expenses. No file, no external service. The baseline that works on day one for any user.

- Always available, always free
- Best for: cash accounts, informal debt, income, one-off values
- Stored directly in SQLite

### 2. CSV / Excel File Import (existing, from ADR-001)
Preserved as-is. Watch folder + column mapping + institution presets remain core. No change to existing behavior.

- Best for: brokerage exports (Fidelity, Schwab, Robinhood), crypto (Coinbase), bank statement history
- Still the most privacy-preserving path for transaction history

### 3. Plaid Integration (new, opt-in)
Real-time bank account, credit card, and liability sync via Plaid (or a free alternative — see below). Requires explicit user opt-in and credential setup. Never enabled by default.

- Best for: live balance sync, credit card tracking, debt liabilities (student loans, auto, mortgage)
- User controls connection; credentials are stored locally (Plaid access tokens in SQLite, never sent to Libertas servers — there are none)
- **Cost constraint:** Plaid's production pricing is non-trivial. Free alternatives must be evaluated first (SimpleFIN Bridge, Teller.io personal tier, direct OFX export). Plaid is only chosen if alternatives are clearly inferior for the use case. See issue #26.

---

## Privacy Position (updated)

The original privacy stance is preserved and strengthened, not weakened:

| Method | Data leaves machine? | Third party involved? |
|---|---|---|
| Manual input | No | No |
| CSV import | No | No |
| Plaid (opt-in) | Plaid token exchange only | Yes — Plaid (or alternative) |

Plaid integration does involve a third-party token exchange during the OAuth flow. This is disclosed clearly in the UI. Once connected, transaction/balance data is fetched directly from the bank via Plaid and stored locally in SQLite — no Libertas cloud, no external analytics.

**Privacy as a feature remains front-and-center.** Plaid is opt-in, clearly labeled, and the user can always use CSV or manual entry instead.

---

## Consequences

- The FIRE model and net worth calculation must aggregate data from all three sources cleanly
- The data model needs a `source` field on accounts/balances to track origin (manual | csv | plaid)
- Onboarding flow must present all three options without overwhelming new users
- Legal scan (#2) must account for Plaid's data handling terms in addition to AI advice framing
- ADR-001's CSV importer is unchanged; this ADR adds to it, does not replace it

---

## Alternatives Considered

**Keep CSV-only:** Rejected. Too much friction for ongoing use. A financial freedom planner needs accurate, current data — weekly CSV exports are not a sustainable user behavior.

**Replace CSV with Plaid-only:** Rejected. Breaks the privacy guarantee. Many users specifically choose Libertas *because* there's no account linking. CSV + manual must remain viable standalone paths.

**Manual entry only for MVP:** Valid for day-one simplicity. CSV and Plaid can follow. This is the recommended MVP order: manual first, CSV already exists, Plaid after cost evaluation.
