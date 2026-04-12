---
layout: home

hero:
  name: Libertas
  text: Your private financial command center
  tagline: See your full net worth, make better money decisions, and stay in control — without giving your financial life to a cloud app.
  actions:
    - theme: brand
      text: Run Libertas Locally
      link: https://github.com/adeebahmed/Libertas
    - theme: alt
      text: View Product Roadmap
      link: /technical

features:
  - icon: 🛡️
    title: Privacy You Can Verify
    details: No SaaS account. No institution credential sharing. Data stays on your machine in local SQLite.
  - icon: 🧭
    title: One Place For Everything
    details: Brokerage, crypto, cash, debt, and real estate in one view so your next move is obvious.
  - icon: ⚡
    title: Fast Updates, Low Friction
    details: Drag-and-drop import, watch-folder auto-ingest, and manual entry so you can keep data fresh your way.
  - icon: 🧠
    title: Guidance, Not Just Charts
    details: Debt, retirement, tax, and portfolio insights help you act — not just monitor.
---

## Why Libertas

Most money apps ask for your credentials and then sell convenience in exchange for trust.

Libertas flips that model:

- **You own your data path**: manual entry, local file import, and optional integrations by choice
- **You keep context together**: net worth, liabilities, goals, and account-level detail in one system
- **You get decision support**: actionable insights for debt payoff, retirement readiness, allocation risk, and tax opportunities

If you like tools like Copilot, Monarch, or Fey but want **local-first control**, this is the alternative.

## Built For People Who Want Control

- Investors who track across multiple brokerages and crypto wallets
- Households balancing debt payoff and long-term investing
- Privacy-conscious users who do not want permanent account-link access
- Builders/analysts who want transparent logic and local data ownership

## What’s Shipping In The Current Merge Cycle

These updates are focused on making Libertas more usable day-to-day, especially when your data is messy or incomplete:

- **Manual account workflows**: set balances, add manual transactions, and manage manual holdings directly from Accounts
- **Import quality signals**: see failed row counts, parse error samples, and potential transfer warnings after each import
- **Safer corrections**: rollback-aware import flows and backups make bad imports recoverable
- **Debt planning upgrades**: maintain APR, minimum payment, and payoff-date detail where debt decisions happen
- **Freshness visibility**: account-level staleness indicators help you know what needs updating before acting

## Core Product Areas

- **Dashboard**: net worth trend, allocation, account summary, and relevant financial news
- **Accounts**: holdings, transactions, manual entry flows, and debt detail management
- **Import**: CSV upload + watch-folder automation + rollback
- **Debt & Retirement**: payoff strategy modeling and retirement trajectory planning
- **Taxes & Insights**: estimate support, harvesting opportunities, and optional AI-assisted guidance
- **Settings & Backups**: profile controls, institution setup, checkpoints, and restore confidence

## Local-First, By Design

Libertas is designed around a simple promise: your financial operating system should run for you, not on you.

- Default mode is local and private
- Cloud dependence is not required for core value
- You can inspect the code, data model, and decisions any time

For architecture notes, ADRs, and implementation details, go to [Technical Docs](/technical).
