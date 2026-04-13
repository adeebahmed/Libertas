# Phase 3: Onboarding & FIRE — Design Spec

**Date:** 2026-04-12  
**Target users:** 20-40 demographic (wealth builders, debt-conscious, retirement-aware)  
**Vision:** Understand your retirement readiness in 10 seconds. Pick your FIRE path. Know exactly when you're free.

---

## Overview

Phase 3 transforms the Retirement page from a generic projection calculator into a 3-tab experience: **Retirement Overview** (holistic readiness), **FIRE Calculator** (type-selectable with smart recommendations), and **Scenarios** (manual playground). Plus a first-run onboarding wizard that gets users to their first net worth view in under 3 minutes.

---

## Retirement Page — 3-Tab Layout

### Tab 1: Retirement Overview

Holistic view pulling from ALL account data. Zero configuration needed — computed from portfolio state.

**Retirement Accounts Breakdown:**
- List each retirement account (401k, IRA, Roth IRA, pension) with individual balance
- Total retirement assets (sum)
- Percentage of total net worth in retirement accounts

**Contribution Utilization:**
- 2026 limits: $23,500 (401k) / $7,000 (IRA) / $7,000 (Roth IRA)
- Visual fill bars showing YTD contributions vs limit
- "You're leaving $X/yr on the table" callout if under-contributing
- Catch-up contribution note if age >= 50

**Tax-Advantaged vs Taxable Split:**
- Donut or bar: retirement accounts vs brokerage vs cash vs other
- Helps users see if they're over-indexed on taxable accounts

**Retirement Readiness Gauge:**
- Single percentage: current portfolio / FIRE target (from Tab 2 or settings)
- Visual progress bar or radial gauge
- "X% of the way to financial freedom"

**Age Milestones Timeline:**
- Horizontal timeline with "you are here" marker
- Key dates: Roth contribution access (59½), 401k penalty-free (59½), Medicare (65), Social Security (62/67/70)
- User's target retirement age highlighted

**Monthly Needed to Stay on Track:**
- "Contribute $X/mo to hit your target by age Y"
- Comparison to current monthly contribution
- Delta: "Increase by $Z/mo" or "You're ahead by $Z/mo"

---

### Tab 2: FIRE Calculator

#### FIRE Type Selector

Five FIRE types presented as selectable cards. One highlighted as **"Recommended for you"** with reason badge.

| Type | Target Formula | Description |
|------|---------------|-------------|
| **Lean FIRE** | Bare-minimum expenses × 25 | Earliest exit, frugal lifestyle |
| **Regular FIRE** | Current expenses × 25 | Comfortable current lifestyle, standard path |
| **Fat FIRE** | Desired expenses × 25 | Upgraded lifestyle, won't downgrade |
| **Coast FIRE** | Enough invested NOW to coast to retirement | Stop saving aggressively, let compound growth work |
| **Barista FIRE** | Semi-retire + part-time income | Downshift careers, portfolio grows, part-time covers gap |

#### Recommendation Engine

Based on user profile (age, savings rate, expenses, income, debt), highlight one type as recommended with plain-language explanation:

**Rules:**

```
Age < 30 + savings rate < 20%
→ Coast FIRE
  "You have time on your side. Get enough invested now and compound 
   growth does the heavy lifting. Focus on hitting your Coast number."

Age 25-35 + savings rate > 30%
→ Regular FIRE
  "You're saving aggressively — standard FIRE is realistic within 
   10-15 years at this pace. Stay the course."

Age 25-35 + savings rate > 30% + high expenses (>$6k/mo)
→ Fat FIRE
  "Your lifestyle costs more — own it. Fat FIRE gives you an honest 
   number instead of a target you'd never actually live on."

Age 30-40 + moderate savings (15-30%) + has debt
→ Barista FIRE
  "Full retirement feels far with current obligations. Part-time work 
   + portfolio growth = freedom sooner than you think."

Low income + frugal habits (expenses < $3k/mo)
→ Lean FIRE
  "Your low expenses are a superpower. Lean FIRE is achievable years 
   before others your age. Stay disciplined."

Default (no strong signal)
→ Regular FIRE
  "Start here. Regular FIRE uses your actual expenses — the most 
   realistic baseline. Explore other types once you dial in your number."
```

**Profile inputs used:** age (from birth_year setting), monthly income, monthly expenses, savings rate (computed), total debt, current retirement balance.

#### Configurable Inputs Per Type

Inputs panel adapts based on selected FIRE type:

