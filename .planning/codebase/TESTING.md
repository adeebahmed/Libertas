# Testing Patterns

**Analysis Date:** 2026-04-11

## Test Framework

**Status:** No test framework currently configured

**Discovery:**
- No `pytest.ini`, `jest.config.*`, `vitest.config.*` files present
- No `*.test.*` or `*.spec.*` files in `src/`, `backend/`, or `frontend/` directories
- No test dependencies in `package.json` (React, Vite only; no Jest, Vitest, Testing Library)
- No test runner scripts in `package.json` (only `dev`, `build`, `preview`)
- Backend `requirements.txt` has no pytest, unittest, or testing framework

**Assertion Library:** Not applicable (no tests configured)

**Run Commands:** Not available

## Test File Organization

**Recommended Structure (not yet implemented):**

For future test setup:

**Backend (Python):**
```
backend/
├── tests/
│   ├── __init__.py
│   ├── test_importers/
│   │   ├── test_ingest.py
│   │   ├── test_analyzer.py
│   │   └── test_filename_parser.py
│   ├── test_routers/
│   │   ├── test_accounts.py
│   │   ├── test_debt.py
│   │   ├── test_snapshots.py
│   │   └── test_*.py (one per router)
│   ├── test_models.py
│   ├── conftest.py (pytest fixtures)
│   └── fixtures/  (sample CSV/Excel files for testing)
```

**Frontend (TypeScript/React):**
```
frontend/src/
├── __tests__/
│   ├── pages/
│   │   ├── Dashboard.test.tsx
│   │   ├── Import.test.tsx
│   │   └── *.test.tsx
│   ├── hooks/
│   │   ├── useApi.test.ts
│   │   └── *.test.ts
│   ├── api/
│   │   └── client.test.ts
│   └── utils/  (if helpers extracted)
```

## Current Test Coverage

**Untested Areas:**

**Backend (Critical):**
- `routers/*.py` — All endpoint handlers (`list_accounts()`, `get_debts()`, `record_snapshots()`, etc.)
  - No validation of HTTP responses
  - No error case testing (invalid IDs, malformed data)
  - No database transaction rollback scenarios
- `importers/ingest.py` — Core data import pipeline
  - No CSV parsing edge cases (malformed headers, empty files, encoding issues)
  - No deduplication logic testing
  - No symbol normalization or transaction classification tests
- `importers/analyzer.py` — Column detection algorithm
  - No unit tests for `auto_detect_columns()` with various CSV formats
  - No date/number parsing edge case coverage
- `importers/filename_parser.py` — Institution/account type extraction
  - No tests for filename pattern matching

**Frontend (Critical):**
- React components: `Dashboard.tsx`, `Import.tsx`, `Accounts.tsx`, `Debt.tsx`, `Retirement.tsx`, `RealEstate.tsx`, `Insights.tsx`, `Settings.tsx`, `Taxes.tsx`
  - No rendering tests
  - No user interaction tests (clicks, form submissions)
  - No loading/error state tests
- `hooks/useApi.ts` — Custom hook for all data fetching
  - No error handling tests
  - No refetch behavior tests
- `api/client.ts` — HTTP client
  - No network error handling
  - No retry logic tests

## Manually Tested Workflows (No Automated Tests)

Based on recent commits and code inspection, these workflows appear to be tested manually:

1. **File Import (`feat: new-ux...` and `fix: strip HTML from news summaries`):**
   - CSV/Excel ingest from watch folder
   - Column auto-detection and mapping
   - Transaction deduplication
   - Import history logging

2. **News Feed (`Guarantee AI-first news cards...`):**
   - News fetch from external APIs (feedparser)
   - HTML stripping from summaries
   - Loading states and on-demand refresh

3. **Dashboard Views:**
   - Net worth aggregation
   - Portfolio growth charts (Recharts integration)
   - Account allocation pie chart
   - Balance snapshots

4. **Debt Payoff Calculations (`backend/routers/debt.py`):**
   - Months-to-payoff formula
   - Avalanche vs. snowball strategy comparison
   - Interest calculation

5. **UI Components (Recent commits show polish):**
   - Responsive layouts
   - Glass-morphism news cards
   - Navigation restructuring

## What Should Be Tested (Priority Order)

### High Priority (Business Logic)

**1. Import Pipeline (`backend/importers/ingest.py`):**
```python
# Example test structure (not yet implemented)
def test_ingest_file_happy_path():
    """Full CSV → DB flow with dedup and holding rebuild."""
    # Setup: Create test file with known data
    # Execute: ingest_file()
    # Assert: Transactions imported, holdings rebuilt, snapshot taken

def test_ingest_deduplicates_rows():
    """Same file imported twice should not duplicate."""
    # Run same CSV twice
    # Assert: Second import has rows_skipped > 0, no new transactions

def test_csv_parsing_handles_encodings():
    """UTF-8-sig, UTF-8, Latin-1 encoded files."""

def test_column_auto_detection_various_formats():
    """Fidelity, Schwab, Robinhood, Coinbase, Chase exports."""
```

