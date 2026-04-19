# Libertas Redesign — "Terminal" Direction

**Owner:** Codex execution
**Status:** Ready to execute
**Branch strategy:** Dedicated branch `redesign/terminal` off `main`. One commit per task. PR at end.
**Scope:** Full visual system replacement. No backend changes. No new features (other than ⌘K palette).

---

## 1. Objective

Replace the current "premium SaaS dark navy" aesthetic with a **Terminal** direction: Bloomberg × Linear. A serious instrument for people who actively chose a local-only finance tool. Near-monochrome, data-first, monospace for every number, keyboard-driven, no decoration that doesn't carry information.

---

## 2. Design principles (non-negotiable)

1. **Data is the decoration.** If a visual element is not data or hierarchy, remove it. No radial glows, no card gradient fills, no drop shadows beyond `0 1px 0 rgba(0,0,0,0.4)`.
2. **Monochrome + one functional accent.** Near-black bg, near-white text, three gray steps between. Amber (`#f5a524`) for active/actionable only. Green/red reserved for signed deltas only.
3. **Numbers are mono, always.** Every dollar amount, percent, date, and count uses `Geist Mono` with `font-variant-numeric: tabular-nums`. No exceptions.
4. **Sharp geometry.** Radius drops from 14px → 4px. Borders 1px hairline, never soft-shadowed cards.
5. **Dense where dense is earned.** Data tables in their native element: tight rows, horizontal rules, no card wrapping. Pages breathe in the margins, not inside the data.
6. **One hero per page.** Dashboard has one 72px number. Everything else defers.
7. **Keyboard-first.** ⌘K palette, `g a` = go accounts, `g d` = dashboard, `/` = focus search, `?` = help.

---

## 3. Token system — replace `:root` block in `frontend/src/index.css` lines 3–41

```css
:root {
  /* Surface */
  --bg:            #0a0a0a;
  --bg-1:          #111111;
  --bg-2:          #171717;
  --bg-elev:       #1f1f1f;
  --border:        #1f1f1f;
  --border-strong: #2a2a2a;
  --border-focus:  #3f3f3f;

  /* Text */
  --text:          #ededed;
  --text-2:        #a1a1a1;
  --text-3:        #666666;
  --text-mute:     #404040;

  /* Functional */
  --accent:        #f5a524;   /* amber — actionable/active only */
  --accent-dim:    #6b4a10;
  --pos:           #22c55e;   /* positive delta only */
  --neg:           #ef4444;   /* negative delta only */
  --focus-ring:    #3f3f3f;

  /* Typography */
  --font-sans: 'Geist', 'Inter', -apple-system, 'Segoe UI', sans-serif;
  --font-mono: 'Geist Mono', 'JetBrains Mono', 'SFMono-Regular', Menlo, monospace;

  /* Scale */
  --r:    4px;
  --r-sm: 2px;

  --s-1:  4px;
  --s-2:  8px;
  --s-3:  12px;
  --s-4:  16px;
  --s-5:  24px;
  --s-6:  32px;
  --s-7:  48px;
  --s-8:  64px;

  --fs-xs:   11px;
  --fs-sm:   12px;
  --fs-base: 13px;
  --fs-md:   15px;
  --fs-lg:   18px;
  --fs-xl:   24px;
  --fs-2xl:  32px;
  --fs-3xl:  48px;
  --fs-hero: 72px;
}
```

**Deleted tokens (must not survive):**
`--gold`, `--gold-dim`, `--gold-warm`, `--blue`, `--blue-bright`, `--blue-glow`, `--green`, `--red`, `--purple`, `--cyan`, `--amber`, `--*-chart` family, `--font-serif`, Fraunces import. Replace every reference. Grep: `rg -n "gold|blue|purple|cyan|Fraunces|var\(--green\)|var\(--red\)"`.

---

## 4. Typography

