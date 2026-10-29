import os
import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import (
    User, CareerProfile, JobListing, RecruiterContact, ResumeVersion,
    ApplicationRecord, AutomationPolicy, EmailMessage
)
from app.services.gmail_service import GmailService, GmailAPIError
from app.services.email_service import EmailOutreachService

@pytest.fixture
def sender_test_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    user = User(id=1, email="test@candidate.com", full_name="Adil")
    session.add(user)
    session.commit()

    profile = CareerProfile(id=1, user_id=1, full_name="Adil", email="test@candidate.com", phone="+919000000000")
    session.add(profile)

    job = JobListing(
        id=801,
        title="Operations Coordinator",
        company_name="Apex Logistics",
        location="Hyderabad, India",
        original_url="https://example.com/job/801",
        description="Operations management and ERP tracking.",
        vacancy_status="VERIFIED_OPEN",
        match_score=85,
        is_seed=False
    )
    session.add(job)
    session.commit()

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
    session.commit()

    resume = ResumeVersion(id=1, profile_id=1, version_name="v1", full_text="Resume text")
    session.add(resume)
    session.commit()

    app = ApplicationRecord(
        id=1,
        job_id=job.id,
        current_status="APPROVED_BY_USER",
        submission_method="email",
        primary_recipient="priya.sharma@apexlogistics.com"
    )
    session.add(app)
    session.commit()

    yield session
    session.close()

def test_missing_credentials_raises_error():
    # Ensure no token in environment
    with patch.dict(os.environ, {}, clear=True):
        with patch("os.path.exists", return_value=False):
            with pytest.raises(GmailAPIError, match="Gmail API credentials missing"):
                GmailService.get_access_token()

def test_no_silent_fallback_to_mock_when_real_send_fails(sender_test_db):
    session = sender_test_db
    app = session.query(ApplicationRecord).first()
    rv = session.query(ResumeVersion).first()

    with patch.dict(os.environ, {"EMAIL_PROVIDER": "gmail_api", "GMAIL_API_TOKEN": "", "GMAIL_OAUTH_TOKEN": ""}):
        orig_exists = os.path.exists
        def custom_exists(p):
            if "token.json" in str(p):
                return False
            return orig_exists(p)

        with patch("os.path.exists", side_effect=custom_exists):
            # Must raise GmailAPIError, NEVER fall back to mock
            with pytest.raises(GmailAPIError, match="Gmail API credentials missing"):
                EmailOutreachService.send_application_email(app, rv, session)

def test_mock_send_explicitly_labelled_mock(sender_test_db):
    session = sender_test_db
    app = session.query(ApplicationRecord).first()
    rv = session.query(ResumeVersion).first()

    with patch.dict(os.environ, {"EMAIL_PROVIDER": "dry_run"}):
        res = EmailOutreachService.send_application_email(app, rv, session)
        assert res["status"] == "SUCCESS"
        assert res["evidence"]["provider"] == "MOCK"
        assert app.current_status == "MOCK_SENT"

        # Check DB record
        email_rec = session.query(EmailMessage).filter_by(application_id=app.id).first()
        assert email_rec is not None
        assert email_rec.provider == "MOCK"
        assert email_rec.status == "MOCK_SENT"
        assert email_rec.thread_id.startswith("mock-thread-")

def test_gmail_api_send_and_save_ids():
    with patch.dict(os.environ, {"GMAIL_API_TOKEN": "mock-token-xyz"}):
        with patch("requests.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "id": "18c01ab23def456",
                "threadId": "18c01ab23def999"
            }
            mock_post.return_value = mock_resp

            res = GmailService.send_message(
                sender="me@example.com",
                recipient="hr@apex.com",
                subject="Application",
                body_text="Hello"
            )

            assert res["message_id"] == "18c01ab23def456"
            assert res["thread_id"] == "18c01ab23def999"
            assert res["provider"] == "GMAIL_API"

def test_gmail_api_create_draft():
    with patch.dict(os.environ, {"GMAIL_API_TOKEN": "mock-token-xyz"}):
        with patch("requests.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "id": "r-draft-12345",
                "message": {
                    "id": "msg-draft-123",
                    "threadId": "thread-draft-123"
                }
            }
            mock_post.return_value = mock_resp

            draft = GmailService.create_draft(
                sender="me@example.com",
                recipient="hr@apex.com",
                subject="Draft Application",
                body_text="Draft body"
            )

            assert draft["draft_id"] == "r-draft-12345"
            assert draft["message_id"] == "msg-draft-123"
            assert draft["thread_id"] == "thread-draft-123"
            assert draft["status"] == "DRAFT_CREATED"
