# App-Wide UI Review — Non-Dashboard Surfaces

**Audited:** 2026-04-16
**Baseline:** Abstract 6-pillar standards; brand north star: Copilot Money
**Screenshots:** Not captured (Playwright CLI unavailable; dev server confirmed running at localhost:5173)
**Excluded:** pages/Dashboard.tsx (audited separately in 02-UI-REVIEW.md)

---

## Pillar Scores

| Pillar | Score | Key Finding |
|--------|-------|-------------|
| 1. Copywriting | 3/4 | Copy is largely purposeful and contextual; three systemic gaps: hardcoded "2024" year in Taxes, technical empty-sub instructions as primary guidance, and missing `.empty-title` on several loading-as-empty states |
| 2. Visuals | 2/4 | Two competing tab component systems (`.tab` vs `.tab-btn`) produce inconsistent active-state chrome; Retirement page silently renders nothing during load; RealEstate add-form has no loading/saving feedback |
| 3. Color | 2/4 | Hardcoded hex colors are systemic across Debt, Retirement, Import, Insights, and Accounts — 20+ instances outside the token system; two rogue CSS colors (`#e0c06a`, `#e0906a`) not in `:root` |
| 4. Typography | 2/4 | 10 distinct inline `fontSize` values used across the 7 audited pages (10–28px), completely independent of the CSS class system defined in index.css; weight 450 and 550 are non-standard |
| 5. Spacing | 2/4 | Off-scale values (6, 10, 12.5, 14, 20) appear in 6 of 7 pages; `gap: 6`, `gap: 10`, `marginBottom: 10`, `gap: 20` all fall between defined 8px-scale steps |
| 6. Experience Design | 2/4 | RealEstate and Retirement have no loading state; Settings "Remove" buttons fire instant deletes with no confirmation; no global error boundary anywhere in the app |

**Overall: 13/24**

---

## Top 5 Priority Fixes

1. **Consolidate to one tab component** — Retirement uses `.tab` while Insights uses `.tab-btn`; they have different border radii, font weights, and active-state backgrounds, so two pages that both use the same "tabs" pattern look different. Fix: pick `.tab-btn` (the newer, more refined definition in index.css) and update Retirement.tsx lines 76–77 to use `className={\`tab-btn${tab === 'plan' ? ' active' : ''}\`}`.

2. **Token-lock all chart line colors** — Retirement.tsx uses `#5cad7a`, `#d4a840`, `#c95f52` on 6 chart `<Line>` props (lines 161–163, 217–219). Debt.tsx uses `#c95f52`, `#6a9fc0`, `#d4a840`, `#9b85c4` (lines 18–21). None of these are CSS variables. Add `--green-chart`, `--gold-chart`, `--red-chart`, `--blue-chart`, `--purple-chart` to `:root` in index.css and replace all inline hex values. This closes the color drift seen between Debt tags, Retirement lines, and Dashboard pie slices.

3. **Add loading states to RealEstate and Retirement** — `RealEstatePage` destructures only `data` and `refetch` from `useApi` (line 26), dropping `loading` silently. When the API is slow, the page is entirely blank — no skeleton, no spinner. Retirement does the same (lines 42–43). Fix: destructure `loading` from `useApi` in both pages and render `<div className="empty"><div className="empty-sub">Loading…</div></div>` while `loading` is true.

4. **Replace Settings "Remove" button instant-deletes with confirmation** — Settings.tsx lines 307 and 344 fire `api.delete()` directly on click with no confirmation dialog. Removing an institution or an account is destructive and may cascade-delete transaction history. Fix: wrap in `window.confirm()` at minimum, or better, render a brief inline confirmation state ("Remove?" / "Yes, remove" / "Cancel") to avoid the native-dialog dark-theme mismatch documented in the prior audit.

5. **Eliminate inline `fontSize` integers; use CSS utility classes** — Across 7 audited pages, raw `fontSize: 10`, `11`, `12`, `12.5`, `13`, `14`, `16`, `17`, `24`, `26`, `28` appear 67 times as inline JSX style props. Only the CSS class system in index.css (`.insight-title` at 15px, `.insight-desc` at 13.5px, etc.) has named abstractions. Add `.text-xxs` (10.5px), `.text-xs` (12px), `.text-sm` (13px), `.text-base` (14px), `.text-lg` (16px), `.text-xl` (20px) to index.css and replace inline integer font sizes.

