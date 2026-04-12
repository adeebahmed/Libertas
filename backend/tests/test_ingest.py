from __future__ import annotations

from datetime import datetime
from pathlib import Path

from backend.importers.ingest import ingest_file
from backend.models import Account, Holding, Institution, Transaction


FIXTURES = Path(__file__).parent / "fixtures"


def _write_text(path: Path, text: str, encoding: str = "utf-8") -> Path:
    path.write_bytes(text.encode(encoding))
    return path


def _ingest(db, path: Path):
    return ingest_file(str(path), db)


def test_ingest_is_idempotent_for_the_same_csv(db_session_factory):
    db = db_session_factory()
    try:
        path = FIXTURES / "chase_checking.csv"

        first = _ingest(db, path)
        second = _ingest(db, path)

        assert first.status == "success"
        assert second.status == "success"
        assert first.rows_imported == 5
        assert first.rows_skipped == 0
        assert second.rows_imported == 0
        assert second.rows_skipped == 5
        assert second.rows_failed == 0
        assert second.parse_errors == "0"

        assert db.query(Transaction).count() == 5
    finally:
        db.close()


def test_ingest_detects_and_decodes_latin1_csv(tmp_path, db_session_factory):
    db = db_session_factory()
    try:
        path = _write_text(
            tmp_path / "Marcus_Savings_2025.csv",
            "\n".join(
                [
                    "Account,Date,Description,Amount,Balance",
                    "Checking,01/02/2025,Café Groceries,-18.75,981.25",
                    "Checking,01/03/2025,Crème Brûlée Dinner,-34.10,947.15",
                ]
            )
            + "\n",
            encoding="latin-1",
        )

        log = _ingest(db, path)

        assert log.status == "success"
        assert log.rows_imported == 2

        descriptions = [tx.description for tx in db.query(Transaction).order_by(Transaction.date).all()]
        assert descriptions == ["Café Groceries", "Crème Brûlée Dinner"]
    finally:
        db.close()


def test_ingest_reports_header_drift(tmp_path, db_session_factory):
    db = db_session_factory()
    try:
        path = tmp_path / "Fidelity_Brokerage_2025.csv"
        _write_text(
            path,
            "\n".join(
                [
                    "Date,Symbol,Quantity,Price,Amount,Type,Description",
                    "01/05/2025,AAPL,1,150.00,-150.00,BUY,Initial buy",
                ]
            )
            + "\n",
        )
        first = _ingest(db, path)
        assert first.status == "success"

        _write_text(
            path,
            "\n".join(
                [
                    "Date,Symbol,Quantity,Price,Amount,Type,Description,Category",
                    "01/06/2025,AAPL,1,152.00,-152.00,BUY,More shares,Trade",
                ]
            )
            + "\n",
        )
        second = _ingest(db, path)

        assert second.status == "success"
        assert second.header_drift_detected is True
        assert second.header_drift["detected"] is True
        assert second.header_drift["added"] == ["Category"]
        assert second.header_drift["removed"] == []
        assert second.header_drift["current_headers"] == [
            "Date",
            "Symbol",
            "Quantity",
            "Price",
            "Amount",
            "Type",
            "Description",
            "Category",
        ]
    finally:
        db.close()


def test_ingest_populates_quality_fields(tmp_path, db_session_factory):
    db = db_session_factory()
    try:
        path = _write_text(
            tmp_path / "Chase_Checking_Activity_2025.csv",
            "\n".join(
                [
                    "Date,Description,Amount,Type,Balance",
                    "01/10/2025,Transfer out to savings,-500.00,TRANSFER OUT,4500.00",
                    "01/10/2025,Transfer in from brokerage,500.00,TRANSFER IN,5000.00",
                    "not-a-date,Bad date,-25.00,DEBIT,4950.00",
                ]
            )
            + "\n",
        )

        log = _ingest(db, path)

        assert log.status == "success"
        assert log.rows_imported == 3
        assert log.rows_failed == 1
        assert log.parse_errors == "1"
        assert log.potential_transfers == 1
    finally:
        db.close()


def test_ingest_preserves_manual_holdings_on_rebuild(tmp_path, db_session_factory):
    db = db_session_factory()
    try:
        institution = Institution(name="Fidelity")
        db.add(institution)
        db.flush()

        account = Account(name="Fidelity Brokerage", type="brokerage", institution_id=institution.id)
        db.add(account)
        db.flush()

        manual_holding = Holding(
            account_id=account.id,
            symbol="MANUAL",
            quantity=7,
            cost_basis=700.0,
            last_price=100.0,
            last_updated=datetime.utcnow(),
        )
        db.add(manual_holding)
        db.commit()

        path = _write_text(
            tmp_path / "Fidelity_Brokerage_2025.csv",
            "\n".join(
                [
                    "Date,Symbol,Quantity,Price,Amount,Type,Description",
                    "01/12/2025,AAPL,5,150.00,-750.00,BUY,Import buy",
                ]
            )
            + "\n",
        )

        log = _ingest(db, path)

        assert log.status == "success"

        holdings = db.query(Holding).filter(Holding.account_id == account.id).order_by(Holding.symbol).all()
        symbols = [holding.symbol for holding in holdings]
        assert symbols == ["AAPL", "MANUAL"]

        preserved = next(holding for holding in holdings if holding.symbol == "MANUAL")
        assert preserved.quantity == 7
        assert preserved.cost_basis == 700.0
        assert preserved.last_price == 100.0

        imported = next(holding for holding in holdings if holding.symbol == "AAPL")
        assert imported.quantity == 5
        assert imported.cost_basis == 750.0
    finally:
        db.close()
