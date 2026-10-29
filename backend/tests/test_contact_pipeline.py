import pytest
from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models import JobListing, RecruiterContact
from app.services.contact_pipeline import ContactPipeline
from app.services.contact_rules import validate_contact_rules

@pytest.fixture
def pipeline_test_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

def test_extract_from_jd_text_and_verify(pipeline_test_db):
    session = pipeline_test_db
    job = JobListing(
        id=101,
        title="Operations Executive",
        company_name="Apex Logistics",
        original_url="https://apexlogistics.com/jobs/101",
        description="Please send your CV directly to priya.sharma@apexlogistics.com for review.",
        is_seed=False
    )
    session.add(job)
    session.commit()

    # Mock Hunter verifier returning deliverable
    with patch("app.services.contact_pipeline.ContactPipeline.verify_email_deliverability", return_value=(True, "hunter_verified", "Hunter score 99")):
        contact = ContactPipeline.find_and_verify_hr_contact_for_job(job, session)

    assert contact is not None
    assert contact.email == "priya.sharma@apexlogistics.com"
    assert contact.source_url == "https://apexlogistics.com/jobs/101"
    assert contact.verification_status == "SOURCE_VERIFIED"
    assert contact.verification_method == "hunter_verified"

    # Confirm contact passes Step 3 rules
    ok, reason = validate_contact_rules(contact)
    assert ok is True

def test_extract_from_careers_page_when_not_in_jd(pipeline_test_db):
    session = pipeline_test_db
    job = JobListing(
        id=102,
        title="Supply Chain Coordinator",
        company_name="LogiFlow Solutions",
        original_url="https://logiflow.com/jobs/102",
        description="Apply through our portal or reach out to our team.",
        is_seed=False
    )
    session.add(job)
    session.commit()

    with patch("app.services.contact_pipeline.ContactPipeline.extract_from_careers_page", return_value=("careers.hr@logiflow.com", "https://logiflow.com/careers", "company_careers_page")):
        with patch("app.services.contact_pipeline.ContactPipeline.verify_email_deliverability", return_value=(True, "zerobounce_verified", "ZeroBounce valid")):
            contact = ContactPipeline.find_and_verify_hr_contact_for_job(job, session, domain="logiflow.com")

    assert contact is not None
    assert contact.email == "careers.hr@logiflow.com"
    assert contact.source_url == "https://logiflow.com/careers"
    assert contact.verification_status == "SOURCE_VERIFIED"
    assert contact.verification_method == "zerobounce_verified"

def test_extract_from_hunter_apollo_when_careers_page_missing(pipeline_test_db):
    session = pipeline_test_db
    job = JobListing(
        id=103,
        title="Vendor Operations Specialist",
        company_name="MetalWorks India",
        original_url="https://metalworks.example.com/jobs/103",
        description="Responsible for vendor POs and ERP reconciliations.",
        is_seed=False
    )
    session.add(job)
    session.commit()

    with patch("app.services.contact_pipeline.ContactPipeline.extract_from_careers_page", return_value=None):
        with patch("app.services.contact_pipeline.ContactPipeline.extract_from_hunter_or_apollo", return_value=("kavita.nair@metalworks.com", "https://api.hunter.io/v2/domain-search?domain=metalworks.com", "hunter_api")):
            with patch("app.services.contact_pipeline.ContactPipeline.verify_email_deliverability", return_value=(True, "hunter_verified", "Hunter score 95")):
                contact = ContactPipeline.find_and_verify_hr_contact_for_job(job, session)

    assert contact is not None
    assert contact.email == "kavita.nair@metalworks.com"
    assert "hunter.io" in contact.source_url
    assert contact.verification_status == "SOURCE_VERIFIED"

def test_no_verifier_result_blocks_send(pipeline_test_db):
    session = pipeline_test_db
    job = JobListing(
        id=104,
        title="Warehouse Coordinator",
        company_name="FastFreight",
        original_url="https://fastfreight.com/jobs/104",
        description="Email rajesh@fastfreight.com with resume.",
        is_seed=False
    )
    session.add(job)
    session.commit()

    # When Hunter and ZeroBounce return no result (e.g. unverified or no API keys)
    with patch("app.services.contact_pipeline.ContactPipeline.verify_email_deliverability", return_value=(False, "unverified", "No verifier result")):
        contact = ContactPipeline.find_and_verify_hr_contact_for_job(job, session)

    assert contact is not None
    assert contact.email == "rajesh@fastfreight.com"
    assert contact.verification_status == "UNVERIFIED"

    # Strict rule: No verifier result = no send
    ok, reason = validate_contact_rules(contact)
    assert ok is False
    assert "hunter_verified" in reason or "Real verifier" in reason
