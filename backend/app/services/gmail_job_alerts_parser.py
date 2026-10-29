"""
Gmail Job Alerts Parser:
Reads job-alert emails (LinkedIn, Naukri, Indeed, Apna) from Gmail label "job-alerts"
via the Gmail API and stores title, company, location, job URL and the email message ID.
Marks source = "gmail_alert", is_seed = False.
Validates each URL before it can be drafted.
"""
from __future__ import annotations
import re
import base64
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import lxml.html
from sqlalchemy.orm import Session

from app.models import JobListing
from app.services.gmail_service import GmailService, GmailAPIError
from app.services.job_validator import check_live_job_url
from app.services.adapters import canonicalize_url
from app.services.audit import record_audit_log

def decode_payload_body(payload: Dict[str, Any]) -> str:
    """Recursively extracts and decodes text/html and text/plain parts from Gmail payload."""
    body_data = ""
    mime_type = payload.get("mimeType", "")
    
    if "data" in payload.get("body", {}):
        raw_b64 = payload["body"]["data"]
        try:
            body_data += base64.urlsafe_b64decode(raw_b64.encode("ascii")).decode("utf-8", errors="replace")
        except Exception:
            pass

    for part in payload.get("parts", []):
        body_data += "\n" + decode_payload_body(part)

    return body_data

