import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import Base, engine, SessionLocal
from app.models import CareerProfile

@pytest.fixture(scope="module")
def client():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    # Ensure profile exists
    prof = db.query(CareerProfile).first()
    if not prof:
        prof = CareerProfile(
            full_name="SK Adil Raja",
            primary_email="adilrazask@gmail.com",
            primary_phone="+91 9177174624",
            current_role="Operations Executive",
            current_company="Omnia Steels Pvt Ltd",
            location="Attapur, Hyderabad, India",
            experience_years=2.5,
            highest_education="M.Sc. Computer Science"
        )
        db.add(prof)
        db.commit()
    db.close()
    with TestClient(app) as c:
        yield c

def test_outside_portal_directory(client):
    res = client.get("/api/outside-portal/directory")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] > 0
    assert any(d["company"] == "Tata Steel Downstream" for d in data["directory"])

def test_outside_portal_verify_email_synthetic_blocked(client):
    res = client.post("/api/outside-portal/verify-email", json={"email_or_domain": "rahul.verma@tatasteeldow.com"})
    assert res.status_code == 200
    data = res.json()
    assert data["valid"] is False
    assert data["has_mx"] is False
    assert "Synthetic or blocked" in data["reason"]

def test_outside_portal_search(client):
    res = client.post("/api/outside-portal/search", json={
        "query": "Operations Executive",
        "location": "Hyderabad, India",
        "portal": "all",
        "max_results": 5
    })
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "SUCCESS"
    assert "jobs" in data
    assert len(data["jobs"]) > 0
    # Every job must have verified recipient and hot mail draft mentioning Omnia Steels
    first_job = data["jobs"][0]
    assert "verified_recipient" in first_job
    assert "@" in first_job["verified_recipient"]
    assert "hot_mail_draft" in first_job
    assert "Omnia Steels" in first_job["hot_mail_draft"]["body"] or "Omnia Steels" in first_job["hot_mail_draft"]["subject"]

def test_outside_portal_extract_url(client):
    res = client.post("/api/outside-portal/extract", json={
        "url": "https://www.linkedin.com/jobs/view/operations-executive-at-tata-steel-12345",
        "company_name": "Tata Steel",
        "job_title": "Operations Executive"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "SUCCESS"
    assert data["verified_recipient"] == "careers@tatasteel.com"
    assert data["dns_verified"] is True
    assert "Omnia Steels" in data["hot_mail_draft"]["body"]

def test_outside_portal_send_hot_mail_rejects_fake(client):
    res = client.post("/api/outside-portal/send-hot-mail", json={
        "company_name": "Fake Company",
        "job_title": "Operations Manager",
        "recipient_email": "priya.sharma@fakecompany.com",
        "subject": "Test Application",
        "body_text": "Hello world"
    })
    assert res.status_code == 400
    assert "Banned placeholder" in res.json()["detail"] or "Domain verification rejected" in res.json()["detail"]
