# Phase 1: Data Foundation - Research

**Researched:** 2026-04-11
**Domain:** FastAPI + SQLAlchemy + React 18 — data entry, CSV import hardening, schema extensibility
**Confidence:** HIGH (codebase directly inspected, all claims below are verified against source files)

---

## Summary

Phase 1 builds the data entry layer that lets users populate Libertas without CSV files. The backend
already has account CRUD, holdings read, and a CSV import pipeline — but it's missing the pieces that
make manual data entry first-class: no endpoint to set a manual balance snapshot, no endpoint to create
transactions by hand, no endpoint to create/edit holdings manually, and no staleness-indicator logic.

The CSV pipeline is partially hardened (SHA256 dedup, row-hash, header skip heuristic, rollback) but
is missing several requirements: it is hardcoded to `encoding="utf-8-sig"` with no fallback, it
surfaces only top-level errors to ImportLog (not per-row parse failures), it has no header-drift
detection (no stored raw headers), no transfer-pair detection, and no chardet/encoding auto-detection.

Schema extensibility for Plaid is not present: `Account` and `Transaction` lack `external_id` and
`sync_source` columns. These must be added via a lightweight migration in `database.py`.

The frontend Accounts page is read-only (no add/edit/delete from the page itself — accounts are only
created via Settings or auto-created by CSV import). No manual-entry modals exist anywhere. The
`AccountType` union in `frontend/src/types/index.ts` is missing `'real_estate'` and `'mortgage'`.

**Primary recommendation:** Build in two lanes — (1) backend CRUD gaps (balance set, transaction
create, holding create) and schema migrations, (2) CSV hardening (encoding, parse error surfacing,
header drift, transfer pair). Frontend adds manual-entry modals to the Accounts page and a staleness
indicator using the existing `last_updated` field returned by `GET /api/accounts`.

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| FR-1.1 | Manual account creation/editing, all account types including debt fields | `POST /api/accounts` exists; needs balance-set endpoint + debt fields on create; missing `real_estate` type in TS union |
| FR-1.1 | Manual transaction entry per account | No `POST /api/accounts/{id}/transactions` endpoint exists; must be added |
| FR-1.1 | Manual holdings entry for investment accounts | No `POST /api/accounts/{id}/holdings` endpoint exists; must be added |
| FR-1.2 | CSV idempotent deduplication (SHA256 hash) | Already implemented in `ingest.py:_compute_row_hash()` [VERIFIED] |
| FR-1.2 | Parse error surfacing (count + sample bad rows, never silent) | Not implemented — ingest catches top-level exception only, no per-row error tracking [VERIFIED] |
| FR-1.2 | Header drift detection | Not implemented — no stored raw headers in ImportLog or Institution [VERIFIED] |
| FR-1.2 | Encoding auto-detection | Not implemented — hardcoded `utf-8-sig` only [VERIFIED] |
| FR-1.2 | Junk-row skipping | Partially — finds first line with 2+ commas, but fragile [VERIFIED] |
| FR-1.2 | Transfer pair detection | Not implemented [VERIFIED] |
| FR-1.3 | Staleness indicators green/yellow/red | Not implemented — `last_updated` date is returned, logic must be added to frontend [VERIFIED] |
| FR-1.3 | Manual price override | RealEstate has `manual_override` field; Holding has `last_price` patchable via holdings endpoint (to be added) |
| NFR-4 | `external_id` + `sync_source` on Account and Transaction | Not present in `models.py` — must be added [VERIFIED] |
</phase_requirements>

---

## Project Constraints (from CLAUDE.md)

- **Backend:** Python 3.11+, FastAPI, SQLAlchemy, SQLite (`/data/libertas.db`)
- **Frontend:** Vite + React 18 + TypeScript + Recharts
- **Package manager:** `uv` (backend), Bun (frontend)
- **Dev start:** `./start.sh` — port 8000 (API) + port 5173 (Vite dev server)
- **ADR required:** Every new subsystem or non-trivial architectural decision must get an ADR in `docs/adr/`
- **Design bar:** Copilot Money reference. Modern, clean, non-generic.
- **CSV import:** Watch folder (`/data/watch/`), saved column mappings per institution
- **No direct institution API links** — CSV only for V1
- **Migrations:** Lightweight in `database.py:_apply_sqlite_migrations()` — check column existence before `ALTER TABLE`

