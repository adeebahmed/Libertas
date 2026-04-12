---
phase: 2
slug: net-worth-dashboard
status: draft
nyquist_compliant: false
wave_0_complete: true
created: 2026-04-11
---

# Phase 2 — Validation Strategy

## Test Infrastructure

| Property | Value |
|----------|-------|
| Framework | pytest + frontend smoke checks |
| Quick run | `cd backend && python -m pytest tests/ -x -q` |
| Frontend check | `cd frontend && bun run build` |
| Full run | backend tests + frontend build |

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | Status |
|---------|------|------|-------------|-----------|-------------------|--------|
| 2-01-01 | 02-01 | 1 | FR-2.3 | unit | `pytest tests/test_snapshots.py -q` | ⬜ pending |
| 2-02-01 | 02-02 | 2 | FR-2.1/2.2/2.4 | ui-build | `cd frontend && bun run build` | ⬜ pending |
| 2-03-01 | 02-03 | 2 | FR-3.1/3.2/3.3 | integration | `pytest tests/test_accounts.py -k "performance or transactions" -q` | ⬜ pending |
| 2-04-01 | 02-04 | 3 | FR-4.1/4.2 | unit | `pytest tests/test_insights.py -q` | ⬜ pending |
| 2-05-01 | 02-05 | 3 | NFR-1 | benchmark | `pytest tests/test_dashboard_perf.py -q` | ⬜ pending |

## Manual Verification

| Behavior | Check |
|----------|-------|
| Range selector UX | Confirm 1M/3M/6M/YTD/1Y/All updates chart correctly |
| Grouped account cards | Confirm investments/cash/real-estate/liabilities grouping |
| Account detail drill-in | Confirm filters/search and holdings gain/loss render correctly |

## Validation Sign-Off

- [ ] All new backend routes covered by tests
- [ ] Frontend build green
- [ ] Dashboard render and API response timings recorded
- [ ] `nyquist_compliant: true` updated at phase completion
