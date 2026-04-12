# Libertas — Roadmap

## Goal: V1 — Production-ready personal finance dashboard

**Milestones aligned with GitHub project board:**
- Phases 1-3 → MVP milestone
- Phase 4 → Multi-Model milestone
- Phase 5 → Plaid Integration (post-V1, architecture ready)

---

## Phase 1: Data Foundation

**Goal:** Complete, reliable data layer that works day-one without CSV files.

**GitHub Issues:** #28 (manual data entry)

**Plans:** 5 plans

**What gets built:**
- Manual account creation and balance editing (all account types: checking, savings, brokerage, IRA/401k, crypto, real estate, auto loan, student loan, mortgage, credit card)
- Manual transaction entry per account
- Manual holdings entry for investment accounts (symbol, shares, cost basis)
- CSV import hardening: idempotent deduplication, parse error surfacing, header drift detection, encoding auto-detection, junk-row skipping, transfer pair detection
- Account staleness indicators (green/yellow/red based on last-updated timestamp)
- Database schema extensibility hooks for future Plaid sync (`external_id`, `sync_source` columns)

Plans:
- [ ] 01-01-PLAN.md — Test infrastructure (pytest, conftest, stub tests)
- [ ] 01-02-PLAN.md — Schema migrations (9 new columns across 5 models)
- [ ] 01-03-PLAN.md — Backend manual entry endpoints (balance, transactions, holdings)
- [ ] 01-04-PLAN.md — CSV import hardening (chardet encoding, per-row errors, header drift, transfer pairs)
- [ ] 01-05-PLAN.md — Frontend manual entry modals + staleness indicators + import quality display

**Success criteria:**
- New user can reach a populated net worth view using only manual entry, no CSV required
- Re-importing the same CSV file produces zero new records
- CSV parse errors shown with count and sample rows (never silently dropped)
- All account types with positive and negative balances supported

---

## Phase 2: Net Worth Dashboard

**Goal:** The "is it real?" test — five Tier 1 features every net worth dashboard needs.

**GitHub Issues:** #10 (mission differentiation)

**What gets built:**
- Hero net worth number (assets minus liabilities) with 30-day change
- Asset allocation donut by asset class (Equities, Cash, Crypto, Real Estate, Liabilities)
- Net worth over time line chart with time range selector (1M / 3M / 6M / YTD / 1Y / All)
- Monthly snapshot stored automatically at end of each calendar month
- Account list grouped by type with staleness indicators and quick-add
- Per-account depth: transaction history (searchable/filterable), holdings breakdown, real estate equity view
- Rule-based insight cards: concentration risk, liquidity ratio, emergency fund coverage, allocation drift
- "Privacy by design" in-app callout (#10): local-first positioning visible on dashboard

**Success criteria:**
- Dashboard renders with accurate net worth in <500ms
- Allocation donut includes liabilities (not just assets)
- Net worth chart shows full history from first imported data
- All five Tier 1 features complete and polished

---

## Phase 3: Onboarding & FIRE Model

**Goal:** Users understand the product on day one and can define + track their financial freedom goal.

**GitHub Issues:** #25 (onboarding), #24 (FIRE model), #11 (user journey)

**What gets built:**
- First-run wizard: data entry method selection → first account → goal setting → dashboard
- FIRE calculator: current savings rate, annual expenses, expected return, target retirement date
- Three CAGR scenarios (conservative 4%, base 6%, optimistic 8%)
- "Can I retire by [date]?" output with plain-language projection
- Goal progress visualization on main dashboard (progress toward FIRE number)
- User journey for financial freedom goal-setting (#11)

**Success criteria:**
- First-run wizard guides a user to their first net worth view in under 3 minutes
- FIRE calculator produces a readable retirement projection
- Dashboard shows goal progress without requiring FIRE model usage (optional)

---

## Phase 4: AI & Multi-Model Intelligence

**Goal:** "Talk to your finances like having a personal financial advisor."

**GitHub Issues:** #18 (abstraction), #19 (Claude), #20 (OpenAI), #21 (Ollama), #22 (model UI), #23 (context management), #27 (cost evaluation)

**What gets built:**
- LLM provider abstraction layer with clean interface (#18)
- Claude (Anthropic) integration with API key stored locally (#19)
- OpenAI integration (#20)
- Ollama local model support (#21)
- Model selection UI in Settings with provider status and model picker (#22)
- Provider cost estimates and free/local option recommendations (#27)
- Summarization/context management system (#23):
  - Rolling 90-day transaction window by default
  - Pre-computed account summaries (net worth, allocation, recent patterns)
  - System prompt with financial context injected automatically
- AI chat interface in Insights panel
- Answers labeled as informational, not financial advice (legal compliance)

**Success criteria:**
- User can select Claude, OpenAI, or Ollama and ask financial questions
- "Where did my money go last month?" returns accurate answer from transaction data
- AI answers reference actual user data, not generic advice
- Large transaction histories (2+ years) don't hit context limits

---

## Phase 5: Plaid Integration (Post-V1)

**Goal:** Optional account linking for users who want live sync without compromising local-first architecture.

**GitHub Issues:** #13 (OAuth flow), #14 (bank sync), #17 (debt data), #26 (pricing/alternatives evaluation)

**What gets built:**
- Plaid OAuth connection flow (#13)
- Bank account and credit card transaction sync (#14)
- Debt data sourcing and sync model (#17)
- Plaid pricing evaluation and free alternative options (#26)
- Sync coexists with CSV import — both can be active for same account

**Success criteria:**
- Plaid connection doesn't break existing CSV-only workflow
- Transactions from Plaid deduplicate correctly with CSV-imported transactions
- Users who don't want Plaid see zero Plaid UI (fully optional)

---

## Phases at a Glance

| Phase | Focus | GitHub Issues | Milestone |
|-------|-------|---------------|-----------|
| 1 | Data Foundation | #28 | MVP |
| 2 | Net Worth Dashboard | #10 | MVP |
| 3 | Onboarding & FIRE | #25, #24, #11 | MVP |
| 4 | AI & Multi-Model | #18-#23, #27 | Multi-Model |
| 5 | Plaid Integration | #13, #14, #17, #26 | Plaid |
