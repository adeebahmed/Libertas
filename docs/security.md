# Security & Encryption

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

All sensitive text fields in SQLite are encrypted with **AES-256-GCM** before writing to disk. Every field is encrypted individually with a unique random nonce, so identical values produce different ciphertext.

### What's encrypted

| Field type | Encrypted |
|---|---|
| Account names and external IDs | ✅ Yes |
| Institution names, URLs, and notes | ✅ Yes |
| Transaction descriptions and ticker symbols | ✅ Yes |
| Holdings symbols | ✅ Yes |
| Property addresses | ✅ Yes |
| API keys (Claude, Plaid, News) | ✅ Yes |
| Account balance | ❌ No (required for SQL aggregation) |
| Transaction amounts | ❌ No (required for SQL aggregation) |
| Prices and interest rates | ❌ No (required for SQL aggregation) |

Numeric fields are stored plaintext to allow SQL aggregations (SUM, GROUP BY) that power the dashboard. An attacker with raw DB access sees account totals but cannot read account names or API credentials.

### The encryption key

AES-256-GCM requires a 32-byte key. Where that key comes from depends on your security setting:

**macOS Keychain (default)**

A random 32-byte key is generated the first time you run Libertas. macOS stores it in your system Keychain — the same place Safari stores passwords. It's protected by your login password and unlocks automatically with Touch ID on supported hardware. The key is never written to the database or any file.

**Passphrase (maximum security)**

If you switch to passphrase mode in Settings → Data Security, Libertas derives the encryption key from your passphrase using **Argon2id** — the current gold standard for password-based key derivation. Argon2id is intentionally slow and memory-intensive, making brute-force attacks impractical.

A random salt is generated and stored in the database (not secret — it ensures the same passphrase produces a unique key per database). The derived key lives only in memory for the duration of the session.

::: warning
If you use passphrase mode and lose your passphrase, the data **cannot be recovered**. There is no backdoor, no recovery key, no support ticket that can help. This is a feature, not a limitation — it means no one else can access your data either.
:::

---

## When data is decrypted

Decryption happens in memory, on demand, when:

1. The app loads a page that reads from the database
2. You run a search or filter
3. Claude analyzes your data (see below)

Decrypted data is never written back to disk. It exists in RAM for the duration of the request, then is discarded.

---

## Data residency

By default, **zero bytes of your financial data leave your machine.**

```
Your machine
├── SQLite database  (/data/libertas.db)  ← encrypted at rest
├── CSV imports      (/data/watch/)        ← processed locally, never uploaded
└── Encryption key   (macOS Keychain)     ← never transmitted
```

The backend binds to `127.0.0.1` only. It is not accessible from other machines on your network.

---

## How Claude interacts with your data

When you use AI chat or ask for AI-powered insights, here's exactly what happens:

```
Your question
     ↓
Libertas queries the database
     ↓
SQLAlchemy decrypts matching rows in memory
     ↓
Decrypted results are formatted as context
     ↓
Context + your question → Claude API (HTTPS/TLS 1.3)
     ↓
Claude analyzes and responds
     ↓
Response displayed in app
```

**Claude never:**
- Touches the database file
- Receives encrypted ciphertext
- Stores or remembers your data between sessions
- Has access to your encryption key

**Claude only receives:**
- The specific rows needed to answer your question
- Your question and any context you explicitly provide

API calls to Claude are encrypted in transit with TLS 1.3. Anthropic's data retention policy applies — review it at [anthropic.com/privacy](https://anthropic.com/privacy) if this matters to your threat model.

---

## Changing your security mode

Go to **Settings → Data Security** to switch between modes. When you switch to macOS Keychain mode, the key is initialized immediately. When you switch to Passphrase mode, you set your passphrase there — existing data will be re-encrypted on the next write using your new key.

---

## Optional integrations

Every integration that touches an external network is **explicitly opt-in** and requires you to set an API key in Settings.

### News API (optional)

- Used for: live market news headlines
- What's sent: HTTP request for news articles — no user data included
- Falls back to: public RSS feeds if no key is set

### Plaid (optional)

- Used for: direct bank connection (read-only balance + transaction sync)
- What's sent: OAuth flow via Plaid's hosted Link UI — Libertas never sees your bank credentials
- Disable by removing the Plaid key from Settings

---

## No telemetry

Libertas contains **no analytics, no crash reporting, no usage tracking** of any kind. There is no "phone home" on startup, no event logging to a remote server, no A/B testing infrastructure.

If you run Libertas in airplane mode, it works identically to connected mode — except optional network integrations will be unavailable.

---

## Technical reference

- Cipher: AES-256-GCM (authenticated encryption — detects tampering)
- Key derivation (passphrase mode): Argon2id, 3 iterations, 64 MB memory, 4 threads, 32-byte output
- Keychain integration: Python `keyring` library → macOS Security framework
- Encrypted value format: `enc1:` prefix + base64(12-byte nonce + ciphertext + 16-byte GCM tag)
- Implementation: `backend/services/encryption.py`, `backend/models.py` (`EncryptedText` TypeDecorator)
- ADR: [ADR-010 — At-Rest Encryption](/adr/010-at-rest-encryption)

---

## Open source

All of this is verifiable. The full source code is on [GitHub](https://github.com/adeebahmed/Libertas). The encryption implementation is in `backend/services/encryption.py`.

---

## Reporting issues

Found a security issue? Open a [GitHub issue](https://github.com/adeebahmed/Libertas/issues) or email the maintainer directly. There is no bug bounty program — this is a personal open-source project.
