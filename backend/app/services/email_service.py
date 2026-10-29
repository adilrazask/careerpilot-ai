from __future__ import annotations
import os
import re
import ssl
import smtplib
import imaplib
import email
from email.message import EmailMessage
from email.header import decode_header
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.config import settings
from app.models import (
    ApplicationRecord, ApplicationAttempt, EmailMessage as EmailModel, EmailEvent,
    JobListing, RecruiterContact, ResumeVersion, AutomationPolicy, RecruiterResponse,
    Interview, FollowUpTask
)
from app.services.audit import record_audit_log

def classify_recruiter_email(subject: str, body: str) -> Dict[str, Any]:
    """Rule-based and heuristic NLP classification of incoming recruitment messages."""
    text = f"{subject} {body}".lower()

    # 1. Check for Security / Suspicious requests
    suspicious_patterns = [
        "wire transfer", "bank account", "processing fee", "registration fee",
        "crypto", "bitcoin", "telegram for interview", "whatsapp task", "pay for training"
    ]
    if any(p in text for p in suspicious_patterns):
        return {
            "classification": "SUSPICIOUS",
            "action_required": True,
            "action_desc": "Flagged as potentially suspicious recruitment request. Owner review required.",
            "sentiment": "NEGATIVE"
        }

    # 2. Check for Job Offer
    offer_patterns = ["offer of employment", "job offer letter", "formal offer", "pleased to offer you the position"]
    if any(p in text for p in offer_patterns):
        return {
            "classification": "OFFER",
            "action_required": True,
            "action_desc": "Job Offer received! Requires owner review and manual negotiation/acceptance.",
            "sentiment": "VERY_POSITIVE"
        }

    # 3. Check for Interview Invitation
    interview_patterns = [
        "interview", "schedule a call", "invitation to interview", "round of discussion",
        "video call", "zoom meeting", "google meet", "teams meeting", "technical discussion"
    ]
    if any(p in text for p in interview_patterns):
        return {
            "classification": "INTERVIEW_INVITATION",
            "action_required": True,
            "action_desc": "Interview invitation detected. Review proposed time and format.",
            "sentiment": "POSITIVE"
        }

    # 4. Check for Document Request
    doc_patterns = ["send your payslips", "relieving letter", "experience certificate", "updated portfolio", "marksheet"]
    if any(p in text for p in doc_patterns):
        return {
            "classification": "DOCUMENT_REQUEST",
            "action_required": True,
            "action_desc": "Employer requested supplementary documents.",
            "sentiment": "NEUTRAL"
        }

    # 5. Check for Rejection
    rejection_patterns = [
        "unfortunately", "not moving forward", "other candidates", "pursuing other applicants",
        "wishing you all the best in your job search", "regret to inform you"
    ]
    if any(p in text for p in rejection_patterns):
        return {
            "classification": "REJECTION",
            "action_required": False,
            "action_desc": "Application declined by employer.",
            "sentiment": "NEGATIVE"
        }

    # 6. Check for Recruiter Question
    question_patterns = ["notice period", "current ctc", "expected salary", "availability for interview", "years of experience in"]
    if any(p in text for p in question_patterns):
        return {
            "classification": "RECRUITER_QUESTION",
            "action_required": True,
            "action_desc": "Recruiter enquired about candidate parameters (e.g. notice period, salary).",
            "sentiment": "NEUTRAL"
        }

    # 7. Check for Acknowledgement
    ack_patterns = ["application received", "thank you for applying", "we have received your resume", "profile is under review"]
    if any(p in text for p in ack_patterns):
        return {
            "classification": "ACKNOWLEDGEMENT",
            "action_required": False,
            "action_desc": "Standard automated receipt acknowledgement.",
            "sentiment": "NEUTRAL"
        }

    return {
        "classification": "UNRELATED",
        "action_required": False,
        "action_desc": "General message or update.",
        "sentiment": "NEUTRAL"
    }