| Input | Lean | Regular | Fat | Coast | Barista |
|-------|------|---------|-----|-------|---------|
| Annual expenses | ✓ (lean budget) | ✓ (current) | ✓ (desired) | — | ✓ (reduced) |
| Safe withdrawal rate | ✓ (default 4%) | ✓ (default 4%) | ✓ (default 3.5%) | — | ✓ (default 4%) |
| Expected annual return | ✓ (default 6%) | ✓ (default 7%) | ✓ (default 7%) | ✓ (default 7%) | ✓ (default 7%) |
| Target retirement age | ✓ | ✓ | ✓ | ✓ (coast-to age) | ✓ |
| Monthly income | ✓ | ✓ | ✓ | ✓ | ✓ |
| Monthly contribution | ✓ | ✓ | ✓ | ✓ | ✓ |
| Part-time income | — | — | — | — | ✓ |
| Current age | ✓ | ✓ | ✓ | ✓ | ✓ |

Defaults pre-filled from Settings where available. All adjustable inline.

#### Results Dashboard (adapts per type)

**Always visible:**
- **FIRE Number** — big hero number for selected type
- **Progress bar** — current portfolio / FIRE number as percentage
- **Savings Rate** — hero metric (income - expenses) / income × 100
- **Time to FIRE** — "At current pace: X years (age Y)" with growth chart
- **"What if" sliders:**
  - Savings rate ±5% → shows time-to-FIRE delta
  - Return rate ±1% → shows time-to-FIRE delta
  - Monthly expenses ±$500 → shows FIRE number delta + time delta

**Coast FIRE specific:**
- Coast FIRE number: "You need $X invested today to never contribute again and retire at [age]"
- Current vs needed: "You have $Y. Gap: $Z" or "You've hit Coast FIRE ✓"
- "If you coast from today, projected balance at retirement: $X"

**Barista FIRE specific:**
- Part-time income offset: "Part-time covers $X/yr of expenses"
- Reduced FIRE number: "Portfolio only needs to cover $Y/yr → FIRE number: $Z"
- "Work 20hrs/week at $20/hr = $20k/yr → cuts your FIRE number by $500k"

**Lean vs Fat comparison (shown for Lean and Fat types):**
- Side-by-side: Lean number vs Fat number
- Time difference: "Lean FIRE in 8 years. Fat FIRE in 15 years. Difference: 7 years."

#### Educational Context Panel

Collapsible "Understanding [FIRE Type]" section per type:

**Structure:**
- 2-3 sentence explanation of the concept
- Pros (2-3 bullets)
- Cons (2-3 bullets)  
- "Common mistake" callout
- "If this doesn't feel right" link to alternative type

**Examples:**

**Coast FIRE:**
> Coast FIRE means you've invested enough that compound growth alone will carry you to a comfortable retirement — even if you never save another dollar. Once you hit your Coast number, you can take a lower-paying job, go part-time, or pursue passion projects without worrying about retirement.
>
> **Pros:** Freedom to downshift careers early. Less pressure to maximize income. Mental relief of knowing retirement is handled.
>
> **Cons:** Requires discipline not to withdraw early. Market downturns can push your coast date out. Doesn't cover pre-retirement expenses.
>
> **Common mistake:** Forgetting healthcare costs. Without employer coverage, budget $500-800/mo for health insurance before age 65.
>
> **If Coast feels too passive →** Try Barista FIRE for a structured part-time approach.

**Lean FIRE:**
> Lean FIRE targets the minimum viable retirement — covering basic needs without luxury. Your FIRE number is based on bare-bones annual expenses (typically $25k-40k/yr), making it achievable years earlier than other paths.
>
> **Pros:** Achievable earliest. Forces intentional spending habits. Works well in low cost-of-living areas.
>
> **Cons:** Little margin for unexpected expenses. Lifestyle may feel restrictive long-term. Healthcare and inflation can erode the buffer.
>
> **Common mistake:** Using today's lean budget without inflation adjustment. $30k/yr today ≠ $30k/yr in 15 years.
>
> **If Lean feels too tight →** Try Regular FIRE with your actual current expenses.

#### Smart Nudges

Deterministic rules computed from portfolio data (same engine as Phase 2 insights):

- "You're $12k from Coast FIRE. One strong savings year could close the gap."
- "Your savings rate is 35%. At this pace, Regular FIRE in 12 years."
- "Switching from Fat → Regular FIRE saves you 8 years."
- "Your 401k is only 40% utilized. Maxing it adds $14k/yr toward your FIRE number."
- "At 28, starting now vs waiting 3 years = $180k difference at retirement (7% return)."
- "Your Roth IRA is empty. $7k/yr tax-free growth is the best tool at your age."

---

### Tab 3: Scenarios (existing, refined)

Keep existing manual playground with improvements:

- **Inputs:** Monthly contribution, years, conservative/moderate/aggressive rates (all adjustable)
- **Output:** Three scenario growth curves with final values
- **Enhancement:** Add "Which scenario am I on?" indicator — highlight which curve user's current trajectory most closely matches
- **Enhancement:** Add "To reach [FIRE target] in [years]" reverse calculator — "You need to save $X/mo"

---

## Onboarding Wizard

### First-Run Flow

