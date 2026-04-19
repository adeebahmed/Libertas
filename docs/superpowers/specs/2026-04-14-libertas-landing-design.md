# Libertas Landing Redesign — Design Spec

**Date:** 2026-04-14
**Status:** Approved, ready for plan
**Scope:** Full overhaul of `docs/` VitePress site into a high-conversion product landing. No ADRs in public nav. Theme preserved + elevated (no palette rewrite).

---

## 1. Goals

- High-conversion, "super salesy" single-page landing at `/`
- Clear, scannable — current site is text-heavy and disorganized
- Audience: self-directed people with many accounts who want consolidation, clarity, trajectory, and control (NOT wealth optimization, NOT cashflow budgeting)
- Preserve existing blue/Manrope/Instrument Serif theme; elevate fidelity
- Remove ADRs from public surface (files stay in repo, unlinked)
- Works on GitHub Pages (static only) at base `/Libertas/`

## 2. Non-Goals

- No palette/typography rewrite
- No social proof section v1 (no stars/quotes/press available yet — slot reserved)
- No blog / changelog
- No i18n
- No in-browser demo of the app (screenshots only; app runs only on user's machine)
- No SSR / dynamic content

## 3. Information Architecture

Single-page scrollytelling landing + thin feature pages.

| Route | Purpose |
|---|---|
| `/` | Conversion-focused scrollytelling landing |
| `/features/` | Index of 6 feature detail pages |
| `/features/<slug>` | One per feature: dashboard, accounts, import, real-estate, projections, insights |
| `/privacy/` | "Why local-first" deep dive |
| `/download/` | Install + quickstart |

**Nav:** `Features · Why Private · Download` + GitHub icon.

**ADRs:** `docs/adr/*.md` remain in repo. Removed from VitePress nav + sidebar config. Not linked from any public page.

## 4. Messaging

**Primary hook:** Consolidation — "All your accounts. One private view." / "Stop juggling 12 logins."
**Secondary hook:** Trajectory/control — surfaced in walkthrough copy, feature page taglines, and section subheads.

No social proof v1. Leave visual slot between Feature Grid and Privacy section for later addition.

## 5. Landing Page Sections (in order)

1. **Hero** — headline (consolidation), sub (trajectory/control), primary CTA "Download", secondary "See features". Dashboard screenshot right. Trust strip: "100% local · No accounts · Open source · MIT".
2. **Problem** — 3-line punch ("12 logins. 5 spreadsheets. Zero clarity.")
3. **Sticky Product Walkthrough** — 6 scroll steps, one per feature. Sticky screenshot crossfades on step change. Left copy: active bright, inactive dimmed 40%. Left-rail progress dots.
4. **Feature Grid** — 6 cards linking to feature pages.
5. **[Proof slot — empty v1]**
6. **Privacy strip** — 3 bullets + link to `/privacy/`.
7. **FAQ** — 5–6 Q&A (free? windows support? data location? price data? backup? import format?).
8. **Final CTA** — download block + install one-liner + GitHub link.
9. **Footer** — license, GitHub, docs.

## 6. Feature Detail Page Template

All 6 pages share layout, driven by frontmatter.

Sections:
- Hero strip — tagline + hero screenshot + Download CTA
- What it does — 2 short paragraphs
- How it works — 3 steps (icon + label + 1 line)
- Private by design — 1 paragraph feature-specific
- Screenshot gallery — 2–3 shots
- Reused `CTABlock`
- `← All features` back link

## 7. Architecture

**Stack:** VitePress 1.6.3 (unchanged). Custom theme extension. All output static → GitHub Pages.

**File additions:**
```
docs/.vitepress/theme/
  components/
    Hero.vue
    ProductWalkthrough.vue
    FeatureGrid.vue
    PrivacyStrip.vue
    FAQ.vue
    CTABlock.vue
  layouts/
    feature.vue
  index.ts               # register components + layout
  custom.css             # extended (not replaced)

docs/features/
  index.md
  dashboard.md
  accounts.md
  import.md
  real-estate.md
  projections.md
  insights.md

docs/privacy/index.md    # new expanded privacy page
docs/download/index.md   # new install page
docs/public/screenshots/ # PNGs captured from real app

backend/seed_demo.py     # new — builds libertas-demo.db
```

**File removals from nav only (files stay):**
- `docs/technical.md` — delete (was public) or move under `docs/internal/` unlinked
- ADR sidebar entries — removed from `config.ts`

## 8. Design Tokens

**Preserved:** all existing `--lp-*` and `--vp-c-brand-*` tokens, Manrope/Instrument Serif, light+dark modes.

**Added:**
```css
--lp-hero-grad         /* subtle mesh, not flat */
--lp-card-bg
--lp-card-border
--lp-card-hover
--lp-scroll-step-active
--lp-scroll-step-dim
--lp-shadow-screenshot
--lp-radius-lg: 16px
--lp-space-1..8: 4/8/12/16/24/40/64/96 (px)
--lp-ease: cubic-bezier(.22,.61,.36,1)
--lp-dur-fast: 180ms
--lp-dur-med: 360ms
```

**Type scale bumps:**
- Hero h1: `clamp(2.5rem, 5vw, 4.5rem)`
- Section h2: `clamp(1.75rem, 3vw, 2.75rem)`
- Display serif: hero + section headings only, never body

## 9. Components

| Component | Props | Used on |
|---|---|---|
| `Hero.vue` | headline, sub, ctaPrimary, ctaSecondary, screenshot, trustItems[] | `/` |
| `ProductWalkthrough.vue` | steps[] (copy, screenshot) | `/` |
| `FeatureGrid.vue` | features[] (icon, title, oneLine, href) | `/`, `/features/` |
| `PrivacyStrip.vue` | bullets[] | `/` |
| `FAQ.vue` | items[] (q, a) | `/` |
| `CTABlock.vue` | title, sub, installCmd | `/`, all feature pages |
| `feature.vue` (layout) | frontmatter-driven | `/features/<slug>` |

All registered in `theme/index.ts` for markdown usage.

`ProductWalkthrough.vue` scroll logic: IntersectionObserver on step elements → sets active index → sticky image `<img>` sources swap with CSS opacity crossfade. No scroll listener. No layout thrash.

## 10. Motion

**Budget (all transforms + opacity only):**
- Hero: fade-up on load, screenshot float 400ms (one-shot)
- Walkthrough: sticky crossfade 360ms between steps; copy active/dim transition 240ms; progress dots fill
- Feature cards: hover lift 2px + border glow 180ms
- FAQ: accordion expand 240ms ease-out
- CTA: gradient shift on hover

**Forbidden:** parallax, autoplay video, scroll-jacking, number counters, particles, typewriter.

**Reduced motion:** `prefers-reduced-motion: reduce` → all durations → 0ms. Sticky scroll still works, images snap-swap.

## 11. Screenshot Pipeline

**Seed script** — `backend/seed_demo.py`:
- Builds `libertas-demo.db` with realistic fake data
- 8 accounts: 2 Fidelity, 2 Schwab, 1 Coinbase, 2 Chase, 1 Vanguard
- ~40 holdings across equity/crypto/cash
- 6 months price history (synthetic but plausible curves)
- 2 real estate entries with overrides
- Separate DB file — never touches `/data/libertas.db`

**Launch flag:** `./start.sh --demo` → backend uses `libertas-demo.db`.

**Capture checklist** (manual, executed during plan, not here):
- 1440×900 viewport, light + dark mode each
- 6 hero shots (one per page) + 2–3 supporting each
- Save: `docs/public/screenshots/<slug>.png`, `<slug>-dark.png`
- PNG, optimized via `oxipng` or equivalent

## 12. Performance Targets

- Lighthouse Performance ≥ 95 (static site, should be easy)
- LCP < 1.5s on 4G
- No CLS from screenshot swaps (reserve aspect ratio containers)
- All screenshots lazy except hero
- Total JS on landing < 80KB gzipped (VitePress baseline + one Vue component)

## 13. Accessibility

- All interactive components keyboard-reachable (FAQ accordion, feature cards, CTAs)
- Screenshots have descriptive alt text (not "screenshot")
- Sticky walkthrough: step copy remains semantic (headings + paragraphs), not visual-only
- Color contrast ≥ AA in both modes
- Respect `prefers-reduced-motion`

## 14. Out of scope / deferred

- Social proof section (gated on having real proof)
- Changelog / release notes on public site
- Email capture / mailing list
- Dark-mode screenshot pairs — included in v1 capture pass, but if time-constrained, light-only is acceptable
- A/B testing infra
- Analytics — deferred decision (likely privacy-friendly or none)

## 15. Open questions

None blocking. All resolved during brainstorm.

---

## Appendix A — Content to write during implementation

- 6 feature taglines (one line each)
- 18 feature copy paragraphs (3 per feature page: what / how / private-angle)
- 6 walkthrough step copy blocks (~40 words each)
- 5–6 FAQ entries
- Privacy page expanded content
- Download page content
