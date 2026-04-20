from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase
import os

_DEFAULT_DB = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "libertas.db")
DB_PATH = os.environ.get("LIBERTAS_DB", _DEFAULT_DB)
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})


@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    Base.metadata.create_all(bind=engine)
    _apply_sqlite_migrations()


def _apply_sqlite_migrations():
    """Best-effort lightweight migrations for existing local SQLite DBs."""
    with engine.begin() as conn:
        def col_names(table: str) -> set:
            rows = conn.exec_driver_sql(f"PRAGMA table_info({table})").fetchall()
            return {row[1] for row in rows}

        # real_estate: mortgage_rate (pre-existing migration)
        re_cols = col_names("real_estate")
        if "mortgage_rate" not in re_cols:
            conn.exec_driver_sql("ALTER TABLE real_estate ADD COLUMN mortgage_rate FLOAT")

        # accounts: Plaid extensibility columns
        ac_cols = col_names("accounts")
        if "external_id" not in ac_cols:
            conn.exec_driver_sql("ALTER TABLE accounts ADD COLUMN external_id TEXT")
        if "sync_source" not in ac_cols:
            conn.exec_driver_sql("ALTER TABLE accounts ADD COLUMN sync_source TEXT")
        if "source_kind" not in ac_cols:
            conn.exec_driver_sql("ALTER TABLE accounts ADD COLUMN source_kind TEXT")
        if "source_record_id" not in ac_cols:
            conn.exec_driver_sql("ALTER TABLE accounts ADD COLUMN source_record_id TEXT")
        if "source_priority" not in ac_cols:
            conn.exec_driver_sql("ALTER TABLE accounts ADD COLUMN source_priority INTEGER DEFAULT 0")
        if "provenance" not in ac_cols:
            conn.exec_driver_sql("ALTER TABLE accounts ADD COLUMN provenance JSON")
        if "merge_conflict" not in ac_cols:
            conn.exec_driver_sql("ALTER TABLE accounts ADD COLUMN merge_conflict INTEGER DEFAULT 0")

        # transactions: Plaid extensibility columns
        tx_cols = col_names("transactions")
        if "external_id" not in tx_cols:
            conn.exec_driver_sql("ALTER TABLE transactions ADD COLUMN external_id TEXT")
        if "sync_source" not in tx_cols:
            conn.exec_driver_sql("ALTER TABLE transactions ADD COLUMN sync_source TEXT")
        if "source_kind" not in tx_cols:
            conn.exec_driver_sql("ALTER TABLE transactions ADD COLUMN source_kind TEXT")
        if "source_record_id" not in tx_cols:
            conn.exec_driver_sql("ALTER TABLE transactions ADD COLUMN source_record_id TEXT")
        if "source_priority" not in tx_cols:
            conn.exec_driver_sql("ALTER TABLE transactions ADD COLUMN source_priority INTEGER DEFAULT 0")
        if "canonical_key" not in tx_cols:
            conn.exec_driver_sql("ALTER TABLE transactions ADD COLUMN canonical_key TEXT")
        if "provenance" not in tx_cols:
            conn.exec_driver_sql("ALTER TABLE transactions ADD COLUMN provenance JSON")
        if "merge_conflict" not in tx_cols:
            conn.exec_driver_sql("ALTER TABLE transactions ADD COLUMN merge_conflict INTEGER DEFAULT 0")

        # holdings: manual vs csv source flag
        ho_cols = col_names("holdings")
        if "source" not in ho_cols:
            conn.exec_driver_sql("ALTER TABLE holdings ADD COLUMN source TEXT DEFAULT 'csv'")

        # import_log: per-row error tracking + transfer pair count
        il_cols = col_names("import_log")
        if "rows_failed" not in il_cols:
            conn.exec_driver_sql("ALTER TABLE import_log ADD COLUMN rows_failed INTEGER DEFAULT 0")
        if "parse_errors" not in il_cols:
            conn.exec_driver_sql("ALTER TABLE import_log ADD COLUMN parse_errors TEXT")
        if "potential_transfers" not in il_cols:
            conn.exec_driver_sql("ALTER TABLE import_log ADD COLUMN potential_transfers INTEGER DEFAULT 0")
        if "header_drift" not in il_cols:
            conn.exec_driver_sql("ALTER TABLE import_log ADD COLUMN header_drift JSON")
        if "header_drift_detected" not in il_cols:
            conn.exec_driver_sql("ALTER TABLE import_log ADD COLUMN header_drift_detected INTEGER DEFAULT 0")
        if "header_drift_added" not in il_cols:
            conn.exec_driver_sql("ALTER TABLE import_log ADD COLUMN header_drift_added JSON")
        if "header_drift_removed" not in il_cols:
            conn.exec_driver_sql("ALTER TABLE import_log ADD COLUMN header_drift_removed JSON")
        if "header_drift_order_changed" not in il_cols:
            conn.exec_driver_sql("ALTER TABLE import_log ADD COLUMN header_drift_order_changed INTEGER DEFAULT 0")

        # debt_details: user-entered payoff target date
        dd_cols = col_names("debt_details")
        if "payoff_date" not in dd_cols:
            conn.exec_driver_sql("ALTER TABLE debt_details ADD COLUMN payoff_date DATE")
