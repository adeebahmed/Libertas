from datetime import date

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database import Base, get_db
from backend.models import Account, BalanceSnapshot, Setting
from backend.routers.retirement import router as retirement_router


def _make_client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)

    app = FastAPI()
    app.include_router(retirement_router)

    def override_get_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    return client, session_factory


def test_retirement_overview_returns_expected_shape():
    client, session_factory = _make_client()
    db = session_factory()
    acct = Account(name="401k", type="401k")
    db.add(acct)
    db.flush()
    db.add(BalanceSnapshot(account_id=acct.id, date=date.today(), balance=150000))
    db.add(Setting(key="monthly_expenses", value="5000"))
    db.commit()
    db.close()

    res = client.get("/api/retirement/overview")
    assert res.status_code == 200
    body = res.json()
    assert "retirement_accounts" in body
    assert "tax_split" in body
    assert "readiness" in body
    assert body["total_retirement_assets"] >= 150000


def test_fire_endpoint_returns_core_metrics():
    client, session_factory = _make_client()
    db = session_factory()
    acct = Account(name="Brokerage", type="brokerage")
    db.add(acct)
    db.flush()
    db.add(BalanceSnapshot(account_id=acct.id, date=date.today(), balance=100000))
    db.add(Setting(key="monthly_expenses", value="4000"))
    db.add(Setting(key="monthly_income", value="9000"))
    db.add(Setting(key="monthly_contribution", value="2000"))
    db.commit()
    db.close()

    res = client.get("/api/retirement/fire?fire_type=regular")
    assert res.status_code == 200
    body = res.json()
    assert body["fire_type"] == "regular"
    assert body["fire_number"] > 0
    assert "time_to_fire_years" in body
    assert "recommended_fire_type" in body


def test_recommend_endpoint_returns_reason():
    client, _ = _make_client()
    res = client.get("/api/retirement/fire/recommend")
    assert res.status_code == 200
    body = res.json()
    assert "recommended_fire_type" in body
    assert "reason" in body
