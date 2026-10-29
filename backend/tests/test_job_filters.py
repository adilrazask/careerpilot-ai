import pytest
from app.models import JobListing
from app.services.job_filters import validate_job_filters, validate_email_subject

def test_title_whitelist():
    valid_job = JobListing(
        title="Supply Chain Operations Executive",
        company_name="Apex Logistics",
        location="Hyderabad, India",
        description="Overseeing daily supply chain operations and ERP dispatches.",
        match_score=85
    )
    is_valid, reason = validate_job_filters(valid_job)
    assert is_valid is True

    invalid_title_job = JobListing(
        title="React Frontend Developer",
        company_name="Tech Corp",
        location="Hyderabad, India",
        description="Building React applications with Redux.",
        match_score=85
    )
    is_valid, reason = validate_job_filters(invalid_title_job)
    assert is_valid is False
    assert "does not match allowed title whitelist" in reason

def test_location_filtering():
    foreign_job = JobListing(
        title="Operations Executive",
        company_name="Global Corp",
        location="London, United Kingdom",
        description="London on-site warehouse coordination.",
        match_score=85
    )
    is_valid, reason = validate_job_filters(foreign_job)
    assert is_valid is False
    assert "outside allowed locations" in reason

def test_max_seniority_rejection():
    senior_titles = [
        "Operations Manager",
        "Senior Manager Logistics",
        "Director of Supply Chain",
        "VP of Procurement",
        "Head of Operations",
        "Chief Operations Officer"
    ]
    for st in senior_titles:
        job = JobListing(
            title=st,
            company_name="Apex Logistics",
            location="Hyderabad, India",
            description="Leading regional operations teams.",
            match_score=85
        )
        is_valid, reason = validate_job_filters(job)
        assert is_valid is False
        assert "exceeds maximum allowed seniority" in reason

def test_blocked_keywords():
    blocked_cases = [
        ("Telesales Executive", "Cold calling customers for credit cards"),
        ("Operations Executive", "Work in telemarketing outbound call center"),
        ("Operations Coordinator", "Handling cold calling for merchant onboarding"),
        ("BPO Operations Executive", "International voice process BPO night shifts")
    ]
    for title, desc in blocked_cases:
        job = JobListing(
            title=title,
            company_name="Apex Services",
            location="Hyderabad, India",
            description=desc,
            match_score=85
        )
        is_valid, reason = validate_job_filters(job)
        assert is_valid is False
        assert "contains blocked keyword" in reason

def test_min_fit_score_70():
    low_fit_job = JobListing(
        title="Operations Executive",
        company_name="Apex Logistics",
        location="Hyderabad, India",
        description="General office operations.",
        match_score=65 # Below 70
    )
    is_valid, reason = validate_job_filters(low_fit_job, min_fit_score=70)
    assert is_valid is False
    assert "below required threshold" in reason

def test_subject_validation():
    # Digits at start
    is_val, r = validate_email_subject("4,000+ Operations Executive — Direct Employer")
    assert is_val is False
    assert "cannot start with digits" in r

    is_val, r = validate_email_subject("1567 Erp Implementation — Job Lead")
    assert is_val is False
    assert "cannot start with digits" in r

    # Portal names in subject
    is_val, r = validate_email_subject("Application for Operations Executive — Naukri.com")
    assert is_val is False
    assert "contains portal name" in r

    is_val, r = validate_email_subject("Indeed Application: Operations Coordinator")
    assert is_val is False
    assert "contains portal name" in r

    # Clean valid subject
    is_val, r = validate_email_subject("Application for Operations Executive – Adil | Operations, ERP")
    assert is_val is True
    assert "Subject line is valid" in r
