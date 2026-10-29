"""
Job Filters & Subject Validation Service
Enforces Step 4 rules:
1. Title whitelist (operations, logistics, supply chain, procurement, ERP, etc.)
2. Allowed locations (Hyderabad, Secunderabad, Telangana, Remote, India)
3. Max seniority (Reject manager, senior manager, director, vp, head, lead, chief)
4. Blocked keywords in title/description (telesales, telemarketing, cold calling, bpo, etc.)
5. Min fit score: >= 70
6. Subject validation: reject subjects starting with digits or containing portal names
"""
from __future__ import annotations
import re
from typing import Tuple, List, Optional
from app.models import JobListing

DEFAULT_TITLE_WHITELIST = [
    "operations", "supply chain", "logistics", "procurement", "inventory",
    "erp", "coordinator", "executive", "analyst", "dispatch", "purchase",
    "warehouse", "commercial"
]

DEFAULT_ALLOWED_LOCATIONS = [
    "hyderabad", "secunderabad", "telangana", "remote", "india"
]

BLOCKED_SENIORITY_KEYWORDS = [
    "manager", "sr. manager", "senior manager", "director", "vp",
    "vice president", "head", "lead", "chief", "partner"
]

BLOCKED_JOB_KEYWORDS = [
    "telesales", "telemarketing", "cold calling", "telecaller",
    "call center", "bpo", "manager+"
]

BLOCKED_PORTAL_NAMES_IN_SUBJECT = [
    "naukri", "indeed", "linkedin", "apna", "monster", "shine", "glassdoor"
]

def validate_job_filters(
    job: JobListing,
    min_fit_score: int = 70,
    title_whitelist: Optional[List[str]] = None,
    allowed_locations: Optional[List[str]] = None
) -> Tuple[bool, str]:
    """
    Validates job title whitelist, location, max seniority, blocked keywords, and min fit score.
    Returns (is_valid, reason).
    """
    whitelist = title_whitelist or DEFAULT_TITLE_WHITELIST
    locations = allowed_locations or DEFAULT_ALLOWED_LOCATIONS

    title_lower = (job.title or "").strip().lower()
    desc_lower = (job.description or "").strip().lower()
    loc_lower = (job.location or "").strip().lower()

    # 1. Configurable title whitelist
    if not any(w in title_lower for w in whitelist):
        return False, f"Job title '{job.title}' does not match allowed title whitelist: {whitelist}"

    # 2. Allowed locations
    if not any(loc in loc_lower for loc in locations):
        return False, f"Job location '{job.location}' is outside allowed locations: {locations}"

    # 3. Max Seniority
    for senior_kw in BLOCKED_SENIORITY_KEYWORDS:
        # Check as word boundary
        pattern = r"\b" + re.escape(senior_kw) + r"\b"
        if re.search(pattern, title_lower):
            return False, f"Job exceeds maximum allowed seniority: contains '{senior_kw}' in title ('{job.title}')"

    # 4. Blocked Keywords
    full_text = f"{title_lower} {desc_lower}"
    for blocked_kw in BLOCKED_JOB_KEYWORDS:
        pattern = r"\b" + re.escape(blocked_kw) + r"\b"
        if re.search(pattern, full_text):
            return False, f"Job contains blocked keyword: '{blocked_kw}'"

    # 5. Min fit score 70
    score = job.match_score or 0
    if score < min_fit_score:
        return False, f"Job match score {score} is below required threshold ({min_fit_score})"

    return True, "Job passed all qualification filters."

def validate_email_subject(subject: str) -> Tuple[bool, str]:
    """
    Validates email subject line:
    - Must NOT start with digits (e.g. '4,000+ Operations Executive', '1567 Erp')
    - Must NOT contain portal names (naukri, indeed, linkedin, apna, etc.)
    """
    clean_subj = (subject or "").strip()
    if not clean_subj:
        return False, "Subject line is empty."

    # Reject subjects starting with digits
    if re.match(r"^\s*\d", clean_subj):
        return False, f"Subject line rejected: cannot start with digits ('{clean_subj}')"

    # Reject subjects containing portal names
    subj_lower = clean_subj.lower()
    for portal in BLOCKED_PORTAL_NAMES_IN_SUBJECT:
        pattern = r"\b" + re.escape(portal) + r"\b"
        if re.search(pattern, subj_lower):
            return False, f"Subject line rejected: contains portal name '{portal}' ('{clean_subj}')"

    return True, "Subject line is valid."