class EmailOutreachService:
    """Manages secure outbound sending and inbound monitoring with idempotency and daily cap enforcement."""

    @classmethod
    def send_application_email(
        cls,
        application: ApplicationRecord,
        resume_version: ResumeVersion,
        db: Session,
        is_unattended: bool = False
    ) -> Dict[str, Any]:
        """Send application email with tailored attachments under strict policy and duplicate checks."""
        job = application.job
        contact_email = application.primary_recipient.strip()

        # Idempotency check: verify no prior attempt in state 'SENT' or 'SENDING'
        idempotency_key = f"app-{application.id}-job-{job.id}-{contact_email}"
        prior_attempt = db.query(ApplicationAttempt).filter_by(idempotency_key=idempotency_key).first()
        if prior_attempt and prior_attempt.status in ["SUCCESS", "SENDING"]:
            raise RuntimeError(f"Duplicate submission prevented: Application {application.id} already has attempt state '{prior_attempt.status}'.")

        # Step 1 Rule: SEED DATA refusal
        if getattr(job, "is_seed", False):
            raise ValueError(f"Application refused: Job ID {job.id} ('{job.title}' at '{job.company_name}') is marked as SEED data and cannot be dispatched.")

        contact = db.query(RecruiterContact).filter_by(job_id=job.id).first()
        if contact and getattr(contact, "is_seed", False):
            raise ValueError(f"Application refused: Recruiter contact for Job ID {job.id} ('{contact.email}') is marked as SEED data and cannot be dispatched.")

        seed_match = db.query(RecruiterContact).filter(RecruiterContact.email == contact_email, RecruiterContact.is_seed == True).first()
        if seed_match:
            raise ValueError(f"Application refused: Recruiter email '{contact_email}' is from a SEED contact.")

        # Step 5 Rule: APPROVAL STATUS & RATE LIMITS
        from app.services.approval_guard import check_approval_and_rate_limits
        is_approved, appr_reason = check_approval_and_rate_limits(application, db)
        if not is_approved:
            raise ValueError(f"Application refused: {appr_reason}")

        # Step 3 Rule: CONTACT RULES (Block generic local parts, portal domains, require source_url and Hunter/ZeroBounce)
        from app.services.contact_rules import validate_contact_rules
        target_contact = contact or db.query(RecruiterContact).filter_by(email=contact_email).first()
        if target_contact:
            is_valid_c, c_reason = validate_contact_rules(target_contact)
            if not is_valid_c:
                raise ValueError(f"Application refused by Contact Rules for '{contact_email}': {c_reason}")
        else:
            raise ValueError(f"Application refused: No verified RecruiterContact record exists for '{contact_email}'. Real verifier (Hunter/ZeroBounce) required.")

        # Create or update attempt as SENDING (reserve state)
        attempt = ApplicationAttempt(
            application_id=application.id,
            submission_method="email",
            recipient_or_portal=contact_email,
            idempotency_key=idempotency_key,
            status="SENDING",
            attempt_number=(len(application.attempts) + 1),
            attempted_at=datetime.now(timezone.utc)
        )
        db.add(attempt)
        application.current_status = "SUBMISSION_IN_PROGRESS"
        db.commit()

        # Prepare Email Content using AdilEmailDrafter (Grounded strictly in Candidate Facts & JD Analysis)
        from app.services.job_validator import validate_job_freshness
        validate_job_freshness(job, db)

        from app.services.adil_email_drafter import AdilEmailDrafter
        policy = db.query(AutomationPolicy).filter_by(id=1).first()
        contact = db.query(RecruiterContact).filter_by(job_id=job.id).first()
        hr_name = contact.contact_name if contact else None

        draft_res = AdilEmailDrafter.draft(
            job_title=job.title,
            company_name=job.company_name,
            jd_text=job.description or "",
            hr_name=hr_name,
            resume_attached=True
        )

        candidate_name = settings.CAREER_FULL_NAME or "SK Adil Raja"
        candidate_phone = settings.CAREER_PHONE or "+91 9583029294"
        candidate_email = settings.CAREER_EMAIL or settings.EMAIL_FROM or "adilrazask@gmail.com"

        if policy and policy.custom_application_subject:
            try:
                subject = policy.custom_application_subject.format(
                    title=job.title,
                    company=job.company_name,
                    name=candidate_name
                )
            except Exception:
                subject = draft_res.get("subject") or f"Application for {job.title} – Adil | Operations, ERP"
        else:
            subject = draft_res.get("subject") or f"Application for {job.title} – Adil | Operations, ERP"

        if policy and policy.custom_application_body:
            try:
                body_text = policy.custom_application_body.format(
                    title=job.title,
                    company=job.company_name,
                    name=candidate_name,
                    phone=candidate_phone,
                    email=candidate_email
                )
            except Exception:
                body_text = draft_res.get("body")
        else:
            body_text = draft_res.get("body")

        # Step 4 Rule: JOB FILTERS & SUBJECT VALIDATION
        from app.services.job_filters import validate_job_filters, validate_email_subject
        is_job_ok, filter_err = validate_job_filters(job, min_fit_score=70)
        if not is_job_ok:
            raise ValueError(f"Application refused by Job Filters: {filter_err}")

        is_subj_ok, subj_err = validate_email_subject(subject)
        if not is_subj_ok:
            raise ValueError(f"Application refused by Subject Validation: {subj_err}")

        # Determine attachments
        original_user_pdf = "./data/resumes/SK_Adil_Raja_Resume.pdf"
        pdf_path_to_use = None
        if os.path.exists(original_user_pdf):
            pdf_path_to_use = original_user_pdf
        elif resume_version and resume_version.pdf_path and os.path.exists(resume_version.pdf_path):
            pdf_path_to_use = resume_version.pdf_path

        sender = settings.CAREER_EMAIL or settings.EMAIL_FROM or "adilrazask@gmail.com"
        now_ts = datetime.now(timezone.utc)

        # Check if dry_run mode is active
        provider_setting = os.environ.get("EMAIL_PROVIDER") or getattr(settings, "EMAIL_PROVIDER", "dry_run")
        is_dry_run = (provider_setting == "dry_run")

        if is_dry_run:
            # Explicit dry_run simulation: must be labeled MOCK in DB and UI
            mock_msg_id = f"<mock-{attempt.id}@{job.company_name.lower().replace(' ', '')}.com>"
            mock_thread_id = f"mock-thread-{attempt.id}"
            attempt.status = "SUCCESS"
            attempt.evidence = {
                "provider": "MOCK",
                "status": "MOCK_SIMULATED",
                "message_id": mock_msg_id,
                "thread_id": mock_thread_id,
                "timestamp": now_ts.isoformat(),
                "note": "Dry run mock dispatch; provider = dry_run."
            }
            application.current_status = "MOCK_SENT"
            application.external_confirmation_id = mock_msg_id
            application.thread_id = mock_thread_id
            application.delivery_evidence = attempt.evidence

            email_rec = EmailModel(
                application_id=application.id,
                direction="outbound",
                sender=sender,
                recipient=contact_email,
                subject=subject,
                body_text=body_text,
                status="MOCK_SENT",
                provider="MOCK",
                message_id_header=mock_msg_id,
                thread_id=mock_thread_id,
                sent_or_received_at=now_ts
            )
            db.add(email_rec)
            db.commit()

            record_audit_log(
                db=db,
                action="application_email_sent_mock",
                actor="worker" if is_unattended else "owner",
                entity_type="application_record",
                entity_id=str(application.id),
                details={"recipient": contact_email, "provider": "MOCK"}
            )
            return {"status": "SUCCESS", "message": "Email simulated successfully (MOCK mode)", "evidence": attempt.evidence}

        if provider_setting == "smtp":
            import smtplib
            from email.mime.multipart import MIMEMultipart
            from email.mime.text import MIMEText
            from email.mime.application import MIMEApplication
            import uuid

            msg = MIMEMultipart()
            msg["From"] = sender
            msg["To"] = contact_email
            msg["Subject"] = subject
            msg_id = f"<{uuid.uuid4().hex}@{sender.split('@')[-1]}>"
            msg["Message-ID"] = msg_id
            thread_id = f"thread-{uuid.uuid4().hex[:12]}"
            msg["X-Thread-ID"] = thread_id

            msg.attach(MIMEText(body_text, "plain", "utf-8"))

            if pdf_path_to_use and os.path.exists(pdf_path_to_use):
                with open(pdf_path_to_use, "rb") as f:
                    part = MIMEApplication(f.read(), Name="SK_Adil_Raja_Resume.pdf")
                part["Content-Disposition"] = 'attachment; filename="SK_Adil_Raja_Resume.pdf"'
                msg.attach(part)

            host = settings.SMTP_HOST or "smtp.gmail.com"
            port = settings.SMTP_PORT or 587
            user = settings.SMTP_USERNAME or sender
            password = settings.SMTP_PASSWORD

            if not user or not password:
                raise ValueError("SMTP_USERNAME or SMTP_PASSWORD is not configured. Cannot send email.")

            with smtplib.SMTP(host, port, timeout=25) as server:
                server.starttls()
                server.login(user, password)
                server.send_message(msg)

            attempt.status = "SUCCESS"
            attempt.evidence = {
                "provider": "SMTP",
                "message_id": msg_id,
                "thread_id": thread_id,
                "timestamp": now_ts.isoformat(),
                "status": "Accepted by Google SMTP server"
            }
            application.current_status = "EMAIL_SENT"
            application.external_confirmation_id = msg_id
            application.thread_id = thread_id
            application.delivery_evidence = attempt.evidence

            email_rec = EmailModel(
                application_id=application.id,
                direction="outbound",
                sender=sender,
                recipient=contact_email,
                subject=subject,
                body_text=body_text,
                status="SENT",
                provider="smtp",
                message_id_header=msg_id,
                thread_id=thread_id,
                sent_or_received_at=now_ts
            )
            db.add(email_rec)
            db.commit()

            record_audit_log(
                db=db,
                action="application_email_sent_smtp",
                actor="worker" if is_unattended else "owner",
                entity_type="application_record",
                entity_id=str(application.id),
                details={"recipient": contact_email, "provider": "smtp", "message_id": msg_id}
            )
            return {"status": "SUCCESS", "message": f"Email delivered to {contact_email} via Google SMTP", "evidence": attempt.evidence}

        # Real Send: Gmail API OAuth (never falls back to mock silently)
        from app.services.gmail_service import GmailService
        send_res = GmailService.send_message(
            sender=sender,
            recipient=contact_email,
            subject=subject,
            body_text=body_text,
            pdf_attachment_path=pdf_path_to_use
        )

        attempt.status = "SUCCESS"
        attempt.evidence = {
            "provider": "GMAIL_API",
            "message_id": send_res["message_id"],
            "thread_id": send_res["thread_id"],
            "timestamp": now_ts.isoformat(),
            "status": "Accepted by Gmail API"
        }
        application.current_status = "EMAIL_SENT"
        application.external_confirmation_id = send_res["message_id"]
        application.thread_id = send_res["thread_id"]
        application.delivery_evidence = attempt.evidence

        email_rec = EmailModel(
            application_id=application.id,
            direction="outbound",
            sender=sender,
            recipient=contact_email,
            subject=subject,
            body_text=body_text,
            status="SENT",
            provider="gmail_api",
            message_id_header=send_res["message_id"],
            thread_id=send_res["thread_id"],
            sent_or_received_at=now_ts
        )
        db.add(email_rec)
        db.commit()

        record_audit_log(
            db=db,
            action="application_email_sent",
            actor="worker" if is_unattended else "owner",
            entity_type="application_record",
            entity_id=str(application.id),
            details={"recipient": contact_email, "evidence": attempt.evidence}
        )
        return {"status": "SUCCESS", "message": "Application email sent via Gmail API", "evidence": attempt.evidence}

    @classmethod
    def send_follow_up_email(cls, task: FollowUpTask, db: Session) -> Dict[str, Any]:
        """Dispatches an automated polite follow-up email to the recruiter with candidate's tailored resume attached."""
        app = task.application
        job = app.job

        if getattr(job, "is_seed", False):
            raise ValueError(f"Follow-up refused: Job ID {job.id} ('{job.title}') is marked as SEED data and cannot be dispatched.")
        contact = db.query(RecruiterContact).filter_by(job_id=job.id).first()
        if contact and getattr(contact, "is_seed", False):
            raise ValueError(f"Follow-up refused: Recruiter contact for Job ID {job.id} ('{contact.email}') is marked as SEED data.")

        recipient = (app.primary_recipient or "").strip()
        if not recipient:
            raise ValueError(f"Application {app.id} does not have a primary recipient.")

        subject = task.draft_subject or f"Following up: Application for {job.title} — {settings.CAREER_FULL_NAME}"
        body_text = task.draft_body or (
            f"Dear Hiring Team at {job.company_name},\n\n"
            f"I hope this email finds you well. I recently submitted my application for the {job.title} position "
            f"and wanted to politely follow up to reiterate my strong enthusiasm for the role.\n\n"
            f"Please let me know if you need any additional information from my side.\n\n"
            f"Warm regards,\n{settings.CAREER_FULL_NAME}\n{settings.CAREER_PHONE} | {settings.CAREER_EMAIL or settings.EMAIL_FROM}"
        )

        sender = settings.CAREER_EMAIL or settings.EMAIL_FROM or "adilrazask@gmail.com"
        now_ts = datetime.now(timezone.utc)

        # Check if dry_run mode is active
        provider_setting = os.environ.get("EMAIL_PROVIDER") or getattr(settings, "EMAIL_PROVIDER", "dry_run")
        is_dry_run = (provider_setting == "dry_run")

        if is_dry_run:
            task.status = "SENT"
            task.sent_at = now_ts
            mock_msg_id = f"<mock-followup-{task.id}@careerpilot.ai>"
            email_rec = EmailModel(
                application_id=app.id,
                direction="outbound",
                sender=sender,
                recipient=recipient,
                subject=subject,
                body_text=body_text,
                status="MOCK_SENT",
                provider="MOCK",
                message_id_header=mock_msg_id,
                thread_id=app.thread_id or f"mock-thread-{app.id}",
                sent_or_received_at=now_ts
            )
            db.add(email_rec)
            db.commit()
            return {"status": "SUCCESS", "message": "Follow-up email sent (MOCK mode)", "recipient": recipient}

        # Real Send: Gmail API OAuth (in the same thread)
        from app.services.gmail_service import GmailService
        send_res = GmailService.send_message(
            sender=sender,
            recipient=recipient,
            subject=subject,
            body_text=body_text,
            pdf_attachment_path=None,
            thread_id=app.thread_id or None,
            in_reply_to=app.external_confirmation_id or None
        )

        task.status = "SENT"
        task.sent_at = now_ts
        email_rec = EmailModel(
            application_id=app.id,
            direction="outbound",
            sender=sender,
            recipient=recipient,
            subject=subject,
            body_text=body_text,
            status="SENT",
            provider="gmail_api",
            message_id_header=send_res["message_id"],
            thread_id=send_res["thread_id"],
            sent_or_received_at=now_ts
        )
        db.add(email_rec)
        db.commit()

        record_audit_log(
            db=db,
            action="follow_up_email_sent_gmail_api",
            actor="follow_up_service",
            entity_type="follow_up_task",
            entity_id=str(task.id),
            details={"recipient": recipient, "sequence": task.follow_up_sequence, "thread_id": send_res["thread_id"]}
        )
        return {"status": "SUCCESS", "message": "Follow-up email sent via Gmail API", "recipient": recipient, "thread_id": send_res["thread_id"]}

    @classmethod
    def poll_inbound_recruiter_replies(cls, db: Session) -> List[Dict[str, Any]]:
        """Poll incoming emails via IMAP, classify recruiter responses, and update ATS application statuses."""
        host = settings.IMAP_HOST
        port = settings.IMAP_PORT
        user = settings.IMAP_USERNAME
        password = settings.IMAP_PASSWORD

        if not all([host, user, password]):
            # IMAP not configured; return empty
            return []

        processed = []
        try:
            mail = imaplib.IMAP4_SSL(host, port)
            mail.login(user, password)
            mail.select("inbox")

            # Search unseen messages from past 7 days
            since_date = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%d-%b-%Y")
            status, messages = mail.search(None, f'(UNSEEN SINCE "{since_date}")')
            if status != "OK":
                mail.logout()
                return []

            for num in messages[0].split():
                status, data = mail.fetch(num, "(RFC822)")
                if status != "OK":
                    continue
                raw_email = data[0][1]
                msg = email.message_from_bytes(raw_email)

                # Decode subject
                subject_raw, encoding = decode_header(msg.get("Subject", ""))[0]
                if isinstance(subject_raw, bytes):
                    subject = subject_raw.decode(encoding or "utf-8", errors="ignore")
                else:
                    subject = str(subject_raw)

                sender = msg.get("From", "")
                sender_email = re.findall(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", sender)
                clean_sender = sender_email[0] if sender_email else sender

                # Extract body
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            body = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                            break
                else:
                    body = msg.get_payload(decode=True).decode("utf-8", errors="ignore")

                classification = classify_recruiter_email(subject, body)

                # Try to correlate with an existing application
                # Match by sender email or company/role in subject
                app = db.query(ApplicationRecord).filter(
                    ApplicationRecord.primary_recipient.ilike(f"%{clean_sender}%")
                ).first()

                now_ts = datetime.now(timezone.utc)

                # Save email record
                em_record = EmailModel(
                    application_id=app.id if app else None,
                    direction="inbound",
                    sender=clean_sender,
                    recipient=user,
                    subject=subject,
                    body_text=body[:5000],
                    classification=classification["classification"],
                    status="DELIVERED",
                    provider="imap",
                    sent_or_received_at=now_ts
                )
                db.add(em_record)

                if app:
                    # Update application status
                    if classification["classification"] == "INTERVIEW_INVITATION":
                        app.current_status = "INTERVIEW_INVITED"
                        app.interview_invited = True
                        db.add(Interview(
                            application_id=app.id,
                            format="Video / Phone",
                            status="INVITED",
                            notes=f"Auto-detected from recruiter email: {subject}"
                        ))
                    elif classification["classification"] == "REJECTION":
                        app.current_status = "REJECTED_BY_EMPLOYER"
                        app.rejection_received = True
                    elif classification["classification"] == "ACKNOWLEDGEMENT":
                        app.current_status = "APPLICATION_ACKNOWLEDGED"
                        app.acknowledgement_received = True
                    elif classification["classification"] in ["RECRUITER_QUESTION", "DOCUMENT_REQUEST"]:
                        app.current_status = "RECRUITER_RESPONSE_RECEIVED"

                    db.add(RecruiterResponse(
                        application_id=app.id,
                        sender_email=clean_sender,
                        subject=subject,
                        body_summary=body[:1000],
                        response_type=classification["classification"],
                        sentiment=classification["sentiment"],
                        requires_user_action=classification["action_required"],
                        action_description=classification["action_desc"],
                        received_at=now_ts
                    ))

                db.commit()
                processed.append({
                    "sender": clean_sender,
                    "subject": subject,
                    "classification": classification["classification"],
                    "matched_application_id": app.id if app else None
                })

            mail.logout()
        except Exception as e:
            record_audit_log(
                db=db,
                action="imap_poll_error",
                actor="email_service",
                details={"error": str(e)}
            )

        return processed