---

## Detailed Findings

### Pillar 1: Copywriting (3/4)

**Strengths across pages:**
- Debt empty state is specific and instructional: "Add accounts with type credit_card, student_loan, auto_loan, or personal_loan" (Debt.tsx:89). Actionable, not generic.
- Import guide card copy (lines 265–278) is excellent — five named steps with plain-English explanations. "Filename matters" is a particularly good micro-copywriting moment.
- Insights chat prompt cards ("Should I pay off my high-interest debt or invest more?") lower the blank-screen intimidation well.
- Insights loading state says "Analysing portfolio…" (line 93) rather than "Loading…" — contextually appropriate.
- Retirement on-track card distinguishes "surplus" vs "shortfall" with the correct monetary sign — precise, no jargon.
- Settings field labels are clear: "Monthly expenses ($)", "1099 / freelance income ($/yr)", "Target retirement age" — all self-describing.

**Issues:**

- **Taxes.tsx:43 — hardcoded "2024 Tax Estimate"**: The section label uses the literal year 2024. When the app is used in 2026 or 2027 this becomes stale. Use a dynamic `new Date().getFullYear() - 1` or make it a configurable constant.

- **Retirement.tsx:133 — empty-sub used as primary instruction**: When `plan.on_track` is null, the fallback card renders `empty-sub` text: "Set your birth year, retirement age, and monthly contribution in Settings to see your personalized plan." This is useful guidance but `empty-sub` is a secondary caption style (13px, `--text-3`). It is the only text in the card and has no heading above it, making the actionable instruction visually subordinate to the surrounding whitespace.

- **Debt.tsx:89 — empty state reveals internal type string syntax**: "Add accounts with type credit_card, student_loan, auto_loan, or personal_loan" shows raw backend enum values to the user. This is a leaky abstraction. Use the human-readable labels from `TYPE_LABEL`: "Credit Card, Student Loan, Auto Loan, or Personal Loan."

- **Import.tsx:175 — rollback confirm dialog is technically accurate but cold**: "Roll back this import? This will delete all transactions from this import and rebuild the account." The tone is accurate but "rebuild the account" is ambiguous — does the account get deleted? Better: "Roll back this import? All transactions from this file will be removed. The account remains — only this import's data is undone."

- **Settings.tsx:307, 344 — "Remove" label on destructive buttons with no context**: Institutions and accounts are removed with a single unlabeled "Remove" button. No copy signals what happens downstream (account history lost, etc.).

- **RealEstate.tsx:59 — cancel CTA changes label to "Cancel"**: The add-property button toggles its label between "+ Add Property" and "Cancel" based on `showForm`. While functional, using the same button for both open and close creates an ambiguous toggle instead of a clear primary action with a separate close affordance.

---

### Pillar 2: Visuals (2/4)

**Strengths:**
- Import dropzone uses a dedicated `.dropzone` class with hover/drag-over state (`.dropzone.over`), giving clear drag affordance — one of the better interaction moments in the app.
- Retirement Plan tab has a top-border accent (`borderTop: 3px solid var(--green/red)`) on the on-track card — a clean semantic use of color as status signal.
- Insight cards use the left-border color system from the CSS for 11 distinct category types, defined in index.css — this is the best example of systematic visual encoding in the non-dashboard pages.
- LTVBar in RealEstate is a clean inline progress bar with semantic color thresholds (green/gold/red).

**Issues:**

- **Two incompatible tab styles**: Retirement.tsx uses `.tab` (lines 76–77) while Insights.tsx uses `.tab-btn` (lines 64–67). In CSS: `.tab` has `border-radius: 8px`, `font-weight: 600`, `border: 1px solid transparent`; `.tab-btn` has `border-radius: 4px`, `font-weight: 450`, no border. These produce visually distinct tab bars on two pages that should look identical. Users switching between pages notice the inconsistency.

- **Retirement page shows nothing during load**: `RetirementPage` renders `{tab === 'plan' && plan && (...)}` — when `plan` is null (loading), the plan tab renders blank. The scenarios tab similarly renders a blank chart card with an "Adjust parameters above" empty state during initial API call. There is no loading indicator for either tab.

- **RealEstate "Refresh estimate" button has no loading state**: Clicking "Refresh estimate" fires an `await api.post(...)` but the button has no `disabled` prop, no spinner, and the page just silently refreshes. Users may double-click or assume the action failed.

