# ADR-002: Taxes Page

**Date:** 2026-04-05
**Status:** Accepted

---

## Context

Users may have multiple income types (W-2, 1099/self-employment, rental, crypto) and varying business entity structures. They need to understand their tax position, reduce liability legally, and get jurisdiction-aware recommendations on business structure. This is not covered in ADR-001.

## Decision

Add a dedicated **Taxes** page with three responsibilities:

1. **Running tax estimate** — current-year federal + state liability broken down by income type, updated as transactions are imported. Prior years in a collapsed history section.

2. **Tax-loss harvesting** — surfaces unrealized losses with estimated savings and wash-sale warnings. Shown as a proactive Insights card + full detail section on the Taxes page.

3. **Entity structure recommendations** — powered by user profile (income, location, business activity). Shows recommended entity, plain-English rationale, estimated annual tax savings vs current structure, and a setup checklist.

## Jurisdiction Awareness

All tax guidance uses `country` + `state` from the user profile in Settings. State-specific rules (no-income-tax states, community property, etc.) are factored in where applicable.

## AI Dependency

Entity structure recommendations and complex tax strategy interpretation require the Claude API (opt-in, key in `.env`). Running estimates and loss harvesting are rule-based and work without an API key.

## Consequences

- New `Taxes` router in backend
- Tax estimate logic must handle: short-term vs long-term capital gains, self-employment tax (15.3%), qualified dividends, rental income deductions
- User profile fields added to `settings` table (see spec for full list)
- `.env` keeps API keys out of the DB and git
