# Security & Privacy

Libertas is built on a single principle: **your financial data belongs to you and only you.**

This page documents exactly what that means in practice — what's encrypted, what leaves your machine (nothing by default), and how the optional integrations are designed to stay in your control.

---

## Threat model

Libertas is a local tool. The threats it guards against are:

| Threat | Mitigation |
|---|---|
| Physical access to your machine | AES-256-GCM encryption on all sensitive DB fields |
| Stolen or leaked database file | Encrypted fields unreadable without the derived key |
| Third-party data breach | No third party holds your data |
| Credential phishing | No bank OAuth — you import CSVs only |
| Unintended data exfiltration | Zero telemetry, zero analytics, no outbound calls by default |

What Libertas does **not** protect against: a fully compromised OS, malware with keylogger access, or an attacker who can already run code as your user. Those are OS-level threats outside any app's scope.

---

## At-rest encryption

All sensitive `TEXT` fields in SQLite are encrypted with **AES-256-GCM** before writing to disk.

- **Algorithm:** AES-256-GCM (authenticated encryption — detects tampering)
- **Key derivation:** PBKDF2-HMAC-SHA256 with a random 16-byte salt, 200,000 iterations
- **Key source:** A machine-local secret stored outside the database (`/data/libertas.key`)
- **Nonce:** 12-byte random nonce prepended to each ciphertext — unique per field per write
- **Scope:** Account names, institution names, notes, API keys stored in settings

Numeric fields (`balance`, `quantity`, `price`) are stored **plaintext** to allow SQL aggregations (SUM, GROUP BY) that power the dashboard. An attacker with raw DB access sees account totals but cannot read account names or API credentials.

### What's encrypted

| Field type | Encrypted |
|---|---|
| Account name | ✅ Yes |
| Institution name | ✅ Yes |
| API keys (Claude, Plaid, News) | ✅ Yes |
| Notes / descriptions | ✅ Yes |
| Account balance | ❌ No (required for SQL aggregation) |
| Transaction amounts | ❌ No (required for SQL aggregation) |
| Ticker symbols | ❌ No |

---

## Data residency

By default, **zero bytes of your financial data leave your machine.**

```
Your machine
├── SQLite database  (/data/libertas.db)  ← encrypted at rest
├── CSV imports      (/data/watch/)        ← processed locally, never uploaded
└── Encryption key   (/data/libertas.key) ← never transmitted
```

The backend binds to `127.0.0.1` only. It is not accessible from other machines on your network.

---

## Optional integrations

Every integration that touches an external network is **explicitly opt-in** and requires you to set an API key in Settings.

### Claude API (optional)

- Used for: AI chat, portfolio Q&A
- What's sent: your questions + a summary of your portfolio (account names + balances)
- What's NOT sent: raw transaction history, CSV files, or credentials
- You control this: disable by removing the Claude API key from Settings

### News API (optional)

- Used for: live market news headlines
- What's sent: HTTP request for news articles — no user data included
- Falls back to: public RSS feeds if no key is set

### Plaid (optional)

- Used for: direct bank connection (read-only balance + transaction sync)
- What's sent: OAuth flow via Plaid's hosted Link UI — Libertas never sees your bank credentials
- You control this: disable by removing the Plaid key from Settings

---

## No telemetry

Libertas contains **no analytics, no crash reporting, no usage tracking** of any kind. There is no "phone home" on startup, no event logging to a remote server, no A/B testing infrastructure.

If you run Libertas in airplane mode, it works identically to connected mode — except optional network integrations will be unavailable.

---

## Open source

All of this is verifiable. The full source code is on [GitHub](https://github.com/adeebahmed/Libertas). The encryption implementation is in `backend/services/encryption.py`. The ADR that documents the design decisions is [ADR-010](/adr/010-at-rest-encryption).

---

## Reporting issues

Found a security issue? Open a [GitHub issue](https://github.com/adeebahmed/Libertas/issues) or email the maintainer directly. There is no bug bounty program — this is a personal open-source project.