- **Settings Integrations section is dense and under-structured**: The Plaid and Sheets sub-cards sit inside a `.grid-2` inside the outer Integrations card, giving nested-card-in-card visual nesting. The connection status table appears below with no visual separator other than a thin border-top. The section needs either a visual hierarchy step (heading, subsection label) or a dedicated subsection component.

- **Insights filter buttons are fully custom-styled inline** (Insights.tsx:79–86): padding, borderRadius, fontSize, fontWeight, border, background, color, cursor, textTransform — all inline. They do not use `.btn`, `.tag`, or any existing class. This is a one-off control that looks slightly different from the rest of the button system.

- **RealEstate property cards use `grid-template-columns: 1fr 1fr` for the field grid** but the rightmost column items ("Purchased") are empty for two positions, causing a lopsided 3-field / 2-field split that creates visual imbalance inside the card.

---

### Pillar 3: Color (2/4)

**Token system is coherent; hardcoded escape valves are systemic:**

The `:root` defines 10 named semantic colors plus three background levels and three text levels — a solid foundation. However, nearly every page has hardcoded hex values that escape the token contract.

**Hardcoded hex inventory (non-dashboard pages):**

| File | Lines | Values | Issue |
|------|-------|--------|-------|
| Debt.tsx | 18–21 | `#c95f52`, `#6a9fc0`, `#d4a840`, `#9b85c4` | TYPE_COLOR map — none are `:root` tokens |
| Retirement.tsx | 161–163, 192–194, 217–219 | `#5cad7a`, `#d4a840`, `#c95f52` | Chart line colors — repeated on every chart render |
| Import.tsx | 49–50 | `#f8717128`, `#d4a84028`, `#60a5fa28` | Badge border/background tints |
| Insights.tsx | 119, 175 | `rgba(59,130,246,0.06)`, `rgba(59,130,246,0.18)` | Action callout and chat bubble tints |
| Accounts.tsx | 117–118, 158–162 | 10 hex values | Badge and type-color maps |
| index.css | 587, 589 | `#e0c06a`, `#e0906a` | Tax and Estate insight card border/cat colors — not in `:root` |

`#e0c06a` (tax category accent) and `#e0906a` (estate category accent) in index.css are the only two `:root`-level colors that were added directly to selector rules rather than to `:root`. They should become `--gold-warm` and `--amber` CSS variables.

The `#5cad7a` green in Retirement does not match `--green: #51d09a`. The `#c95f52` red does not match `--red: #ff7d81`. The color drift between chart lines and the token-based tag colors is visible when both appear on screen (e.g., Debt page where the bar chart and the type tag for the same debt type will be slightly different shades).

**Registry audit:** shadcn not initialized — no third-party registry audit needed.

---

### Pillar 4: Typography (2/4)

**CSS-defined type system (index.css):**

| Class | Size | Weight |
|-------|------|--------|
| `.num-hero` | clamp(2.4–4rem) | 600 |
| `.page-title` | clamp(1.95–2.45rem) | 600 |
| `.num-large` | clamp(1.45–1.8rem) | variable |
| `.num-mid` | clamp(1–1.2rem) | variable |
| `.section-label` | 0.64rem | 700 |
| `.insight-title` | 15px | 500 |
| `.insight-desc` | 13.5px | — |
| `.insight-why` | 12.5px | — |
| `.tab-btn` | 12.5px | 450 |
| `.dropzone-title` | 22px (Fraunces serif) | — |

This is already 10+ defined sizes. Inline styles add 10 more anonymous sizes across the audited pages.

**Inline `fontSize` values found across 7 pages:**

| Value | Count (approx) | Locations |
|-------|---------------|-----------|
| `10` | 3 | Insights badge, priority label, Taxes limit label |
| `11` | 8 | Debt XAxis ticks, RealEstate field labels, Retirement label, Taxes StatCard sub |
| `12` | 10 | Debt Tooltip, Import history date, Retirement tooltip, Settings feed validation |
| `12.5` | 4 | Import filename, Import error, Debt type breakdown |
| `13` | 14 | Debt by-type labels, Import guide, Retirement status, Taxes recs body text |
| `14` | 5 | Import error result, RealEstate address, Taxes recs type, Settings integration header |
| `16` | 2 | Import toast checkmark, chat close button |
| `24` | 1 | Retirement scenario card value (fontSize: 24 — no CSS class) |
| `26` | 1 | Retirement scenario card value (fontSize: 26 — same block, inconsistency) |
| `28` | 1 | Dropzone icon (defined in CSS as `font-size: 28px` on `.dropzone-icon` — redundant inline) |

