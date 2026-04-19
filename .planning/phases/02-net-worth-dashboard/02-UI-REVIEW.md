# Phase 2 — UI Review: Net Worth Dashboard

**Audited:** 2026-04-16
**Baseline:** Abstract 6-pillar standards (no UI-SPEC.md); brand reference: Copilot Money
**Screenshots:** Not captured (Playwright CLI unavailable; dev server confirmed running at localhost:5173)

---

## Pillar Scores

| Pillar | Score | Key Finding |
|--------|-------|-------------|
| 1. Copywriting | 3/4 | Contextual, purposeful copy throughout; "Quick add" is misleading — it navigates away, not creates in-place |
| 2. Visuals | 3/4 | Strong hero hierarchy and insight card differentiation; chart area is undersized at 250px height |
| 3. Color | 3/4 | Well-structured semantic token system; hardcoded hex values scattered across chart components outside the token contract |
| 4. Typography | 2/4 | Too many ad-hoc inline font sizes (11, 12, 13, 14, 17) alongside CSS class sizes; weight 550/450 are non-standard values |
| 5. Spacing | 3/4 | Utility class system is consistent; mixing class-based and arbitrary inline values creates maintenance risk |
| 6. Experience Design | 2/4 | Dashboard silently shows `$—` on load with no loading skeleton; error states from useApi are unused in Dashboard |

**Overall: 16/24**

---

## Top 3 Priority Fixes

1. **Dashboard has no loading or error UI** — Users see a blank `$—` hero number and no chart for several seconds on every page load, which feels broken on slow local SQLite. Fix: destructure `loading` and `error` from `useApi` in Dashboard.tsx and render a skeleton or spinner for the hero number and chart card during initial load.

2. **"Quick add" CTA is a navigation lie** — The primary action button on the dashboard hero section says "Quick add" but navigates to `/accounts` instead of opening an inline creation modal. This is the most prominent CTA on the page and it breaks user expectation. Fix: rename to "Manage accounts" or implement an actual inline quick-add modal consistent with the intent described in FR-2.4.

3. **Ad-hoc inline font sizes fragment the type scale** — Dashboard.tsx uses `fontSize: 11`, `12`, `13`, `14`, and `17` as raw inline integers alongside the CSS class system (`.section-label`, `.num-hero`, `.insight-title`). The 17px recommendation title in particular has no CSS class equivalent, creating a one-off rogue size. Fix: add a `.text-lg` or `.insight-headline` class to index.css and remove the inline `fontSize: 17` override.

---

## Detailed Findings

### Pillar 1: Copywriting (3/4)

**Strengths:**
- Empty states are specific and actionable: "Add an account in Accounts or import a CSV file" (Dashboard.tsx:318), "Add your first position to start tracking cost basis and market value" (Accounts.tsx:989). These match the Copilot Money caliber.
- Section labels are descriptive: "Allocation (incl. liabilities)", "Net worth history", "Top recommendation" — no generic "Data" or "Section 1" style labels.
- Freshness labels are human-readable: "Fresh", "1d old", "14d old" with tooltip context (Accounts.tsx:99-104).
- The footer tagline "Local-first. Your data stays here." (Dashboard.tsx:322) is a good brand reinforcement moment.
- Insight card copy distinguishes title, description, and action fields — three distinct voice layers.

**Issues:**
- **"Quick add"** (Dashboard.tsx:261) navigates to `/accounts`. The label implies in-place creation. Users clicking it expecting a modal will be disoriented by a full page navigation. This is a copywriting-behavior mismatch, not just a label issue.
- **"Cancel"** appears in modal footers (Accounts.tsx:1175, 1205, 1260, 1298). This is acceptable in modal context but the button has no visual distinction from secondary actions — it is purely a text label with no icon affordance. Minor; not a scoring blocker.
- Plaid error messages surface raw internal text: "Unable to start Plaid: {e?.message}" (Accounts.tsx:512). These will be user-visible and should be paraphrased.
- The "Pick an account" empty title in the account detail panel (Accounts.tsx:827) is a bare instruction. Consider "Select an account on the left to see its details" for more direction.

---

### Pillar 2: Visuals (3/4)

**Strengths:**
- Clear visual hierarchy: `.num-hero` at clamp(2.4rem, 7.4vw, 4rem) for the net worth total is the undisputed focal point.
- Insight card left-border color-coding by priority (red/gold/green) provides pre-attentive visual differentiation without overwhelming the layout.
- Account cards use freshness dot (green/gold/red) as a compact status indicator — well-chosen for scanning.
- The sidebar uses a blue gradient + left-border active state that cleanly indicates current page without feeling overbuilt.
- Responsive breakpoints at 1240px and 980px are defined; mobile nav collapses gracefully (index.css:762-800).