---

## Standard Stack

### Core (already in project)
| Library | Version | Purpose | Status |
|---------|---------|---------|--------|
| FastAPI | 0.111.0 | REST API framework | In use [VERIFIED: requirements.txt] |
| SQLAlchemy | 2.0.30 | ORM, sync sessions | In use [VERIFIED: requirements.txt] |
| Pydantic v2 | bundled with FastAPI | Request/response validation, `model_dump(exclude_unset=True)` | In use [VERIFIED: accounts.py] |
| pandas | 2.2.2 | CSV/Excel parsing, used in ingest | In use [VERIFIED: requirements.txt] |
| openpyxl | 3.1.5 | Excel support | In use [VERIFIED: requirements.txt] |
| watchdog | 4.0.1 | File system monitor for /data/watch/ | In use [VERIFIED: requirements.txt] |
| React 18.3.1 | 18.3.1 | Frontend SPA | In use [VERIFIED: package.json] |
| TypeScript | 5.5.3 | Type safety | In use [VERIFIED: package.json] |
| Recharts | 2.12.7 | Charts | In use [VERIFIED: package.json] |

### New Dependencies Required

| Library | Version | Purpose | Why Needed |
|---------|---------|---------|------------|
| chardet | latest stable | Encoding auto-detection for CSV files | `_read_csv()` hardcoded to `utf-8-sig`; latin-1 bank exports will error |

**Installation:**
```bash
# Backend
uv pip install chardet
echo "chardet" >> backend/requirements.txt
```

**chardet not currently installed** — must be added as part of CSV hardening. [VERIFIED: chardet not in requirements.txt, not pip-installed]

---

## Architecture Patterns

### Existing Pattern: New API Endpoint
Add to an existing router file. Define Pydantic model for request body. Use `Depends(get_db)` for DB access. [VERIFIED: accounts.py pattern]

```python
# Source: backend/routers/accounts.py (existing pattern)
class TransactionCreate(BaseModel):
    date: str  # ISO format
    type: str
    amount: Optional[float] = None
    description: Optional[str] = None
    symbol: Optional[str] = None
    quantity: Optional[float] = None
    price: Optional[float] = None

@router.post("/{account_id}/transactions")
def create_transaction(account_id: int, data: TransactionCreate, db: Session = Depends(get_db)):
    # validate account exists, create Transaction with import_hash=None (manual)
    ...
```

### Existing Pattern: Lightweight Migration
Check column existence before ALTER. All migrations go in `_apply_sqlite_migrations()`. [VERIFIED: database.py]

```python
# Source: backend/database.py (existing pattern)
def _apply_sqlite_migrations():
    with engine.begin() as conn:
        columns = conn.exec_driver_sql("PRAGMA table_info(accounts)").fetchall()
        column_names = {row[1] for row in columns}
        if "external_id" not in column_names:
            conn.exec_driver_sql("ALTER TABLE accounts ADD COLUMN external_id TEXT")
        if "sync_source" not in column_names:
            conn.exec_driver_sql("ALTER TABLE accounts ADD COLUMN sync_source TEXT")
        # Same for transactions table
        columns_tx = conn.exec_driver_sql("PRAGMA table_info(transactions)").fetchall()
        col_names_tx = {row[1] for row in columns_tx}
        if "external_id" not in col_names_tx:
            conn.exec_driver_sql("ALTER TABLE transactions ADD COLUMN external_id TEXT")
        if "sync_source" not in col_names_tx:
            conn.exec_driver_sql("ALTER TABLE transactions ADD COLUMN sync_source TEXT")
```

### Existing Pattern: Balance Snapshot (manual set)
`BalanceSnapshot` table holds one row per (account_id, date). The accounts router already reads the
latest snapshot as the "balance" for cash accounts. A new `POST /api/accounts/{id}/balance` endpoint
should upsert today's snapshot with the user-supplied value. [VERIFIED: accounts.py lines 98-115]

