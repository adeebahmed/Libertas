# ADR-010 — At-Rest Encryption

**Status:** Accepted  
**Date:** 2026-04-19

## Context

Libertas stores sensitive financial data locally in a SQLite database. The file is unprotected by default — if a machine is compromised or the disk is imaged, all account names, transaction descriptions, holdings, and API keys are readable as plaintext.

The goal is to make the database unreadable without the user's key, while keeping the app fully functional and not requiring cloud infrastructure.

## Decision

Implement field-level AES-256-GCM encryption on all TEXT columns containing PII or financial data. Numeric columns (amounts, prices, balances) are left unencrypted — encrypting floats would break SQL aggregations that power dashboards and charts.

Two key storage modes are supported:

- **macOS Keychain (default):** A 32-byte random key is generated once and stored in the system Keychain. macOS protects it with the user's login or Touch ID. The app loads it automatically on startup — no user action required after initial setup.
- **Passphrase (maximum security):** The user provides a passphrase. Argon2id derives a 32-byte key from the passphrase + a stored salt. The key exists only in memory during the session. If lost, the data cannot be recovered.

## Encrypted columns

| Model | Columns |
|-------|---------|
| Institution | name, export_url, notes |
| Account | name, external_id |
| Holding | symbol |
| Transaction | symbol, description |
| RealEstate | address |
| Setting | value |

Columns intentionally left unencrypted: all Float/Integer columns (amount, price, quantity, balance, rate), dates, foreign keys, status fields, and JSON blobs containing only structural metadata.

## Implementation

A custom SQLAlchemy `TypeDecorator` (`EncryptedText`) wraps `Text`. On write it encrypts and prefixes with `enc1:`. On read it detects the prefix and decrypts. Rows written before encryption was enabled pass through unchanged, and are encrypted on their next write.

The active key is held in a module-level variable in memory. It is never written to disk (passphrase mode) or written in recoverable form (keychain mode stores only the key, not the passphrase).

## Consequences

- Database file is unreadable without the key — stolen disk yields no financial data
- No schema migration required — `EncryptedText` maps to `Text` at the SQLite level
- Passphrase mode: losing the passphrase = permanent data loss (by design)
- SQL `LIKE`, `ORDER BY`, and range queries on encrypted columns no longer work — acceptable since all filtering happens in Python after decryption
- Claude never touches the raw database — it receives only decrypted query results passed in the API call
