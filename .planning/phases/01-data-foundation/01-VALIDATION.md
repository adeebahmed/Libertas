---
phase: 1
slug: data-foundation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-11
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | `backend/` (run from project root) |
| **Quick run command** | `cd backend && python -m pytest tests/ -x -q` |
| **Full suite command** | `cd backend && python -m pytest tests/ -v` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && python -m pytest tests/ -x -q`
- **After every plan wave:** Run `cd backend && python -m pytest tests/ -v`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 1-01-01 | 01 | 1 | FR-1.1 | — | N/A | unit | `pytest tests/test_accounts.py -k "test_manual_account_create"` | ❌ W0 | ⬜ pending |
| 1-01-02 | 01 | 1 | FR-1.1 | — | N/A | unit | `pytest tests/test_accounts.py -k "test_manual_transaction_entry"` | ❌ W0 | ⬜ pending |
| 1-01-03 | 01 | 1 | FR-1.1 | — | N/A | unit | `pytest tests/test_accounts.py -k "test_manual_holdings_entry"` | ❌ W0 | ⬜ pending |
| 1-01-04 | 01 | 2 | FR-1.2 | — | N/A | unit | `pytest tests/test_ingest.py -k "test_csv_idempotent"` | ❌ W0 | ⬜ pending |
| 1-01-05 | 01 | 2 | FR-1.2 | — | N/A | unit | `pytest tests/test_ingest.py -k "test_parse_error_surfacing"` | ❌ W0 | ⬜ pending |
| 1-01-06 | 01 | 2 | FR-1.2 | — | N/A | unit | `pytest tests/test_ingest.py -k "test_encoding_autodetect"` | ❌ W0 | ⬜ pending |
| 1-01-07 | 01 | 3 | FR-1.3 | — | N/A | unit | `pytest tests/test_accounts.py -k "test_staleness_indicator"` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/test_accounts.py` — stubs for FR-1.1 (manual account/transaction/holdings CRUD)
- [ ] `backend/tests/test_ingest.py` — stubs for FR-1.2 (CSV hardening: idempotency, error surfacing, encoding)
- [ ] `backend/tests/conftest.py` — shared test database fixture (in-memory SQLite)

*Wave 0 must be created before Wave 1 tasks begin.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Transfer pair detection surface in import UI | FR-1.2 | Requires visual UI verification | Import a CSV with matching debit/credit across accounts; confirm pair is highlighted in import preview |
| Account staleness color rendering | FR-1.3 | CSS/visual state | Add an account, set last_updated to >7 days ago in DB; confirm red indicator renders on dashboard |
| Column mapping persistence across re-imports | FR-1.2 | Requires two sequential import actions | Import CSV for an institution, verify mapping saved; import again, confirm same mapping auto-applied |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