```python
class BalanceSet(BaseModel):
    balance: float
    date: Optional[str] = None  # defaults to today

@router.post("/{account_id}/balance")
def set_manual_balance(account_id: int, data: BalanceSet, db: Session = Depends(get_db)):
    snap_date = date.fromisoformat(data.date) if data.date else date.today()
    existing = db.query(BalanceSnapshot).filter(
        BalanceSnapshot.account_id == account_id,
        BalanceSnapshot.date == snap_date
    ).first()
    if existing:
        existing.balance = data.balance
    else:
        db.add(BalanceSnapshot(account_id=account_id, date=snap_date, balance=data.balance))
    db.commit()
    return {"ok": True}
```

### Pattern: Staleness Indicator (frontend)
`GET /api/accounts` already returns `last_updated` as an ISO date string (or null). [VERIFIED: accounts.py line 125]
Staleness logic belongs in a shared utility function:

```typescript
// Source: derived from FR-1.3 requirement and existing last_updated field
function staleness(lastUpdated: string | null): 'green' | 'yellow' | 'red' | 'none' {
  if (!lastUpdated) return 'none'
  const days = Math.floor((Date.now() - new Date(lastUpdated).getTime()) / 86400000)
  if (days < 3) return 'green'
  if (days <= 7) return 'yellow'
  return 'red'
}
```

### Pattern: Per-Row Parse Error Tracking
Currently `ingest.py` only records top-level `error_message` on the ImportLog. To surface bad-row
count + sample rows, the import loop must track failures separately and store them in ImportLog.
`ImportLog.error_message` is `Text` — can store JSON. Add `rows_failed` integer column. [VERIFIED: models.py]

New migration:
```sql
ALTER TABLE import_log ADD COLUMN rows_failed INTEGER DEFAULT 0;
ALTER TABLE import_log ADD COLUMN parse_errors TEXT;  -- JSON array of sample bad rows
```

Ingest loop change — wrap per-row processing in try/except, accumulate failed rows:
```python
failed_rows = []
for row in rows:
    try:
        # ... existing extraction logic
    except Exception as row_err:
        failed_rows.append({"row": dict(row), "error": str(row_err)})

log.rows_failed = len(failed_rows)
if failed_rows:
    log.parse_errors = json.dumps(failed_rows[:10])  # store sample
```

### Pattern: Encoding Auto-Detection
Replace hardcoded `open(filepath, "r", encoding="utf-8-sig")` with chardet detection:

```python
# Source: derived from FR-1.2 requirement; chardet is the standard library for this [CITED: pypi.org/project/chardet]
import chardet

def _read_csv(filepath: str) -> tuple[list[str], list[dict]]:
    with open(filepath, "rb") as f:
        raw = f.read()
    detected = chardet.detect(raw)
    encoding = detected.get("encoding") or "utf-8"
    text = raw.decode(encoding, errors="replace")
    # ... rest of existing logic
```

### Pattern: Header Drift Detection
Store raw CSV headers in `Institution.column_mapping` (already JSON). On re-import, compare stored
headers against current file headers. Surface a warning (not a blocker) in ImportLog.

```python
# In ingest_file(), after detecting column_map:
stored_mapping = institution.column_mapping or {}
stored_headers = stored_mapping.get("_raw_headers", [])
if stored_headers and set(stored_headers) != set(headers):
    drift_warning = f"Header drift detected: expected {stored_headers}, got {headers}"
    log.error_message = drift_warning  # stored as warning, not blocking
# Save headers for future comparison
if not stored_headers:
    institution.column_mapping = {**(stored_mapping), "_raw_headers": list(headers)}
    db.flush()
```

### Pattern: Transfer Pair Detection
After ingesting all rows, scan for potential transfer pairs: same absolute amount, within 3 days,
opposite types (credit + debit), across different accounts. Surface count in ImportLog.