The `fontSize: 24` and `fontSize: 26` on adjacent scenario cards in Retirement (lines 198, 202) are a direct inconsistency — two cards in the same grid section use different font sizes for the same semantic element (the projected balance figure).

Font weight 450 appears in `.tab-btn` and `.btn` CSS definitions. Weight 550 also appears in index.css. Both are non-standard on the Google Fonts Manrope variable range, which goes 400–800. The browser will interpolate these, but they are outside the documented variable weight axis stops, making them fragile.

---

### Pillar 5: Spacing (2/4)

**Defined scale (index.css):** 8, 12, 16, 24, 32px for margins/gaps. The grid helpers enforce 16px gap. This is a clean 8px-base scale.

**Off-scale values found (non-dashboard pages):**

| Value | Files | Notes |
|-------|-------|-------|
| `gap: 6` | Import.tsx:42 | QualityBadges flex gap — should be 8 |
| `gap: 10` | Debt.tsx:142, Taxes.tsx:154, RealEstate.tsx:125 | Half-step between 8 and 12 |
| `gap: 12` | Settings.tsx:313, 350 | On-scale but via inline style, not `.gap-12` class |
| `gap: 16` | Settings.tsx:378 | On-scale but inline |
| `gap: 20` | Retirement.tsx:173 | Off-scale — controls grid uses `gap: 20`, outside defined steps |
| `marginBottom: 4` | RealEstate:51, Retirement:96 | Sub-step, acceptable as micro-spacing |
| `marginBottom: 10` | Insights.tsx:73 | Off-scale |
| `padding: 16` | Settings Integrations sub-cards | On-scale but inline |
| `padding: '16px 20px'` | Settings inline forms | Mixed-axis padding, `20px` horizontal is off-scale |

The worst offender is Retirement.tsx:173 (`gap: 20`) in the controls grid — this is the largest structural layout gap and it sits between two defined steps (16 and 24), making the controls panel feel looser than the rest of the page grid.

Settings.tsx has the most inline spacing: the two inline forms (Institutions, Accounts) each use `padding: '16px 20px'` and `gap: 12` inline rather than the class system. While the values are nearly on-scale, putting them inline bypasses the class tokens.

---

### Pillar 6: Experience Design (2/4)

**Loading states:**

| Page | Loading State | Notes |
|------|---------------|-------|
| Debt | Yes — text "Loading…" in `.empty` | Functional but uses empty-state chrome instead of skeleton |
| Import | Yes — dropzone switches icon/title to "Processing…" | Well handled |
| Insights | Yes — "Analysing portfolio…" text | Contextually worded |
| Taxes | Yes — `estLoading` renders "Calculating…" | Covers main data block only; `harvest` and `recs` load silently |
| Retirement | No — `plan` null renders nothing | Blank page during load |
| RealEstate | No — `loading` not destructured | Blank page during load |
| Settings | No — all four `useApi` calls drop `loading` | Forms appear instantly empty, no indication data is loading |

**Error states:**

| Page | Error Handling | Notes |
|------|---------------|-------|
| Import | Yes — catch sets `result.status = 'error'`, displayed with red border | Best in class |
| Debt | No — `error` not destructured from `useApi` | Silently shows empty state on API failure |
| Insights | Partial — chat tab catches API errors and displays in red text; insights tab has no error state |
| Retirement | No — `error` not destructured | Silently blank |
| RealEstate | No — `handleAdd` has no try/catch; API failure is swallowed | |
| Settings | Partial — `runAction` wrapper catches errors and shows toast, but the four `useApi` loads drop `error` | |
| Taxes | No — none of three `useApi` calls destructure `error` | |

No global error boundary exists in App.tsx or main.tsx. A React render error in any page component will crash the entire shell including the sidebar nav.

**Destructive action confirmations:**