Triggered when no accounts exist (or onboarding_complete flag not set).

**Step 1: Welcome**
- "Welcome to Libertas. Your finances, your machine, your control."
- Privacy callout: "Everything stays local. No cloud. No account linking. No tracking."

**Step 2: Data Entry Method**
- Three options: Manual Entry / CSV Import / Both
- Brief explanation of each
- "You can always add more later"

**Step 3: First Account**
- If Manual: quick-add form (account name, type, balance)
- If CSV: file picker with preset detection
- Skip option available

**Step 4: Goal Setup (optional)**
- "Want to set a financial goal?"
- Quick FIRE type picker (simplified — just Lean/Regular/Fat with 1-line each)
- Or skip: "I'll explore first"

**Step 5: Dashboard**
- Redirect to dashboard with first account visible
- Celebration moment: "You're set up. Your net worth journey starts now."

**Target:** First net worth view in <3 minutes.

---

## Backend API Changes

### New Endpoints

**GET /api/retirement/overview**
- Returns: retirement accounts breakdown, contribution utilization (YTD vs limits), tax-advantaged vs taxable split, readiness percentage, age milestones
- Inputs: none (computed from portfolio + settings)

**GET /api/retirement/fire**
- Returns: FIRE number, progress, savings rate, time-to-FIRE, recommendation, nudges
- Query params: `fire_type` (lean/regular/fat/coast/barista), all configurable inputs as overrides
- Uses settings as defaults, query params override

**GET /api/retirement/fire/recommend**
- Returns: recommended FIRE type + reason based on user profile
- Inputs: none (computed from settings + portfolio)

### Modified Endpoints

**GET /api/retirement** (existing)
- Keep as-is for Scenarios tab backward compatibility

**GET /api/retirement/plan** (existing)
- Enhance to include FIRE type context if set

### New Settings Keys

- `fire_type` — selected FIRE type (lean/regular/fat/coast/barista)
- `monthly_income` — gross monthly income (for savings rate calc)
- `annual_lean_expenses` — bare-minimum annual expenses
- `annual_fat_expenses` — desired/upgraded annual expenses
- `part_time_income` — expected part-time income (Barista FIRE)
- `onboarding_complete` — boolean flag

---

## Data & Computation

### FIRE Calculations

**Lean FIRE number:** `annual_lean_expenses / SWR`  
**Regular FIRE number:** `(monthly_expenses × 12) / SWR`  
**Fat FIRE number:** `annual_fat_expenses / SWR`  
**Coast FIRE number:** `FIRE_target / (1 + return_rate) ^ years_to_retirement`  
**Barista FIRE number:** `((monthly_expenses × 12) - part_time_income) / SWR`

**Savings rate:** `(monthly_income - monthly_expenses) / monthly_income × 100`

**Time to FIRE:** Iterative: starting from current investable balance, add monthly contribution, compound at return rate, find year where balance >= FIRE number.

**Contribution utilization:** Track retirement account types, sum current year transactions as contributions, compare to IRS limits.

### Recommendation Algorithm

Priority-ordered rule matching (first match wins):
1. Age < 30 + savings rate < 20% → Coast
2. Age 25-35 + savings rate > 30% + expenses > $6k/mo → Fat
3. Age 25-35 + savings rate > 30% → Regular
4. Age 30-40 + savings rate 15-30% + total debt > $50k → Barista
5. Expenses < $3k/mo → Lean
6. Default → Regular

---

## Success Criteria

1. Retirement Overview shows accurate retirement accounts, contribution utilization, and readiness gauge
2. FIRE type selector works — switching types updates all calculations and inputs dynamically
3. Recommendation engine produces sensible type suggestion based on user profile
4. All 5 FIRE types calculate correctly with type-specific formulas
5. "What if" sliders update time-to-FIRE in real-time
6. Educational panels provide actionable context per FIRE type
7. Smart nudges compute from actual portfolio data (deterministic, no AI)
8. Scenarios tab maintains backward compatibility + adds trajectory indicator
9. Onboarding wizard completes in <3 minutes for new user
10. All computations offline, deterministic, local SQLite only

---

## Execution Plan

Five sub-phases (mapped to .planning/phases/03-onboarding-fire/):

1. **03-01:** Onboarding state primitives + new settings keys + profile fields
2. **03-02:** First-run wizard UI (method → account → goal → dashboard)
3. **03-03:** Retirement page rebuild — Overview tab + FIRE calculator + type selector + recommendation engine
4. **03-04:** Dashboard goal progress connected to FIRE type + smart nudges
5. **03-05:** Validation + ADR + phase sign-off

---

## Out of Scope

- AI-powered financial advice (Phase 4)
- Plaid account linking in onboarding (Phase 5)
- Tax optimization recommendations (existing Taxes page)
- Rebalancing execution / trade suggestions
- Social Security income estimation (future enhancement)
