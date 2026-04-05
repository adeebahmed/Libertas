# ADR-004: User Profile and AI-Powered Guidance

**Date:** 2026-04-05
**Status:** Accepted

---

## Context

ADR-001's Insights page mentioned an optional Claude API chat. This ADR formalizes a broader decision: collect a rich user profile in Settings and use it to power personalized, jurisdiction-aware guidance across the entire app — Insights, Taxes, and Projections.

## Decision

### User Profile (stored in `settings` table)
Collect the following to personalize guidance:
- Date of birth, country, state/province
- Tax filing status, estimated income by type (W-2, 1099, rental)
- Current business entity (none / sole prop / LLC / S-Corp / other)
- Risk profile, monthly expenses, retirement target age and amount

This profile is passed as context to the Claude API for any AI-powered feature.

### Guidance Tiers

**Rule-based (no API key required):**
- Tax estimates, tax-loss harvesting flags, insight cards, projection curves
- Uses user profile for jurisdiction-specific rules

**AI-powered (opt-in, requires `CLAUDE_API_KEY` in `.env`):**
- Insights chat (full portfolio + profile as context)
- Entity structure recommendations (reasoning + estimated savings + setup checklist)
- Complex tax strategy interpretation

### Privacy
- User profile stored only in local SQLite DB
- Claude API calls are made server-side; only relevant slices of data are sent (not the full DB)
- API key in `.env`, gitignored

## Consequences

- Settings page gains a "User Profile" section
- New settings keys added to `settings` table (see spec for full list)
- Backend profile-aware logic in `insights.py` and new `taxes.py` router
- Claude API integration centralized in a new `ai.py` utility module
- `.env.example` documents `CLAUDE_API_KEY` without a real value
