# Libertas Pages Design Spec
**Date:** 2026-04-05
**Scope:** All 9 pages — Dashboard, Accounts, Import, Real Estate, Projections, Insights, Debt, Taxes, Settings

---

## Context

Libertas is a locally-hosted personal finance dashboard for a 30-year-old with a target of retiring at 45. The user has W-2 income, 1099/self-employment income, rental real estate, crypto trading activity, and is evaluating business entity structures (LLC, S-Corp). All data stays local. No cloud. No account linking.

---

## 1. Dashboard

### Purpose
The first thing seen each morning — a motivational, high-signal overview.

### Layout
- **Hero:** Total net worth (large) + delta since yesterday (green/red)
- **Motivational quote:** Random daily quote from a curated finance/wealth-building list. Changes once per day.
- **Accounts overview:** Cards grouped by type (Investments, Cash, Crypto, Real Estate, Debt, Retirement). Each card shows account name, balance, staleness indicator (green < 3 days, yellow 3–7 days, red > 7 days).
- **Top movers:** Biggest gainers and losers across all holdings today (symbol, $ change, % change).
- **News feed:** Articles relevant to holdings and selected categories (Tech, Politics, Markets, Crypto). Source: RSS feeds (always on) + NewsAPI (when key configured in `.env`). Holdings-weighted — if user holds NVDA, NVDA news ranks higher.

### News Feed Detail
- NewsAPI key stored in `.env` as `NEWS_API_KEY`, never committed to git
- RSS sources: Reuters, AP, Yahoo Finance (no key required, always available)
- Filtering: holdings symbols extracted from DB + user-selected categories from Settings
- Holdings-based results take priority over category results in display order
- If NewsAPI key absent: RSS only, no error shown

---

## 2. Accounts

### List Page
- All accounts in a list with: name, type badge, current balance, last import date, staleness indicator (color-coded)
- **One-click export link** per account — opens the institution's export/login URL in the browser
- Staleness color: green < 3 days, yellow 3–7, red > 7

### Account Detail Page (3 tabs)

**Transactions tab**
- Full transaction history table
- Filters (all active simultaneously): date range picker, transaction type multi-select (buy/sell/deposit/withdrawal/dividend/transfer), symbol/ticker search
- Sortable columns

**Holdings tab**
- Per holding: symbol, quantity, current value, gain/loss ($), gain/loss (%), % of account, cost basis
- Sorted by value descending by default

**Performance tab**
- Line chart of account balance over time
- Default: All Time
- Toggles: 1M / 3M / 6M / 1Y / All

---

## 3. Import

### CSV Detection
- Default behavior: toast notification — "143 new transactions from Fidelity — Import?"
- User can toggle to silent auto-import in Settings (no interruption)
- Watch folder path configurable in Settings

### New Institution Setup
- Auto-detect column mapping from headers + sample rows
- Show 3 sample rows of actual data for verification
- Manual override toggle — user can switch to full manual mapping table if needed
- Saved mapping reused on all subsequent imports from that institution

### Import History Log
- Columns: date, institution, file name, rows imported, duplicates skipped
- **Undo/rollback** — revert the most recent import (removes inserted transactions and restores previous balance snapshots)

### Institution Cards
- Each institution shows: name, last import date, direct link to their export/login page
- Quick access to institution management (same data as Settings > Institutions)

---

## 4. Real Estate

### Property Cards
- Hero number: **Equity** (value − mortgage balance)
- Also shown: current estimated value (Zillow or override), mortgage balance, LTV %
- Manual override field: user-entered value takes precedence over Zillow estimate when set
- Zillow auto-refresh on demand

### Equity Over Time Chart
- Per-property line chart tracking equity as Zillow estimate updates over time
- X-axis: date of each Zillow refresh or manual value entry

### Multiple Properties
- Each property shown as its own card
- No cross-property summary view

---

## 5. Projections

### North Star
**Retire by 45** (user is 30 — 15 years). Page is anchored to this goal.

### Target Display (3 views)
All three shown simultaneously:
1. **Fixed number target** — user sets a number (e.g. $2M), shows if current trajectory hits it by 45
2. **Monthly income target** — user sets desired monthly passive income, back-calculates required portfolio size
3. **4% rule** — auto-calculates 25× annual expenses (pulled from Settings > monthly expenses × 12)

On-track / off-track indicator for each view.

### Projection Curves
- Three scenarios: Conservative, Moderate, Aggressive
- Default return rates configurable per account type (stocks, crypto, real estate, cash/savings, retirement accounts)
- Chart shows projected total value year by year to age 45 (and beyond to age 65 for context)

### Contributions
- Per-account monthly contribution input
- Contributions factored into all three scenario curves

---

## 6. Insights

### Card Grid
One card per insight, color-coded by category:
- Risk / Performance / Tax Efficiency / Liquidity / Trends / Real Estate

### Priority Tiers
- **High-priority:** Concrete recommended action included ("what to do about it")
- **Low-priority:** Flags the issue only, no prescribed action

### Tax Efficiency (prioritized)
- Asset placement recommendations: bonds in taxable, growth assets in Roth, etc.
- Surfaces opportunities specific to user's jurisdiction (from Settings > location)
- High-priority tier — always includes recommended action

