"""
Contact Discovery & Verification Pipeline:
For each validated job, looks for an HR email in this strict order:
(a) in the JD text
(b) company careers page
(c) Hunter / Apollo
Saves contact_source_url.
Verifies with Hunter / ZeroBounce (or Apollo).
Strict Rule: No verifier result = no send (status UNVERIFIED).
"""
from __future__ import annotations
import re
import urllib.parse
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
import requests
from sqlalchemy.orm import Session

from app.config import settings
from app.models import JobListing, RecruiterContact, ContactVerificationRecord
from app.services.contact_rules import BLOCKED_LOCAL_PARTS, BLOCKED_PORTAL_DOMAINS
from app.services.adapters.apollo_adapter import ApolloContactAdapter
from app.services.audit import record_audit_log

EMAIL_REGEX = re.compile(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+')

def filter_valid_hr_email(email: str) -> bool:
    """Filters out blocked generic mailboxes and portal domains."""
    if not email or "@" not in email:
        return False
    clean = email.strip(".,;:()<>[]'\"").lower()
    local_part, domain = clean.split("@", 1)
    
    if local_part in BLOCKED_LOCAL_PARTS:
        return False
    if any(p in domain for p in BLOCKED_PORTAL_DOMAINS):
        return False
    if any(clean.endswith(ext) for ext in [".png", ".jpg", ".gif", ".webp"]):
        return False
    return True

class ContactPipeline:
    """Discovers HR contacts strictly by hierarchy (JD text -> careers page -> Hunter/Apollo) and verifies deliverability."""

    @classmethod
    def extract_from_jd_text(cls, jd_text: str, job_url: str) -> Optional[Tuple[str, str, str]]:
        """(a) Looks for HR email in the JD text."""
        if not jd_text:
            return None
        matches = EMAIL_REGEX.findall(jd_text)
        for m in matches:
            clean = m.strip(".,;:()<>[]'\"")
            if filter_valid_hr_email(clean):
                return clean, job_url, "jd_text"
        return None

    @classmethod
    def extract_from_careers_page(cls, company_name: str, domain: Optional[str] = None) -> Optional[Tuple[str, str, str]]:
        """(b) Looks for HR email on the company's careers page."""
        target_domain = domain
        if not target_domain:
            clean_name = re.sub(r"[^a-zA-Z0-9]+", "", company_name).lower()
            target_domain = f"{clean_name}.com"

        careers_url = f"https://{target_domain}/careers"
        try:
            res = requests.get(
                careers_url,
                headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"},
                timeout=5,
                allow_redirects=True
            )
            if res.status_code == 200 and res.text:
                matches = EMAIL_REGEX.findall(res.text)
                for m in matches:
                    clean = m.strip(".,;:()<>[]'\"")
                    if filter_valid_hr_email(clean) and target_domain in clean.lower():
                        return clean, res.url, "company_careers_page"
        except Exception:
            pass

        return None

    @classmethod
    def extract_from_hunter_or_apollo(cls, company_name: str, domain: Optional[str] = None) -> Optional[Tuple[str, str, str]]:
        """(c) Queries Hunter.io or Apollo AI directories."""
        target_domain = domain or (f"{re.sub(r'[^a-zA-Z0-9]+', '', company_name).lower()}.com")

        # 1. Hunter.io Domain Search
        if settings.HUNTER_API_KEY:
            try:
                res = requests.get(
                    f"https://api.hunter.io/v2/domain-search?domain={target_domain}&department=hr&api_key={settings.HUNTER_API_KEY}",
                    timeout=8
                )
                if res.status_code == 200:
                    data = res.json().get("data", {})
                    for p in data.get("emails", []):
                        em = (p.get("value") or "").strip()
                        if filter_valid_hr_email(em):
                            src = f"https://api.hunter.io/v2/domain-search?domain={target_domain}"
                            return em, src, "hunter_api"
            except Exception:
                pass

        # 2. Apollo AI Directory
        if settings.APOLLO_API_KEY:
            try:
                people = ApolloContactAdapter.search_hr_contacts(company_name, domain=target_domain, location="India", limit=3)
                for p in people:
                    em = (p.get("email") or "").strip()
                    if filter_valid_hr_email(em):
                        src = p.get("source_url") or f"https://app.apollo.io/#/people?domain={target_domain}"
                        return em, src, "apollo_api"
            except Exception:
                pass

        return None

    @classmethod
    def verify_email_deliverability(cls, email: str) -> Tuple[bool, str, str]:
        """
        Verifies email using Hunter or ZeroBounce.
        Strict rule: No real verifier result = no send (returns False).
        """
        # 1. Hunter.io email verifier
        if settings.HUNTER_API_KEY:
            try:
                res = requests.get(
                    f"https://api.hunter.io/v2/email-verifier?email={email}&api_key={settings.HUNTER_API_KEY}",
                    timeout=8
                )
                if res.status_code == 200:
                    data = res.json().get("data", {})
                    status_val = data.get("status") # "valid", "invalid", "accept_all"
                    result_val = data.get("result") # "deliverable", "risky", "undeliverable"
                    if status_val == "valid" or result_val == "deliverable":
                        return True, "hunter_verified", f"Hunter.io score: {data.get('score', 95)} (deliverable)"
                    return False, "hunter_rejected", f"Hunter.io marked status '{status_val}', result '{result_val}'"
            except Exception as e:
                pass

        # 2. ZeroBounce email verifier
        if settings.ZEROBOUNCE_API_KEY:
            try:
                res = requests.get(
                    f"https://api.zerobounce.net/v2/validate?email={email}&api_key={settings.ZEROBOUNCE_API_KEY}",
                    timeout=8
                )
                if res.status_code == 200:
                    data = res.json()
                    status_val = (data.get("status") or "").lower()
                    if status_val == "valid":
                        return True, "zerobounce_verified", f"ZeroBounce validated: {status_val}"
                    return False, "zerobounce_rejected", f"ZeroBounce marked status '{status_val}'"
            except Exception as e:
                pass

        # If verifier keys are not configured or no result was returned:
        return False, "unverified", "No verifier result from Hunter or ZeroBounce. Sending strictly prohibited."

    @classmethod
    def find_and_verify_hr_contact_for_job(cls, job: JobListing, db: Session, domain: Optional[str] = None) -> Optional[RecruiterContact]:
        """
        Finds HR contact in hierarchy (JD text -> careers page -> Hunter/Apollo) and verifies with Hunter/ZeroBounce.
        No verifier result = no send.
        """
        found = None

        # (a) Look in JD text
        found = cls.extract_from_jd_text(job.description or "", job.original_url or "")
        source_level = "jd_text"

        # (b) Look on company careers page
        if not found:
            found = cls.extract_from_careers_page(job.company_name, domain)
            source_level = "company_careers_page"

        # (c) Look in Hunter / Apollo
        if not found:
            found = cls.extract_from_hunter_or_apollo(job.company_name, domain)
            source_level = "hunter_or_apollo"

        if not found:
            return None

        email_addr, source_url, origin = found

        # Run strict Hunter / ZeroBounce verification
        is_verified, method, details = cls.verify_email_deliverability(email_addr)
        now_ts = datetime.now(timezone.utc)

        contact = db.query(RecruiterContact).filter_by(job_id=job.id, email=email_addr).first()
        if not contact:
            contact = RecruiterContact(
                job_id=job.id,
                company_name=job.company_name,
                contact_name=f"{job.company_name} Talent Acquisition",
                contact_role="Talent Acquisition / HR",
                email=email_addr,
                source_url=source_url,
                is_seed=False,
                is_test=False,
                confidence=0.95 if is_verified else 0.0,
                verification_status="SOURCE_VERIFIED" if is_verified else "UNVERIFIED",
                verification_method=method if is_verified else "unverified",
                last_verification_date=now_ts if is_verified else None,
                notes=f"Found via {origin}. Verifier: {details}"
            )
            db.add(contact)
        else:
            contact.source_url = source_url
            contact.verification_status = "SOURCE_VERIFIED" if is_verified else "UNVERIFIED"
            contact.verification_method = method if is_verified else "unverified"
            contact.last_verification_date = now_ts if is_verified else None
            contact.notes = f"Found via {origin}. Verifier: {details}"

        db.commit()
        db.refresh(contact)

        record_audit_log(
            db=db,
            action="contact_pipeline_executed",
            actor="contact_pipeline",
            entity_type="recruiter_contact",
            entity_id=str(contact.id),
            details={
                "job_id": job.id,
                "email": email_addr,
                "origin": origin,
                "verified": is_verified,
                "method": method
            }
        )

        return contact
