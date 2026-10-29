import pytest
from app.models import RecruiterContact, CompanyProfile
from app.services.contact_rules import validate_contact_rules

def test_blocked_local_parts():
    blocked_emails = [
        "info@apexlogistics.com",
        "support@supplychain.in",
        "service@delivery.com",
        "hello@startup.io",
        "contact@freightcorp.com",
        "noreply@automated.com",
        "no-reply@company.com",
        "accommodations@nestle.com",
        "leaves@enterprise.com"
    ]
    for email in blocked_emails:
        rc = RecruiterContact(
            email=email,
            company_name="Test Corp",
            source_url="https://testcorp.com/careers",
            verification_method="hunter_verified",
            verification_status="SOURCE_VERIFIED"
        )
        is_valid, reason = validate_contact_rules(rc)
        assert is_valid is False
        assert "Blocked generic email prefix" in reason

def test_careers_blocked_for_over_1000_staff():
    rc = RecruiterContact(
        email="careers@megacorp.com",
        company_name="MegaCorp",
        source_url="https://megacorp.com/careers",
        verification_method="hunter_verified",
        verification_status="SOURCE_VERIFIED"
    )
    # Company with 5000 employees
    is_valid, reason = validate_contact_rules(rc, company_employee_count=5000)
    assert is_valid is False
    assert "Blocked 'careers@' email for large enterprise" in reason

def test_blocked_portal_domains():
    portal_emails = [
        "recruiter@naukri.com",
        "hr@indeed.com",
        "talent@linkedin.com",
        "hiring@apna.co"
    ]
    for email in portal_emails:
        rc = RecruiterContact(
            email=email,
            company_name="Portal Corp",
            source_url="https://portal.com",
            verification_method="hunter_verified",
            verification_status="SOURCE_VERIFIED"
        )
        is_valid, reason = validate_contact_rules(rc)
        assert is_valid is False
        assert "Blocked portal domain" in reason

def test_require_source_url():
    rc = RecruiterContact(
        email="priya.sharma@apexsupply.com",
        company_name="Apex Supply",
        source_url="", # Missing source URL
        verification_method="hunter_verified",
        verification_status="SOURCE_VERIFIED"
    )
    is_valid, reason = validate_contact_rules(rc)
    assert is_valid is False
    assert "Missing or invalid contact_source_url" in reason

def test_mx_only_rejected():
    rc = RecruiterContact(
        email="priya.sharma@apexsupply.com",
        company_name="Apex Supply",
        source_url="https://apexsupply.com/team",
        verification_method="mx_check", # MX only
        verification_status="EMAIL_VALIDATED"
    )
    is_valid, reason = validate_contact_rules(rc)
    assert is_valid is False
    assert "MX-only verification is not enough" in reason

def test_real_verifier_hunter_zerobounce_accepted():
    for method in ["hunter_verified", "zerobounce_verified", "apollo_ai_verified"]:
        rc = RecruiterContact(
            email="priya.sharma@apexsupply.com",
            company_name="Apex Supply",
            source_url="https://apexsupply.com/team",
            verification_method=method,
            verification_status="SOURCE_VERIFIED"
        )
        is_valid, reason = validate_contact_rules(rc, company_employee_count=200)
        assert is_valid is True
        assert "Contact passed all verification rules" in reason
