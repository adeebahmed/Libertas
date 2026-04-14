---
phase: 3
slug: onboarding-fire
status: draft
nyquist_compliant: false
wave_0_complete: true
created: 2026-04-11
updated: 2026-04-13
---

# Phase 3 — Validation Strategy

## Automated Checks

| Area | Command |
|------|---------|
| Backend | `cd backend && python -m pytest backend/tests/ -x -q` |
| Frontend | `cd frontend && npm run build` |

## Per-Task Verification Map

| Task ID | Plan | Requirement | Automated Command | Status |
|---------|------|-------------|-------------------|--------|
| 3-01-01 | 03-01 | FR-6.1 | `pytest tests/test_onboarding.py -q` | ⬜ pending |
| 3-02-01 | 03-02 | FR-6.1 | `cd frontend && bun run build` | ⬜ pending |
| 3-03-01 | 03-03 | FR-5.1 | `pytest tests/test_retirement.py -k "fire" -q` | ⬜ pending |
| 3-04-01 | 03-04 | FR-5.2/FR-6.2 | `cd frontend && bun run build` | ⬜ pending |
| 3-05-01 | 03-05 | phase close | `pytest tests/ -q` | ⬜ pending |

## Current Implementation Evidence (Branch PR Review)

| Ticket | Branch | Verification Artifact |
|--------|--------|-----------------------|
| #54 | `codex/54-phase3-onboarding-primitives` | `backend/tests/test_onboarding.py` passing |
| #55 | `codex/55-phase3-onboarding-wizard` | Frontend build passing |
| #56 | `codex/56-phase3-retirement-fire-engine` | `backend/tests/test_retirement.py` + frontend build passing |
| #57 | `codex/57-phase3-dashboard-fire-progress` | Frontend build passing |
| #58 | `codex/58-phase3-validation-adr` | ADR-007 + validation doc updates |

## Exit Criteria

- All five Phase 3 PRs reviewed and approved.
- Project board cards #53–#58 moved to `Done`.
- Local demo walkthrough completed on Vite dev server.

## Manual Verification

| Behavior | Check |
|----------|-------|
| First-run path | New user reaches dashboard in <3 min |
| Goal optionality | User can skip goal and still complete onboarding |
| Privacy callout | Local-first message visible and readable in flow |
| FIRE calculator | Type switch updates projection outputs |
| Dashboard progress | FIRE module shows progress + nudges |
