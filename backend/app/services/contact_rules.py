"""
Strict Recruiter Contact Validation Service
Enforces Step 3 contact rules:
1. Block generic local parts: info, support, service, hello, contact, noreply, no-reply, accommodations, leaves, careers (>1000 staff)
2. Block job portal domains (naukri, indeed, linkedin, apna, etc.)
3. Require contact_source_url (valid http/https URL)
4. Require real verifier result (Hunter / ZeroBounce / Apollo); MX-only is NOT enough.
"""
from __future__ import annotations
import re
from typing import Tuple, Optional
from app.models import RecruiterContact, CompanyProfile

BLOCKED_LOCAL_PARTS = {
    "info", "support", "service", "hello", "contact",
    "noreply", "no-reply", "accommodations", "leaves"
}

BLOCKED_PORTAL_DOMAINS = [
    "naukri", "indeed", "linkedin", "apna", "workindia", "monster", "shine"
]

def validate_contact_rules(
    contact: RecruiterContact,
    company_employee_count: Optional[int] = None
) -> Tuple[bool, str]:
    """
    Validates a recruiter contact against Step 3 rules:
    Returns (is_valid, rejection_reason).
    """
    email = (contact.email or "").strip().lower()
    if not email or "@" not in email:
        return False, "Missing or invalid email address format."

    local_part, domain = email.split("@", 1)
    local_part_clean = local_part.strip().lower()

    # 1. Blocked local parts
    if local_part_clean in BLOCKED_LOCAL_PARTS:
        return False, f"Blocked generic email prefix: '{local_part}@'"

    # careers blocked for companies over 1000 staff
    if local_part_clean == "careers":
        emp_count = company_employee_count
        if emp_count is None and hasattr(contact, "company") and contact.company:
            emp_count = getattr(contact.company, "employee_count", None)
        # If employee count is explicitly > 1000 or company is known enterprise (>1000)
        if emp_count is not None and emp_count > 1000:
            return False, f"Blocked 'careers@' email for large enterprise (>1000 staff: {emp_count})"

    # 2. Block portal domains
    domain_clean = domain.lower()
    for portal in BLOCKED_PORTAL_DOMAINS:
        if portal in domain_clean:
            return False, f"Blocked portal domain '{domain}' (cannot dispatch to aggregator/portal domains)"

    # 3. Require contact_source_url
    source_url = (contact.source_url or "").strip()
    if not source_url or not (source_url.startswith("http://") or source_url.startswith("https://")):
        return False, f"Missing or invalid contact_source_url: '{source_url}' (proof of origin URL required)"

    # 4. Require real verifier result (Hunter / ZeroBounce / Apollo); MX-only is NOT enough
    allowed_methods = {"hunter_verified", "zerobounce_verified", "apollo_ai_verified"}
    method = (contact.verification_method or "").strip().lower()
    status = (contact.verification_status or "").strip().upper()

    if method in {"mx_check", "dns_mx_check", "official_source_and_mx", "official_careers_page", "official_careers_channel"}:
        return False, f"Verification method '{contact.verification_method}' rejected: MX-only verification is not enough. Real verifier (Hunter/ZeroBounce/Apollo) required."

    if method not in allowed_methods:
        return False, f"Contact verification method '{contact.verification_method}' is unapproved. Must be one of: {allowed_methods}"

    if status not in {"SOURCE_VERIFIED", "VERIFIED"}:
        return False, f"Contact verification status '{contact.verification_status}' is insufficient. Must be SOURCE_VERIFIED or VERIFIED."

    return True, "Contact passed all verification rules."