**Issues:**
- **Chart height is capped at 250px** (Dashboard.tsx:195). At 1440px wide with the chart consuming ~two-thirds of the upper grid, 250px feels compressed. Copilot Money typically uses 300-380px for primary charts. The visual imbalance between chart width and height creates a "squashed" impression.
- **Allocation donut at 170px height** (Dashboard.tsx:226) is very small for a 320px-wide card. The donut's inner radius (50) to outer radius (76) ratio gives only 26px of ring width, making slices hard to distinguish when there are 5+ asset types.
- **The hero grid collapses at 1240px** to a single column, which pushes the recommendation card below the fold on screens under 1240px — the second most important piece of information disappears from the opening viewport.
- Account cards in the overview section do not use the `.card-hover` class (index.css:361), so they have no hover feedback despite being clickable buttons. Users navigating with keyboard or slow pointer may not notice cards are interactive.

---

### Pillar 3: Color (3/4)

**Strengths:**
- Token system in `:root` is coherent: six semantic colors (gold, blue, blue-bright, green, red, purple/cyan) map to clear meaning categories (warning, primary, positive, negative, special).
- The 60/30/10 split is evident: deep navy (`--bg`, `--bg-card`, `--bg-elevated`) dominates, muted blue-grays (`--text-2`, `--text-3`, `--border`) form the secondary layer, and `--blue` / accent colors are used selectively.
- Tag system in index.css correctly scopes accent usage to account type labels rather than ambient decoration.
- Insight card border-left colors are the sole semantic use of the full color palette per card — disciplined.

**Issues:**
- **Hardcoded hex values in chart components**: Dashboard.tsx uses `#3b82f6` for the area chart stroke and gradient stops (lines 199-211) and `PIE_COLORS` array contains `['#3b82f6', '#34d399', '#d4a840', '#a78bfa', '#22d3ee', '#f87171', '#60a5fa']` — all hardcoded. These values are equivalent to token values (`--blue`, `--green`, `--gold`, etc.) but are not connected to the CSS variables. If the design system color changes, charts will remain stale.
- Debt.tsx lines 18-21 contain hardcoded hex values for debt type colors (`#c95f52`, `#6a9fc0`, `#d4a840`, `#9b85c4`) that diverge slightly from the CSS token values (e.g., `var(--red)` is `#ff7d81`, but the chart uses `#c95f52`). This creates visual inconsistency between the debt chart ring and the debt account tags in Accounts.tsx.
- Badge component in Accounts.tsx (lines 158-162) stores hardcoded hex strings for border and background tints inline. These should reference token values.
- The hardcoded `rgba(4, 8, 17, 0.72)` overlay in ModalShell (Accounts.tsx:290) could be expressed as `rgba(var(--bg), 0.72)` if CSS custom properties permitted it, or at minimum documented as derived from `--bg`.

**Registry audit:** shadcn not initialized — no third-party registry audit needed.

---

### Pillar 4: Typography (2/4)

**CSS class type scale (defined in index.css):**

| Class | Size | Weight | Font |
|-------|------|--------|------|
| `.num-hero` | clamp(2.4–4rem) | 600 | Fraunces (serif) |
| `.page-title` | clamp(1.95–2.45rem) | 600 | Fraunces |
| `.num-large` | clamp(1.45–1.8rem) | — | Mono |
| `.num-mid` | clamp(1–1.2rem) | — | Mono |
| `.section-label` | 0.64rem | 700 | Sans |
| `.insight-title` | 15px | 500 | Sans |
| `.insight-desc` | 13.5px | — | Sans |
| `.btn` | 13px | 450 | Sans |
| `.tbl th` | 10.5px | 500 | Sans |
| `.tbl td` | 13.5px | — | Sans |
| `.tag` | 10.5px | 500 | Sans |

This is already 10+ distinct CSS-defined size values. The class system shows intent but the range (10.5px to clamp 4rem) is very wide.

**Ad-hoc inline sizes in Dashboard.tsx (not in CSS system):**
- `fontSize: 11` — group header labels (line 268)
- `fontSize: 12` — inline meta text (line 237)
- `fontSize: 13` — delta/timestamp row (line 140)
- `fontSize: 14` — account balance in card (line 301)
- `fontSize: 17` — recommendation title (line 153) — no CSS class equivalent

The 17px recommendation title is a particular issue: it is the headline of the most prominent interactive card on the page, yet it lives as an anonymous inline integer with no named abstraction.

**Font weights:**
- CSS uses 400, 500, 550, 600, 700, 800, and 450. Weights 550 and 450 are non-standard on the web font loading range. Manrope's variable font supports them, but the combination of 6+ distinct weight values exceeds what a two-weight system (regular/medium + semibold) would need.

**Fix priority:** Define `.text-sm` (13px), `.text-xs` (11px), `.text-base` (14px) utilities in index.css, or add a `.recommendation-title` class at 17px/600. Replace all raw `fontSize:` integers in Dashboard.tsx with class-based utilities.

---

### Pillar 5: Spacing (3/4)

