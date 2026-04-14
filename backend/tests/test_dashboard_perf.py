import time
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


def test_dashboard_snapshot_query_under_500ms(client, db):
    checking = _seed_account(db, "Cash", "checking")
    start_date = date.today() - timedelta(days=720)

    for i in range(720):
        db.add(BalanceSnapshot(account_id=checking.id, date=start_date + timedelta(days=i), balance=10000 + i * 12))
    db.commit()

    start = time.perf_counter()
    response = client.get("/api/snapshots/net-worth?range=ALL")
    elapsed_ms = (time.perf_counter() - start) * 1000

    assert response.status_code == 200
    assert len(response.json()) >= 700
    assert elapsed_ms < 500
