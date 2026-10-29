import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.main import app
from app.database import Base, get_db
from app.models import User, UserSession

@pytest.fixture
def auth_test_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Create admin user and session
    admin_user = User(
        id=1,
        email="adilrazask@gmail.com",
        full_name="Adil Raja",
        hashed_password="hash",
        role="admin",
        is_active=True
    )
    session.add(admin_user)
    session.commit()

    admin_session = UserSession(
        id=1,
        user_id=1,
        session_token="admin-session-valid-token-12345",
        is_active=True
    )
    session.add(admin_session)

    # Create non-admin user and session
    regular_user = User(
        id=2,
        email="regular@example.com",
        full_name="Regular User",
        hashed_password="hash",
        role="candidate",
        is_active=True
    )
    session.add(regular_user)
    session.commit()

    regular_session = UserSession(
        id=2,
        user_id=2,
        session_token="regular-session-token-67890",
        is_active=True
    )
    session.add(regular_session)

    session.commit()
    yield session
    session.close()

def test_health_audit_missing_token_blocked(auth_test_db):
    app.dependency_overrides[get_db] = lambda: auth_test_db
    client = TestClient(app)
    try:
        res = client.get("/health/audit")
        assert res.status_code == 401
        assert "Valid admin token required" in res.json()["detail"]
    finally:
        app.dependency_overrides.clear()

def test_health_audit_invalid_token_blocked(auth_test_db):
    app.dependency_overrides[get_db] = lambda: auth_test_db
    client = TestClient(app)
    try:
        res = client.get("/health/audit", headers={"X-Admin-Token": "wrong-secret-token"})
        assert res.status_code == 401
    finally:
        app.dependency_overrides.clear()

def test_health_audit_x_admin_token_allowed(auth_test_db):
    app.dependency_overrides[get_db] = lambda: auth_test_db
    client = TestClient(app)
    try:
        res = client.get("/health/audit", headers={"X-Admin-Token": "cp_admin_audit_secret_token_9876"})
        assert res.status_code == 200
        assert "live_jobs" in res.json()
    finally:
        app.dependency_overrides.clear()

def test_health_audit_bearer_admin_token_allowed(auth_test_db):
    app.dependency_overrides[get_db] = lambda: auth_test_db
    client = TestClient(app)
    try:
        res = client.get("/health/audit", headers={"Authorization": "Bearer cp_admin_audit_secret_token_9876"})
        assert res.status_code == 200
    finally:
        app.dependency_overrides.clear()

def test_health_audit_active_admin_session_allowed(auth_test_db):
    app.dependency_overrides[get_db] = lambda: auth_test_db
    client = TestClient(app)
    try:
        res = client.get("/health/audit", headers={"Authorization": "Bearer admin-session-valid-token-12345"})
        assert res.status_code == 200
    finally:
        app.dependency_overrides.clear()

def test_health_audit_regular_user_session_rejected(auth_test_db):
    app.dependency_overrides[get_db] = lambda: auth_test_db
    client = TestClient(app)
    try:
        res = client.get("/health/audit", headers={"Authorization": "Bearer regular-session-token-67890"})
        assert res.status_code == 401
    finally:
        app.dependency_overrides.clear()

def test_api_audit_logs_protected(auth_test_db):
    app.dependency_overrides[get_db] = lambda: auth_test_db
    client = TestClient(app)
    try:
        # Without token -> 401
        res = client.get("/api/audit/logs")
        assert res.status_code == 401

        # With admin token -> 200
        res_ok = client.get("/api/audit/logs", headers={"X-Admin-Token": "cp_admin_audit_secret_token_9876"})
        assert res_ok.status_code == 200
    finally:
        app.dependency_overrides.clear()
