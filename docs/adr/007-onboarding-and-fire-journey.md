# ADR-007: Onboarding + FIRE Journey Architecture

- **Date:** 2026-04-13
- **Status:** Accepted
- **Related Phase:** Phase 3 (Onboarding & FIRE)
- **Supersedes:** None

## Context

Libertas Phase 2 improved dashboard clarity, but first-run experience and retirement goal modeling remained fragmented:

- New users could land in a blank app without guided setup.
- Retirement outputs existed, but no unified FIRE mode selection and recommendation flow.
- Goal progress lived mostly in retirement views, not in daily dashboard context.

Phase 3 requires a cohesive flow:

1. Guide first-time users to value quickly.
2. Provide deterministic FIRE modeling (offline/local-first).
3. Surface progress and nudges in primary app views.

## Decision

We adopt a 3-part architecture:

1. **Onboarding state contract**
   - Persist `onboarding_complete` in settings.
   - Expose onboarding status endpoint for frontend route gating.
   - Keep onboarding data local and deterministic.

2. **Retirement/FIRE API split**
   - Keep legacy projection endpoint for compatibility.
   - Add dedicated FIRE endpoints for:
     - overview metrics
     - FIRE projection by type
     - recommendation reasoning
   - Recommendation engine stays rule-based (no external AI dependency).

3. **Dashboard goal-progress integration**
   - Add FIRE progress component to dashboard.
   - Show deterministic nudges tied to model outputs.
   - Use selected FIRE type context for user-facing status language.

## Consequences

### Positive

- Faster first-run activation and clearer path to first value.
- Better separation of concerns between generic projection and FIRE-specific modeling.
- Unified progress visibility across retirement and dashboard surfaces.
- Fully local/offline-compatible behavior remains intact.

### Trade-offs

- Additional API and frontend state complexity.
- FIRE recommendations are intentionally heuristic, not personalized advice.
- Some metrics depend on data quality from imported/manual account coverage.

## Alternatives Considered

1. **Single monolithic retirement endpoint**
   - Rejected: hard to evolve, weak frontend composability.

2. **AI-generated FIRE recommendation**
   - Rejected for Phase 3: non-deterministic, adds external dependency and privacy complexity.

3. **Onboarding only in frontend local storage**
   - Rejected: no reliable cross-device/profile persistence and weaker backend observability.

## Rollout Notes

- Ship as separate PRs mapped to Phase 3 tickets (#54–#58).
- Keep project board statuses synchronized with branch/PR progress.
- Validate with backend tests and frontend production build before merge.
