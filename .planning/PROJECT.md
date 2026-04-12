# Libertas — Project Context

## Vision

A local-first personal finance dashboard that works like a personal financial advisor in your pocket. Own your data, own your insights. No credentials leaving your machine, no SaaS subscriptions, no privacy trade-offs.

**Positioning:** The only app combining fully local/offline operation + multi-asset net worth (crypto + real estate + brokerage) + CSV import with saved mappings + conversational AI. Copilot requires Plaid and is iOS-only. No privacy-respecting competitor offers full-context LLM chat against real user data.

## Core Differentiators

1. **Local-first by design** — SQLite on your machine. No cloud sync, no account linking required. Zero credentials leave the device.
2. **AI-powered insights** — Talk to your finances like having a personal financial advisor. Rule engine does the math; Claude explains it.
3. **CSV-sourced investment data** — Because data matches exactly what you exported, investment accuracy is inherently better than live-sync competitors (the most-complained-about feature category across all finance apps).
4. **Multi-asset depth** — Brokerage, crypto, real estate, cash, and liabilities in one unified net worth view.

## Target Users

- Privacy-first DIY investors burned by the Plaid $58M data-sharing lawsuit
- Multi-account portfolio holders with no unified view (brokerage + crypto + real estate)
- Mint refugees (shut down March 2024) who want depth without iOS-only or cloud-required replacements
- Developer/power users who want SQLite access and open architecture

## V1 Scope

**Milestone 1 — MVP:** Core data pipeline, dashboard, onboarding, FIRE model
**Milestone 2 — Multi-Model:** LLM provider abstraction, Claude/OpenAI/Ollama support
**Milestone 3 — Plaid:** Optional account linking for users who want it

## Success Criteria for V1

- [ ] Net worth dashboard with hero number, allocation donut, time-series, staleness indicators
- [ ] Manual data entry works without needing a CSV (day-one usability)
- [ ] CSV import is idempotent with visible deduplication feedback
- [ ] FIRE model answers "Can I retire by date X?" with adjustable scenarios
- [ ] Onboarding flow guides new users to their first net worth view
- [ ] AI chat (Claude) works with opt-in API key, labeled as informational

## Design North Star

Reference: **Copilot Money** (copilot.money)
Target aesthetic: Modern, clean, non-generic. The Jarvis/executive palette established in the new-ux branch.

## GitHub Project Board

Issues are organized into three milestones:
- **MVP:** #28 (manual entry), #25 (onboarding), #24 (FIRE model), #11 (user journey), #10 (mission differentiation)
- **Multi-Model:** #18 (abstraction layer), #19 (Claude), #20 (OpenAI), #21 (Ollama), #22 (model UI), #23 (prompt management), #27 (cost evaluation)
- **Plaid Integration:** #13 (OAuth flow), #14 (bank sync), #17 (debt data), #26 (pricing evaluation)

## Stack

- **Backend:** Python 3.12+, FastAPI, SQLAlchemy, SQLite (`/data/libertas.db`)
- **Frontend:** Vite + React 18 + TypeScript + Recharts
- **Dev:** `./start.sh` — backend (port 8000) + frontend (port 5173/5174)
