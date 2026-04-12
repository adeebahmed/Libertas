---
phase: 4
slug: ai-multi-model
status: draft
nyquist_compliant: false
wave_0_complete: true
created: 2026-04-11
---

# Phase 4 — Validation Strategy

## Automated Checks

| Area | Command |
|------|---------|
| Backend unit | cd backend && python -m pytest tests/test_ai_providers.py -q |
| Backend integration | cd backend && python -m pytest tests/test_insights_chat.py -q |
| Frontend build | cd frontend && bun run build |

## Per-Task Verification Map

| Task ID | Plan | Requirement | Command | Status |
|---------|------|-------------|---------|--------|
| 4-01-01 | 04-01 | FR-7.1 | pytest tests/test_ai_abstraction.py -q | ⬜ pending |
| 4-02-01 | 04-02 | FR-7.2 | pytest tests/test_ai_providers.py -k claude -q | ⬜ pending |
| 4-03-01 | 04-03 | FR-7.2 | pytest tests/test_ai_providers.py -k openai -q | ⬜ pending |
| 4-04-01 | 04-04 | FR-7.2 | pytest tests/test_ai_providers.py -k ollama -q | ⬜ pending |
| 4-05-01 | 04-05 | FR-7.3/7.4 | cd frontend && bun run build | ⬜ pending |
| 4-06-01 | 04-06 | FR-7.4 | pytest tests/test_insights_chat.py -q | ⬜ pending |
| 4-07-01 | 04-07 | phase close | pytest tests/ -q | ⬜ pending |

## Manual Verification

| Behavior | Check |
|----------|-------|
| Provider switching | Change provider in settings and verify chat response path |
| Cost hints | Confirm provider cost guidance appears in settings |
| Advisory label | Confirm every AI response is tagged informational/non-advice |
