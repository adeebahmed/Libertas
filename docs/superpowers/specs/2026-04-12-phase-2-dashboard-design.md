# Phase 2: Net Worth Dashboard — Design Spec

**Date:** 2026-04-12  
**Target users:** 20-40 demographic (wealth builders, debt-conscious, retirement-aware)  
**Vision:** Clarity through simplicity. Open app, immediately know financial situation + what action to take.

---

## Overview

Phase 2 transforms Libertas into a complete net worth experience with ruthless focus on what matters. Dashboard prioritizes three things: **see your accounts**, **understand your situation**, **act on what matters most**.

Core principle: zero cognitive overhead. Account overview + actionable recommendation visible in <3 seconds.

---

## Dashboard Layout

### Visual Hierarchy (top to bottom)

**Hero Section:**
- Net worth number (e.g., "$462,761")
- 30-day change (e.g., "+$8,200 | +1.8%")
- Last updated timestamp

**Recommendation Carousel:**
- Single rotating insight from insights engine
- Changes on page refresh
- Pin button to lock current insight
- Example: "Diversify. You're 45% tech. Add $50k to bonds to hit 40% target."

**Account Overview:**
- Accounts grouped by type: Checking, Savings, Brokerage, Crypto, Real Estate, Debt
- Each account shows: name + balance + status icon (✓ green / ⚠ yellow / 🔴 red)
- Click to navigate to account detail page
- Status based on staleness: green <7d updated, yellow <30d, red >30d

**Secondary Layers (below fold):**
- Net worth chart with range selector (1M / 3M / 6M / YTD / 1Y / All)
- Asset allocation donut (includes liabilities)
- All insights carousel (browse full set of 12-15 insight cards)

**Privacy Callout:**
- Persistent on dashboard: "Local-first. Your data stays here."

---

## Recommendation Carousel

**Behavior:**
- Displays one insight at a time, rotates to next on page refresh
- User can pin current insight to prevent rotation (pinned insight shows first, others rotate behind it)
- Pin state persisted in browser localStorage

**Content:**
- Insight title + context (e.g., "Concentration Risk")
- Actionable advice in plain English (e.g., "You're 45% in tech stocks. Consider adding $50k to bonds to hit your 40% target.")
- Optional metric or benchmark (e.g., "Your ideal range: 30-40%")

**Visual:**
- Prominent card below hero number
- Green border for positive insights, yellow for caution, red for critical
- Pin icon (top right) for locking

---

## Account Overview Cards

**Display (minimal):**
- Account type icon + name
- Current balance
- Status indicator (✓/⚠/🔴) based on last_updated timestamp

**Interaction:**
- Click card → navigate to account detail page
- Quick-add button (+ icon) → modal for adding transaction / holding / balance update

**Grouping:**
- Checking Accounts
- Savings Accounts
- Brokerage / Investment Accounts
- Crypto Accounts
- Real Estate
- Debt (mortgages, loans, credit cards)

---

## Account Detail Page

**Tabs:**

**Transactions Tab:**
- All transactions for account (searchable, filterable by date / amount / category)
- Sortable by date / amount
- Pagination or infinite scroll

**Holdings Tab** (investment accounts):
- Table: Symbol | Shares | Cost Basis | Current Value | Gain/Loss | % of Portfolio
- Sortable by any column

**Real Estate Tab** (real estate accounts):
- Property details: address, value, mortgage balance, LTV, equity
- Last assessed date
- Mortgage payoff timeline (if applicable)

**Account Header:**
- Account name + type
- Current balance (large, prominent)
- Staleness indicator with last-updated timestamp
- Quick-add button

---

## Insights System

### Insights Engine (12-15 rules, all rule-based, offline-compatible)

#### Financial Health (5 rules)

1. **Concentration Risk**
   - Rule: Flag if any single asset class or sector >40% of portfolio
   - Insight: "You're 45% in tech. Ideal max: 40%. Diversify to reduce volatility."

2. **Liquidity Ratio (Emergency Fund)**
   - Rule: Compare liquid assets (checking + savings) to monthly expenses
   - Insight: "Emergency fund covers 2 months. Ideal: 3-6 months. Build to $X."

3. **Allocation Drift**
   - Rule: Compare actual asset class allocation to user's target allocation
   - Insight: "Actual: 60% equities, 25% bonds, 15% cash. Target: 50/30/20. Rebalance to align."

4. **Debt-to-Income Ratio**
   - Rule: (Total debt payments / gross income) × 100
   - Insight: "Debt-to-income: 25%. Healthy range: 20-36%. Good position. Consider accelerating payoff."