```python
# Source: [ASSUMED] standard heuristic from Actual Budget community
def _detect_transfer_pairs(account_id: int, imported_tx_ids: list[int], db: Session) -> int:
    """Return count of potential transfer pairs detected."""
    # Query newly imported transactions
    new_txns = db.query(Transaction).filter(Transaction.id.in_(imported_tx_ids)).all()
    # Query all other accounts' transactions in the same date range
    # Match: same abs(amount), within 3 days, opposite type
    # Return count — do NOT auto-merge (user decision)
    ...
```

The ImportLog response should include `potential_transfers: int` so the frontend can show a warning.

### Anti-Patterns to Avoid

- **Modifying `import_hash` computation:** The SHA256 includes the filename. Changing the formula breaks idempotency for existing records. Do not modify `_compute_row_hash()` — only add new capabilities around it. [VERIFIED: ingest.py:87]
- **Rebuilding holdings from manual transactions:** `_rebuild_holdings()` deletes ALL holdings then recreates from transactions. If a user manually adds a holding AND has CSV transactions for the same account, the rebuild will overwrite manual holdings. Manual holdings should be flagged with `source="manual"` and preserved during rebuild.
- **Blocking imports on header drift:** Header drift should warn, not block. Many institutions add or rename columns between export versions.
- **Using `datetime.utcnow()`:** CONCERNS.md flags this as debt. New code must use `datetime.now(timezone.utc)`. [VERIFIED: CONCERNS.md]

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Encoding detection | Manual byte sniffing | `chardet` | Handles 40+ encodings including latin-1, cp1252, UTF-16 |
| CSV dialect detection | Custom comma/semicolon logic | `csv.Sniffer` (stdlib) | Handles delimiter, quotechar variants automatically |
| Per-row try/except error accumulation | Custom error log table | Add `rows_failed` + `parse_errors` JSON to existing ImportLog | No new table needed; existing model handles it |
| Staleness color logic | Custom component | Single `staleness()` utility function | Used in 3+ places (account list, account detail, dashboard) |
| Plaid schema fields | Complex migration system | Lightweight `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` | Already the project pattern in `database.py` |

---

## Common Pitfalls

### Pitfall 1: Holdings Rebuild Wipes Manual Entries
**What goes wrong:** `_rebuild_holdings()` calls `db.query(Holding).filter(...).delete()` then recreates from transactions. If the planner adds `POST /api/accounts/{id}/holdings` (manual holding creation), those holdings will be deleted on the next CSV import for the same account.
**Why it happens:** Rebuild assumes all holdings come from transactions. [VERIFIED: ingest.py lines 125-158]
**How to avoid:** Add a `source` column to `Holding` (`"csv"` | `"manual"`). Preserve `source="manual"` holdings during rebuild (filter delete to `source != "manual"`).
**Warning signs:** User adds a manual holding, then imports a CSV, holding disappears.

### Pitfall 2: SHA256 Hash Includes Filename
**What goes wrong:** The dedup hash is `SHA256(row_content + "|" + filename)`. If the same file is renamed and re-imported, all rows will be treated as new. If the file is uploaded via the UI (which uses a temp file path), the hash includes the temp filename prefix, which changes on each upload.
**Why it happens:** `_compute_row_hash` uses `os.path.basename(filepath)`. [VERIFIED: ingest.py:87-89]
**How to avoid:** For the hardening work, consider whether the hash should include original filename or be purely content-based. The current behavior is intentional (allows re-importing from different filenames as a feature) but may surprise users.
**Warning signs:** Re-importing the same CSV by drag-drop imports duplicates if the temp filename varies.

### Pitfall 3: Cash Account Balance Logic Gap
**What goes wrong:** `GET /api/accounts` uses `last_snap.balance` for cash accounts. If a user manually sets a balance via the new endpoint and then imports a CSV that produces a new snapshot with $0, the manual balance is lost.
**Why it happens:** `_take_snapshot()` writes a snapshot for today, overwriting any existing one. [VERIFIED: ingest.py lines 189-197]
**How to avoid:** The manual balance set endpoint should write a snapshot with a distinct `source` flag, OR the snapshot logic should not overwrite a user-set balance within the same day.

