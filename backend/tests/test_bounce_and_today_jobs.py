import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from app.main import app
from app.database_init import init_db
from app.database import get_db, SessionLocal
from app.models import JobListing, ApplicationRecord, ResumeVersion, RecruiterContact, ApplicationAttempt
from app.services.email_service import extract_bounce_target_and_reason, EmailOutreachService

@pytest.fixture(scope="module")
def client():
    init_db()
    with TestClient(app) as c:
        yield c

def test_extract_bounce_target_and_reason():
    subject = "Delivery Status Notification (Failure)"
    body = """
    ** Address not found **
    Your message wasn't delivered to rahul.verma@tatasteeldow.com because the domain tatasteeldow.com couldn't be found.
    Check for typos or unnecessary spaces and try again.
    The response was:
    DNS Error: 2167732 DNS type 'mx' lookup of tatasteeldow.com responded with code NXDOMAIN
    """
    target, reason = extract_bounce_target_and_reason(subject, body)
    assert target == "rahul.verma@tatasteeldow.com"
    assert "tatasteeldow.com" in reason or "NXDOMAIN" in reason or "not found" in reason

def test_today_jobs_endpoint(client):
    res = client.get("/api/jobs/today")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "SUCCESS"
    assert "total_today" in data
    assert isinstance(data["jobs"], list)

def test_portal_sources_endpoint(client):
    res = client.get("/api/jobs/portal-sources")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "SUCCESS"
    assert len(data["sources"]) >= 5
    names = [s["name"] for s in data["sources"]]
    assert "LinkedIn Jobs" in names
    assert "Naukri.com" in names
    assert "Indeed India & Gulf" in names
    assert "Apollo.io AI Contact Engine" in names

def test_delete_job_endpoint(client):
    db = SessionLocal()
    try:
        now_ts = datetime.now(timezone.utc)
        test_job = JobListing(
            title="Temporary Warehouse Executive",
            company_name="DeleteMe Logistics",
            location="Hyderabad, India",
            source_platform="Test",
            description="Testing deletion of job vacancies and cascading dependencies.",
            original_url="https://example.com/delete-me-job",
            canonical_url="https://example.com/delete-me-job",
            vacancy_status="VERIFIED_OPEN",
            date_discovered=now_ts
        )
        db.add(test_job)
        db.commit()
        db.refresh(test_job)
        job_id = test_job.id
    finally:
        db.close()

    res = client.delete(f"/api/jobs/{job_id}")
    assert res.status_code == 200
    assert res.json()["status"] == "SUCCESS"

    # Confirm it is gone
    db = SessionLocal()
    try:
        j = db.query(JobListing).filter_by(id=job_id).first()
        assert j is None
    finally:
        db.close()

def test_check_inbox_and_recover_contact_flow(client):
    import uuid
    uid = uuid.uuid4().hex[:8]
    db = SessionLocal()
    try:
        now_ts = datetime.now(timezone.utc)
        job = JobListing(
            title="Logistics Dispatch Executive",
            company_name="Tata Steel Downstream",
            location="Hyderabad, India",
            source_platform="Direct Hot-Mailer",
            description="Logistics and warehouse dispatch executive role for steel operations.",
            original_url=f"https://example.com/tata-job-{uid}",
            canonical_url=f"https://example.com/tata-job-{uid}",
            vacancy_status="VERIFIED_OPEN",
            date_discovered=now_ts
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        contact = RecruiterContact(
            job_id=job.id,
            company_name="Tata Steel Downstream",
            contact_name="Rahul Verma",
            contact_role="Talent Acquisition",
            email="rahul.verma@tatasteeldow.com",
            source_url=f"https://example.com/tata-job-{uid}",
            verification_method="official_careers_channel",
            verification_status="SOURCE_VERIFIED",
            confidence=0.9,
            is_seed=False
        )
        db.add(contact)
        db.commit()

        rv = ResumeVersion(
            profile_id=1,
            job_id=job.id,
            version_name="v1",
            headline="Operations Executive",
            full_text="SK Adil Raja Operations Executive Resume Text",
            pdf_path="./data/resumes/SK_Adil_Raja_Resume.pdf"
        )
        db.add(rv)
        db.commit()

        app_rec = ApplicationRecord(
            job_id=job.id,
            resume_version_id=rv.id,
            current_status="EMAIL_SENT",
            submission_method="email",
            primary_recipient="rahul.verma@tatasteeldow.com",
            unattended_approved=True
        )
        db.add(app_rec)
        db.commit()
        db.refresh(app_rec)
        app_id = app_rec.id
    finally:
        db.close()

    # Test recovery endpoint
    rec_res = client.post(f"/api/applications/{app_id}/recover-contact")
    assert rec_res.status_code == 200
    rec_data = rec_res.json()
    assert rec_data["status"] == "SUCCESS"
    assert rec_data["failed_email"] == "rahul.verma@tatasteeldow.com"

    # Test resend endpoint with dry_run
    resend_res = client.post(f"/api/applications/{app_id}/resend", json={
        "recipient_email": "adilrazask@gmail.com",
        "contact_name": "Adil Self Verification"
    })
    assert resend_res.status_code == 200
    assert resend_res.json()["status"] == "SUCCESS"

    db = SessionLocal()
    try:
        updated_app = db.query(ApplicationRecord).filter_by(id=app_id).first()
        assert updated_app.primary_recipient == "adilrazask@gmail.com"
        assert updated_app.current_status in ["EMAIL_SENT", "MOCK_SENT"]
    finally:
        db.close()
