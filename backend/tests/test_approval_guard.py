import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import ApplicationRecord, EmailMessage, JobListing
from app.services.approval_guard import (
    check_approval_and_rate_limits,
    get_random_send_delay,
    DAILY_SEND_CAP,
    MIN_SEND_GAP_SECONDS,
    MAX_SEND_GAP_SECONDS,
    IST_TIMEZONE
)

@pytest.fixture
def approval_test_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    job = JobListing(
        id=701,
        title="Operations Executive",
        company_name="Apex Logistics",
        location="Hyderabad, India",
        original_url="https://example.com/job/701",
        description="Daily operations",
        vacancy_status="VERIFIED_OPEN",
        match_score=85
    )
    session.add(job)
    session.commit()

    yield session
    session.close()

def test_unapproved_application_rejected(approval_test_db):
    session = approval_test_db
    app = ApplicationRecord(
        id=1,
        job_id=701,
        current_status="APPLICATION_READY", # Not APPROVED_BY_USER
        primary_recipient="hr@apex.com"
    )
    session.add(app)
    session.commit()

    is_ok, reason = check_approval_and_rate_limits(app, session, enforce_working_hours=False)
    assert is_ok is False
    assert "Only 'APPROVED_BY_USER' rows can be sent" in reason

def test_approved_application_accepted(approval_test_db):
    session = approval_test_db
    app = ApplicationRecord(
        id=2,
        job_id=701,
        current_status="APPROVED_BY_USER",
        primary_recipient="hr@apex.com"
    )
    session.add(app)
    session.commit()

    is_ok, reason = check_approval_and_rate_limits(app, session, enforce_working_hours=False)
    assert is_ok is True
    assert "verified" in reason.lower()

def test_daily_send_cap_15(approval_test_db):
    session = approval_test_db
    app = ApplicationRecord(
        id=3,
        job_id=701,
        current_status="APPROVED_BY_USER",
        primary_recipient="hr@apex.com"
    )
    session.add(app)

    # Insert 15 sent emails today
    now = datetime.now(timezone.utc)
    for i in range(15):
        msg = EmailMessage(
            application_id=app.id,
            direction="outbound",
            status="SENT",
            sender="me@example.com",
            recipient=f"recruiter{i}@example.com",
            subject="Application",
            body_text="Body",
            provider="smtp",
            sent_or_received_at=now - timedelta(seconds=(15 - i) * 5)
        )
        session.add(msg)
    session.commit()

    is_ok, reason = check_approval_and_rate_limits(app, session, enforce_working_hours=False)
    assert is_ok is False
    assert f"Daily send cap ({DAILY_SEND_CAP}) reached" in reason

def test_working_hours_enforcement(approval_test_db):
    session = approval_test_db
    app = ApplicationRecord(
        id=4,
        job_id=701,
        current_status="APPROVED_BY_USER",
        primary_recipient="hr@apex.com"
    )
    session.add(app)
    session.commit()

    # Simulate 8:00 AM IST (outside 10:00-17:00 IST)
    fake_time_early = datetime(2026, 10, 28, 8, 30, tzinfo=IST_TIMEZONE)
    with patch("app.services.approval_guard.datetime") as mock_dt:
        mock_dt.now.return_value = fake_time_early
        mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)

        is_ok, reason = check_approval_and_rate_limits(app, session, enforce_working_hours=True)
        assert is_ok is False
        assert "restricted to 10:00-17:00 IST" in reason

    # Simulate 14:00 (2:00 PM) IST (inside 10:00-17:00 IST)
    fake_time_work = datetime(2026, 10, 28, 14, 0, tzinfo=IST_TIMEZONE)
    with patch("app.services.approval_guard.datetime") as mock_dt:
        mock_dt.now.return_value = fake_time_work
        mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)

        is_ok, reason = check_approval_and_rate_limits(app, session, enforce_working_hours=True)
        assert is_ok is True

def test_random_send_delay_range():
    for _ in range(50):
        delay = get_random_send_delay()
        assert MIN_SEND_GAP_SECONDS <= delay <= MAX_SEND_GAP_SECONDS