- Import: `https://fonts.googleapis.com/css2?family=Geist:wght@400;500;600;700&family=Geist+Mono:wght@400;500;600&display=swap`
- Drop Manrope + Fraunces entirely.
- Body: `--font-sans` 13px/1.5, `-0.005em` tracking.
- Mono class `.num`: already exists (line 323). Keep. Ensure applied to **every** money, percent, date, and count render.
- Page titles: `--font-sans`, `--fs-xl` (24px), weight 500, `-0.02em` tracking. **No serif.**
- Hero number (`.num-hero`): `--font-mono`, `--fs-hero` (72px), weight 500, `-0.04em` tracking, tabular-nums.
- Section labels (`.section-label`): `--font-mono`, 10px, weight 500, uppercase, 0.14em tracking, `--text-3`.

---

## 5. Component system changes

### 5.1 Cards
- Replace gradient fill + 14px radius with: `background: var(--bg-1); border: 1px solid var(--border); border-radius: var(--r);`
- Remove `box-shadow`. Remove `card-hover` transform. Hover state = `border-color: var(--border-strong)` only.

### 5.2 Background
- Remove the three-layer radial gradient on `body` (lines 57–60). Replace with flat `background: var(--bg);`.

### 5.3 Sidebar
- Remove gradient background, backdrop-filter, border-left accent on active item.
- Flat `background: var(--bg);` separated from main by `1px solid var(--border)`.
- Active link: `color: var(--text); background: var(--bg-1);` (no gradient, no border accent).
- Logo: sans, weight 600, 16px. Drop the serif display size.
- Add bottom-fixed row with keyboard hint: `⌘K` in mono.

### 5.4 Data tables (`.tbl`)
- Row height 36px. Header 30px, uppercase, 10px mono, `--text-3`.
- Horizontal rules only (`border-bottom: 1px solid var(--border)` on rows). No verticals. No zebra.
- First column left-aligned text. Numeric columns right-aligned, mono, tabular-nums.
- Hover: row gets `background: var(--bg-1)`.
- Selected row: 2px left border in `--accent`.

### 5.5 Buttons
- Primary: `background: var(--text); color: var(--bg); border-radius: var(--r); padding: 8px 14px; font-weight: 500; font-size: 12px;`
- Secondary: `background: transparent; color: var(--text); border: 1px solid var(--border-strong);`
- Destructive: `color: var(--neg); border: 1px solid var(--neg); background: transparent;` — **always behind confirm**.
- Icon button: 28x28, `var(--r-sm)` radius, transparent bg.
- Kill all pill-shaped (`border-radius: 999px`) buttons except filter chips.

### 5.6 Empty states
- One centered mono block per page: label in `--text-3`, one line of body in `--text-2`, one action button.
- No illustrations. No emoji. The restraint is the point.

### 5.7 Charts
See Section 7 — this is a dedicated task.

---

## 6. Task breakdown for Codex

Execute in order. One commit per task. Each task must leave `npm run build --prefix frontend` green.

### T01 — Token swap + font swap
- **Files:** `frontend/src/index.css` (lines 1–41), `frontend/index.html` (if font link is there)
- **Do:** Replace `:root` per Section 3. Replace font import per Section 4. Keep existing class names; only values change.
- **Accept:** App loads, text renders in Geist, numbers in Geist Mono, no console errors. Build green.
- **Commit:** `refactor(design): swap tokens + typography to Terminal direction`

### T02 — Purge deleted tokens
- **Files:** every `.tsx` under `frontend/src/`, all of `frontend/src/index.css` after T01
- **Do:** Grep and replace all references:
  - `var(--gold)` / `var(--gold-*)` → `var(--accent)`
  - `var(--blue)` / `var(--blue-bright)` / `var(--blue-glow)` → `var(--text)` (or `var(--accent)` where it marks active state)
  - `var(--purple)` / `var(--cyan)` / `var(--amber)` / `var(--gold-warm)` → `var(--text-2)`
  - `var(--green)` → `var(--pos)`, `var(--red)` → `var(--neg)`
  - `var(--font-serif)` → `var(--font-sans)`
  - All `--*-chart` references → see T06.
