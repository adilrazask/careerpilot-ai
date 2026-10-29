import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.main import app
from app.database import Base, get_db
from app.models import (
    JobListing, RecruiterContact, EmailMessage, FollowUpTask, ApplicationRecord
)

@pytest.fixture
def audit_test_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # 1. Add a seed job (should NOT be counted in live_jobs)
    seed_job = JobListing(
        id=1,
        title="Seed Job Title",
        company_name="Seed Corp",
        location="Hyderabad, India",
        original_url="https://example.com/seed",
        description="Seed description",
        vacancy_status="VERIFIED_OPEN",
        last_verified_at=datetime.now(timezone.utc),
        is_seed=True
    )
    session.add(seed_job)

    # 2. Add a non-seed verified live job (SHOULD be counted)
    live_job = JobListing(
        id=2,
        title="Operations Executive",
        company_name="Live Logistics",
        location="Hyderabad, India",
        original_url="https://livelogistics.co.in/careers/ops-101",
        description="Live operations coordinator",
        vacancy_status="VERIFIED_OPEN",
        last_verified_at=datetime.now(timezone.utc),
        is_seed=False
    )
    session.add(live_job)

    # 3. Add an expired non-seed job (>24h old, should NOT be counted)
    stale_job = JobListing(
        id=3,
        title="Operations Assistant",
        company_name="Stale Inc",
        location="Hyderabad, India",
        original_url="https://example.com/stale",
        description="Stale job",
        vacancy_status="VERIFIED_OPEN",
        last_verified_at=datetime.now(timezone.utc) - timedelta(hours=36),
        is_seed=False
    )
    session.add(stale_job)

    # 4. Add seed contact (should NOT be counted)
    seed_contact = RecruiterContact(
        id=1,
        job_id=1,
        company_name="Seed Corp",
        contact_name="Seed HR",
        email="seed.hr@seedcorp.com",
        source_url="https://seedcorp.com/team",
        verification_method="hunter_verified",
        verification_status="SOURCE_VERIFIED",
        is_seed=True
    )
    session.add(seed_contact)

    # 5. Add MX-only contact (should NOT be counted per Step 3 rules)
    mx_contact = RecruiterContact(
        id=2,
        job_id=2,
        company_name="Live Logistics",
        contact_name="MX HR",
        email="mx.hr@livelogistics.com",
        source_url="https://livelogistics.com/team",
        verification_method="official_source_and_mx",
        verification_status="SOURCE_VERIFIED",
        is_seed=False
    )
    session.add(mx_contact)

    # 6. Add genuinely verified non-seed contact (SHOULD be counted)
    real_contact = RecruiterContact(
        id=3,
        job_id=2,
        company_name="Live Logistics",
        contact_name="Kavita Rao",
        email="kavita.rao@livelogistics.com",
        source_url="https://livelogistics.com/team",
        verification_method="hunter_verified",
        verification_status="SOURCE_VERIFIED",
        is_seed=False
    )
    session.add(real_contact)

    # 7. Add MOCK sent email (should NOT count as sent_with_message_id)
    mock_email = EmailMessage(
        id=1,
        direction="outbound",
        sender="adil@gmail.com",
        recipient="kavita.rao@livelogistics.com",
        subject="Application",
        body_text="Cover letter",
        status="MOCK_SENT",
        provider="MOCK",
        message_id_header="<mock-123@careerpilot.ai>"
    )
    session.add(mock_email)

    # 8. Add real sent email with genuine message ID (SHOULD count)
    real_email = EmailMessage(
        id=2,
        direction="outbound",
        sender="adil@gmail.com",
        recipient="kavita.rao@livelogistics.com",
        subject="Application for Operations Executive",
        body_text="Cover letter",
        status="SENT",
        provider="GMAIL_API",
        message_id_header="18d348a0f8b1a2c3"
    )
    session.add(real_email)

    # 9. Add scheduled follow-up
    fup = FollowUpTask(
        id=1,
        application_id=1,
        follow_up_sequence=1,
        due_date=datetime.now(timezone.utc) + timedelta(days=5),
        status="SCHEDULED",
        draft_subject="Following up",
        draft_body="Checking in"
    )
    session.add(fup)

    session.commit()
    yield session
    session.close()

ADMIN_HEADERS = {"X-Admin-Token": "cp_admin_audit_secret_token_9876"}

def test_health_audit_endpoint_counts_and_unproven(audit_test_db):
    app.dependency_overrides[get_db] = lambda: audit_test_db
    client = TestClient(app)

    try:
        # Without token -> 401
        res_unauth = client.get("/health/audit")
        assert res_unauth.status_code == 401

        # With admin token -> 200
        res = client.get("/health/audit", headers=ADMIN_HEADERS)
        assert res.status_code == 200
        data = res.json()

        # Check required top-level counts
        assert "live_jobs" in data
        assert "verified_contacts" in data
        assert "drafts_in_gmail" in data
        assert "sent_with_message_id" in data
        assert "scheduled_follow_ups" in data

        # Check calculated values
        # live_jobs: exactly 1 (job 2 is live and <=24h; job 1 is seed; job 3 is >24h)
        assert data["live_jobs"] == 1

        # verified_contacts: exactly 1 (contact 3 is non-seed, hunter_verified; contact 1 is seed; contact 2 is mx-only)
        assert data["verified_contacts"] == 1

        # drafts_in_gmail: without valid token, must be marked 'NOT VERIFIED'
        assert data["drafts_in_gmail"] == "NOT VERIFIED"

        # sent_with_message_id: exactly 1 (mock_email is excluded, real_email is included)
        assert data["sent_with_message_id"] == 1

        # scheduled_follow_ups: exactly 1
        assert data["scheduled_follow_ups"] == 1
    finally:
        app.dependency_overrides.clear()

def test_health_audit_drafts_count_when_gmail_available(audit_test_db):
    app.dependency_overrides[get_db] = lambda: audit_test_db
    client = TestClient(app)

    try:
        with patch("app.services.gmail_service.GmailService.get_drafts_count", return_value=4):
            res = client.get("/health/audit", headers=ADMIN_HEADERS)
            assert res.status_code == 200
            data = res.json()
            assert data["drafts_in_gmail"] == 4
    finally:
        app.dependency_overrides.clear()

def test_api_audit_health_audit_alias(audit_test_db):
    app.dependency_overrides[get_db] = lambda: audit_test_db
    client = TestClient(app)

    try:
        # Without token -> 401
        res_unauth = client.get("/api/audit/health/audit")
        assert res_unauth.status_code == 401

        # With admin token -> 200
        res = client.get("/api/audit/health/audit", headers=ADMIN_HEADERS)
        assert res.status_code == 200
        data = res.json()
        assert data["live_jobs"] == 1
        assert data["verified_contacts"] == 1
    finally:
        app.dependency_overrides.clear()