### Pitfall 4: No `real_estate` in Frontend AccountType Union
**What goes wrong:** TypeScript `AccountType` is missing `'real_estate'` and `'mortgage'`. If the backend returns an account of type `real_estate`, TypeScript will raise a type error.
**Why it happens:** The frontend type was written before the real estate account type was added. [VERIFIED: types/index.ts lines 27-38]
**How to avoid:** Add `'real_estate'` and `'mortgage'` to the `AccountType` union in `frontend/src/types/index.ts`.

### Pitfall 5: `_rebuild_holdings()` Called After Every Manual Transaction
**What goes wrong:** If the new `POST /api/accounts/{id}/transactions` endpoint calls `_rebuild_holdings()` after each transaction (as the CSV importer does), it is correct but expensive for bulk manual entry.
**Why it happens:** [ASSUMED] The natural implementation mirrors the CSV importer.
**How to avoid:** For manual single-transaction entry, an incremental holding update is sufficient. Only call full rebuild when needed (CSV import or explicit reconcile).

### Pitfall 6: `encoding="utf-8-sig"` Silently Corrupts Latin-1 Files
**What goes wrong:** Bank exports (especially older Chase, Navient) may export latin-1 encoded CSVs. The current `open(..., encoding="utf-8-sig")` will raise `UnicodeDecodeError` or silently corrupt characters with accents/special chars.
**Why it happens:** Hardcoded encoding in `_read_csv()`. [VERIFIED: ingest.py:39]
**How to avoid:** Use chardet to detect encoding before opening. Fall back to `latin-1` if chardet returns low confidence.

---

## Code Examples

### Current ImportLog model (for context of what to extend)
```python
# Source: backend/models.py (verified)
class ImportLog(Base):
    __tablename__ = "import_log"
    id = Column(Integer, primary_key=True)
    filename = Column(Text, nullable=False)
    filepath = Column(Text)
    institution_name = Column(Text)
    account_id = Column(Integer, ForeignKey("accounts.id"))
    preset_used = Column(Text)
    rows_imported = Column(Integer, default=0)
    rows_skipped = Column(Integer, default=0)
    status = Column(Text, default="success")  # success | error | skipped
    error_message = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
```
Missing: `rows_failed`, `parse_errors`, `potential_transfers`.

### Current Account model (for context of what to extend)
```python
# Source: backend/models.py (verified)
class Account(Base):
    __tablename__ = "accounts"
    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False)
    type = Column(Text, nullable=False)
    institution_id = Column(Integer, ForeignKey("institutions.id"))
    currency = Column(Text, default="USD")
    created_at = Column(DateTime, server_default=func.now())
```
Missing: `external_id`, `sync_source` (for future Plaid).

### Current Holding model (for context of what to extend)
```python
# Source: backend/models.py (verified)
class Holding(Base):
    __tablename__ = "holdings"
    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    symbol = Column(Text, nullable=False)
    quantity = Column(Float, nullable=False)
    cost_basis = Column(Float)
    last_price = Column(Float)
    last_updated = Column(DateTime)
```
Missing: `source` column to distinguish manual vs. CSV-derived holdings.

### Current dedup hash (do not change formula)
```python
# Source: backend/importers/ingest.py:86-89 (verified)
def _compute_row_hash(row: dict, filepath: str) -> str:
    raw = json.dumps(row, sort_keys=True, default=str) + "|" + os.path.basename(filepath)
    return hashlib.sha256(raw.encode()).hexdigest()
```

### Current DebtDetail model (already has interest_rate + minimum_payment)
```python
# Source: backend/models.py:122-130 (verified)
class DebtDetail(Base):
    __tablename__ = "debt_details"
    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), unique=True, nullable=False)
    interest_rate = Column(Float, default=0.0)
    minimum_payment = Column(Float, default=0.0)
```
FR-1.1 requires `payoff_date` on debt accounts — this field is missing from DebtDetail. Must be added.

---

## What Currently Exists vs. What Must Be Built

