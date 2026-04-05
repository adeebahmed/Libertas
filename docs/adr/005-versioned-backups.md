# ADR-005: Versioned Backups and Rollback

**Date:** 2026-04-05
**Status:** Accepted

---

## Context

Users need confidence that importing bad data or making mistakes won't permanently corrupt their financial history. ADR-001 mentioned a simple JSON export; this ADR extends that to versioned, restorable checkpoints.

## Decision

### Backup Types
- **JSON export** — full data export (all tables) as a single JSON file
- **CSV export** — per-account transaction and holdings exports
- **Database checkpoints** — date-stamped `.db` snapshots stored locally (not in git)

### Checkpoint Triggers
- Manual: user clicks "Create checkpoint" in Settings
- Automatic: before every import (so imports are always reversible)

### Rollback
- Settings > Data & Backups shows a list of all checkpoints with date, label, and size
- "Restore" button on any checkpoint replaces the current `libertas.db` with that snapshot
- Current state is auto-checkpointed before rollback so the rollback itself is reversible

### Storage
- Checkpoints stored in `/data/backups/` (gitignored)
- `backups` table in DB tracks metadata (path, date, label, size)
- Old checkpoints beyond 30 days auto-pruned (configurable)

## Consequences

- New `backups` router in backend
- `/data/backups/` directory created on first run, added to `.gitignore`
- `backups` table added to DB
- Import flow always creates a checkpoint before committing
- Settings page gains "Data & Backups" section
