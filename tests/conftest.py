"""
Pytest configuration and test client fixtures.
"""

import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.models.user import UserModel
from server import app

# Shared in-memory SQLite for testing with StaticPool
TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()

    # Seed test super admin
    super_admin = UserModel(
        id="u_super_admin",
        email="admin@sovereign.local",
        name="مهدی جعفری",
        password="admin",
        role="super_admin",
        organization_id=None,
        team_id=None,
        is_active=True,
        used_tokens=0,
        token_limit=50000000,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    db.add(super_admin)
    db.commit()
    db.close()
    yield
    Base.metadata.drop_all(bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def auth_headers(client):
    res = client.post("/api/auth/login", json={"email": "admin@sovereign.local", "password": "admin"})
    assert res.status_code == 200
    token = res.json()["token"]
    return {"Authorization": f"Bearer {token}"}
