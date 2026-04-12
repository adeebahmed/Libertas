# Phase 3: Onboarding & FIRE Model - Research

**Researched:** 2026-04-11
**Domain:** First-run experience, goal setup flow, FIRE projection usability
**Confidence:** HIGH

## Summary

The project already has retirement projections and settings-backed plan calculation, but it does not have a true first-run onboarding wizard or a dedicated FIRE goal journey integrated into dashboard progress.

Current strengths:
- Retirement projections and plan endpoint exist (`/api/retirement`, `/api/retirement/plan`)
- Settings persist key inputs (birth year, retirement age, monthly contribution, target)
- Dashboard and insights already consume core portfolio state

Primary gaps:
- No first-run route/flow gating new users through setup
- No "data entry method" choice UX during onboarding
- No FIRE-specific inputs for savings rate and target date journey
- No dashboard progress module linked to FIRE goal completion state

<phase_requirements>
## Phase Requirements

| ID | Description |
|----|-------------|
| FR-5.1 | FIRE calculator with scenarios + plain-language readiness output |
| FR-5.2 | Goal-setting journey and progress visualization |
| FR-6.1 | First-run wizard (method -> first account -> goal -> dashboard) |
| FR-6.2 | Privacy-by-design mission callout in onboarding/dashboard |
</phase_requirements>

## Execution Recommendation

1. Onboarding state + backend profile/status contract
2. Wizard UI and step transitions
3. FIRE model API expansion and clear language outputs
4. Goal progress modules on dashboard + onboarding completion persistence
5. ADR + validation sign-off
