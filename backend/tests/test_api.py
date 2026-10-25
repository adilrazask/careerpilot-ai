import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database_init import init_db

@pytest.fixture(scope="module")
def client():
    init_db()
    with TestClient(app) as c:
        yield c

def test_health_check(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "HEALTHY"

def test_dashboard_metrics(client):
    res = client.get("/api/dashboard/metrics")
    assert res.status_code == 200
    data = res.json()
    assert "agent_status" in data
    assert "total_vacancies_discovered" in data
    assert "current_automation_mode" in data

def test_profile_endpoints(client):
    res = client.get("/api/profile")
    assert res.status_code == 200
    data = res.json()
    assert "adil raja" in data["full_name"].lower()
    assert "Operations" in data["summary"]

    # Update profile
    update_res = client.put("/api/profile", json={"phone": "+91 99999 88888"})
    assert update_res.status_code == 200
    assert update_res.json()["phone"] == "+91 99999 88888"

def test_job_and_tailoring_pipeline(client):
    # 1. Create a job manually
    import uuid
    unique_slug = uuid.uuid4().hex[:6]
    job_payload = {
        "title": "Business Operations Coordinator",
        "company_name": "Apex Supply Logistics",
        "location": "Hyderabad, India",
        "work_mode": "Hybrid",
        "employment_type": "Full-time",
        "salary_min": 600000.0,
        "salary_max": 850000.0,
        "salary_currency": "INR",
        "source_platform": "Company Careers",
        "original_url": f"https://apexsupply.example.com/careers/ops-coord-{unique_slug}",
        "description": "Seeking an operations coordinator with experience in procurement, SAP ERP, GRN verification, and Excel.",
        "notes": "Verified official careers listing"
    }
    job_res = client.post("/api/jobs/create", json=job_payload)
    assert job_res.status_code == 200
    job_data = job_res.json()
    job_id = job_data["id"]
    assert job_data["match_score"] > 60

    # 2. Tailor resume for this job
    tailor_res = client.post("/api/resumes/tailor", json={"job_id": job_id, "use_ai": False})
    assert tailor_res.status_code == 200
    tailor_data = tailor_res.json()
    assert tailor_data["job_id"] == job_id
    assert "Apex Supply Logistics" in tailor_data["headline"]
    assert tailor_data["factual_consistency_score"] == 100.0

    # 3. Add contact and verify
    contact_payload = {
        "job_id": job_id,
        "company_name": "Apex Supply Logistics",
        "contact_name": "Priya Sharma",
        "contact_role": "Head of Talent Acquisition",
        "email": "priya.sharma@apexsupply.com",
        "source_url": "https://apexsupply.example.com/team"
    }
    contact_res = client.post("/api/contacts/create", json=contact_payload)
    assert contact_res.status_code == 200

    # 4. Prepare application
    app_res = client.post(f"/api/applications/prepare/{job_id}")
    assert app_res.status_code == 200
    app_data = app_res.json()
    assert app_data["job_id"] == job_id
    assert app_data["current_status"] in ["APPLICATION_READY", "RESUME_READY"]

def test_agent_workspace_instruction(client):
    res = client.post("/api/agent/instruct", json={
        "prompt": "Find operations coordinator jobs in Hyderabad requiring 3 to 5 years of experience."
    })
    assert res.status_code == 200
    data = res.json()
    assert "objective" in data
    assert data["status"] in ["ACTIVE", "COMPLETED"]

def test_integrations_list_and_test(client):
    res = client.get("/api/integrations")
    assert res.status_code == 200
    items = res.json()
    assert len(items) >= 4

    # Test an integration
    test_res = client.post("/api/integrations/test", json={"provider_name": "SMTP Outbound Mail"})
    assert test_res.status_code == 200
    assert test_res.json()["status"] == "SUCCESS"

def test_audit_logs(client):
    res = client.get("/api/audit/logs")
    assert res.status_code == 200
    logs = res.json()
    assert len(logs) > 0