- **Accept:** `rg -n "gold|blue-bright|purple|cyan|Fraunces|font-serif"` returns zero in `frontend/src/`.
- **Commit:** `refactor(design): purge legacy color + serif tokens`

### T03 — Flatten surfaces (body, cards, sidebar)
- **Files:** `frontend/src/index.css`
- **Do:** Apply Section 5.1, 5.2, 5.3. Remove body radial gradients, card gradient fills, card box-shadows, card hover-transform, sidebar gradient, sidebar backdrop-filter, active-link gradient + border-left.
- **Accept:** No `radial-gradient`, no `backdrop-filter`, no gradient card fills remain in `index.css`. Visually flat.
- **Commit:** `refactor(design): flatten surfaces — no gradients, no shadows`

### T04 — Radius + spacing normalization
- **Files:** `frontend/src/index.css`, all `.tsx` with inline `padding`/`borderRadius`
- **Do:** Global radius 14→4 via `--r`. Enumerate off-scale inline spacings (6, 10, 14, 20px — flagged in the audit) and snap to `--s-*`. Inline `borderRadius: N` → class or `var(--r)`.
- **Accept:** `rg -n "borderRadius:\s*['\"]?[0-9]" frontend/src/` returns zero. Inline padding/margin uses only tokens.
- **Commit:** `refactor(design): normalize radius + spacing to scale`

### T05 — Purge inline fontSize integers
- **Files:** all `.tsx` under `frontend/src/pages/` and `frontend/src/components/`
- **Do:** Audit flagged 67+ inline `fontSize: N`. Add utilities to `index.css`:
  ```css
  .text-xs  { font-size: var(--fs-xs); }
  .text-sm  { font-size: var(--fs-sm); }
  .text-base{ font-size: var(--fs-base); }
  .text-md  { font-size: var(--fs-md); }
  .text-lg  { font-size: var(--fs-lg); }
  .text-xl  { font-size: var(--fs-xl); }
  ```
  Replace every inline `fontSize: N` with the nearest utility. Drop sizes outside the scale — snap up to nearest.
- **Accept:** `rg -n "fontSize:\s*[0-9]" frontend/src/` returns zero.
- **Commit:** `refactor(design): move inline fontSize to scale utilities`

### T06 — Chart system (replace Recharts defaults)
- **Files:** `frontend/src/components/` (new `Chart.tsx`), all pages importing Recharts
- **Do:** Build a single `<LineChart data={…} height={…} />` wrapper over Recharts with locked defaults:
  - Stroke: `var(--text)` 1.5px.
  - Gradient fill: `var(--text)` 14% → transparent, vertical.
  - Axes: 10px mono, `var(--text-3)`, no tick marks, minimal ticks (4 max).
  - Grid: off. Replace with a single horizontal baseline at y=0 in `var(--border)`.
  - Tooltip: custom, black bg, 1px border, mono, tabular-nums, shows one line per series.
  - Crosshair: 1px vertical in `var(--border-strong)` on hover.
  - No legend by default (caller provides above the chart if needed).
- Same treatment for `<AreaChart>` and `<BarChart>` via same wrapper file.
- Donut (Dashboard allocation) — rebuild as a minimal ring: 8px stroke, mono labels outside, no fill, no shadows.
- Delta colors: only `--pos` / `--neg` permitted in chart strokes. No other hues.
- **Accept:** No hardcoded hex in any chart component. All charts use the wrapper. Visual: they read as "instrument," not "presentation."
- **Commit:** `feat(charts): custom Terminal-direction chart wrappers`

### T07 — Global shell redesign
- **Files:** `frontend/src/App.tsx`, `frontend/src/index.css` (sidebar block)
- **Do:**
  - Sidebar width 248 → 220.
  - Logo: sans 16px, weight 600, plain text "Libertas" + 1px vertical hairline + page title in the main area's header.
  - Nav items: 12px sans, `var(--text-3)` idle, `var(--text)` + `var(--bg-1)` active. Remove icon opacity animation.
  - Bottom of sidebar: keyboard hint row `Press ⌘K` in mono, `var(--text-3)`.
  - Main padding 34/36/46 → 32/40/48.
  - Page header: title left, action cluster right, 1px hairline bottom. Title is sans 24px, no serif.
