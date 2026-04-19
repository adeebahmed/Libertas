# ADR-008: Command Palette and Keyboard Navigation

- Status: Accepted
- Date: 2026-04-13

## Context

Libertas targets users who chose a local-only tool over managed apps — a cohort that skews toward keyboard-driven workflows. The existing navigation required mouse clicks through a sidebar. There was no way to jump between pages, trigger common actions, or change timeframes without lifting hands from the keyboard.

The Terminal design direction (ADR-007) mandated keyboard-first as a non-negotiable principle. This ADR captures the specific keyboard navigation system shipped alongside that redesign.

## Decision

### ⌘K Command Palette

A full-screen overlay triggered by `⌘K` (macOS) / `Ctrl+K` (Windows/Linux). Visual: 560px wide, centered, 40% from top. Black background, 1px `--border-strong` border, Geist Mono input, 36px result rows, keyboard arrow navigation, Enter fires the selected command.

Focus is trapped inside the palette while open. Escape closes. The palette is mounted at the App root so it's reachable from any page.

Registered commands at launch:

| Category | Commands |
|---|---|
| Navigation | Dashboard, Accounts, Debt, Import, Insights, Real Estate, Retirement, Settings, Taxes |
| Actions | Quick-add transaction, Quick-add account |
| Timeframe | 1M, 3M, 6M, 1Y, YTD, ALL |
| UI | Toggle theme |

### Chord navigation

Linear-style two-key chord sequences, active when focus is outside any input:

| Chord | Destination |
|---|---|
| `g d` | Dashboard |
| `g a` | Accounts |
| `g r` | Retirement |
| `g s` | Settings |
| `/` | Focus search input on current page |
| `?` | Open keyboard help overlay |

Chords are implemented via a shared `useHotkeys` hook registered once in App. The hook ignores events when an `<input>`, `<textarea>`, or `contenteditable` element has focus.

### Implementation

- `frontend/src/components/CommandPalette.tsx` — palette component
- `frontend/src/hooks/useHotkeys.ts` — chord + single-key registration
- Mounted in `frontend/src/App.tsx`

No third-party hotkey library. The hook uses `keydown` listeners with a 500ms chord timeout — if the second key doesn't arrive within 500ms, the sequence resets.

Sidebar footer shows `Press ⌘K` in mono `--text-3` as a persistent discoverability hint.

## Consequences

Positive:
- Navigation between any two pages is reachable in ≤ 3 keystrokes from anywhere in the app.
- Common actions (add transaction, change timeframe) no longer require locating the relevant page first.
- Consistent with the Terminal design direction's "keyboard-first" mandate.

Trade-offs:
- Chord sequences conflict with browser shortcuts if not carefully scoped; the focus guard (skip when input active) handles most cases but is not exhaustive.
- Command list is statically registered; dynamic commands (e.g., jump to a specific account) require a more sophisticated registry in future.
- `?` help overlay is registered but the overlay content is minimal at launch.

## Follow-ups

- As new pages or actions are added, their commands should be registered in `CommandPalette.tsx` at the same time.
- A dynamic command registry (search across account names, transactions) is a natural Phase 3+ extension.
