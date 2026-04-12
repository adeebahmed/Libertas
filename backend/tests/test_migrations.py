"""
Tests for NFR-4: Schema extensibility and Phase 1 migration columns.
"""
from pathlib import Path

from sqlalchemy import create_engine

from backend import database
from backend.models import Account, DebtDetail, Holding, ImportLog, Transaction


def _columns(engine, table: str) -> set:
    with engine.connect() as conn:
        rows = conn.exec_driver_sql(f"PRAGMA table_info({table})").fetchall()
    return {row[1] for row in rows}


def _create_legacy_tables(engine):
    stmts = [
        "CREATE TABLE accounts (id INTEGER PRIMARY KEY, name TEXT NOT NULL, type TEXT NOT NULL, institution_id INTEGER, currency TEXT, created_at DATETIME)",
        "CREATE TABLE transactions (id INTEGER PRIMARY KEY, account_id INTEGER NOT NULL, import_log_id INTEGER, date DATE NOT NULL, type TEXT NOT NULL, symbol TEXT, quantity REAL, price REAL, amount REAL, description TEXT, raw_row JSON, import_hash TEXT UNIQUE)",
        "CREATE TABLE holdings (id INTEGER PRIMARY KEY, account_id INTEGER NOT NULL, symbol TEXT NOT NULL, quantity REAL NOT NULL, cost_basis REAL, last_price REAL, last_updated DATETIME)",
        "CREATE TABLE import_log (id INTEGER PRIMARY KEY, filename TEXT NOT NULL, filepath TEXT, institution_name TEXT, account_id INTEGER, preset_used TEXT, rows_imported INTEGER DEFAULT 0, rows_skipped INTEGER DEFAULT 0, status TEXT DEFAULT 'success', error_message TEXT, created_at DATETIME)",
        "CREATE TABLE debt_details (id INTEGER PRIMARY KEY, account_id INTEGER NOT NULL UNIQUE, interest_rate REAL DEFAULT 0.0, minimum_payment REAL DEFAULT 0.0)",
        "CREATE TABLE real_estate (id INTEGER PRIMARY KEY, account_id INTEGER NOT NULL, address TEXT NOT NULL, purchase_price REAL, purchase_date DATE, zillow_estimate REAL, manual_override REAL, mortgage_balance REAL, last_updated DATETIME)",
    ]
    with engine.begin() as conn:
        for s in stmts:
            conn.exec_driver_sql(s)


def test_orm_has_phase1_columns():
    assert {'external_id', 'sync_source'}.issubset(set(Account.__table__.columns.keys()))
    assert {'external_id', 'sync_source'}.issubset(set(Transaction.__table__.columns.keys()))
    assert 'source' in set(Holding.__table__.columns.keys())
    assert {'rows_failed', 'parse_errors', 'potential_transfers'}.issubset(set(ImportLog.__table__.columns.keys()))
    assert 'payoff_date' in set(DebtDetail.__table__.columns.keys())


def test_sqlite_migrations_are_idempotent(tmp_path, monkeypatch):
    db_path = Path(tmp_path) / 'legacy.db'
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    _create_legacy_tables(engine)

    monkeypatch.setattr(database, 'engine', engine)
    monkeypatch.setattr(database, 'DB_PATH', str(db_path))

    database._apply_sqlite_migrations()

    expected = {
        'accounts': {'external_id', 'sync_source'},
        'transactions': {'external_id', 'sync_source'},
        'holdings': {'source'},
        'import_log': {'rows_failed', 'parse_errors', 'potential_transfers'},
        'debt_details': {'payoff_date'},
        'real_estate': {'mortgage_rate'},
    }

    before = {}
    for t, cols in expected.items():
        got = _columns(engine, t)
        assert cols.issubset(got)
        before[t] = got

    database._apply_sqlite_migrations()

    after = {t: _columns(engine, t) for t in expected}
    assert before == after