- **Accept:** Shell looks severe and quiet. Active nav reads instantly.
- **Commit:** `refactor(shell): minimal terminal sidebar + header`

### T08 — ⌘K command palette
- **Files:** `frontend/src/components/CommandPalette.tsx` (new), `frontend/src/App.tsx` (mount), `frontend/src/hooks/` (new `useHotkeys.ts` if not present)
- **Do:**
  - Open on `⌘K` / `Ctrl+K`. Focus trapped. Esc closes.
  - Commands registered: jump-to-page (Dashboard, Accounts, Debt, Import, Insights, RealEstate, Retirement, Settings, Taxes), quick-add transaction, quick-add account, switch timeframe (1M / 3M / 6M / 1Y / YTD / ALL), toggle theme (future).
  - Visual: 560px wide, centered, 40% from top, black bg, 1px `--border-strong`, mono input, results 36px rows, keyboard arrows highlight, enter fires.
  - Also register `g a` `g d` `g r` `g s` chord navigation (Linear-style) via the same hook.
- **Accept:** ⌘K opens from any page. Each command navigates or fires. Chord navigation works outside input focus.
- **Commit:** `feat(palette): ⌘K command palette + chord nav`

### T09 — Dashboard redesign
- **Files:** `frontend/src/pages/Dashboard.tsx`
- **Do:**
  - Hero: one mono 72px net-worth number top-left. Below it, one line: delta vs previous period (signed, mono, `--pos`/`--neg`), and period selector in mono pill row.
  - Chart: full-width below hero, 280px tall, no card wrapper, just data + baseline.
  - Allocation: single column of rows, not a donut. Each row = category label + horizontal bar + mono percent + mono amount. Right-aligned numbers, tabular.
  - Accounts summary: flat data table per Section 5.4.
  - Insights: 3 rows max, mono prefix `001 / 002 / 003`, one-line findings, no cards.
  - Loading: hero shows `—` in `--text-3`, chart shows 1px baseline only, tables show 3 skeleton rows (flat `--bg-1` blocks).
  - Error: top banner `ERR · ${status}` in `--neg`, mono, 1px border.
- **Accept:** Matches the audit's top fix: loading/error consumed. Hero dominates. No decoration.
- **Commit:** `refactor(dashboard): hero-first Terminal redesign`

### T10 — Accounts / Debt / RealEstate / Taxes — table-first
- **Files:** `frontend/src/pages/{Accounts,Debt,RealEstate,Taxes}.tsx`
- **Do:**
  - Drop card grids. Primary UI = one data table per Section 5.4.
  - Filters above table: mono chips, 1px border, active chip = `--accent` border + text.
  - Row click = open right-side drawer with detail (reuse existing inline state; if absent, collapse to below-row expansion).
  - Destructive actions (Settings Remove flagged in audit) must route through a custom confirm dialog component — no `window.confirm`.
- **Accept:** All four pages read as ledgers. Numbers right-aligned, mono. Hover state subtle.
- **Commit:** `refactor(pages): table-first ledger view for accounts/debt/real-estate/taxes`