class GmailJobAlertParser:
    """Parses email notifications from job platforms into validated JobListing records."""

    @classmethod
    def parse_job_alert_content(cls, message_id: str, sender: str, subject: str, body: str) -> List[Dict[str, Any]]:
        """Parses job leads from an alert email body."""
        sender_lower = sender.lower()
        subject_lower = subject.lower()
        extracted: List[Dict[str, Any]] = []

        try:
            doc = lxml.html.fromstring(body)
            link_elements = doc.xpath('//a')
            links = [{"href": el.get("href", ""), "text": el.text_content().strip(), "el": el} for el in link_elements if el.get("href")]
        except Exception:
            links = []

        # 1. LinkedIn Job Alerts
        if "linkedin" in sender_lower or "linkedin" in subject_lower:
            for a in links:
                href = a["href"]
                text = a["text"]
                if "/jobs/view/" in href or "linkedin.com/comm/jobs/view" in href:
                    clean_url = href.split("?")[0]
                    title = text if len(text) > 3 and not text.lower().startswith("view") else "Operations Role"
                    parent = a["el"].getparent()
                    comp = "LinkedIn Partner Company"
                    loc = "Hyderabad, India"
                    if parent is not None:
                        parent_text = parent.text_content().strip()
                        parts = [p.strip() for p in parent_text.split("|") if p.strip()]
                        if len(parts) >= 2:
                            comp = parts[1] if parts[0] == title and len(parts) > 1 else parts[0]
                    extracted.append({
                        "title": title,
                        "company": comp,
                        "location": loc,
                        "url": clean_url,
                        "message_id": message_id,
                        "platform": "LinkedIn"
                    })

        # 2. Naukri Job Alerts
        elif "naukri" in sender_lower or "naukri" in subject_lower:
            for a in links:
                href = a["href"]
                text = a["text"]
                if "naukri.com/job-listings" in href:
                    clean_url = href.split("?")[0]
                    title = text if len(text) > 3 else "Operations Specialist"
                    parent = a["el"].getparent()
                    comp = "Naukri Hiring Client"
                    loc = "Hyderabad, India"
                    if parent is not None:
                        parent_text = parent.text_content().strip()
                        parts = [p.strip() for p in parent_text.split("|") if p.strip()]
                        if len(parts) >= 2:
                            comp = parts[1] if parts[0] == title else parts[0]
                    extracted.append({
                        "title": title,
                        "company": comp,
                        "location": loc,
                        "url": clean_url,
                        "message_id": message_id,
                        "platform": "Naukri"
                    })

        # 3. Indeed Job Alerts
        elif "indeed" in sender_lower or "indeed" in subject_lower:
            for a in links:
                href = a["href"]
                text = a["text"]
                if "/viewjob" in href or "/rc/clk" in href or "indeed.com/job" in href:
                    clean_url = href.split("&")[0] if "&" in href else href
                    title = text if len(text) > 3 else "Operations Lead"
                    parent = a["el"].getparent()
                    comp = "Indeed Employer"
                    loc = "Hyderabad, India"
                    if parent is not None:
                        parent_text = parent.text_content().strip()
                        parts = [p.strip() for p in parent_text.split("|") if p.strip()]
                        if len(parts) >= 2:
                            comp = parts[1] if parts[0] == title else parts[0]
                    extracted.append({
                        "title": title,
                        "company": comp,
                        "location": loc,
                        "url": clean_url,
                        "message_id": message_id,
                        "platform": "Indeed"
                    })

        # 4. Apna Job Alerts
        elif "apna" in sender_lower or "apna" in subject_lower:
            for a in links:
                href = a["href"]
                text = a["text"]
                if "apna.co/job/" in href:
                    clean_url = href.split("?")[0]
                    title = text if len(text) > 3 else "Operations Executive"
                    parent = a["el"].getparent()
                    comp = "Apna Recruiter"
                    loc = "Hyderabad, India"
                    if parent is not None:
                        parent_text = parent.text_content().strip()
                        parts = [p.strip() for p in parent_text.split("|") if p.strip()]
                        if len(parts) >= 2:
                            comp = parts[1] if parts[0] == title else parts[0]
                    extracted.append({
                        "title": title,
                        "company": comp,
                        "location": loc,
                        "url": clean_url,
                        "message_id": message_id,
                        "platform": "Apna"
                    })

        # 5. Generic Fallback Parser for Plain Text or Other Alerts
        if not extracted:
            # Check for generic job URLs in text
            job_url_pattern = re.compile(r'https?://[^\s"\'<>]+(?:/job/|/jobs/|/viewjob|/job-listings-[^\s"\'<>]+)')
            matches = job_url_pattern.findall(body)
            for u in set(matches):
                clean_url = u.split("?")[0]
                extracted.append({
                    "title": subject.replace("Job Alert:", "").strip() or "Operations Coordinator",
                    "company": "Discovered Alert Employer",
                    "location": "Hyderabad, India",
                    "url": clean_url,
                    "message_id": message_id,
                    "platform": "Generic"
                })

        return extracted

    @classmethod
    def ingest_job_alerts_from_gmail(cls, db: Session, label: str = "job-alerts", max_emails: int = 25) -> List[Dict[str, Any]]:
        """
        Polls Gmail for messages with label 'job-alerts', parses job alerts,
        stores with source='gmail_alert', is_seed=False, and validates each URL
        before it can be drafted.
        """
        try:
            messages = GmailService.list_messages_by_query(query=f"label:{label}", max_results=max_emails)
        except GmailAPIError as e:
            record_audit_log(
                db=db,
                action="gmail_job_alerts_fetch_error",
                actor="gmail_alert_parser",
                entity_type="gmail_alerts",
                entity_id="0",
                details={"error": str(e)}
            )
            return []

        imported_jobs: List[Dict[str, Any]] = []

        for m_summary in messages:
            msg_id = m_summary.get("id")
            if not msg_id:
                continue

            try:
                full_msg = GmailService.get_message(msg_id)
            except Exception:
                continue

            headers = {h.get("name", "").lower(): h.get("value", "") for h in full_msg.get("payload", {}).get("headers", [])}
            sender = headers.get("from", "")
            subject = headers.get("subject", "")
            body = decode_payload_body(full_msg.get("payload", {}))

            job_leads = cls.parse_job_alert_content(msg_id, sender, subject, body)

            for lead in job_leads:
                job_url = lead["url"]
                # Deduplication check
                existing = db.query(JobListing).filter_by(original_url=job_url).first()
                if existing:
                    continue

                # Step 6 Rule: Validate each URL before it can be drafted
                is_valid_url, val_reason = check_live_job_url(job_url)
                now_ts = datetime.now(timezone.utc)

                status = "VERIFIED_OPEN" if is_valid_url else "CLOSED"
                job = JobListing(
                    title=lead["title"],
                    company_name=lead["company"],
                    location=lead["location"],
                    source_platform="gmail_alert",
                    original_url=job_url,
                    canonical_url=canonicalize_url(job_url),
                    employer_job_id=msg_id,
                    is_seed=False,
                    is_test=False,
                    description=f"Discovered via Gmail alert message {msg_id}. Title: {lead['title']} at {lead['company']}.",
                    vacancy_status=status,
                    last_verified_at=now_ts if is_valid_url else None,
                    notes=f"Source: Gmail label '{label}'. Validation: {val_reason}"
                )
                db.add(job)
                db.commit()
                db.refresh(job)

                imported_jobs.append({
                    "id": job.id,
                    "title": job.title,
                    "company_name": job.company_name,
                    "url": job.original_url,
                    "vacancy_status": job.vacancy_status,
                    "is_seed": job.is_seed,
                    "source_platform": job.source_platform,
                    "message_id": msg_id,
                    "validation_reason": val_reason
                })

                record_audit_log(
                    db=db,
                    action="gmail_job_alert_ingested",
                    actor="gmail_alert_parser",
                    entity_type="job_listing",
                    entity_id=str(job.id),
                    details={
                        "title": job.title,
                        "company": job.company_name,
                        "url": job_url,
                        "status": job.vacancy_status,
                        "message_id": msg_id
                    }
                )

        return imported_jobs
