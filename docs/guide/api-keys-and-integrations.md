# API Keys & Integrations

All integrations are optional. Libertas works locally without them.

## Claude API key (optional)

Where to set:

- `Settings` → `API Keys` → `Claude API key`
- Or environment variable `CLAUDE_API_KEY`

What it unlocks:

- `Insights` chat (`POST /api/insights/chat`)
- AI-assisted guidance features

Behavior without key:

- Rule-based insights and planning still work
- AI chat returns a not-configured message

## News API key (optional)

Where to set:

- `Settings` → `API Keys` → `News API key`
- Or environment variable `NEWS_API_KEY`

What it unlocks:

- richer market/news coverage

Behavior without key:

- dashboard news falls back to RSS/cached sources

## Plaid (optional)

Where to set:

- `Settings` → `API Keys` → Plaid `Client ID`, `Secret`, `Environment`

Relevant endpoints:

- `/api/integrations/plaid/create-link-token`
- `/api/integrations/plaid/exchange-public-token`
- `/api/integrations/plaid/sync-now`
- `/api/integrations/plaid/status`

Notes:

- Keep Plaid optional for users preferring CSV/manual-only workflows
- Use `sandbox` first while validating behavior

## Google Sheets CSV feeds (optional)

Libertas supports Sheets through CSV export URLs (no Google OAuth requirement).

Relevant endpoints:

- `/api/integrations/sheets/validate-feed`
- `/api/integrations/sheets/add-feed`
- `/api/integrations/sheets/sync-now`
- `/api/integrations/sheets/status`

## Security notes

- Keys stored via Settings are local to your machine (SQLite)
- At-rest encryption support is documented in [Security & Encryption](/security)
- For strongest control, use passphrase mode and store secrets in a local password manager