### Backend — EXISTS
| Feature | Location | Notes |
|---------|----------|-------|
| Account CRUD (create, read, update, delete) | `backend/routers/accounts.py` | Missing `external_id`/`sync_source` fields |
| Institution CRUD | `backend/routers/accounts.py` | Fully present |
| Transaction list per account | `GET /api/accounts/{id}/transactions` | Read-only |
| Holdings list per account | `GET /api/accounts/{id}` (embedded) | Read-only |
| CSV upload + ingest | `POST /api/imports/upload` | Hardening needed |
| CSV preview (headers + sample) | `POST /api/imports/preview` | Present |
| Import rollback | `POST /api/imports/{id}/rollback` | Present |
| Watchdog folder watcher | `backend/watchers/folder_watcher.py` | Fully functional |
| SHA256 dedup | `ingest.py:_compute_row_hash()` | Present |
| Holdings rebuild from transactions | `_rebuild_holdings()` | Present but will wipe manual holdings |
| Balance snapshot (auto from import) | `_take_snapshot()` | Present |
| Debt detail (interest rate, min payment) | `backend/routers/debt.py` + DebtDetail model | Missing `payoff_date` |
| Institution presets (filename-based) | `backend/importers/filename_parser.py` | Present |

### Backend — MISSING (must build)
| Feature | Where to Add | Complexity |
|---------|-------------|------------|
| `POST /api/accounts/{id}/balance` (manual balance set) | `accounts.py` | Low |
| `POST /api/accounts/{id}/transactions` (manual transaction create) | `accounts.py` | Low |
| `DELETE /api/accounts/{id}/transactions/{tx_id}` (delete manual transaction) | `accounts.py` | Low |
| `POST /api/accounts/{id}/holdings` (manual holding create) | `accounts.py` | Low |
| `PATCH /api/accounts/{id}/holdings/{holding_id}` (edit holding) | `accounts.py` | Low |
| `DELETE /api/accounts/{id}/holdings/{holding_id}` | `accounts.py` | Low |
| `external_id`, `sync_source` on Account + Transaction | `models.py` + `database.py` migration | Low |
| `source` column on Holding (manual vs. csv) | `models.py` + `database.py` migration | Low |
| `rows_failed`, `parse_errors`, `potential_transfers` on ImportLog | `models.py` + migration | Low |
| `payoff_date` on DebtDetail | `models.py` + migration | Low |
| Encoding auto-detection (chardet) | `importers/ingest.py:_read_csv()` | Low |
| Per-row parse error tracking | `importers/ingest.py:ingest_file()` | Medium |
| Header drift detection | `importers/ingest.py:ingest_file()` | Medium |
| Transfer pair detection | `importers/ingest.py` (post-import pass) | Medium |
| `_rebuild_holdings()` preserve manual source | `importers/ingest.py:_rebuild_holdings()` | Low |

### Frontend — EXISTS
| Feature | Location | Notes |
|---------|----------|-------|
| Account list (read-only table) | `Accounts.tsx` | No add/edit/delete |
| Account detail with holdings table | `Accounts.tsx` | Read-only |
| Import page (drag-drop, log, rollback) | `Import.tsx` | No preview/column-mapping UI |
| Account create form | `Settings.tsx` (partial) | Only name, type, institution_id |
| `last_updated` display | `Accounts.tsx` | No color indicator |
| TypeScript types | `types/index.ts` | Missing `real_estate`/`mortgage` AccountType |