5. **Asset Class Diversification**
   - Rule: Count number of asset classes with >0 balance; flag if <3
   - Insight: "You hold 2 asset classes. Add bonds or real estate for better diversification."

#### Retirement & Long-Term (4 rules)

6. **Net Worth Growth Rate**
   - Rule: Compare 3-month, 6-month, YTD net worth growth
   - Insight: "Net worth growing $2,500/mo. At this pace, double your wealth in 14 years."

7. **Retirement Readiness / FIRE Timeline**
   - Rule: Project net worth growth to user's FIRE target (from Phase 3)
   - Insight: "At $2,500/mo savings, reach FIRE by age 38. On track."

8. **401k / IRA Contribution Rate**
   - Rule: Compare current year contributions to annual limit ($23,500 401k / $7,000 IRA)
   - Insight: "You've contributed $5,800 to 401k (25% of limit). Increase by $200/mo to max out."

9. **Compound Growth Projection**
   - Rule: Project portfolio value 10y forward at 6% annual return
   - Insight: "Projected net worth in 10 years: $850k (assuming 6% return, current contributions)."

#### Debt Management (3 rules)

10. **Debt Payoff Trajectory**
    - Rule: Compare current debt balance to 6-month / 1-year ago; extrapolate payoff date
    - Insight: "Student loans down 8% YoY. At current pace, paid off by age 32."

11. **Total Interest Burden**
    - Rule: Sum annual interest across all debt (mortgages, loans, CCs)
    - Insight: "You're paying $1,200/year in interest. Paying extra $100/mo would save $4,800 over 5 years."

12. **Mortgage Affordability** (if applicable)
    - Rule: Mortgage balance / home value (LTV); compare to standard benchmarks
    - Insight: "LTV: 65%. Conservative. Can afford to take on more debt if needed."

#### Cash Flow (3 rules)

13. **Savings Rate Trend**
    - Rule: (Income - expenses) / income × 100, tracked monthly
    - Insight: "Savings rate: 22% last month, 18% avg. Keep up the savings discipline."

14. **Income Stability / Volatility**
    - Rule: Coefficient of variation of last 6 months income
    - Insight: "Income stable ($5,000±2% monthly). Low volatility—reliable for planning."

15. **Passive vs. Earned Income Breakdown**
    - Rule: Sum investment returns + other passive income vs. salary
    - Insight: "Passive income: $200/mo (2% of total). Focus: increase passive streams for flexibility."

### Insights Display

- **All Insights Carousel:** Browse all 12-15 insights below fold
- **Insight Cards:** Each shows rule name, current status, actionable advice
- **Color coding:** Green (healthy), yellow (caution), red (critical)
- **Offline guarantee:** All rules compute from local SQLite, no external API calls

---

## Data & Computation

### Monthly Snapshots
- Auto-captured at end of each calendar month
- Fields: date, net_worth, allocation (asset class breakdown), snapshot_source
- Used for historical net worth chart

### Staleness Tracking
- Account.last_updated timestamp maintained
- Status: green (<7d), yellow (<30d), red (>30d)
- Visual indicator on account card + account detail

### Insights Computation
- Computed on-demand when dashboard loads (cache results for 1 hour or on manual refresh)
- Deterministic, rule-based (no ML)
- Store rule outputs (score, status, explanation) in insights cache table

---

## Success Criteria

1. Dashboard <500ms render on local SQLite (hero + accounts + top recommendation)
2. All Tier 1 features complete (hero, allocation, chart, accounts, monthly snapshots)
3. Recommendation carousel works (rotates on refresh, pin persists)
4. 12-15 insights rules all implemented, tested, offline-compatible
5. Allocation donut includes liabilities
6. Account overview scannable in <3 seconds
7. Per-account detail views (transactions, holdings, real estate) fully functional
8. All insights compute offline, deterministic results

---

## Execution Plan

Five sub-phases (mapped to .planning/phases/02-net-worth-dashboard/):

1. **02-01:** Backend history + snapshot cadence APIs
2. **02-02:** Dashboard hero + allocation + recommendation carousel + account overview UI
3. **02-03:** Account detail pages (transactions, holdings, real estate)
4. **02-04:** Insights engine (12-15 rules) + insight cards UI
5. **02-05:** Final polish + performance profiling + ADR

---

## Out of Scope

- FIRE goal visualization (Phase 3: Onboarding & FIRE)
- Comparison features vs. benchmarks (handled via insights)
- Rebalance / move money actions (Phase 3+)
- Alerts (future phase)
