from datetime import date

from backend.models import Account, Institution, Transaction
from backend.services.source_ingest import upsert_transaction


def test_source_precedence_plaid_beats_csv(db_session_factory):
    db = db_session_factory()
    try:
        inst = Institution(name="Test Bank")
        db.add(inst)
        db.flush()

        account = Account(name="Checking", type="checking", institution_id=inst.id)
        db.add(account)
        db.commit()

        csv_tx, created_csv, _ = upsert_transaction(
            db,
            account_id=account.id,
            tx_date=date(2026, 1, 10),
            tx_type="buy",
            symbol=None,
            quantity=None,
            price=None,
            amount=-42.10,
            description="Coffee Shop",
            source_kind="csv",
            source_record_id="row1",
            import_hash="hash-1",
            raw_row={"Date": "01/10/2026"},
        )
        assert created_csv is True
        db.commit()

        plaid_tx, created_plaid, merged = upsert_transaction(
            db,
            account_id=account.id,
            tx_date=date(2026, 1, 10),
            tx_type="buy",
            symbol=None,
            quantity=None,
            price=None,
            amount=-42.10,
            description="Coffee Shop",
            source_kind="plaid",
            source_record_id="txn_123",
            external_id="txn_123",
            raw_row={"transaction_id": "txn_123"},
        )
        db.commit()

        assert created_plaid is False
        assert merged is True
        assert plaid_tx.id == csv_tx.id
        assert plaid_tx.source_kind == "plaid"
        assert plaid_tx.external_id == "txn_123"
        assert plaid_tx.merge_conflict == 1

        assert db.query(Transaction).count() == 1
    finally:
        db.close()


def test_manual_does_not_override_csv(db_session_factory):
    db = db_session_factory()
    try:
        inst = Institution(name="Test Broker")
        db.add(inst)
        db.flush()

        account = Account(name="Brokerage", type="brokerage", institution_id=inst.id)
        db.add(account)
        db.commit()

        tx, _, _ = upsert_transaction(
            db,
            account_id=account.id,
            tx_date=date(2026, 1, 11),
            tx_type="sell",
            symbol="AAPL",
            quantity=1,
            price=180,
            amount=180,
            description="AAPL Sell",
            source_kind="csv",
            source_record_id="row-csv",
            import_hash="hash-csv",
            raw_row={"row": 1},
        )
        db.commit()

        manual_tx, _, merged = upsert_transaction(
            db,
            account_id=account.id,
            tx_date=date(2026, 1, 11),
            tx_type="other",
            symbol="AAPL",
            quantity=1,
            price=170,
            amount=180,
            description="AAPL Sell",
            source_kind="manual",
            raw_row=None,
        )
        db.commit()

        assert merged is False
        assert manual_tx.id == tx.id
        assert manual_tx.source_kind == "csv"
        assert manual_tx.price == 180
        assert db.query(Transaction).count() == 1
    finally:
        db.close()
