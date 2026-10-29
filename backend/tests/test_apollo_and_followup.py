from __future__ import annotations
import uuid
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.database import SessionLocal
from app.database_init import init_db
from app.models import (
    JobListing, RecruiterContact, ApplicationRecord, FollowUpTask,
    AutomationPolicy, RecruiterResponse, IntegrationCredentialsMetadata, ResumeVersion,
    CareerProfile
)
from app.services.adapters.apollo_adapter import ApolloContactAdapter
from app.services.contact_service import ContactService
from app.services.follow_up_service import FollowUpService
from app.services.integrations import IntegrationManager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base, get_db

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    policy = AutomationPolicy(id=1, is_autonomous_enabled=True, enable_auto_follow_ups=True)
    session.add(policy)
    session.commit()
    try:
        yield session
    finally:
        session.close()

def test_apollo_connection_test_missing_key():
    """Verify Apollo connection returns UNCONFIGURED when no key is set."""
    res = ApolloContactAdapter.test_connection(api_key="")
    assert res["status"] == "UNCONFIGURED"
    assert "not configured" in res["message"].lower() or "missing" in res["message"].lower()

def test_apollo_connection_test_mock_success():
    """Verify Apollo connection returns SUCCESS when key is valid."""
    with patch("requests.get") as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"healthy": True}
        res = ApolloContactAdapter.test_connection(api_key="valid_apollo_key_123")
        assert res["status"] == "SUCCESS"
        assert "authenticated successfully" in res["message"].lower()

def test_apollo_search_hr_contacts_parsing():
    """Verify ApolloContactAdapter extracts names, titles, verified emails, and phone numbers."""
    mock_payload = {
        "people": [
            {
                "id": "apol_001",
                "first_name": "Priya",
                "last_name": "Sharma",
                "name": "Priya Sharma",
                "title": "Lead Talent Acquisition Specialist",
                "email": "priya.sharma@targetcorp.com",
                "email_status": "verified",
                "sanitized_phone": "+91 98765 43210",
                "linkedin_url": "https://www.linkedin.com/in/priyasharma",
                "organization": {
                    "name": "Target Corp",
                    "website_url": "https://targetcorp.com"
                }
            }
        ]
    }
    with patch("requests.post") as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = mock_payload

        results = ApolloContactAdapter.search_hr_contacts(
            company_name="Target Corp",
            domain="targetcorp.com",
            location="Hyderabad, India",
            api_key="test_key"
        )
        assert len(results) == 1
        rec = results[0]
        assert rec["name"] == "Priya Sharma"
        assert rec["title"] == "Lead Talent Acquisition Specialist"
        assert rec["email"] == "priya.sharma@targetcorp.com"
        assert rec["phone"] == "+91 98765 43210"
        assert rec["email_status"] == "verified"
        assert "app.apollo.io/#/people/apol_001" in rec["source_url"]

