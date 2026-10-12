from datetime import timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.models import Base, User, RevokedToken
from app.core.database import get_db
from app.core.security import create_access_token, hash_password

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

def test_successful_registration():
    payload = {
        "email": "analyst@cloudguard.io",
        "password": "SecurePassword123!",
        "full_name": "Security Analyst"
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "analyst@cloudguard.io"
    assert data["full_name"] == "Security Analyst"
    assert data["is_active"] is True
    assert "id" in data
    assert "created_at" in data
    # Ensure sensitive credentials are never leaked
    assert "password" not in data
    assert "password_hash" not in data

def test_duplicate_registration():
    payload = {
        "email": "lead@cloudguard.io",
        "password": "SecurePassword123!",
        "full_name": "Lead Engineer"
    }
    # Initial registration
    first_res = client.post("/api/v1/auth/register", json=payload)
    assert first_res.status_code == 201

    # Attempt duplicate registration with case variation
    dup_payload = {
        "email": "LEAD@cloudguard.io",
        "password": "AnotherPassword456!",
        "full_name": "Duplicate Lead"
    }
    dup_res = client.post("/api/v1/auth/register", json=dup_payload)
    assert dup_res.status_code == 400
    assert "already registered" in dup_res.json()["detail"].lower()

def test_invalid_email():
    payload = {
        "email": "not-an-email-address",
        "password": "SecurePassword123!",
        "full_name": "Invalid Email User"
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 422

def test_weak_password():
    # Password shorter than 8 characters
    short_pw = {
        "email": "user1@cloudguard.io",
        "password": "123",
        "full_name": "Short Password User"
    }
    res1 = client.post("/api/v1/auth/register", json=short_pw)
    assert res1.status_code == 422

    # Password without digits or special characters
    alpha_only_pw = {
        "email": "user2@cloudguard.io",
        "password": "onlylettershere",
        "full_name": "Alpha Only User"
    }
    res2 = client.post("/api/v1/auth/register", json=alpha_only_pw)
    assert res2.status_code == 422

def test_successful_login():
    # Register user first
    reg_payload = {
        "email": "dev@cloudguard.io",
        "password": "DevPassword2026!",
        "full_name": "Dev User"
    }
    client.post("/api/v1/auth/register", json=reg_payload)

    # Login
    login_payload = {
        "email": "dev@cloudguard.io",
        "password": "DevPassword2026!"
    }
    response = client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] > 0
    assert data["user"]["email"] == "dev@cloudguard.io"
    assert "password_hash" not in data["user"]

def test_wrong_password():
    reg_payload = {
        "email": "audit@cloudguard.io",
        "password": "CorrectPassword123!",
        "full_name": "Auditor"
    }
    client.post("/api/v1/auth/register", json=reg_payload)

    login_payload = {
        "email": "audit@cloudguard.io",
        "password": "WrongPassword999!"
    }
    response = client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == 401
    assert "incorrect email or password" in response.json()["detail"].lower()

def test_nonexistent_user():
    login_payload = {
        "email": "ghost@cloudguard.io",
        "password": "SomePassword123!"
    }
    response = client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == 401
    assert "incorrect email or password" in response.json()["detail"].lower()

def test_authenticated_me():
    reg_payload = {
        "email": "me@cloudguard.io",
        "password": "MySecretPassword123!",
        "full_name": "Current User"
    }
    client.post("/api/v1/auth/register", json=reg_payload)

    login_res = client.post("/api/v1/auth/login", json={
        "email": "me@cloudguard.io",
        "password": "MySecretPassword123!"
    })
    token = login_res.json()["access_token"]

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "me@cloudguard.io"
    assert data["full_name"] == "Current User"
    assert data["is_active"] is True
    assert "password_hash" not in data

def test_missing_token():
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert "authentication required" in response.json()["detail"].lower()

def test_invalid_token():
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer this-is-not-a-valid-jwt-token"}
    )
    assert response.status_code == 401
    assert "invalid token" in response.json()["detail"].lower()

def test_expired_token():
    db = TestingSessionLocal()
    user = User(
        id="expired-user-1",
        email="expired@cloudguard.io",
        password_hash=hash_password("Password123!"),
        full_name="Expired User",
        is_active=True
    )
    db.add(user)
    db.commit()
    db.close()

    # Create a token that expired 15 minutes ago
    expired_token = create_access_token(
        subject="expired-user-1",
        expires_delta=timedelta(minutes=-15)
    )

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"}
    )
    assert response.status_code == 401
    assert "expired" in response.json()["detail"].lower()

def test_inactive_user():
    db = TestingSessionLocal()
    user = User(
        id="inactive-user-1",
        email="inactive@cloudguard.io",
        password_hash=hash_password("Password123!"),
        full_name="Inactive User",
        is_active=False
    )
    db.add(user)
    db.commit()
    db.close()

    # Login attempt should fail with 400
    login_res = client.post("/api/v1/auth/login", json={
        "email": "inactive@cloudguard.io",
        "password": "Password123!"
    })
    assert login_res.status_code == 400
    assert "inactive" in login_res.json()["detail"].lower()

    # /me access with active token should fail
    active_token = create_access_token(subject="inactive-user-1")
    me_res = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {active_token}"}
    )
    assert me_res.status_code == 400
    assert "inactive" in me_res.json()["detail"].lower()

def test_logout_and_revocation():
    reg_payload = {
        "email": "logout-test@cloudguard.io",
        "password": "Password123!",
        "full_name": "Logout Tester"
    }
    client.post("/api/v1/auth/register", json=reg_payload)

    login_res = client.post("/api/v1/auth/login", json={
        "email": "logout-test@cloudguard.io",
        "password": "Password123!"
    })
    token = login_res.json()["access_token"]

    # Verify token works before logout
    me_before = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert me_before.status_code == 200

    # Call logout to revoke token server-side
    logout_res = client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert logout_res.status_code == 200
    assert "logged out" in logout_res.json()["message"].lower()

    # Attempt to reuse the revoked token
    me_after = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert me_after.status_code == 401
    assert "revoked" in me_after.json()["detail"].lower()
