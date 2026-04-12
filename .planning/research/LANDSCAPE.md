# Personal Finance App Landscape Research

**Project:** Libertas — Personal Finance Dashboard
**Date:** 2026-04-11
**Confidence:** MEDIUM-HIGH

---

## Key Findings

### 1. Fey Is Gone
The reference app in ADR-001 was acquired by Wealthsimple and shut down September 30, 2025. Copilot Money is now the sole design north star.

### 2. The Whitespace Is Real and Uncontested
No current app combines: fully local/offline + multi-asset net worth (crypto + real estate + brokerage) + CSV import with saved mappings + conversational AI. Copilot requires Plaid and is iOS-only. Actual Budget and Firefly III are transaction/budgeting focused with no investment depth. Lunch Money is cloud-based.

### 3. The Plaid $58M Settlement Is the Trust-Killer
This is the single most-cited reason users are actively looking for local-first alternatives. Libertas's "no credentials leave the machine" positioning should be front-and-center, not buried.

### 4. CSV Import Must Be Idempotent and Bulletproof
The Actual Budget community treats deduplication as a first-class feature. Users re-import the same file. The hash-per-row approach in ADR-001 is correct.

**Hidden failure modes to guard against:**

| Problem | Root cause | Prevention |
|---------|-----------|------------|
| Silent data loss | Bad-row parse failures silently dropped | Show parse error count + sample bad rows |
| Header drift | Institution changes export format between versions | Store raw headers; flag mismatch on next import |
| Encoding issues | UTF-8 / latin-1 mix | Auto-detect with chardet; never surface encoding error to user |
| Date format ambiguity | `01/02/03` is ambiguous | Show parsed dates in preview before commit |
| Junk rows at header | Bank adds summary rows before data starts | Auto-skip rows before detected header row |
| Transfer double-counting | Debit in checking + credit in brokerage = same transfer | Surface "potential transfer pair" in import preview |

### 5. AI Integration Is the Killer Differentiator
No privacy-conscious competitor offers LLM chat with full financial context. The risk is Claude's context window with large transaction histories — a summarization/RAG layer is needed before querying. LLMs are weak at raw calculation; they're strong at narrative analysis and pattern explanation. The rule engine should do the math; Claude explains it.

### 6. Investment Tracking Has the Worst Reputation Across All Apps
Every app's most-downvoted complaint category is investment data quality. Since Libertas uses CSV (not live sync), the data matches exactly what the user exported — this is a genuine competitive advantage.

### 7. Feature Completeness for "Net Worth Dashboard" Has a Clear Tier 1
Without these five, users don't consider the product real:
1. Hero net worth number
2. Allocation donut (must include liabilities)
3. Net worth time-series chart
4. Account list with staleness indicators
5. Per-account transaction history

---

## Market Segment Analysis

**Primary user archetypes:**

| Archetype | Trigger | Core need |
|-----------|---------|-----------|
| Privacy-first DIY investor | Plaid lawsuit, data monetization concerns | Zero credentials leaving device |
| Multi-account portfolio holder | No unified view across asset types | Net worth across brokerage + crypto + real estate |
| Mint refugee (technical) | Mint shutdown March 2024; replacements too expensive or iOS-only | Free/cheap local alternative with feature depth |
| High-net-worth self-manager | Complexity of assets, distrust of SaaS | Tax efficiency, allocation, LTV, sophisticated views |
| Developer/power user | Wants to own and extend the data | SQLite access, CSV exports, open architecture |

---

## AI Finance Assistant Use Cases

**Highest utility question types (in order):**

1. Spending pattern analysis: "Where did my money go last month?"
2. Portfolio health: "Am I concentrated in tech?"
3. Projection/retirement: "Am I on track to retire at 60?"
4. Risk stress-testing: "What does a 20% market drop do to my net worth?"
5. Liquidity check: "How many months of expenses are in liquid accounts?"
6. Tax efficiency: "Which accounts have the wrong asset types?"
7. Anomaly detection: "Was there anything unusual this month?"

Bank of America's Erica — 20M users, 676M interactions/year — proves massive consumer demand for this pattern.

**Design constraint:** Claude answers must be labeled informational, not financial advice. The opt-in/API-key framing in ADR-001 is correct.

---

## Feature Prioritization Signals

**Tier 1 — Without these it's not a dashboard:**
- Single net worth hero number (accurate and current)
- Asset allocation donut (must include cash and liabilities)
- Net worth over time line chart (1+ year of monthly snapshots)
- Account list with staleness indicators (green <3d, yellow 3-7d, red >7d)
- Transaction history per account (searchable)

**Tier 2 — Users notice absence after a week:**
- Top movers (today's live price gainers/losers)
- Investment performance vs. S&P 500 benchmark
- Spending by category
- Real estate equity (LTV, mortgage balance vs. current value)

**Tier 3 — Differentiators:**
- Projections (3-scenario CAGR model with adjustable inputs)
- AI chat (single biggest differentiator — no competitor does this locally)
- Insights cards (rule-based: concentration risk, liquidity ratio, allocation drift)
- Tax efficiency signals

**Anti-features for V1:**
- Budgeting / envelope system (different user mindset; Copilot and YNAB own this)
- Bill pay integration (requires institutional API; contradicts privacy model)
- Goals tracking (scope creep; defer to V2)
- Mobile native app (desktop-first is fine; premature complexity)

---

## Recommended Phase Ordering

1. **Core data pipeline** — CSV import, deduplication, watch folder, column mapping
2. **Net worth dashboard** — Hero number, allocation donut, time-series, account list + staleness
3. **Depth views** — Per-account transactions, holdings breakdown, real estate equity
4. **Insights engine (rule-based)** — Concentration, liquidity, allocation drift; must work offline
5. **Projections / FIRE** — Three CAGR scenarios; simple math, high perceived value
6. **AI integration** — Claude chat with summarization layer for large transaction histories
7. **Polish and onboarding** — Institution presets, first-run wizard, docs site

---

## Flags for Phase-Specific Research

| Phase | Risk | Depth needed |
|-------|------|-------------|
| CSV import | Institution header drift; transfer detection logic | LOW — patterns well-established |
| Net worth calculation | Crypto lot accounting (FIFO vs. LIFO), stock splits | MEDIUM — non-trivial for cost basis |
| Price refresh | CoinGecko free tier rate limits (50/min) | LOW — sufficient for personal use |
| AI integration | Claude context window with large transaction history | HIGH — needs RAG/summarization design |
| Real estate | Zillow actively fights scraping; breakage risk | MEDIUM — needs Redfin fallback strategy |
| Tax efficiency | Asset placement rules are situational | LOW — general rules are sufficient |

---

## Open Questions

- **Summarization strategy for AI context:** How to send 2+ years of transactions to Claude without hitting context limits? Options: rolling 90-day window, vector embeddings, pre-computed summaries per account.
- **Transfer pair detection:** What's the right heuristic for cross-account transfers? (same amount, within 3 days, opposite sign)
- **Crypto cost basis method:** FIFO default? Let user choose? Affects realized gain calculations.
- **Zillow scraping reliability:** With Fey gone, what's current Zillow reliability? Redfin fallback should be designed in from the start.
