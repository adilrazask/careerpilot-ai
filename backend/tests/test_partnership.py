import pytest
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

def test_partnership_directors_directory(client):
    res = client.get("/api/partnership/directors")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] > 0
    assert any("Hyderabad Angels" in d["company"] for d in data["directors"])

def test_partnership_discover_auto_search(client):
    res = client.post("/api/partnership/discover", json={
        "query": "Fintech & Algorithmic Trading",
        "location": "Hyderabad & India",
        "sector": "all",
        "max_results": 10
    })
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "SUCCESS"
    assert data["total"] > 0
    first = data["investors"][0]
    assert "name" in first
    assert "email" in first
    assert "pitch_draft" in first
    assert "SK Adil Raja" in first["pitch_draft"]["body"]

def test_partnership_draft_pitch(client):
    res = client.post("/api/partnership/draft", json={
        "director_name": "Mr. Rajesh Kumar",
        "company_name": "T-Hub Hyderabad",
        "demo_url": "https://github.com/adilrazask"
    })
    assert res.status_code == 200
    data = res.json()
    assert "subject" in data
    assert "body" in data
    assert "SK Adil Raja" in data["body"]
    assert "M.Sc. in Computer Science" in data["body"]
    assert "six months" in data["body"].lower()

def test_partnership_verify_email_rejects_fake(client):
    res = client.post("/api/partnership/verify-email", json={"email_or_domain": "priya.sharma@fakecompany.com"})
    assert res.status_code == 200
    data = res.json()
    assert data["valid"] is False
    assert data["has_mx"] is False

def test_partnership_send_pitch_rejects_synthetic(client):
    res = client.post("/api/partnership/send", json={
        "recipient_email": "priya.sharma@fakecompany.com",
        "director_name": "Fake Director",
        "company_name": "Fake Company",
        "subject": "Test Partnership",
        "body_text": "Test body",
        "demo_url": "https://github.com/adilrazask"
    })
    assert res.status_code == 400
    assert "Banned placeholder" in res.json()["detail"] or "Domain verification rejected" in res.json()["detail"]