| Action | Confirmation | Notes |
|--------|-------------|-------|
| Import rollback | `window.confirm()` (Import.tsx:175) | Native dialog, dark theme mismatch |
| Delete account | `window.confirm()` (Accounts.tsx:614) | Same issue |
| Delete transaction | `window.confirm()` (Accounts.tsx:672) | Same issue |
| Delete holding | `window.confirm()` (Accounts.tsx:711) | Same issue |
| Remove institution | None (Settings.tsx:307) | Immediate delete on click — no confirmation at all |
| Remove account | None (Settings.tsx:344) | Immediate delete on click — no confirmation at all |

The Settings "Remove" buttons are the most severe gap: removing an account can cascade-delete years of transaction history, but the action fires on a single click with zero friction.

**Empty states (quality):**

Empty states are generally well-structured with `.empty-icon`, `.empty-title`, `.empty-sub` hierarchy. Issues:
- Taxes account recommendations fallback (line 172) uses only `.empty-sub` with no `.empty-title`, making the placeholder invisible when glanced at quickly.
- Retirement "no plan configured" card (line 133) uses only `.empty-sub` inside a `.card` rather than the `.empty` pattern — it looks like a loading message rather than a deliberate no-data state.
- `RealEstate` form toggle creates an implicit empty state (hiding the empty state when `showForm` is true at line 133) — if the user opens the form and then dismisses it on mobile, the empty state correctly reappears.

**Disabled states:**

- Debt `saveEdit` button correctly disables during save (line 227).
- Settings action buttons correctly disable via `busyAction` guard (lines 390, 395, 400, 437, 442, 447).
- RealEstate "Add Property" button correctly disables when `!form.address` (line 91).
- RealEstate "Refresh estimate" button has no disabled state during the async post (line 126–129).

---

## Per-Page Findings Summary

### Debt.tsx