**2. Net Worth Snapshots (`backend/routers/snapshots.py`):**
```python
def test_current_net_worth_aggregates_holdings():
    """Sum of all account holdings + real estate equity = net_worth."""

def test_net_worth_delta_calculation():
    """Delta = current - previous (from different date)."""

def test_real_estate_contribution():
    """Effective value (manual override if set, else Zillow) - mortgage = equity."""
```

**3. Debt Payoff Calculations (`backend/routers/debt.py`):**
```python
def test_months_to_payoff_formula():
    """Validates _months_to_payoff() across edge cases."""
    # Balance=0, rate=0, rate>0, payment too low, etc.

def test_avalanche_vs_snowball_strategies():
    """Payoff order and interest calculation."""

def test_extra_payment_impact():
    """Extra payment reduces both months and interest."""
```

### Medium Priority (API/Integration)

**4. Account Endpoints:**
```typescript
def test_list_accounts_returns_current_balances():
    """Latest snapshot or holding market value."""

def test_get_account_performance():
    """Snapshots ordered by date, gain_pct calculation."""

def test_institution_crud():
    """Create, read, update, delete institutions."""
```

**5. React Components (useApi hook dependency):**
```typescript
test('Dashboard renders net worth when data loads', () => {
  // Mock api.get
  // Render Dashboard
  // Wait for data
  // Assert: values displayed correctly
});

test('Import page handles file drop and upload', () => {
  // Render Import
  // Simulate file drop
  // Mock api.upload
  // Assert: result shown after upload
});

test('useApi hook handles loading and error states', () => {
  // Test hook with failing fetcher
  // Assert: loading=true, then error set
  // Assert: refetch() retries
});
```

## Testing Best Practices to Establish

**Backend (Python with pytest):**

1. **Fixtures for test data:**
   - Temporary SQLite DB per test
   - Sample CSV files with known data
   - Mock institutions and accounts
   ```python
   # conftest.py pattern
   @pytest.fixture
   def test_db():
       # Create in-memory SQLite, init schema
       yield db
       # Cleanup
   
   @pytest.fixture
   def sample_csv_file(tmp_path):
       # Create temp CSV with known structure
       return tmp_path / "test.csv"
   ```

2. **Database transaction isolation:**
   - Use `pytest-sqlalchemy` or rollback after each test
   - Ensures tests don't interfere with each other

3. **Mock external APIs:**
   - yfinance price fetches
   - CoinGecko API calls
   - Zillow scraping
   ```python
   @patch('backend.routers.prices.yfinance.download')
   def test_refresh_prices(mock_download):
       mock_download.return_value = pd.DataFrame({...})
   ```

4. **Parametrized tests for multiple formats:**
   ```python
   @pytest.mark.parametrize("csv_format,expected_type", [
       ("fidelity_format.csv", "brokerage"),
       ("coinbase_format.csv", "crypto"),
       ("chase_format.csv", "checking"),
   ])
   def test_institution_detection(csv_format, expected_type):
   ```

**Frontend (React Testing Library or Vitest):**

1. **Render component with mock API:**
   ```typescript
   import { render, screen, waitFor } from '@testing-library/react'
   import userEvent from '@testing-library/user-event'
   
   test('Dashboard displays accounts', async () => {
     jest.spyOn(api, 'get').mockResolvedValueOnce(mockAccounts)
     render(<Dashboard />)
     await waitFor(() => {
       expect(screen.getByText('Total net worth')).toBeInTheDocument()
     })
   })
   ```

2. **Test user interactions:**
   ```typescript
   test('Import dropzone accepts files', async () => {
     render(<Import />)
     const dropzone = screen.getByText('Drop a file here')
     
     const file = new File(['csv data'], 'test.csv', { type: 'text/csv' })
     await userEvent.upload(dropzone, file)
     
     await waitFor(() => {
       expect(screen.getByText(/rows imported/)).toBeInTheDocument()
     })
   })
   ```

3. **Hook testing (useApi):**
   ```typescript
   import { renderHook, act } from '@testing-library/react'
   
   test('useApi refetch retries on error', async () => {
     let callCount = 0
     const fetcher = jest.fn(async () => {
       callCount++
       if (callCount === 1) throw new Error('Network error')
       return { data: 'success' }
     })
     
     const { result } = renderHook(() => useApi(fetcher, []))
     expect(result.current.error).toBeDefined()
     
     act(() => { result.current.refetch() })
     await waitFor(() => {
       expect(result.current.data).toEqual({ data: 'success' })
     })
   })
   ```

## Code Coverage Gaps Summary

| Area | Coverage | Risk | Priority |
|------|----------|------|----------|
| Import pipeline | 0% | High — data loss, duplicates | 1 |
| Net worth calculation | 0% | High — financial accuracy | 1 |
| Debt payoff math | 0% | High — loan calculations | 1 |
| Account endpoints | 0% | Medium — REST API contract | 2 |
| React components | 0% | Medium — UI/UX | 2 |
| Price fetching | 0% | Medium — data freshness | 2 |
| Error handling | 0% | Medium — graceful failure | 2 |
| Chart rendering | 0% | Low — display only | 3 |

---

*Testing analysis: 2026-04-11*