**System defined:** index.css defines `.mb-8`, `.mb-12`, `.mb-16`, `.mb-24`, `.mb-32`, `.mt-12`, `.mt-16`, `.mt-24`, `.gap-8`, `.gap-12`, `.gap-16` — a clean 8px-based scale.

**Usage in Dashboard.tsx is mostly consistent:**
- Hero section: `mb-24` class + `paddingBottom: 24` (line 134) — doubles up the spacing mechanism on the same element. The padding should be handled by the class alone or vice versa.
- Chart card: `marginBottom: 24` inline (line 172) — should use `.mb-24`.
- Chart area: `margin={{ top: 4, right: 4, left: -10, bottom: 0 }}` (line 196) — the `-10` left margin is a Recharts label-compensation hack, acceptable but undocumented.
- Account group items: `gap: 10` (line 271) — falls between the 8px and 12px scale steps. Should be `gap: 8` or `gap: 12` to stay on-scale.
- Recommendation card: `gap: 10` (line 150) — same off-scale issue.

**Accounts.tsx spacing:**
- Inline padding values (14px, 18px, 20px, 22px, 24px, 28px) across various sub-cards do not align to an 8px scale. `14px`, `18px`, `22px`, and `28px` are all half-steps.
- The transaction filters grid uses `gap: 10` (line 1050) — again off-scale.

**Verdict:** The scale is defined and used appropriately in the majority of cases, but half-step values (10px, 14px, 18px) appear frequently enough in inline styles to suggest the scale is not being enforced when writing JSX inline styles. A lint rule or a `space` utility token set would close this.

---

### Pillar 6: Experience Design (2/4)

**Loading states:**
- Dashboard.tsx: The `useApi` hook returns `loading` and `error`, but Dashboard **destructures neither** (line 84-87). During initial load, `nw` is null, so the hero shows `$—`, the chart shows the empty state "No chart data", and the account grid shows "No accounts yet" — all permanent-looking empty states. There is no visual distinction between "loading" and "truly empty."
- Accounts.tsx handles loading correctly: `accountsLoading` renders "Loading accounts…" text and `detailLoading` renders "Loading account details…" text (lines 765, 831).
- Insights.tsx renders a loading skeleton-equivalent text block (line 92).
- The inconsistency between pages is the main issue — the most prominent page (Dashboard) has the worst loading coverage.

**Error states:**
- Dashboard.tsx: `useApi` returns `error` but it is never destructured or rendered. If `/api/snapshots/current` or `/api/snapshots/net-worth` fail, the user sees the same `$—` as during load — no indication of failure.
- Accounts.tsx surfaces Plaid errors via `plaidMessage` state (line 746) — adequate for that flow.
- No global error boundary exists in the app. A component-level error in any page will propagate uncaught to the React tree.

**Empty states:**
- Dashboard empty states are specific and actionable (Pillar 1 covers this). The Accounts page "Pick an account" panel (line 827) shows a decorative `◌` icon — a nice touch.
- The allocation donut card falls back to `<div className="empty"><div className="empty-sub">No allocation data yet.</div></div>` (lines 247-250) — missing the `.empty-title` element that other empty states use, making it visually lighter than siblings.

**Destructive action confirmations:**
- Uses `window.confirm()` for deletes (Accounts.tsx:614, 672, 711). This is a native browser dialog — functional but visually breaks the dark theme (native dialog renders in system light theme on macOS). A custom inline confirmation would maintain brand immersion.
- Delete account button in the active panel (line 855) is rendered at the same visual weight as "Edit account" and "Set balance" — no red coloring or separation to signal danger. The form modal correctly separates the Delete button to the left of Cancel/Save, but the panel version does not.

**Disabled states:**
- Buttons disable correctly during `saving` state across all modals (Accounts.tsx:1176, 1206, 1261, 1299).
- The "Pin" button in the recommendation card has no disabled state or tooltip feedback — it toggles silently.

---

## Files Audited

- `/Users/thedeeb/github/Libertas/frontend/src/pages/Dashboard.tsx`
- `/Users/thedeeb/github/Libertas/frontend/src/pages/Accounts.tsx`
- `/Users/thedeeb/github/Libertas/frontend/src/index.css`
- `/Users/thedeeb/github/Libertas/frontend/src/App.tsx`
- `/Users/thedeeb/github/Libertas/frontend/src/main.tsx` (via Glob discovery)
- `/Users/thedeeb/github/Libertas/frontend/src/pages/Insights.tsx` (partial — loading/error patterns)
- `/Users/thedeeb/github/Libertas/frontend/src/pages/Debt.tsx` (partial — color patterns)
- `/Users/thedeeb/github/Libertas/frontend/src/pages/Import.tsx` (partial — error and loading patterns)
- Phase plans: 02-01 through 02-05-PLAN.md, 02-RESEARCH.md, 02-VALIDATION.md

---

## UI REVIEW COMPLETE
