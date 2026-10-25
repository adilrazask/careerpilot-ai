import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models.all_models import User, UserSession

client = TestClient(app)

def test_google_auth_super_admin():
    # Test Super Admin sign-in with Google
    response = client.post("/api/auth/google", json={
        "email": "adilrazask@gmail.com",
        "name": "SK Adil Raja"
    })
    assert response.status_code == 200
    data = response.json()
    assert "token" in data
    assert data["user"]["email"] == "adilrazask@gmail.com"
    assert data["user"]["role"] == "admin"
    assert "admin" in data["user"]["allowed_features"]
    assert "dashboard" in data["user"]["allowed_features"]
    
    admin_token = data["token"]

    # Verify /api/auth/me with admin token
    me_resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {admin_token}"})
    assert me_resp.status_code == 200
    me_data = me_resp.json()
    assert me_data["user"]["email"] == "adilrazask@gmail.com"

def test_member_login_and_admin_termination():
    # 1. Login as Super Admin
    admin_resp = client.post("/api/auth/login", json={"email": "adilrazask@gmail.com"})
    assert admin_resp.status_code == 200
    admin_token = admin_resp.json()["token"]

    # 2. Login as regular team member
    member_resp = client.post("/api/auth/google", json={
        "email": "recruiter@careerpilot.ai",
        "name": "Team Recruiter"
    })
    assert member_resp.status_code == 200
    member_token = member_resp.json()["token"]
    assert member_resp.json()["user"]["role"] == "member"

    # Verify member can access /api/auth/me
    check_member = client.get("/api/auth/me", headers={"Authorization": f"Bearer {member_token}"})
    assert check_member.status_code == 200
    member_session_id = check_member.json()["session_id"]

    # 3. Super Admin lists active sessions
    sessions_resp = client.get("/api/admin/sessions", headers={"Authorization": f"Bearer {admin_token}"})
    assert sessions_resp.status_code == 200
    sessions = sessions_resp.json()
    assert any(s["id"] == member_session_id for s in sessions)

    # 4. Super Admin terminates member's session
    term_resp = client.post(
        f"/api/admin/sessions/{member_session_id}/terminate",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert term_resp.status_code == 200
    assert term_resp.json()["status"] == "success"

    # 5. Terminated member now immediately receives 401 Unauthorized!
    ejected_resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {member_token}"})
    assert ejected_resp.status_code == 401
    assert "terminated" in ejected_resp.json()["detail"].lower()

def test_admin_update_feature_permissions():
    # Admin login
    admin_resp = client.post("/api/auth/login", json={"email": "adilrazask@gmail.com"})
    admin_token = admin_resp.json()["token"]

    # Get users
    users_resp = client.get("/api/admin/users", headers={"Authorization": f"Bearer {admin_token}"})
    assert users_resp.status_code == 200
    users = users_resp.json()
    recruiter = next(u for u in users if u["email"] == "recruiter@careerpilot.ai")

    # Update recruiter's permissions to only ["dashboard", "jobs"]
    update_resp = client.put(
        f"/api/admin/users/{recruiter['id']}/permissions",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "role": "member",
            "allowed_features": ["dashboard", "jobs"]
        }
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["allowed_features"] == ["dashboard", "jobs"]