### Claude API Chat (opt-in)
- Appears at bottom of Insights page
- Requires `CLAUDE_API_KEY` in `.env`
- Full portfolio data passed as context (balances, holdings, account types, user profile)
- User profile context: tax filing status, income bracket, location, business info, goals
- User can ask anything: "Am I too heavy in tech?", "What should I do before year-end?"

---

## 7. Debt

### Overview
- Hero: total debt balance + rate of change (shrinking/growing)
- Debt-free date at current pace
- Debt-to-income ratio (uses income from Settings > user profile)

### Debt Types Tracked
All: loans (student, auto, mortgage), credit cards, lines of credit, buy-now-pay-later

### Per-Debt Card
- Balance, interest rate, minimum payment, payoff date
- Total interest paid if minimums only
- "What if I pay $X extra/month" calculator (inline, interactive)

### Payoff Strategy Section
- **Avalanche** (highest interest first) and **Snowball** (smallest balance first) shown side by side
- Each shows: payoff order, total interest paid, debt-free date
- User can compare and choose

---

## 8. Taxes

### Purpose
Full tax picture: running estimate of what you owe + how to reduce it. Jurisdiction-aware using location and user profile.

### Current Year View (Hero)
- Running estimate of federal + state tax liability for the current calendar year
- Broken down by income type: W-2, 1099/self-employment, capital gains (short/long), dividends, rental income, crypto
- Updates automatically as new transactions are imported

### Prior Years
- Collapsed/accordion section below current year
- Each prior year shows: summary of income types, estimated liability, transactions used

### Tax-Loss Harvesting
- Proactive insight card on the Insights page flags opportunities
- Full detail section on the Taxes page: holdings with unrealized losses, estimated tax savings if harvested, wash-sale warning

### Entity Structure Recommendations
Powered by user profile (income, business activity, location):
- Recommendation: which structure fits (sole prop → LLC → S-Corp, etc.)
- Plain-English explanation of why it fits their situation
- Estimated annual tax savings vs current structure
- Setup checklist: actionable steps to make the switch

### Jurisdiction Awareness
- Uses `country` + `state` from Settings > user profile
- Surfaces state-specific rules (e.g. no state income tax states, community property rules, etc.)

---

## 9. Settings

### Sections

**User Profile** (used across the whole app for personalized guidance)
- Name
- Date of birth (used for age-based projections)
- Country + state/province (jurisdiction for tax law, real estate regulations)
- Tax filing status (single, married filing jointly, etc.)
- Estimated annual income (W-2, 1099/self-employment, rental — separate fields)
- Business entity (none / sole prop / LLC / S-Corp / other)
- Risk profile (conservative / moderate / aggressive)
- Monthly expenses (used for liquidity and 4% rule calculations)

**Accounts & Institutions**
- Manage institutions: add, edit export URL, view/reset column mapping
- Quick access also available from Import page
- Manage accounts: add, rename, delete, assign institution

**Import**
- Watch folder path
- Import notification mode: toast (default) vs silent auto-import toggle

**API Keys**
- `NEWS_API_KEY` — for NewsAPI news feed
- `CLAUDE_API_KEY` — for Insights chat and tax/entity recommendations
- Both stored in `.env`, never committed to git
- Settings page shows masked value + "configured / not configured" status

**Projections**
- Per-account-type return rates (conservative / moderate / aggressive)

**Data & Backups**
- Export all data: JSON, CSV per account
- Versioned date-stamped backups — list of all checkpoints with restore button
- Rolling back restores the full database to that checkpoint

**System**
- Manual "Refresh prices" button
- Watch folder status indicator

---

## Data Model Additions

The following fields are needed beyond ADR-001:

### `user_profile` settings keys (in `settings` table)
- `dob` — date of birth
- `country` — country of residence
- `state` — state/province
- `tax_filing_status` — single / mfj / mfs / hoh
- `income_w2` — annual W-2 income estimate
- `income_1099` — annual 1099/self-employment income estimate
- `income_rental` — annual rental income estimate
- `business_entity` — none / sole_prop / llc / s_corp / other
- `monthly_expenses` — already in ADR-001
- `risk_profile` — already in ADR-001
- `retirement_target_age` — default 45
- `retirement_target_amount` — optional fixed number target
- `retirement_monthly_income_target` — optional monthly income target

### `backups` table
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| created_at | DATETIME | |
| label | TEXT | Auto-generated: "2026-04-05 14:32" |
| file_path | TEXT | Path to `.db` snapshot file |
| size_bytes | INTEGER | |

### `news_cache` table
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| fetched_at | DATETIME | |
| source | TEXT | rss / newsapi |
| title | TEXT | |
| url | TEXT | |
| published_at | DATETIME | |
| symbols | JSON | Array of tickers mentioned |
| categories | JSON | Array of categories |

---

## Environment Variables (`.env`, gitignored)
```
NEWS_API_KEY=your_key_here
CLAUDE_API_KEY=your_key_here
```

---

## Security Notes
- `.env` is gitignored — never committed
- API keys never stored in SQLite DB or any committed file
- Settings page shows masked key values only
