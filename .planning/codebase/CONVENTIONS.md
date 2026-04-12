# Coding Conventions

**Analysis Date:** 2026-04-11

## Naming Patterns

**Files:**
- Python routers: `snake_case.py` (e.g., `accounts.py`, `snapshots.py`, `debt.py`)
- Python modules: `snake_case.py` (e.g., `ingest.py`, `analyzer.py`, `filename_parser.py`)
- React components: `PascalCase.tsx` (e.g., `Dashboard.tsx`, `Import.tsx`, `RealEstate.tsx`)
- Utility/hook files: `camelCase.ts` (e.g., `useApi.ts`, `client.ts`)
- Types file: `index.ts` in `types/` directory

**Functions (Python):**
- Public functions: `snake_case()` (e.g., `read_file()`, `ingest_file()`, `try_parse_date()`)
- Private functions: Leading underscore `_snake_case()` (e.g., `_read_csv()`, `_find_or_create_institution()`, `_take_snapshot()`)
- Handler functions use action verb prefix: `get_*()`, `post_*()`, `update_*()`, `delete_*()`, `record_*()`

**Functions (TypeScript/React):**
- React components: `PascalCase` exported as default or named export
- Hooks: Prefix with `use` (e.g., `useApi<T>()`)
- Helper functions: `camelCase()` (e.g., `resolveBase()`, `request<T>()`)
- Type constructors: `camelCase()` (e.g., `pct()`, `usd()`, `timeAgo()`)

**Variables:**
- Python constants: `UPPER_SNAKE_CASE` (e.g., `DATE_FORMATS`, `MONEY_PATTERN`, `DEBT_TYPES`)
- Python variables: `snake_case` (e.g., `db`, `filepath`, `column_map`, `account_id`)
- TypeScript constants: `UPPER_SNAKE_CASE` for immutable globals (e.g., `BASE`, `PIE_COLORS`)
- React state variables: `camelCase` with descriptive names (e.g., `accountsColHeight`, `newsLoading`, `uploading`)

**Types/Classes:**
- SQLAlchemy models: `PascalCase` (e.g., `Account`, `Institution`, `ImportLog`, `RealEstate`)
- Pydantic models: `PascalCase` (e.g., `AccountCreate`, `InstitutionUpdate`, `DebtDetailUpdate`)
- TypeScript interfaces: `PascalCase` (e.g., `Account`, `Holding`, `NewsArticle`, `NetWorth`)
- Type unions: `PascalCase` (e.g., `AccountType`)
- Enum-like class: `PascalCase` with constant string attributes (e.g., `ColumnRole` with `DATE`, `SYMBOL`, `QUANTITY`)

## Code Style

**Formatting:**
- Python: 4-space indentation (standard PEP 8)
- TypeScript: 2-space indentation
- Line length: Generally followed naturally; no explicit width enforcement visible
- Trailing commas in multi-line structures: Used consistently

**Linting:**
- Python: No explicit linter config visible; follows PEP 8 conventions
- TypeScript: No `.eslintrc` present; relies on TypeScript strict mode (`strict: true` in `tsconfig.json`)

**Imports Organization:**
```python
# Python pattern (from routers/accounts.py):
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from ..database import get_db
from ..models import Account, Institution, Holding, BalanceSnapshot, Transaction
```

```typescript
// TypeScript pattern (from pages/Dashboard.tsx):
import { useEffect, useMemo, useRef, useState } from 'react'
import { useApi } from '../hooks/useApi'
import { api } from '../api/client'
import type { NetWorth, BalanceSnapshot, Account, NewsArticle } from '../types'
import {
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell,
} from 'recharts'
```

**Path Aliases:**
- TypeScript: `@/*` maps to `src/` (defined in `tsconfig.json`)
- Used for cleaner imports: `import type { Account } from '@/types'`

## Error Handling

**Python Patterns:**
- HTTPException for REST API errors: `raise HTTPException(404, "Account not found")`
- Try-catch with `db.rollback()` for transaction safety (see `ingest.py` lines 379-386)
- Logging errors with context: `logger.exception(f"[{filename}] Ingest failed: {e}")`
- Graceful error recording: Failed imports saved as `ImportLog` with `status='error'` and error message

**TypeScript Patterns:**
- Error from async API calls: `catch ((e: any) => setError(e.message))`
- User feedback via alert: `alert(\`Error message: ${e.message}\`)`
- Null checks before state access: `if (!res.ok) { const body = await res.text(); throw new Error(...) }`

## Logging

**Framework:** Python standard `logging` module

**Patterns:**
```python
# From main.py and ingest.py:
logger = logging.getLogger(__name__)
logger.info(f"[{filename}] Detected columns: {column_map}")
logger.warning(f"File watcher disabled due to startup error: {e}")
logger.exception(f"[{filename}] Ingest failed: {e}")
```

