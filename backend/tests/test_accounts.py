from datetime import date

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database import Base, get_db
from backend.models import Account, BalanceSnapshot, DebtDetail, ImportLog, Holding, Transaction
from backend.routers.accounts import router as accounts_router
from backend.routers.debt import router as debt_router


@pytest.fixture()
def session_factory():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)
    yield TestingSessionLocal
    engine.dispose()


@pytest.fixture()
def db(session_factory):
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def app(session_factory):
    app = FastAPI()
    app.include_router(accounts_router)
    app.include_router(debt_router)

    def override_get_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    return app


@pytest.fixture()
def client(app):
    with TestClient(app) as test_client:
        yield test_client


def _seed_account(db, name="Test Account", type_="checking"):
    account = Account(name=name, type=type_)
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


def test_manual_balance_snapshot_updates_current_balance(client, db, session_factory):
    account = _seed_account(db, name="Cash", type_="checking")

    resp = client.post(
        f"/api/accounts/{account.id}/balance",
        json={"balance": 1234.56, "date": "2026-04-11"},
    )

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["snapshot"]["balance"] == 1234.56
    assert payload["snapshot"]["date"] == "2026-04-11"

    verify = session_factory()
    try:
        snap = verify.query(BalanceSnapshot).filter(BalanceSnapshot.account_id == account.id).one()
        assert snap.balance == 1234.56
    finally:
        verify.close()

    account_payload = client.get(f"/api/accounts/{account.id}").json()
    assert account_payload["balance"] == 1234.56
    assert account_payload["last_updated"] == "2026-04-11"


def test_manual_transaction_create_and_delete_guard(client, db, session_factory):
    account = _seed_account(db, name="Brokerage", type_="brokerage")

    create_resp = client.post(
        f"/api/accounts/{account.id}/transactions",
        json={
            "date": "2026-04-11",
            "type": "Buy",
            "symbol": "aapl",
            "quantity": 2,
            "price": 150.0,
            "amount": 300.0,
            "description": "manual buy",
        },
    )

    assert create_resp.status_code == 200
    tx_payload = create_resp.json()
    assert tx_payload["symbol"] == "AAPL"
    assert tx_payload["import_log_id"] is None
    assert tx_payload["import_hash"] is None

    verify = session_factory()
    try:
        tx = verify.query(Transaction).filter(Transaction.id == tx_payload["id"]).one()
        assert tx.import_log_id is None
        assert tx.import_hash is None
    finally:
        verify.close()

    delete_resp = client.delete(f"/api/accounts/{account.id}/transactions/{tx_payload['id']}")
    assert delete_resp.status_code == 200

    verify = session_factory()
    try:
        assert verify.get(Transaction, tx_payload["id"]) is None
    finally:
        verify.close()

    import_log = ImportLog(filename="import.csv", account_id=account.id)
    db.add(import_log)
    db.commit()
    db.refresh(import_log)

    csv_tx = Transaction(
        account_id=account.id,
        import_log_id=import_log.id,
        import_hash="abc123",
        date=date(2026, 4, 11),
        type="buy",
        amount=300.0,
    )
    db.add(csv_tx)
    db.commit()
    db.refresh(csv_tx)

    guard_resp = client.delete(f"/api/accounts/{account.id}/transactions/{csv_tx.id}")
    assert guard_resp.status_code == 400
    assert "CSV transactions cannot be deleted" in guard_resp.json()["detail"]


def test_manual_holdings_crud(client, db, session_factory):
    account = _seed_account(db, name="Investments", type_="brokerage")

    create_resp = client.post(
        f"/api/accounts/{account.id}/holdings",
        json={
            "symbol": "msft",
            "quantity": 5,
            "cost_basis": 200.0,
            "last_price": 300.0,
        },
    )
    assert create_resp.status_code == 200
    holding_payload = create_resp.json()
    assert holding_payload["symbol"] == "MSFT"
    assert holding_payload["quantity"] == 5
    assert holding_payload["market_value"] == 1500.0

    account_payload = client.get(f"/api/accounts/{account.id}").json()
    assert account_payload["balance"] == 1500.0
    assert len(account_payload["holdings"]) == 1

    update_resp = client.patch(
        f"/api/accounts/{account.id}/holdings/{holding_payload['id']}",
        json={"quantity": 6, "last_price": 320.0},
    )
    assert update_resp.status_code == 200
    updated = update_resp.json()
    assert updated["quantity"] == 6
    assert updated["last_price"] == 320.0

    verify = session_factory()
    try:
        holding = verify.query(Holding).filter(Holding.id == holding_payload["id"]).one()
        assert holding.quantity == 6
        assert holding.last_price == 320.0
    finally:
        verify.close()

    delete_resp = client.delete(f"/api/accounts/{account.id}/holdings/{holding_payload['id']}")
    assert delete_resp.status_code == 200

    account_payload = client.get(f"/api/accounts/{account.id}").json()
    assert account_payload["holdings"] == []
    assert account_payload["balance"] == 0


def test_debt_patch_accepts_iso_payoff_date(client, db, session_factory):
    account = _seed_account(db, name="Credit Card", type_="credit_card")
    detail = DebtDetail(account_id=account.id, interest_rate=18.5, minimum_payment=100.0)
    db.add(detail)
    db.commit()
    db.refresh(detail)

    resp = client.patch(
        f"/api/debt/{account.id}",
        json={"payoff_date": "2026-05-01", "interest_rate": 17.25},
    )
    assert resp.status_code == 200
    assert resp.json()["payoff_date"] == "2026-05-01"

    verify = session_factory()
    try:
        updated = verify.query(DebtDetail).filter(DebtDetail.account_id == account.id).one()
        assert updated.interest_rate == 17.25
    finally:
        verify.close()
