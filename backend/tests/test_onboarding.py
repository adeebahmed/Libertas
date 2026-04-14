from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database import Base, get_db
from backend.models import Account
from backend.routers.settings import router as settings_router


def _make_client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)

    app = FastAPI()
    app.include_router(settings_router)

    def override_get_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    return client, session_factory


def test_onboarding_status_defaults_to_should_run():
    client, _ = _make_client()
    res = client.get("/api/settings/onboarding/status")
    assert res.status_code == 200
    body = res.json()
    assert body["has_accounts"] is False
    assert body["account_count"] == 0
    assert body["onboarding_complete"] is False
    assert body["should_run_onboarding"] is True


def test_onboarding_status_false_when_accounts_and_flag_set():
    client, session_factory = _make_client()

    db = session_factory()
    db.add(Account(name="Checking", type="checking"))
    db.commit()
    db.close()

    put_res = client.put("/api/settings/onboarding_complete", json={"value": True})
    assert put_res.status_code == 200

    res = client.get("/api/settings/onboarding/status")
    assert res.status_code == 200
    body = res.json()
    assert body["has_accounts"] is True
    assert body["account_count"] == 1
    assert body["onboarding_complete"] is True
    assert body["should_run_onboarding"] is False


def test_phase3_settings_keys_round_trip():
    client, _ = _make_client()

    payloads = {
        "fire_type": "regular",
        "monthly_income": 9000,
        "annual_lean_expenses": 36000,
        "annual_fat_expenses": 120000,
        "part_time_income": 18000,
        "onboarding_complete": True,
    }
    for key, value in payloads.items():
        res = client.put(f"/api/settings/{key}", json={"value": value})
        assert res.status_code == 200

    settings_res = client.get("/api/settings")
    assert settings_res.status_code == 200
    settings = settings_res.json()
    for key, value in payloads.items():
        assert settings[key] == value
