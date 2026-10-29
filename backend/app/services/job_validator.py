"""
Job Listing Live Validation Service
Ensures no job is drafted or dispatched unless verified live within 24 hours.
Requires HTTP 200 and absence of closed/expired keywords.
"""
from __future__ import annotations
import re
import requests
from datetime import datetime, timezone, timedelta
from typing import Tuple, Optional
from sqlalchemy.orm import Session
from app.models import JobListing

CLOSED_PATTERNS = [
    "no longer accepting applications",
    "job is closed",
    "job expired",
    "this job has expired",
    "posting has closed",
    "position has been filled",
    "not accepting applications",
    "inactive job",
    "page not found",
    "404 not found",
    "this posting has expired",
    "this vacancy is closed",
    "job not found",
    "opening is closed",
    "closed for applications"
]

def check_live_job_url(url: str, timeout: int = 10) -> Tuple[bool, str, Optional[int]]:
    """
    Fetches the job URL via HTTP.
    Requires HTTP 200 and checks body for closure phrases.
    Returns (is_valid, reason, http_status).
    """
    if not url or not (url.startswith("http://") or url.startswith("https://")):
        return False, "Invalid or missing job URL format", None

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    }

    try:
        resp = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        if resp.status_code != 200:
            return False, f"Job URL returned non-200 HTTP status ({resp.status_code})", resp.status_code

        body_lower = resp.text.lower()
        for pattern in CLOSED_PATTERNS:
            if pattern in body_lower:
                return False, f"Job page indicates closure/expiration: '{pattern}'", resp.status_code

        return True, "Job page active and accepting applications", 200
    except requests.RequestException as e:
        return False, f"Network error during live URL validation: {str(e)}", None

def validate_job_freshness(
    job: JobListing,
    db: Session,
    force_live_check: bool = False,
    max_age_hours: int = 24
) -> JobListing:
    """
    Enforces that a job has been verified within max_age_hours (default 24h).
    If older or never verified, fetches the live URL.
    Updates and stores last_verified_at and vacancy_status.
    Raises ValueError if job is unverified, closed, or older than 24h and re-check fails.
    """
    now = datetime.now(timezone.utc)
    target_url = job.canonical_url or job.original_url

    # Check existing timestamp
    if not force_live_check and job.last_verified_at:
        last_v = job.last_verified_at
        if last_v.tzinfo is None:
            last_v = last_v.replace(tzinfo=timezone.utc)
        age = now - last_v
        if age <= timedelta(hours=max_age_hours):
            if job.vacancy_status == "CLOSED":
                raise ValueError(f"Job validation rejected: Job ID {job.id} is marked CLOSED.")
            return job

    # Needs verification
    is_valid, reason, status_code = check_live_job_url(target_url)
    job.last_verified_at = now

    if not is_valid:
        job.vacancy_status = "CLOSED"
        db.commit()
        raise ValueError(f"Job validation rejected for Job ID {job.id} ('{job.title}'): {reason}")

    job.vacancy_status = "VERIFIED_OPEN"
    db.commit()
    return job
