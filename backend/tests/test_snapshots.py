from datetime import date, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database import Base, get_db
from backend.models import Account, BalanceSnapshot
from backend.routers.snapshots import router as snapshots_router


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
    app.include_router(snapshots_router)

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


def _seed_snap(db, account_id: int, day: date, balance: float):
    db.add(BalanceSnapshot(account_id=account_id, date=day, balance=balance))
    db.commit()


def test_net_worth_history_respects_range(client, db):
    checking = _seed_account(db, "Cash", "checking")

    today = date.today()
    for offset, balance in [(400, 1000), (120, 1200), (40, 1400), (20, 1600), (5, 1800)]:
        _seed_snap(db, checking.id, today - timedelta(days=offset), balance)

    all_points = client.get("/api/snapshots/net-worth?range=ALL").json()
    m1_points = client.get("/api/snapshots/net-worth?range=1M").json()
    ytd_points = client.get("/api/snapshots/net-worth?range=YTD").json()

    assert len(all_points) == 5
    assert len(m1_points) == 2
    assert len(ytd_points) >= 2
    assert m1_points[-1]["net_worth"] == 1800


def test_record_month_end_backfills_continuity(client, db):
    checking = _seed_account(db, "Cash", "checking")
    today = date.today()

    _seed_snap(db, checking.id, today - timedelta(days=75), 1000)
    _seed_snap(db, checking.id, today - timedelta(days=10), 1300)

    result = client.post("/api/snapshots/record-month-end").json()

    assert result["accounts"] == 1
    assert result["created"] >= 1

    snaps = (
        db.query(BalanceSnapshot)
        .filter(BalanceSnapshot.account_id == checking.id)
        .order_by(BalanceSnapshot.date.asc())
        .all()
    )
    month_end_dates = [s.date for s in snaps if s.date.day >= 28]
    assert month_end_dates, "Expected at least one generated month-end snapshot"


def test_current_net_worth_includes_30d_delta_and_liabilities(client, db):
    cash = _seed_account(db, "Cash", "checking")
    debt = _seed_account(db, "Credit", "credit_card")

    today = date.today()
    _seed_snap(db, cash.id, today - timedelta(days=35), 10_000)
    _seed_snap(db, cash.id, today - timedelta(days=1), 12_000)
    _seed_snap(db, debt.id, today - timedelta(days=35), 2_000)
    _seed_snap(db, debt.id, today - timedelta(days=1), 1_500)

    payload = client.get("/api/snapshots/current").json()

    assert payload["net_worth"] == 10_500
    assert payload["delta_30d"] is not None
    assert payload["delta_30d_pct"] is not None
    assert payload["by_type"]["liabilities"] == 1500
