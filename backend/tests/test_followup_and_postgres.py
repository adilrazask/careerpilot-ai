import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import (
    User, CareerProfile, JobListing, RecruiterContact, ResumeVersion,
    ApplicationRecord, FollowUpTask, AutomationPolicy
)
from app.services.follow_up_service import FollowUpService, add_working_days

@pytest.fixture
def followup_test_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    policy = AutomationPolicy(id=1, enable_auto_follow_ups=True, max_follow_up_cycles=2)
    session.add(policy)

    job = JobListing(
        id=901,
        title="Operations Coordinator",
        company_name="Apex Logistics",
        location="Hyderabad, India",
        original_url="https://example.com/job/901",
        description="Daily operations",
        vacancy_status="VERIFIED_OPEN",
        match_score=85,
        is_seed=False
    )
    session.add(job)

    contact = RecruiterContact(
        job_id=job.id,
        company_name="Apex Logistics",
        contact_name="Priya Sharma",
        email="priya.sharma@apexlogistics.com",
        source_url="https://apexlogistics.com/team",
        verification_method="hunter_verified",
        verification_status="SOURCE_VERIFIED",
        is_seed=False
    )
    session.add(contact)

    app = ApplicationRecord(
        id=1,
        job_id=job.id,
        current_status="APPROVED_BY_USER",
        submission_method="email",
        primary_recipient="priya.sharma@apexlogistics.com",
        thread_id="thread-xyz-12345",
        external_confirmation_id="msg-initial-1"
    )
    session.add(app)
    session.commit()

    yield session
    session.close()

def test_add_working_days_skips_weekends():
    # Friday Oct 23, 2026
    friday = datetime(2026, 10, 23, 12, 0, tzinfo=timezone.utc)
    # +1 working day must be Monday Oct 26
    next_day = add_working_days(friday, 1)
    assert next_day.weekday() == 0 # Monday
    assert next_day.day == 26

    # +5 working days from Friday must be Friday Oct 30
    five_days = add_working_days(friday, 5)
    assert five_days.weekday() == 4 # Friday
    assert five_days.day == 30

def test_max_2_follow_ups_strictly_enforced(followup_test_db):
    session = followup_test_db
    app = session.query(ApplicationRecord).first()

    # Schedule #1
    t1 = FollowUpService.schedule_follow_up_if_eligible(app, session)
    assert t1 is not None
    assert t1.follow_up_sequence == 1

    # Schedule #2
    t2 = FollowUpService.schedule_follow_up_if_eligible(app, session)
    assert t2 is not None
    assert t2.follow_up_sequence == 2

    # Attempt #3 must return None (strictly capped at 2)
    t3 = FollowUpService.schedule_follow_up_if_eligible(app, session)
    assert t3 is None

def test_follow_up_cancelled_on_thread_reply(followup_test_db):
    session = followup_test_db
    app = session.query(ApplicationRecord).first()

    # Create due follow-up task
    task = FollowUpTask(
        application_id=app.id,
        follow_up_sequence=1,
        due_date=datetime.now(timezone.utc) - timedelta(hours=1),
        status="SCHEDULED"
    )
    session.add(task)
    session.commit()

    # Simulate recruiter response in Gmail thread
    mock_messages = [
        {"id": "msg-1", "payload": {"headers": [{"name": "From", "value": "adilrazask@gmail.com"}]}},
        {"id": "msg-2", "payload": {"headers": [{"name": "From", "value": "priya.sharma@apexlogistics.com"}, {"name": "Subject", "value": "Re: Application"}]}}
    ]

    with patch("app.services.gmail_service.GmailService.check_thread_messages", return_value=mock_messages):
        FollowUpService.process_due_follow_ups(session)

    session.refresh(task)
    assert task.status == "CANCELLED_BY_REPLY"
    assert "reply, bounce, or auto-reply detected" in task.notes

def test_follow_up_fail_closed_on_missing_thread_id(followup_test_db):
    session = followup_test_db
    app = session.query(ApplicationRecord).first()
    app.thread_id = None # Missing thread_id
    session.commit()

    task = FollowUpTask(
        application_id=app.id,
        follow_up_sequence=1,
        due_date=datetime.now(timezone.utc) - timedelta(hours=1),
        status="SCHEDULED"
    )
    session.add(task)
    session.commit()

    FollowUpService.process_due_follow_ups(session)

    session.refresh(task)
    assert task.status == "BLOCKED_UNVERIFIED"
    assert "Missing thread_id on application record" in task.notes

def test_follow_up_fail_closed_on_gmail_error(followup_test_db):
    from app.services.gmail_service import GmailAPIError
    session = followup_test_db
    app = session.query(ApplicationRecord).first()
    app.thread_id = "thread-xyz-error"
    session.commit()

    task = FollowUpTask(
        application_id=app.id,
        follow_up_sequence=1,
        due_date=datetime.now(timezone.utc) - timedelta(hours=1),
        status="SCHEDULED"
    )
    session.add(task)
    session.commit()

    with patch("app.services.gmail_service.GmailService.check_thread_messages", side_effect=GmailAPIError("API rate limit or auth error")):
        FollowUpService.process_due_follow_ups(session)

    session.refresh(task)
    assert task.status == "BLOCKED_UNVERIFIED"
    assert "Gmail thread check failed" in task.notes
    assert "Refusing to send unverified follow-up" in task.notes
