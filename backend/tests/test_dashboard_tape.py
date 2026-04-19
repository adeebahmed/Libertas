from datetime import date, datetime, timedelta
import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database import Base, get_db
from backend.models import Account, BalanceSnapshot, DebtDetail, Holding, NewsCache, Setting
from backend.routers.dashboard import router as dashboard_router


@pytest.fixture()
def session_factory():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)
    yield testing_session_local
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
    app.include_router(dashboard_router)

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


def _set_setting(db, key: str, value):
    row = db.query(Setting).get(key)
    payload = json.dumps(value)
    if row:
        row.value = payload
    else:
        db.add(Setting(key=key, value=payload))
    db.commit()


def test_dashboard_tape_includes_all_segments_and_sequence(client, db):
    brokerage = Account(name="Core Brokerage", type="brokerage")
    checking = Account(name="Daily Checking", type="checking")
    credit = Account(name="Travel Credit", type="credit_card")
    db.add_all([brokerage, checking, credit])
    db.commit()
    db.refresh(brokerage)
    db.refresh(checking)
    db.refresh(credit)

    db.add_all(
        [
            Holding(account_id=brokerage.id, symbol="AAPL", quantity=12, last_price=200, cost_basis=1800),
            Holding(account_id=brokerage.id, symbol="MSFT", quantity=8, last_price=300, cost_basis=2200),
            BalanceSnapshot(account_id=checking.id, date=date.today() - timedelta(days=1), balance=12000),
            BalanceSnapshot(account_id=credit.id, date=date.today() - timedelta(days=12), balance=4500),
            DebtDetail(account_id=credit.id, interest_rate=18.9, minimum_payment=240),
        ]
    )
    db.commit()

    for idx in range(10):
        db.add(
            NewsCache(
                source="Reuters",
                title=f"Headline {idx}",
                url=f"https://example.com/story-{idx}",
                published_at=datetime.utcnow() - timedelta(hours=idx),
                summary="Market update",
                category="markets",
            )
        )
    db.commit()

    _set_setting(db, "monthly_expenses", 5000)
    _set_setting(db, "income_w2", 150000)
    _set_setting(db, "income_1099", 0)
    _set_setting(db, "monthly_contribution", 1800)
    _set_setting(db, "risk_profile", "moderate")

    response = client.get("/api/dashboard/tape")
    assert response.status_code == 200

    payload = response.json()
    assert "generated_at" in payload
    assert set(payload["segments"].keys()) == {"news", "tickers", "personal"}
    assert payload["segments"]["news"]
    assert payload["segments"]["tickers"]
    assert payload["segments"]["personal"]

    kinds = {item["kind"] for item in payload["sequence"]}
    assert {"news", "ticker", "personal"}.issubset(kinds)
    assert payload["sequence"][0]["kind"] == "news"
    assert all(item["kind"] == "news" for item in payload["sequence"][:8])


def test_dashboard_tape_ticker_order_and_cap(client, db):
    brokerage = Account(name="Concentrated", type="brokerage")
    db.add(brokerage)
    db.commit()
    db.refresh(brokerage)

    rows = [
        ("AAA", 5, 100),   # 500
        ("BBB", 2, 1000),  # 2000
        ("CCC", 10, 50),   # 500
        ("DDD", 1, 700),   # 700
        ("EEE", 3, 400),   # 1200
        ("FFF", 4, 150),   # 600
    ]
    db.add_all(
        [
            Holding(account_id=brokerage.id, symbol=symbol, quantity=qty, last_price=price, cost_basis=qty * price)
            for symbol, qty, price in rows
        ]
    )
    db.commit()

    response = client.get("/api/dashboard/tape")
    assert response.status_code == 200
    tickers = response.json()["segments"]["tickers"]

    assert len(tickers) == 5
    market_values = [ticker["market_value"] for ticker in tickers]
    assert market_values == sorted(market_values, reverse=True)
    assert tickers[0]["symbol"] == "BBB"
    assert all(ticker["id"].startswith("sym-") for ticker in tickers)


def test_dashboard_tape_personal_labels_are_aggregate_only(client, db):
    checking = Account(name="Super Secret Checking", type="checking")
    db.add(checking)
    db.commit()
    db.refresh(checking)

    db.add(BalanceSnapshot(account_id=checking.id, date=date.today() - timedelta(days=10), balance=9000))
    db.commit()
    _set_setting(db, "monthly_expenses", 4000)

    response = client.get("/api/dashboard/tape")
    assert response.status_code == 200

    personal = response.json()["segments"]["personal"]
    labels = " ".join(item["label"].lower() for item in personal)
    assert "super secret checking" not in labels


def test_dashboard_tape_empty_state_schema_is_stable(client):
    response = client.get("/api/dashboard/tape")
    assert response.status_code == 200

    payload = response.json()
    assert set(payload.keys()) == {"generated_at", "segments", "sequence"}
    assert payload["segments"]["news"] == []
    assert payload["segments"]["tickers"] == []
    assert payload["segments"]["personal"] == []
    assert payload["sequence"] == []
