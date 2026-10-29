import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import JobListing
from app.services.job_validator import check_live_job_url, validate_job_freshness
from app.services.adil_email_drafter import AdilEmailDrafter

@pytest.fixture
def job_val_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

def test_check_live_job_url_success():
    with patch("requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "<html><body><h1>Operations Executive</h1><p>Active Job Posting</p></body></html>"
        mock_get.return_value = mock_resp

        is_valid, reason, code = check_live_job_url("https://example.com/job/123")
        assert is_valid is True
        assert code == 200

def test_check_live_job_url_non_200():
    with patch("requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_get.return_value = mock_resp

        is_valid, reason, code = check_live_job_url("https://example.com/job/404")
        assert is_valid is False
        assert code == 404
        assert "non-200" in reason

def test_check_live_job_url_closed_text():
    with patch("requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "<html><body>This position has been filled. No longer accepting applications.</body></html>"
        mock_get.return_value = mock_resp

        is_valid, reason, code = check_live_job_url("https://example.com/job/closed")
        assert is_valid is False
        assert "no longer accepting applications" in reason

def test_validate_job_freshness_within_24h(job_val_db):
    session = job_val_db
    recent_time = datetime.now(timezone.utc) - timedelta(hours=2)
    job = JobListing(
        id=501,
        title="Operations Coordinator",
        company_name="Apex Logistics",
        location="Hyderabad, India",
        original_url="https://example.com/job/fresh",
        description="Operations and ERP workflow management",
        vacancy_status="VERIFIED_OPEN",
        last_verified_at=recent_time
    )
    session.add(job)
    session.commit()

    # Should pass without making an HTTP request
    validated_job = validate_job_freshness(job, session, max_age_hours=24)
    assert validated_job.id == 501
    assert validated_job.vacancy_status == "VERIFIED_OPEN"

def test_validate_job_freshness_older_than_24h_fails(job_val_db):
    session = job_val_db
    old_time = datetime.now(timezone.utc) - timedelta(hours=25)
    job = JobListing(
        id=502,
        title="Operations Coordinator",
        company_name="Apex Logistics",
        location="Hyderabad, India",
        original_url="https://example.com/job/stale",
        description="Operations and ERP workflow management",
        vacancy_status="VERIFIED_OPEN",
        last_verified_at=old_time
    )
    session.add(job)
    session.commit()

    with patch("requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_get.return_value = mock_resp

        with pytest.raises(ValueError, match="Job validation rejected"):
            validate_job_freshness(job, session, max_age_hours=24)

        assert job.vacancy_status == "CLOSED"

def test_drafter_rejects_expired_job_url():
    with patch("requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "Job expired. Position closed."
        mock_get.return_value = mock_resp

        with pytest.raises(ValueError, match="Job drafting rejected"):
            AdilEmailDrafter.draft(
                job_title="Operations Executive",
                company_name="Stale Corp",
                jd_text="Operations and ERP",
                job_url="https://example.com/expired-job",
                last_verified_at=datetime.now(timezone.utc) - timedelta(hours=30)
            )
