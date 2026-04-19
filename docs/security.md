# Security & Encryption

Libertas stores everything locally. No data is sent to the cloud, no accounts are linked by default, and the database never leaves your machine — unless you explicitly upload a file or enable Plaid sync.

This page explains how your data is protected at rest, how encryption keys work, and exactly what Claude can and cannot see when you use the AI chat feature.

---

## What gets encrypted

All financial text data is encrypted before it's saved to the database. This includes:

- Account names and external IDs
- Institution names, URLs, and notes
- Transaction descriptions and ticker symbols
- Holdings symbols
- Property addresses
- Settings values (including API keys)

**Not encrypted:** numeric values like balances, amounts, prices, and interest rates. Encrypting numbers would break the charts and dashboards — and raw numbers without names or descriptions reveal very little on their own.

---

## How encryption works

Libertas uses **AES-256-GCM**, the same cipher used to protect classified government data and secure financial systems. Every field is encrypted individually with a unique random nonce, so identical values produce different ciphertext.

The database file itself is standard SQLite. If someone steals it, they see a file full of random-looking bytes for all text fields — nothing readable.

### The encryption key

AES-256-GCM requires a 32-byte key. Where that key comes from depends on your security setting:

**macOS Keychain (default)**

A random 32-byte key is generated the first time you run Libertas. macOS stores it in your system Keychain — the same place Safari stores passwords and Apple stores your iCloud credentials. It's protected by your login password and unlocks automatically with Touch ID on supported hardware.

When Libertas starts, it retrieves the key from Keychain and holds it in memory. No passphrase required, no extra steps. The key is never written to the database or to any file.

**Passphrase (maximum security)**

If you switch to passphrase mode in Settings → Data Security, Libertas derives the encryption key from your passphrase using **Argon2id** — the current gold standard for password-based key derivation. Argon2id is intentionally slow and memory-intensive, making brute-force attacks impractical.

A random salt is generated and stored in the database (the salt is not secret — it just ensures the same passphrase produces a unique key for your specific database). The derived key lives only in memory for the duration of the session.

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

## How Claude interacts with your data

When you use the AI chat or ask for AI-powered insights, here's exactly what happens:

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
- The specific rows needed to answer your question (e.g., last 3 months of transactions for a spending question)
- Your question
- Any context you explicitly provide

API calls to Claude are encrypted in transit with TLS 1.3. Anthropic's data retention policy applies to the content of API calls — review it at [anthropic.com/privacy](https://anthropic.com/privacy) if this matters to your threat model.

---

## Changing your security mode

Go to **Settings → Data Security** to switch between modes. When you switch to macOS Keychain mode, the key is initialized immediately. When you switch to Passphrase mode, you'll set your passphrase there — existing data will be re-encrypted on the next write using your new key.

---

## Technical reference

- Cipher: AES-256-GCM (authenticated encryption — detects tampering)  
- Key derivation (passphrase mode): Argon2id, 3 iterations, 64 MB memory, 4 threads, 32-byte output  
- Keychain integration: Python `keyring` library → macOS Security framework  
- Encrypted value format: `enc1:` prefix + base64(12-byte nonce + ciphertext + 16-byte GCM tag)  
- Implementation: `backend/services/encryption.py`, `backend/models.py` (`EncryptedText` TypeDecorator)  
- ADR: [ADR-010 — At-Rest Encryption](/adr/010-at-rest-encryption)