### Frontend — MISSING (must build)
| Feature | Where to Add | Complexity |
|---------|-------------|------------|
| Add account modal (all fields including debt fields) | `Accounts.tsx` | Medium |
| Edit account modal | `Accounts.tsx` | Medium |
| Delete account (with confirmation) | `Accounts.tsx` | Low |
| Set manual balance modal | `Accounts.tsx` (account detail) | Low |
| Add manual transaction modal | `Accounts.tsx` (account detail) | Medium |
| Delete transaction (manual only) | `Accounts.tsx` (account detail) | Low |
| Add manual holding modal | `Accounts.tsx` (account detail, investment types only) | Medium |
| Edit/delete holding | `Accounts.tsx` (account detail) | Low |
| Staleness indicator (green/yellow/red dot) | `Accounts.tsx` | Low |
| `'real_estate'` + `'mortgage'` in AccountType | `types/index.ts` | Low |
| Debt fields in account create/edit (rate, min payment, payoff date) | `Accounts.tsx` | Medium |
| CSV import preview with column-mapping confirmation | `Import.tsx` | Medium |
| Parse error count + sample display in import result | `Import.tsx` | Low |
| Transfer pair warning in import result | `Import.tsx` | Low |

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Pydantic v1 `.dict()` | Pydantic v2 `.model_dump()` | Pydantic v2 (2023) | Already correct in codebase [VERIFIED] |
| `datetime.utcnow()` | `datetime.now(timezone.utc)` | Python 3.12 deprecation | Old pattern still in codebase; new code must use correct form |
| `db.query(Model).get(id)` | `db.get(Model, id)` | SQLAlchemy 2.0 | Old form still works but deprecated; new endpoints should use `db.get()` |

**Deprecated/outdated patterns in existing code:**
- `db.query(Institution).get(institution_id)` — SQLAlchemy 2.0 deprecated, use `db.get(Institution, institution_id)`. All new endpoints should use the new form. [VERIFIED: accounts.py line 64]

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Transfer pair heuristic: same abs(amount), within 3 days, opposite direction | Architecture Patterns | If wrong, false positives on large round-number transactions; low risk since it's a warning not auto-merge |
| A2 | Manual holdings should use `source="manual"` to survive rebuild | Pitfalls, Don't Hand-Roll | If wrong, alternative is a separate `manual_holdings` table; either works |
| A3 | `payoff_date` is a field on DebtDetail (not a computed property) | What Must Be Built | Could be computed from `months_to_payoff`; but FR-1.1 says "payoff date fields" implying user-entered |

---

## Open Questions (RESOLVED)

1. **Manual holding vs. manual transaction for investment accounts** — RESOLVED
   - Decision: Direct `Holding` insert with `source="manual"`. `_rebuild_holdings()` filters delete to `source != "manual"` only.
   - Reason: Simpler, no risk of accidental cost-basis recalculation from synthetic transactions.

2. **Debt account `payoff_date` field** — RESOLVED
   - Decision: User-entered target date (`Column(Date, nullable=True)`) on `DebtDetail`. The existing `_months_to_payoff()` provides the computed value separately.
   - Reason: User should be able to set their own target date independent of computed amortization.

3. **Preview + column-mapping UI for CSV import** — RESOLVED
   - Decision: Phase 1 shows preview result (headers, detected mapping, sample rows, count) as a confirmation step. Full drag-and-drop remap deferred to Phase 2.
   - Reason: The backend `POST /api/imports/preview` endpoint already exists; Phase 1 just surfaces it in the UI.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12 | Backend runtime | Assumed (per STACK.md) | 3.12 | — |
| uv | Backend package manager | Assumed (per start.sh) | — | pip |
| Bun | Frontend package manager | Assumed (per STACK.md) | — | npm |
| chardet | CSV encoding detection | NOT INSTALLED | — | Skip encoding hardening OR use `errors="replace"` as stopgap |
| SQLite | Database | Bundled with Python | — | — |

**Missing dependencies with no fallback:**
- `chardet`: Required for FR-1.2 encoding auto-detection. Must be `uv pip install chardet` + added to `requirements.txt`.

---

## Validation Architecture

No test infrastructure currently exists in the codebase. [VERIFIED: STRUCTURE.md notes "No test files present in codebase (untested currently)"]