### T11 — Retirement / Insights — unify tab component + chart
- **Files:** `frontend/src/pages/Retirement.tsx`, `frontend/src/pages/Insights.tsx`, `frontend/src/index.css`
- **Do:**
  - Single `.tab-btn` component. Remove `.tab` (audit finding #1). Tab row = mono 11px uppercase, 2px bottom border on active in `--accent`, idle `--text-3`.
  - Replace all Retirement/Debt hex (`#5cad7a`, `#c95f52`, `#d4a840`, `#6a9fc0`, `#9b85c4`) with `--pos`/`--neg`/`--text-2` only. If a comparison needs more than two hues, reconsider the chart.
  - Insights rule cards flatten to rows per Dashboard treatment.
- **Accept:** No `.tab` class survives. No hardcoded chart hex anywhere.
- **Commit:** `refactor(pages): unify tabs + chart palette discipline`

### T12 — Settings + confirm dialog
- **Files:** `frontend/src/pages/Settings.tsx`, `frontend/src/components/Confirm.tsx` (new)
- **Do:**
  - Replace every `window.confirm` / `window.alert` across the app with `<Confirm />` component: black bg, 1px border, mono copy, `[Esc cancel] [Enter confirm]` hint at bottom, destructive variant styles confirm button per Section 5.5.
  - Settings: group sections with 1px hairlines + section label in mono 10px uppercase. No card stacking.
  - Institution/account remove behind Confirm with exact name echo required (type account name to enable confirm button).
- **Accept:** `rg -n "window\.(confirm|alert)" frontend/src/` returns zero.
- **Commit:** `feat(settings): custom confirm + flattened section layout`

### T13 — Empty states + loading primitives
- **Files:** `frontend/src/components/Empty.tsx` (new), `frontend/src/components/Loading.tsx` (new), consumer pages
- **Do:** Per Section 5.6. Replace every empty-state (silent rendering + any `No data`-type string) with `<Empty label message action>`. Replace every missing loading branch (audit: 5 of 7 pages drop `loading`) with `<Loading lines={3} />` skeletons.
- **Accept:** Every page with `useApi` destructures `loading` and `error`. No blank screens during fetch. No silent empty renders.
- **Commit:** `feat(states): unified empty + loading primitives`

### T14 — Global error boundary
- **Files:** `frontend/src/components/ErrorBoundary.tsx` (new), `frontend/src/main.tsx`
- **Do:** Class component wrapping `<App />`. Fallback: centered mono `RUNTIME ERROR`, one-line summary, `[Reload]` button. Logs to console.
- **Accept:** Throwing in any page does not break the sidebar.
- **Commit:** `feat(reliability): global error boundary`

### T15 — QA pass
- **Files:** all touched
- **Do:**
  - Visual pass on all 9 pages at 1440 and 1024 widths.
  - `npm run build --prefix frontend` green.
  - `rg` sweep — all purge checks from T02, T04, T05, T12 return zero.
  - Manual flows: import CSV, add account, ⌘K nav, chord nav, confirm delete, trigger error.
  - Update `docs/adr/` with new ADR `010-terminal-design-direction.md` capturing: the direction, the token palette, the typography, the rationale (audit findings + premium positioning). Reference audits at `.planning/phases/02-net-worth-dashboard/02-UI-REVIEW.md` and `.planning/APP-UI-REVIEW.md`.
- **Accept:** Build green, ADR merged.
- **Commit:** `docs(adr): 010 terminal design direction`

---

## 7. Out of scope (do not do)

- Backend changes. Any new API, schema, or service. If the UI needs data not yet exposed, **skip the feature** and note in the PR.
- New pages. If a page isn't in `frontend/src/pages/` today, don't add it.
- Light mode. Can come later; Terminal is dark-only for now.
- Animations beyond: 120ms color transitions on hover, ⌘K open/close fade (80ms).
- Third-party UI libs (shadcn, Radix extensions beyond what's present, etc.). Only existing dependencies + handwritten code.

---

## 8. Execution protocol

1. `git checkout -b redesign/terminal`
2. Execute T01 → T15 in order. After each task: build green, commit, push.
3. If blocked on a task: commit progress with `[WIP]` prefix and leave a `// TODO-REDESIGN:` comment explaining. Do not skip ahead past a blocker that would contaminate downstream tasks.
4. PR at end against `main` with:
   - Screenshots of all 9 pages before/after.
   - Link to audit files.
   - Link to ADR-010.

## 9. Acceptance criteria (whole project)

- Zero references to removed tokens / inline fontSize / hardcoded chart hex / `window.confirm`.
- Every money/percent/date/count in mono with tabular-nums.
- All 9 pages handle `loading` and `error` from `useApi`.
- ⌘K works from every page.
- ADR-010 merged.
- Score target on repeated UI audit: **≥ 20/24** overall (up from 16/24 Dashboard, 13/24 rest).
