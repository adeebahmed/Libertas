---
phase: 3
slug: onboarding-fire
status: draft
nyquist_compliant: false
wave_0_complete: true
created: 2026-04-11
---

# Phase 3 — Validation Strategy

## Automated Checks

| Area | Command |
|------|---------|
| Backend | `cd backend && python -m pytest tests/ -x -q` |
| Frontend | `cd frontend && bun run build` |

## Per-Task Verification Map

| Task ID | Plan | Requirement | Automated Command | Status |
|---------|------|-------------|-------------------|--------|
| 3-01-01 | 03-01 | FR-6.1 | `pytest tests/test_onboarding.py -q` | ⬜ pending |
| 3-02-01 | 03-02 | FR-6.1 | `cd frontend && bun run build` | ⬜ pending |
| 3-03-01 | 03-03 | FR-5.1 | `pytest tests/test_retirement.py -k "fire" -q` | ⬜ pending |
| 3-04-01 | 03-04 | FR-5.2/FR-6.2 | `cd frontend && bun run build` | ⬜ pending |
| 3-05-01 | 03-05 | phase close | `pytest tests/ -q` | ⬜ pending |

## Manual Verification

| Behavior | Check |
|----------|-------|
| First-run path | New user reaches dashboard in <3 min |
| Goal optionality | User can skip goal and still complete onboarding |
| Privacy callout | Local-first message visible and readable in flow |
