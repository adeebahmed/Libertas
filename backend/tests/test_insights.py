from datetime import date, timedelta
import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database import Base, get_db
from backend.models import Account, BalanceSnapshot, DebtDetail, Setting, Transaction
from backend.routers.insights import router as insights_router


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
    app.include_router(insights_router)

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


def _seed_account(db, name: str, type_: str) -> Account:
    account = Account(name=name, type=type_)
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


def _set_setting(db, key: str, value):
    row = db.query(Setting).get(key)
    payload = json.dumps(value)
    if row:
        row.value = payload
    else:
        db.add(Setting(key=key, value=payload))
    db.commit()


def test_insights_returns_15_rule_cards(client, db):
    brokerage = _seed_account(db, "Brokerage", "brokerage")
    checking = _seed_account(db, "Checking", "checking")
    credit = _seed_account(db, "Credit", "credit_card")

    today = date.today()
    db.add_all(
        [
            BalanceSnapshot(account_id=checking.id, date=today - timedelta(days=40), balance=6000),
            BalanceSnapshot(account_id=checking.id, date=today - timedelta(days=1), balance=7000),
            BalanceSnapshot(account_id=credit.id, date=today - timedelta(days=40), balance=9000),
            BalanceSnapshot(account_id=credit.id, date=today - timedelta(days=1), balance=8500),
            BalanceSnapshot(account_id=brokerage.id, date=today - timedelta(days=40), balance=50000),
            BalanceSnapshot(account_id=brokerage.id, date=today - timedelta(days=1), balance=56000),
            DebtDetail(account_id=credit.id, interest_rate=19.9, minimum_payment=420),
        ]
    )

    _set_setting(db, "monthly_expenses", 4000)
    _set_setting(db, "income_w2", 120000)
    _set_setting(db, "income_1099", 12000)
    _set_setting(db, "monthly_contribution", 1500)
    _set_setting(db, "risk_profile", "moderate")

    db.add_all(
        [
            Transaction(account_id=brokerage.id, date=today - timedelta(days=10), type="dividend", amount=120),
            Transaction(account_id=checking.id, date=today - timedelta(days=20), type="salary", amount=9000),
            Transaction(account_id=checking.id, date=today - timedelta(days=50), type="salary", amount=8700),
        ]
    )
    db.commit()

    payload = client.get("/api/insights").json()

    assert len(payload) == 15
    titles = {item["title"] for item in payload}
    assert "Concentration Risk" in titles
    assert "Liquidity Ratio (Emergency Fund)" in titles
    assert "Passive vs Earned Income" in titles


def test_insights_offline_no_external_dependencies(client, db):
    checking = _seed_account(db, "Checking", "checking")
    db.add(BalanceSnapshot(account_id=checking.id, date=date.today(), balance=5000))
    db.commit()

    payload = client.get("/api/insights").json()

    assert payload
    assert all("title" in insight and "action" in insight for insight in payload)
