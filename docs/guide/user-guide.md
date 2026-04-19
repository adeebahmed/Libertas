# User Guide (Happy Path)

This is the fastest path to getting useful results from Libertas.

## 1. Start Libertas

From the repo root:

```bash
./start.sh
```

Open the frontend dev URL printed by the script (`http://localhost:5173` or `http://localhost:5174`).

## 2. Pick your theme

Go to `Settings` → `Appearance`:

- `Onyx` for dark mode
- `Retro` for blue mode

## 3. Bring in your first data

Choose one of these:

- Upload in `Import` page (`CSV` or `Excel`)
- Drop files into `data/watch/` and let auto-ingest run
- Add/edit accounts manually in `Accounts`

After import, Libertas rebuilds holdings and snapshots automatically.

## 4. Review the Overview page

Use `/` (Overview) to verify:

- Net worth trend and recent delta
- Allocation chart
- Account cards and freshness indicators
- News panel

If values look stale, run `Settings` → `Refresh prices`.

## 5. Use core planning pages

- `Debt`: view payoff strategy options + what-if extra payments
- `Retirement`: evaluate projection and plan assumptions
- `Taxes`: estimate liability and review harvesting/entity guidance
- `Insights`: read deterministic insights and optional AI responses

## 6. Protect your data

In `Settings`:

- Create periodic backups
- Select encryption mode (`macOS Keychain` default, or passphrase)
- Keep your passphrase safe if passphrase mode is enabled

## 7. Roll back bad imports if needed

If an import looked wrong:

- Open `Import`
- Use rollback on the specific import log entry

Rollback removes transactions tied to that import and rebuilds holdings/snapshots.

## 8. Optional AI and integrations

You can use Libertas fully without any API keys.

For optional capabilities, continue to [API Keys & Integrations](/guide/api-keys-and-integrations).