- Contextual prefixes in brackets: `[{filename}]`, `[{model_name}]`
- Log level selection: `info` for state changes, `warning` for degradation, `exception` for errors with full traceback

## Comments

**When to Comment:**
- Module-level docstrings explain purpose (see `importers/ingest.py` lines 1-11, `importers/analyzer.py` lines 1-4)
- Function docstrings for complex logic or public API (e.g., `_take_snapshot()` and `get_account_performance()` have docstrings)
- Inline comments rare; code is self-documenting
- Section comments using `# ---` pattern separate logical blocks (e.g., `# --- Institutions ---`, `# --- Accounts ---`)

**JSDoc/TSDoc:**
- TypeScript: Minimal JSDoc; types provide documentation
- Python: Module docstrings and occasional function docstrings describing purpose
- No strict convention for parameter documentation visible

## Function Design

**Size:** 
- Small, single-purpose functions are preferred
- Utility parsers: 5-15 lines (e.g., `try_parse_date()`, `normalize_symbol()`)
- Endpoint handlers: 20-50 lines including boilerplate
- Complex logic broken into private helper functions (e.g., `_rebuild_holdings()`, `_get_debt_accounts()`)

**Parameters:**
- Python: Type hints required in newer code (all routers use them)
  ```python
  def get_account(account_id: int, db: Session = Depends(get_db)):
  ```
- TypeScript: Explicit types for all parameters
  ```typescript
  function useApi<T>(fetcher: () => Promise<T>, deps: unknown[] = []): { data, loading, error, refetch }
  ```

**Return Values:**
- Python: Implicit None or explicit return statement; Pydantic models auto-serialize to JSON
- TypeScript: Explicit return types on all functions
- Generic type parameters used for data fetching: `useApi<T>()`, `request<T>()`

## Module Design

**Exports:**

Python routers export single `router` instance:
```python
# from routers/accounts.py
from fastapi import APIRouter
router = APIRouter(prefix="/api/accounts", tags=["accounts"])
@router.get("/institutions")
def list_institutions(db: Session = Depends(get_db)):
    return db.query(Institution).all()
```

TypeScript exports default function or named exports:
```typescript
// Named export hook
export function useApi<T>(fetcher: () => Promise<T>, deps: unknown[] = []) {
  // ...
}

// Default export component
export default function Dashboard() {
  // ...
}
```

**Barrel Files:**
- Partial barrel pattern: `routers/__init__.py` imports submodules:
  ```python
  from . import accounts, imports, prices, real_estate, ...
  ```
- Frontend components accessed directly: `src/pages/Dashboard.tsx` (no barrel file)
- Types barrel: `src/types/index.ts` exports all interfaces

## Database Query Patterns

**Session Management:**
```python
# Dependency injection in routers
def some_handler(db: Session = Depends(get_db)):
    db.query(Model).filter(...).all()
    db.add(instance)
    db.commit()
    db.refresh(instance)
```

**Query Style:**
- SQLAlchemy ORM preferred over raw SQL
- Eager loading where needed; relationships defined in models
- Filters chained: `db.query(Model).filter(col1==val1, col2==val2).first()`
- Transactions: Explicit `db.add()`, `db.flush()`, `db.commit()`, with rollback on exception

## API Response Patterns

**FastAPI Endpoints:**
```python
@router.get("/path")
def handler_name(param: Type, db: Session = Depends(get_db)) -> ReturnType:
    """Optional docstring."""
    return {...}  # Auto-serialized to JSON
```

**Response Shapes:**
- List endpoints: return list directly (e.g., `return [...]`)
- Single object: return dict/model (auto-serialized)
- Errors: `raise HTTPException(status_code, detail)`
- Success messages: `{"ok": True}` or operation-specific dict

**TypeScript API Client:**
```typescript
export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) => request<T>(path, { method: 'POST', body: ... }),
  patch: <T>(path: string, body: unknown) => request<T>(path, { method: 'PATCH', body: ... }),
  upload: async <T>(path: string, formData: FormData) => { /* multipart */ },
}
```

## React Component Patterns

**State Management:**
- `useState<T>()` for local component state
- `useRef<T | null>()` for DOM references and mutable values
- `useMemo()` for expensive computations (e.g., determining if refresh needed)
- `useCallback()` for stable function references to prevent re-renders

**Data Fetching:**
- Custom `useApi<T>()` hook handles loading, error, refetch states
- Hook pattern: accepts fetcher function and dependency array
- Automatic retry/refetch via `refetch()` callback

**Styling:**
- Inline `style={}` objects with CSS variables (e.g., `color: 'var(--text)'`)
- CSS variables defined globally (not visible in source, set via stylesheet)
- Tailwind-like utility classes where appropriate (e.g., `className="btn btn-sm"`)

---

*Convention analysis: 2026-04-11*
