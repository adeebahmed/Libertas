---
title: Download
outline: false
aside: false
---

# Download Libertas

Install locally and start with one private financial view.

## Quickstart

```bash
git clone https://github.com/adeebahmed/Libertas
cd Libertas
./start.sh
```

## Requirements

- Python 3.11+
- Node 18+ (or Bun, if you use Bun for frontend commands)

## First run checklist

1. Start the app with `./start.sh`
2. Open the frontend URL shown in terminal
3. Import a CSV or add your first account manually
4. Review Dashboard, Accounts, and Insights

## Data location

- Primary DB: `data/libertas.db`
- Demo DB (optional): `data/libertas-demo.db`

## Backup model

Copy the `.db` file to create a portable backup, or use in-app backup endpoints/workflows.

## Run with demo dataset

```bash
./start.sh --demo
```

This starts against `data/libertas-demo.db` so your main data stays untouched.

[View on GitHub](https://github.com/adeebahmed/Libertas)