### Recommended Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (standard Python; not yet installed) |
| Config file | `backend/pytest.ini` or `pyproject.toml` — Wave 0 creates this |
| Quick run command | `python -m pytest backend/tests/ -x -q` |
| Full suite command | `python -m pytest backend/tests/ -v` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FR-1.2 | Re-import same CSV produces 0 new rows | unit | `pytest backend/tests/test_ingest.py::test_idempotent_reimport -x` | No — Wave 0 |
| FR-1.2 | Latin-1 encoded CSV imports without error | unit | `pytest backend/tests/test_ingest.py::test_latin1_encoding -x` | No — Wave 0 |
| FR-1.2 | CSV with junk header rows correctly skips to data | unit | `pytest backend/tests/test_ingest.py::test_junk_header_skip -x` | No — Wave 0 |
| FR-1.2 | Per-row parse failures recorded in ImportLog | unit | `pytest backend/tests/test_ingest.py::test_parse_error_count -x` | No — Wave 0 |
| FR-1.2 | Header drift warning stored in ImportLog | unit | `pytest backend/tests/test_ingest.py::test_header_drift_detection -x` | No — Wave 0 |
| FR-1.1 | Manual balance set creates BalanceSnapshot | unit | `pytest backend/tests/test_accounts.py::test_manual_balance_set -x` | No — Wave 0 |
| FR-1.1 | Manual transaction creates Transaction with null import_hash | unit | `pytest backend/tests/test_accounts.py::test_manual_transaction_create -x` | No — Wave 0 |
| FR-1.1 | Manual holding survives CSV rebuild | unit | `pytest backend/tests/test_ingest.py::test_manual_holding_preserved -x` | No — Wave 0 |
| NFR-4 | Account.external_id and sync_source columns exist after migration | unit | `pytest backend/tests/test_migrations.py::test_plaid_columns_added -x` | No — Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest backend/tests/ -x -q` (fast, fail-fast)
- **Per wave merge:** `python -m pytest backend/tests/ -v`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `backend/tests/__init__.py` — marks tests as package
- [ ] `backend/tests/conftest.py` — in-memory SQLite fixture, test client
- [ ] `backend/tests/test_ingest.py` — covers FR-1.2 cases above
- [ ] `backend/tests/test_accounts.py` — covers FR-1.1 manual entry cases
- [ ] `backend/tests/test_migrations.py` — covers NFR-4
- [ ] Framework install: `uv pip install pytest pytest-asyncio httpx` + add to requirements

---

## Sources

### Primary (HIGH confidence — directly verified in codebase)
- `backend/models.py` — All ORM definitions inspected
- `backend/database.py` — Migration pattern confirmed
- `backend/routers/accounts.py` — All CRUD endpoints confirmed, gaps identified
- `backend/routers/debt.py` — DebtDetail model + endpoints confirmed
- `backend/routers/imports.py` — Upload + preview + rollback endpoints confirmed
- `backend/routers/snapshots.py` — Snapshot record + net worth confirmed
- `backend/importers/ingest.py` — Full ingest pipeline inspected
- `backend/importers/analyzer.py` — Column detection inspected
- `backend/importers/filename_parser.py` — Institution presets confirmed
- `backend/watchers/folder_watcher.py` — Watchdog implementation confirmed
- `frontend/src/types/index.ts` — TypeScript types inspected, gap found
- `frontend/src/pages/Accounts.tsx` — Read-only state confirmed
- `frontend/src/pages/Import.tsx` — Import UI confirmed (no preview step)
- `frontend/src/pages/Settings.tsx` — Account create form (limited) confirmed
- `backend/requirements.txt` — chardet absence confirmed

### Secondary (MEDIUM confidence)
- `.planning/codebase/CONCERNS.md` — Known bugs and debt cross-referenced with source
- `.planning/codebase/ARCHITECTURE.md` — Data flow description verified against code

### Tertiary (LOW confidence)
- Transfer pair heuristic (3-day, same amount) — community pattern from Actual Budget; not verified against specific docs [ASSUMED]

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — verified against requirements.txt and package.json
- Architecture: HIGH — verified against source files directly
- Gaps/what-to-build: HIGH — absence confirmed in source; no endpoints found for manual entry
- CSV hardening scope: HIGH — hardcoded encoding found, no per-row error tracking found, no header drift logic found
- Schema extensibility: HIGH — external_id/sync_source absence confirmed in models.py
- Transfer pair detection pattern: LOW — heuristic is [ASSUMED], implementation approach is reasonable

**Research date:** 2026-04-11
**Valid until:** 2026-05-11 (stable stack, 30-day horizon)