- Hardcoded `TYPE_COLOR` hex map (#c95f52, #6a9fc0, #d4a840, #9b85c4) diverges from CSS tokens (Pillar 3).
- 7 inline `fontSize` values; none use CSS classes (Pillar 4).
- `gap: 10` in "By Type" breakdown (line 142) is off-scale (Pillar 5).
- `error` not destructured from `useApi` — API failures show empty state (Pillar 6).
- Empty state instruction mentions raw type strings (Pillar 1).

### Import.tsx

- Best error handling in the app: upload errors, rollback errors, quality badges all handled.
- `window.confirm` + `window.alert` for rollback (lines 175, 181) — native dialogs break dark theme (Pillar 6).
- 15 inline `fontSize` values; QualityBadges `fontSize: 10.5` overrides the already-defined `.tag` class `font-size: 10.5px` inline (Pillar 4).
- `gap: 6` in QualityBadges (line 42) is off-scale (Pillar 5).
- Inline `padding: '24px 28px'` on Import guide card (line 262) — on-scale values but bypasses class system.

### Insights.tsx

- Priority filter buttons are entirely custom-styled inline (79–86) — do not use any existing button class (Pillar 2).
- Hardcoded `rgba(59,130,246,0.06)` for action callout tint (line 119) and `rgba(59,130,246,0.18)` for user chat bubble (line 175) — should be a `--blue-tint` CSS variable (Pillar 3).
- `marginBottom: 20` on filter row (line 73) is off-scale; should be `mb-24` or `mb-16` (Pillar 5).
- Chat tab lacks empty-state structure for error messages (just a red div, no `.empty` chrome).

### RealEstate.tsx

- No loading state — `loading` not destructured from `useApi` (Pillar 6, critical).
- No error handling in `handleAdd` — API failures are swallowed silently (Pillar 6).
- "Refresh estimate" button fires async action with no disabled state or feedback (Pillar 2, Pillar 6).
- 10 inline `fontSize` values (Pillar 4).
- Property card sub-label pattern (lines 104, 108, 112, 116, 120) correctly implements a consistent `.text-uppercase` label style inline, but this pattern should be a named utility class.
- CTA label toggle "Cancel" / "+ Add Property" creates ambiguity (Pillar 1).

### Retirement.tsx

- No loading state for either `plan` or `scenarios` API calls (Pillar 6, critical).
- Uses `.tab` class instead of `.tab-btn` — inconsistent with Insights (Pillar 2, critical).
- 13 inline `fontSize` values including the inconsistent `fontSize: 24` vs `fontSize: 26` on adjacent stat cards (Pillar 4).
- Three identical `<Line>` color configurations duplicated across plan chart and scenarios chart — should be a `SCENARIO_COLORS` constant (DRY issue that compounds the color token problem).
- `gap: 20` in controls grid (line 173) is off-scale (Pillar 5).
- Plan tab shows nothing when `plan` is null — no loading indicator, no placeholder (Pillar 6).

### Settings.tsx

- No loading states on any of the four `useApi` calls — forms appear instantly empty (Pillar 6).
- "Remove" buttons on institutions and accounts fire immediate deletes with no confirmation (Pillar 6, high-risk).
- Integrations section nests `.card` inside `.card` — visual hierarchy is unclear (Pillar 2).
- Settings is the only page that uses only 4 inline `fontSize` occurrences — the lowest count; the section-label and field/label CSS classes do most of the work (Pillar 4, relative strength).
- `gap: 16` and `padding: 16` on Integrations sub-cards (lines 378–379) are on-scale values but written inline instead of using CSS classes.

### Taxes.tsx

- Hardcoded "2024 Tax Estimate" section label (line 43) — will become stale (Pillar 1).
- Hardcoded "2024 limit" column label (line 164) — same issue.
- Three `useApi` calls; only `estLoading` is handled — `harvest` and `recs` load silently with no empty-state or loading treatment (Pillar 6).
- Tax recommendations fallback uses only `.empty-sub` with no `.empty-title` (Pillar 2).
- `gap: 12` on recommendations stack (line 150) is on-scale; `gap: 16` on the harvest table row (line 154) is on-scale — spacing is cleaner here than on other pages.

### App.tsx / Global Shell

- No global error boundary in App or main — any page render error crashes the sidebar (Pillar 6).
- Sidebar "Settings" link uses icon-only `.sidebar-icon-btn` with `title="Settings"` tooltip — the icon is `<IconGear>` which is universally recognized; acceptable but worth noting.
- Mobile nav renders the same `NAV` items with icon + label — this is correct behavior.
- Sidebar Import button uses `.sidebar-import-btn` which is a distinct visual class from both `.sidebar-icon-btn` and the standard nav links — three different visual treatments in the sidebar footer is one too many.

---

## Recurring / Systemic Issues

1. **Inline `fontSize` integers** — Present in every audited page. 67+ instances across 7 files using 10 distinct sizes. None use CSS class utilities. The CSS class system in index.css exists but is not being used for these secondary text elements.

2. **`error` not destructured from `useApi`** — Debt, RealEstate, Retirement, Taxes, and Settings all drop the `error` return from `useApi`. API failures produce the same visual output as "no data" (blank or empty state). This was also the primary issue in the Dashboard audit.

3. **Hardcoded chart hex values** — Retirement, Debt, and (from prior audit) Dashboard all use hardcoded hex strings for chart colors instead of CSS variables. The same logical color (e.g., gold) has three slightly different hex values across the three pages.

4. **Off-scale spacing values** — `gap: 10`, `gap: 6`, `gap: 20`, `marginBottom: 10`, `padding: '16px 20px'` all appear across the app. The defined 8px scale is broken in every page except Taxes (which is the best-behaved page for spacing).

5. **`window.confirm()` / `window.alert()` for destructive actions** — 5 instances across Import and Accounts. Native browser dialogs render in the system light theme on macOS, visually breaking the dark UI. Settings has even worse behavior: two "Remove" buttons with no confirmation at all.

---

## Files Audited

- `/Users/thedeeb/github/Libertas/frontend/src/pages/Debt.tsx`
- `/Users/thedeeb/github/Libertas/frontend/src/pages/Import.tsx`
- `/Users/thedeeb/github/Libertas/frontend/src/pages/Insights.tsx`
- `/Users/thedeeb/github/Libertas/frontend/src/pages/RealEstate.tsx`
- `/Users/thedeeb/github/Libertas/frontend/src/pages/Retirement.tsx`
- `/Users/thedeeb/github/Libertas/frontend/src/pages/Settings.tsx`
- `/Users/thedeeb/github/Libertas/frontend/src/pages/Taxes.tsx`
- `/Users/thedeeb/github/Libertas/frontend/src/App.tsx`
- `/Users/thedeeb/github/Libertas/frontend/src/index.css`
- `/Users/thedeeb/github/Libertas/frontend/src/main.tsx`

---

## UI REVIEW COMPLETE
