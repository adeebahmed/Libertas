# Libertas

> Your finances, on your machine. No subscriptions. No account linking. No cloud.

Libertas is a self-hosted personal finance dashboard built for people who want the power of tools like Copilot Money or Fey — without giving a company access to their bank accounts.

Import a CSV. See your net worth. Done.

---

<p align="center">
  <img src="docs/public/screenshots/overview-onyx.png" width="48%" alt="Onyx theme" />
  &nbsp;
  <img src="docs/public/screenshots/overview-retro.png" width="48%" alt="Retro theme" />
</p>
<p align="center"><em>Onyx (left) · Retro (right) — toggle anytime in Settings</em></p>

---

## What you get

- **Net worth dashboard** — history, range controls, 30-day delta, account drill-in
- **Full account coverage** — brokerages, banks, crypto, real estate, debt, retirement
- **Insights engine** — 15 deterministic rules, runs 100% offline, no AI required
- **Retirement planner** — 5 FIRE types, projections, contribution tracking
- **Tax estimates + debt payoff** — built-in calculators
- **At-rest encryption** — AES-256-GCM on all sensitive fields in SQLite
- **Keyboard-driven** — `/` opens command palette, `g d` / `g a` / `g r` / `g s` chord nav
- **Two themes** — Onyx (terminal black + amber) and Retro (deep navy + blue glow)
- **Optional AI chat** — Claude API key unlocks portfolio Q&A and guided insights
- **Optional sync** — Plaid and Google Sheets CSV feeds, fully opt-in

---

## Get running in 60 seconds

**You need:** Python 3.11+, [`uv`](https://github.com/astral-sh/uv), [`bun`](https://bun.sh)

```bash
git clone https://github.com/adeebahmed/Libertas.git
cd Libertas
./start.sh
```

Open **http://127.0.0.1:5173** — import a CSV or add an account manually and you're in.

---

## Importing data

Drop a CSV from any of these into the Import page — Libertas auto-detects the format:

**Fidelity · Schwab · Robinhood · Coinbase · Chase · Vanguard**

Or drag any CSV and map columns once. Subsequent imports use saved mappings.

Prefer hands-off? Drop files into `/data/watch/` and the watcher picks them up automatically.

---

## Optional API keys

Set everything in **Settings** inside the app — stored locally in SQLite, never sent anywhere.

| Key | What it unlocks |
|-----|----------------|
| Claude API | AI insights chat, guided portfolio analysis |
| News API | Live market news (falls back to RSS without it) |
| Plaid | Optional direct bank sync |

---

## Stack

FastAPI + SQLAlchemy + SQLite · React 18 + TypeScript + Vite · yfinance + CoinGecko · VitePress docs

---

## Docs

Full user guide, API key setup, and architecture decisions at the [GitHub Pages site](https://adeebahmed.github.io/Libertas/).

```bash
./start-docs.sh   # preview docs locally
```