def test_contact_service_discover_apollo_contacts(db):
    """Verify ContactService ingests Apollo contacts, performs DNS checks, and stores them in DB."""
    # Ensure job exists
    uid = uuid.uuid4().hex
    job = JobListing(
        title="Operations Executive",
        company_name="Global Steel Works Ltd",
        location="Hyderabad, India",
        source_platform="LinkedIn",
        original_url=f"https://example.com/jobs/{uid}",
        canonical_url=f"https://example.com/jobs/{uid}",
        description="Operations coordination and procurement role.",
        vacancy_status="VERIFIED_OPEN"
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    mock_people = [
        {
            "name": "Rahul Verma",
            "title": "Head of Human Resources",
            "email": "rahul.verma@globalsteelworks.com",
            "phone": "+91 9123456780",
            "linkedin_url": "https://linkedin.com/in/rahulverma",
            "organization_name": "Global Steel Works Ltd",
            "email_status": "verified",
            "apollo_id": "apol_999",
            "source_url": "https://app.apollo.io/#/people/apol_999"
        }
    ]

    with patch("app.services.adapters.apollo_adapter.ApolloContactAdapter.search_hr_contacts", return_value=mock_people):
        with patch("app.config.settings.APOLLO_API_KEY", "mock_apollo_key"):
            discovered = ContactService.discover_apollo_contacts(
                company_name="Global Steel Works Ltd",
                location="Hyderabad, India",
                db=db,
                job_id=job.id
            )
            assert len(discovered) >= 1
            contact = discovered[0]
            assert contact.email == "rahul.verma@globalsteelworks.com"
            assert contact.phone == "+91 9123456780"
            assert contact.contact_role == "Head of Human Resources"
            assert contact.verification_status in ["SOURCE_VERIFIED", "EMAIL_VALIDATED"]
            assert contact.confidence >= 0.9

def test_15_day_follow_up_cadence_scheduling(db):
    """Verify follow-up engine schedules follow-up #1 exactly 15 days out by default."""
    policy = db.query(AutomationPolicy).filter_by(id=1).first()
    policy.enable_auto_follow_ups = True
    policy.follow_up_interval_days = 15
    policy.max_follow_up_cycles = 3
    db.commit()

    # Create test job and application
    uid2 = uuid.uuid4().hex
    job = JobListing(
        title="Supply Chain Coordinator",
        company_name="Schneider Electric India",
        location="Hyderabad, India",
        original_url=f"https://schneider-electric.com/jobs/{uid2}",
        canonical_url=f"https://schneider-electric.com/jobs/{uid2}",
        description="Supply chain and logistics coordinator position.",
        vacancy_status="VERIFIED_OPEN"
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    app_rec = ApplicationRecord(
        job_id=job.id,
        current_status="EMAIL_SENT",
        primary_recipient="priya.sharma@schneiderelectric.com"
    )
    db.add(app_rec)
    db.commit()
    db.refresh(app_rec)

    # Schedule follow-up
    task = FollowUpService.schedule_follow_up_if_eligible(app_rec, db)
    assert task is not None
    assert task.follow_up_sequence == 1
    assert task.status == "SCHEDULED"

    # Due date should be 5 working days in the future (around 7 calendar days)
    now_ts = datetime.now(timezone.utc)
    due = task.due_date if task.due_date.tzinfo else task.due_date.replace(tzinfo=timezone.utc)
    delta_days = (due - now_ts).total_seconds() / 86400
    assert 4.5 <= delta_days <= 8.5
    assert "Supply Chain Coordinator" in task.draft_subject
    assert "submitted my application" in task.draft_body or "check in" in task.draft_body

def test_process_due_follow_up_sends_email_and_schedules_next_cycle(db):
    """Verify due follow-up is delivered via email service and automatically schedules sequence #2 for +15 days."""
    policy = db.query(AutomationPolicy).filter_by(id=1).first()
    policy.enable_auto_follow_ups = True
    policy.follow_up_interval_days = 15
    policy.max_follow_up_cycles = 3
    db.commit()

    uid3 = uuid.uuid4().hex
    job = JobListing(
        title="Business Operations Lead",
        company_name="Mahindra Logistics",
        location="Hyderabad, India",
        original_url=f"https://mahindralogistics.com/jobs/{uid3}",
        canonical_url=f"https://mahindralogistics.com/jobs/{uid3}",
        description="Lead operational efficiency and dispatching.",
        vacancy_status="VERIFIED_OPEN"
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    app_rec = ApplicationRecord(
        job_id=job.id,
        current_status="EMAIL_SENT",
        primary_recipient="priya.sharma@mahindralogistics.com",
        thread_id="thread-mahindra-test-001"
    )
    db.add(app_rec)
    db.commit()
    db.refresh(app_rec)

    # Task is due right now (simulate days elapsed)
    past_due = datetime.now(timezone.utc) - timedelta(hours=1)
    task1 = FollowUpTask(
        application_id=app_rec.id,
        follow_up_sequence=1,
        due_date=past_due,
        status="SCHEDULED",
        draft_subject="Following up: Business Operations Lead",
        draft_body="Dear Hiring Team, politely following up."
    )
    db.add(task1)
    db.commit()

    with patch("app.services.gmail_service.GmailService.check_thread_messages", return_value=[]):
        results = FollowUpService.process_due_follow_ups(db)
    assert len(results) >= 1
    db.refresh(task1)
    assert task1.status == "SENT"
    assert task1.sent_at is not None

    # Check that sequence #2 was automatically scheduled for 15 days later!
    tasks = db.query(FollowUpTask).filter_by(application_id=app_rec.id).order_by(FollowUpTask.follow_up_sequence.asc()).all()
    assert len(tasks) == 2
    task2 = tasks[1]
    assert task2.follow_up_sequence == 2
    assert task2.status == "SCHEDULED"
    # Sequence 2 due date should be 7 working days in the future (around 9-11 calendar days)
    now_ts = datetime.now(timezone.utc)
    due2 = task2.due_date if task2.due_date.tzinfo else task2.due_date.replace(tzinfo=timezone.utc)
    delta_days = (due2 - now_ts).total_seconds() / 86400
    assert 6.5 <= delta_days <= 11.5

def test_api_configure_integration_endpoint(client):
    """Verify POST /api/integrations/configure updates provider key and metadata."""
    res = client.post("/api/integrations/configure", json={
        "provider_name": "Apollo.io (Apollo AI)",
        "api_key": "apol_live_test_key_xyz987"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "SUCCESS"
    assert data["is_configured"] is True
    assert "apol_l" in data["masked_key_hint"]
