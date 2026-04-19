# ADR-007: Terminal Design System

- Status: Accepted
- Date: 2026-04-13

## Context

After Phase 2 shipped, a UI audit scored Libertas at 16/24 on the Dashboard and 13/24 on other pages. The root causes were consistent: decorative surfaces (gradients, shadows, card glows) competing with data, inconsistent typography (serif display mixed with sans, no monospace discipline for numbers), overloaded color palette (gold, blue, purple, cyan all present), and inline styles bypassing the token system.

The existing "premium SaaS dark navy" aesthetic was generic — indistinguishable from a 2022 fintech product. Libertas is a local-first instrument used by people who actively chose not to use cloud finance tools. The UI should reflect that decision: serious, data-dense, and undecorated.

Reference direction: Bloomberg Terminal × Linear — near-monochrome, data-first, every number in monospace, no decoration that doesn't carry information.

## Decision

Replace the visual system wholesale. Backend unchanged. New features excluded from scope (except ⌘K palette, which is part of the keyboard-first mandate).

### Token system

Near-black background (`#0a0a0a`), near-white text (`#ededed`), three gray steps between. Single functional accent: amber (`#f5a524`) for active/actionable state only. Green (`#22c55e`) and red (`#ef4444`) reserved for signed deltas only. No other hues permitted in production UI.

Deleted tokens: `--gold`, `--blue`, `--blue-bright`, `--blue-glow`, `--purple`, `--cyan`, `--amber`, `--*-chart` family, `--font-serif`.

Radius: 14px → 4px. Spacing aligned to an 8-point scale via `--s-1` through `--s-8`.

### Typography

- Body: Geist 13px/1.5, −0.005em tracking. Manrope and Fraunces removed.
- Numbers: Geist Mono everywhere — every dollar amount, percent, date, and count. `font-variant-numeric: tabular-nums` required. No exceptions.
- Hero number: Geist Mono 72px, −0.04em tracking.
- Section labels: Geist Mono 10px uppercase, 0.14em tracking, `--text-3`.

### Surface rules

- Cards: `background: var(--bg-1); border: 1px solid var(--border);` — no gradients, no box-shadow, no hover transform.
- Body: flat `background: var(--bg);` — no radial gradients.
- Sidebar: flat `background: var(--bg);` with 1px hairline separator. Active nav = `var(--bg-1)` background, no gradient, no left-border accent.

### Data tables

Native `<table>` element. 36px rows, 30px header. Horizontal rules only — no zebra, no verticals. First column left-aligned text, numeric columns right-aligned mono tabular. Hover: `background: var(--bg-1)`. Selected: 2px left border in `--accent`.

### Charts

Custom wrapper over Recharts with locked defaults: 1.5px `var(--text)` stroke, gradient fill 14% → transparent, 10px mono axes, no tick marks, no grid lines, single horizontal baseline at y=0. Tooltip: black bg, 1px border, mono tabular. No legend by default. Delta strokes use only `--pos`/`--neg`.

### Inline style discipline

67+ inline `fontSize: N` values replaced with utility classes (`.text-xs` through `.text-xl`) in `index.css`. All inline `borderRadius` converted to `var(--r)`.

## Consequences

Positive:
- UI audit score target: ≥ 20/24 (up from 16/24 Dashboard, 13/24 other pages).
- Zero token drift — deleted palette tokens cannot re-enter without a lint failure.
- Numbers are always scannable at a glance; tabular alignment makes comparisons instant.
- Codebase has one place (index.css `:root`) that defines the entire visual system.

Trade-offs:
- Committed to dark-only for now. Light mode requires a full token inversion pass.
- Geist requires a Google Fonts load; users on air-gapped networks need a local font fallback.
- Stricter token constraints mean contributors cannot introduce one-off colors inline.

## Follow-ups

- ADR-008 covers the ⌘K command palette and keyboard navigation system built alongside this redesign.
- Light mode is out of scope for now; if added, it should be a second `:root[data-theme="light"]` block — no component-level changes.
