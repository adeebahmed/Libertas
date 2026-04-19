# Libertas 🗽

> **Your finances, on your machine.** No subscriptions. No account linking. No cloud. Ever.

Libertas is a self-hosted personal finance dashboard built for people who want the power of tools like Copilot Money or Fey — without handing your financial information to a company.

**Import a CSV. See your net worth. That's it.**

---

<p align="center">
  <img src="docs/public/screenshots/overview-onyx.png" width="48%" alt="Onyx theme" />
  &nbsp;
  <img src="docs/public/screenshots/overview-retro.png" width="48%" alt="Retro theme" />
</p>
<p align="center"><em>✦ Onyx (left) · Retro (right) — both include the live ticker -> news -> signal tape on collapsed Overview ✦</em></p>

---

## ✨ What you get

- 📊 **Net worth dashboard** — history, range controls, 30-day delta, account drill-in
- 📰 **Live market tape** — collapsed Overview cycles ticker -> related headline -> position signal
- 🏦 **Full account coverage** — brokerages, banks, crypto, real estate, debt, retirement
- 🧠 **Insights engine** — 15 deterministic rules, runs 100% offline, no AI required
- 🔥 **Retirement planner** — 5 FIRE types, projections, contribution tracking
- 🧮 **Tax estimates + debt payoff** — built-in calculators
- 🔐 **At-rest encryption** — AES-256-GCM on all sensitive fields in SQLite
- ⌨️ **Keyboard-driven** — `/` command palette, chord nav (`g d` dashboard, `g a` accounts, `g r` real estate, `g s` settings)
- 🎨 **Two themes** — Onyx (terminal black + amber) and Retro (deep navy + blue glow)
- 🤖 **Optional AI chat** — Claude API key unlocks portfolio Q&A and guided insights
- 🔗 **Optional sync** — Plaid and Google Sheets CSV feeds, fully opt-in

---

## 🔒 Privacy is the product

Most finance apps are built around your data leaving your machine. Libertas is built around the opposite.

| What others do | What Libertas does |
|---|---|
| OAuth into your bank | You import a CSV — no credentials, ever |
| Store your data in the cloud | Everything lives in a local SQLite file |
| Sell or train on your transactions | Data never leaves `localhost` |
| Require a subscription to access your own data | Open source, self-hosted, yours to keep |

**At-rest encryption** (AES-256-GCM) protects account names, balances, and all sensitive fields in the local database — even if someone gets physical access to your machine.

All optional integrations (Claude API, Plaid, News API) are explicitly opt-in. Nothing is enabled by default. No telemetry. No analytics. No crash reporting home.

---

## 🚀 Get running in 60 seconds

**You need:** Python 3.11+, [`uv`](https://github.com/astral-sh/uv), [`bun`](https://bun.sh)

```bash
git clone https://github.com/adeebahmed/Libertas.git
cd Libertas
./start.sh
```

Open **http://127.0.0.1:5173** — import a CSV or add an account manually and you're in.

---

## 📥 Importing data

Drop a CSV from any of these into the Import page — Libertas auto-detects the format:

**Fidelity · Schwab · Robinhood · Coinbase · Chase · Vanguard**

Or drag any CSV and map columns once. Subsequent imports use saved mappings.

Prefer hands-off? Drop files into `/data/watch/` and the watcher picks them up automatically.

---

## 🔑 Optional API keys

Set everything in **Settings** inside the app — stored locally in SQLite, never sent anywhere.

| Key | What it unlocks |
|-----|----------------|
| Claude API | 🤖 AI insights chat, guided portfolio analysis |
| News API | 📰 Live market news (falls back to RSS without it) |
| Plaid | 🏦 Optional direct bank sync |

---

## 🛠 Stack

FastAPI + SQLAlchemy + SQLite · React 18 + TypeScript + Vite · yfinance + CoinGecko · VitePress docs

---

## 📚 Docs

Full user guide, API key setup, and architecture decisions at the [GitHub Pages site](https://adeebahmed.github.io/Libertas/).

```bash
./start-docs.sh   # preview docs locally
```
