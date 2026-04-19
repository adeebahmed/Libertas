"""
Shared test fixtures for Libertas backend tests.
Uses an in-memory SQLite database to isolate tests from production data.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database import Base, get_db
from backend.main import app

# Import ALL models so Base.metadata.create_all() registers every table
import backend.models  # noqa: F401

TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="function")
def test_engine():
    """Fresh in-memory SQLite engine per test function."""
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db(test_engine):
    """SQLAlchemy session bound to in-memory DB."""
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = testing_session_local()
    yield session
    session.close()


@pytest.fixture(scope="function")
def db_session_factory(test_engine):
    """Factory for opening multiple DB sessions against the same in-memory engine."""
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    return testing_session_local


@pytest.fixture(scope="function")
def client(test_engine):
    """FastAPI TestClient with DB dependency overridden to in-memory DB."""
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    def override_get_db():
        session = testing_session_local()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
