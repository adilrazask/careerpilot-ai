import pytest
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import (
    User, CareerProfile, JobListing, RecruiterContact, ResumeVersion,
    ApplicationRecord, ApplicationAttempt, AutomationPolicy
)
from app.services.email_service import EmailOutreachService

@pytest.fixture
def seed_test_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # User & profile
    user = User(id=1, email="test@candidate.com", full_name="Adil")
    session.add(user)
    session.commit()

    profile = CareerProfile(id=1, user_id=1, full_name="Adil", email="test@candidate.com", phone="+919000000000")
    session.add(profile)

    resume = ResumeVersion(id=1, profile_id=1, version_name="Default", full_text="Resume text")
    session.add(resume)

    policy = AutomationPolicy(id=1, custom_application_subject="Test", custom_application_body="Test")
    session.add(policy)
    session.commit()

    yield session
    session.close()

def test_seed_flag_blocks_application_send(seed_test_db):
    session = seed_test_db

    # Create a seed job
    seed_job = JobListing(
        id=101,
        title="Operations Lead",
        company_name="Seed Logistics",
        location="Hyderabad, India",
        original_url="https://example.com/seed-job-1",
        description="Seed JD description",
        is_seed=True,
        vacancy_status="VERIFIED_OPEN"
    )
    session.add(seed_job)
    session.commit()

    app = ApplicationRecord(
        id=1,
        job_id=seed_job.id,
        current_status="APPROVED_BY_USER",
        primary_recipient="recruiter@seedlogistics.com"
    )
    session.add(app)
    session.commit()

    resume = session.query(ResumeVersion).first()

    with pytest.raises(ValueError, match="marked as SEED data"):
        EmailOutreachService.send_application_email(
            application=app,
            resume_version=resume,
            db=session
        )

def test_seed_contact_blocks_application_send(seed_test_db):
    session = seed_test_db

    # Create a non-seed job, but with a seed contact
    live_job = JobListing(
        id=102,
        title="Supply Chain Executive",
        company_name="Live Corp",
        location="Hyderabad, India",
        original_url="https://example.com/live-job-2",
        description="Live JD description",
        is_seed=False,
        vacancy_status="VERIFIED_OPEN"
    )
    session.add(live_job)
    session.commit()

    seed_contact = RecruiterContact(
        id=201,
        job_id=live_job.id,
        company_name="Live Corp",
        contact_name="HR Seed",
        email="hr.seed@livecorp.com",
        is_seed=True,
        verification_status="SOURCE_VERIFIED"
    )
    session.add(seed_contact)
    session.commit()

    app = ApplicationRecord(
        id=2,
        job_id=live_job.id,
        current_status="APPROVED_BY_USER",
        primary_recipient="hr.seed@livecorp.com"
    )
    session.add(app)
    session.commit()

    resume = session.query(ResumeVersion).first()

    with pytest.raises(ValueError, match="marked as SEED data"):
        EmailOutreachService.send_application_email(
            application=app,
            resume_version=resume,
            db=session
        )
