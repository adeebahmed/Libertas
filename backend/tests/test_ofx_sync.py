# backend/tests/test_ofx_sync.py
import pytest
from unittest.mock import patch, MagicMock
from datetime import date
import os

os.environ.setdefault("PYTEST_CURRENT_TEST", "1")

from backend.database import Base, engine, SessionLocal
from backend.models import IntegrationConnection, IntegrationRun, Account, Transaction, Institution


@pytest.fixture()
def db():
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


def _make_ofx_connection(db, account_id: int) -> IntegrationConnection:
    conn = IntegrationConnection(
        provider="ofx",
        name="Test Bank Checking",
        status="active",
        config_json={
            "url": "https://example.com/ofx",
            "fi_id": "9999",
            "org": "example.com",
            "account_number": "CHK001",
            "account_type": "CHECKING",
            "is_investment": False,
            "broker_id": None,
            "account_id": account_id,
            "keychain_service": "libertas-ofx-test",
        },
    )
    db.add(conn)
    db.commit()
    db.refresh(conn)
    return conn


def test_sync_creates_transactions(db):
    from backend.services.ofx_sync import sync_ofx_connection

    inst = Institution(name="Test Bank")
    db.add(inst)
    db.flush()
    acct = Account(name="Checking", type="checking", institution_id=inst.id)
    db.add(acct)
    db.flush()
    conn = _make_ofx_connection(db, acct.id)

    fake_txs = [
        {
            "fitid": "20240101001",
            "date": __import__("datetime").datetime(2024, 1, 1),
            "amount": -42.50,
            "description": "STARBUCKS",
            "trntype": "DEBIT",
            "memo": None,
        }
    ]

    with patch("backend.services.ofx_sync.keyring.get_password", return_value="secret"), \
         patch("backend.services.ofx_sync.fetch_ofx_statement", return_value=fake_txs):
        result = sync_ofx_connection(db, conn, trigger="manual")

    db.commit()
    tx = db.query(Transaction).filter(Transaction.account_id == acct.id).first()
    assert tx is not None
    assert tx.external_id == "20240101001"
    assert tx.source_kind == "ofx"
    assert tx.amount == -42.50
    assert result["imported"] == 1
    assert result["skipped"] == 0


def test_sync_deduplicates_by_fitid(db):
    from backend.services.ofx_sync import sync_ofx_connection

    inst = Institution(name="Test Bank 2")
    db.add(inst)
    db.flush()
    acct = Account(name="Checking2", type="checking", institution_id=inst.id)
    db.add(acct)
    db.flush()
    conn = _make_ofx_connection(db, acct.id)

    fake_txs = [
        {
            "fitid": "DUP001",
            "date": __import__("datetime").datetime(2024, 2, 1),
            "amount": -10.0,
            "description": "COFFEE",
            "trntype": "DEBIT",
            "memo": None,
        }
    ]

    with patch("backend.services.ofx_sync.keyring.get_password", return_value="secret"), \
         patch("backend.services.ofx_sync.fetch_ofx_statement", return_value=fake_txs):
        sync_ofx_connection(db, conn, trigger="manual")
        db.commit()
        result2 = sync_ofx_connection(db, conn, trigger="manual")
        db.commit()

    assert result2["imported"] == 0
    assert result2["skipped"] == 1


def test_sync_fails_gracefully_when_no_creds(db):
    from backend.services.ofx_sync import sync_ofx_connection

    inst = Institution(name="Test Bank 3")
    db.add(inst)
    db.flush()
    acct = Account(name="Checking3", type="checking", institution_id=inst.id)
    db.add(acct)
    db.flush()
    conn = _make_ofx_connection(db, acct.id)

    with patch("backend.services.ofx_sync.keyring.get_password", return_value=None):
        result = sync_ofx_connection(db, conn, trigger="manual")
        db.commit()

    assert result["status"] == "error"
    assert "credentials" in result["error"].lower()
    run = db.query(IntegrationRun).filter(IntegrationRun.connection_id == conn.id).first()
    assert run.status == "error"
