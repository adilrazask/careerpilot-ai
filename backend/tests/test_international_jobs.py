import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.database import Base, engine, SessionLocal
from app.models import CareerProfile

@pytest.fixture(scope="module")
def client():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
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

def test_international_directory(client):
    res = client.get("/api/international-jobs/directory")
    assert res.status_code == 200
    data = res.json()
    assert "gulf_portals" in data
    assert "gulf_companies" in data
    assert "western_companies" in data
    assert len(data["gulf_portals"]) >= 5
    assert len(data["gulf_companies"]) >= 10
    assert len(data["western_companies"]) >= 12

    # Check Gulf portals include NaukriGulf and Bayt
    portal_names = [p["name"] for p in data["gulf_portals"]]
    assert "NaukriGulf" in portal_names
    assert "Bayt.com" in portal_names

    # Check Western companies include Australia, New Zealand, USA, UK
    countries = {c["country"] for c in data["western_companies"]}
    assert "Australia" in countries
    assert "New Zealand" in countries
    assert "United States" in countries
    assert "United Kingdom" in countries

def test_international_verify_email(client):
    res = client.post("/api/international-jobs/verify-email", json={"email_or_domain": "careers@dpworld.com"})
    assert res.status_code == 200
    data = res.json()
    assert data["domain"] == "dpworld.com"
    assert "has_mx" in data

def test_international_draft_letter(client):
    res = client.post("/api/international-jobs/draft", json={
        "company_name": "Toll Group",
        "job_title": "Logistics Operations Coordinator",
        "country": "Australia",
        "city": "Melbourne",
        "recipient_name": "Talent Acquisition Team"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "SUCCESS"
    assert "Australia" in data["subject"] or "Toll Group" in data["subject"]
    assert "Omnia Steels Pvt Ltd" in data["body"]
    assert "M.Sc." in data["body"]
    assert "SK Adil Raja" in data["body"]
    assert "resume" in data["body"].lower()

def test_international_send_rejects_synthetic_address(client):
    res = client.post("/api/international-jobs/send", json={
        "company_name": "Fake Logistics Corp",
        "job_title": "Operations Lead",
        "country": "USA",
        "recipient_email": "priya.sharma@fake.corp",
        "recipient_name": "Priya Sharma",
        "subject": "Application for Operations Lead",
        "body": "Dear Hiring Manager..."
    })
    assert res.status_code == 400
    assert "Banned placeholder" in res.json()["detail"]

@patch("app.routers.international_jobs.EmailOutreachService.send_application_email")
def test_international_send_success(mock_send, client):
    mock_send.return_value = {
        "status": "SUCCESS",
        "message": "Email dispatched via Gmail SMTP",
        "timestamp": "2026-11-16T00:00:00Z"
    }

    res = client.post("/api/international-jobs/send", json={
        "company_name": "Linfox Australia",
        "job_title": "Operations Coordinator",
        "country": "Australia",
        "recipient_email": "careers@linfox.com",
        "recipient_name": "Linfox Talent Acquisition",
        "subject": "Application: Operations Coordinator — SK Adil Raja | Omnia Steels Pvt Ltd",
        "body": "Dear Linfox Talent Acquisition,\n\nI am applying for the Operations Coordinator role...",
        "portal_url": "https://www.linfox.com/careers"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "SUCCESS"
    assert "linfox.com" in data["recipient"]
    assert data["resume_attached"] == "SK_Adil_Raja_Resume.pdf"
