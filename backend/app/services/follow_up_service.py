from __future__ import annotations
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.config import settings
from app.models import ApplicationRecord, FollowUpTask, JobListing, AutomationPolicy, RecruiterResponse
from app.services.email_service import EmailOutreachService
from app.services.audit import record_audit_log

def add_working_days(start_date: datetime, num_days: int) -> datetime:
    """Adds a specific number of working days (Monday-Friday) to start_date."""
    current = start_date
    added = 0
    while added < num_days:
        current += timedelta(days=1)
        if current.weekday() < 5:  # Mon=0, Fri=4
            added += 1
    return current

class FollowUpService:
    """Configurable automated follow-up scheduling (max 2 cycles, 5-7 working days), reply detection guards, and thread delivery."""

    @classmethod
    def schedule_follow_up_if_eligible(cls, application: ApplicationRecord, db: Session) -> Optional[FollowUpTask]:
        """Schedules the next follow-up task (Max 2 cycles, 5-7 working days apart) if permitted by user policy."""
        policy = db.query(AutomationPolicy).filter_by(id=1).first()
        if not policy or not policy.enable_auto_follow_ups:
            return None

        # Step 7 Rule: Max 2 follow-ups, 5-7 working days apart
        max_cycles = 2

        # Check existing follow-up tasks
        existing_tasks = db.query(FollowUpTask).filter_by(application_id=application.id).count()
        if existing_tasks >= max_cycles:
            return None # Maximum allowed 2 cycles reached

        next_sequence = existing_tasks + 1
        now_ts = datetime.now(timezone.utc)
        # Follow-up 1: 5 working days; Follow-up 2: 7 working days
        working_days_delay = 5 if next_sequence == 1 else 7
        due_date = add_working_days(now_ts, working_days_delay)

        job = application.job
        company = job.company_name if job else "Hiring Team"
        title = job.title if job else "Position"

        candidate_name = settings.CAREER_FULL_NAME or "SK Adil Raja"
        candidate_phone = settings.CAREER_PHONE or "+91 9583029294"
        candidate_email = settings.CAREER_EMAIL or settings.EMAIL_FROM or "adilrazask@gmail.com"

        # Sequence-tailored polite professional copy with policy override support
        if next_sequence == 1:
            draft_subject = f"Re: Application: {title} — {candidate_name}"
            if policy and getattr(policy, "custom_follow_up_1_body", None):
                try:
                    draft_body = policy.custom_follow_up_1_body.format(
                        title=title, company=company, name=candidate_name, phone=candidate_phone, email=candidate_email
                    )
                except Exception:
                    draft_body = policy.custom_follow_up_1_body
            else:
                draft_body = (
                    f"Hi {company} Hiring Team,\n\n"
                    f"I hope you’re having a great week.\n\n"
                    f"I wanted to quickly check in regarding the {title} position for which I submitted my application. "
                    f"I remain very interested in the role and confident that my background in ERP systems, operations "
                    f"coordination, and client workflow tracking at Gupta Steels will be an immediate asset to your operations.\n\n"
                    f"I’ve re-attached my tailored resume for quick reference. Please let me know if you need any additional details or references.\n\n"
                    f"Best regards,\n\n"
                    f"{candidate_name}\n"
                    f"Phone: {candidate_phone} | Email: {candidate_email}"
                )
        elif next_sequence == 2:
            draft_subject = f"Following up: {title} — {candidate_name}"
            if policy and getattr(policy, "custom_follow_up_2_body", None):
                try:
                    draft_body = policy.custom_follow_up_2_body.format(
                        title=title, company=company, name=candidate_name, phone=candidate_phone, email=candidate_email
                    )
                except Exception:
                    draft_body = policy.custom_follow_up_2_body
            else:
                draft_body = (
                    f"Hi {company} Hiring Team,\n\n"
                    f"I wanted to follow up and see how the hiring process for the {title} position is progressing.\n\n"
                    f"I understand your team likely has a busy schedule, so I wanted to reiterate my keen interest in joining {company}. "
                    f"If the role has moved forward with another candidate, I would also welcome consideration for other upcoming "
                    f"operations or procurement opportunities within your team.\n\n"
                    f"Thank you again for your time and review!\n\n"
                    f"Best regards,\n\n"
                    f"{candidate_name}\n"
                    f"Phone: {candidate_phone} | Email: {candidate_email}"
                )
        else:
            draft_subject = f"Final check-in: {title} — {candidate_name}"
            if policy and getattr(policy, "custom_follow_up_3_body", None):
                try:
                    draft_body = policy.custom_follow_up_3_body.format(
                        title=title, company=company, name=candidate_name, phone=candidate_phone, email=candidate_email
                    )
                except Exception:
                    draft_body = policy.custom_follow_up_3_body
            else:
                draft_body = (
                    f"Hi {company} Hiring Team,\n\n"
                    f"Reaching out for a final check-in regarding the {title} opening.\n\n"
                    f"If the position has already been filled, I completely understand and wish your team continued success. "
                    f"I’d love to stay connected on LinkedIn for future openings where my operations and ERP background might be a strong fit.\n\n"
                    f"Thanks again for your time!\n\n"
                    f"Warm regards,\n\n"
                    f"{candidate_name}\n"
                    f"Phone: {candidate_phone} | Email: {candidate_email}"
                )

        task = FollowUpTask(
            application_id=application.id,
            follow_up_sequence=next_sequence,
            due_date=due_date,
            status="SCHEDULED",
            draft_subject=draft_subject,
            draft_body=draft_body
        )
        db.add(task)
        db.commit()
        db.refresh(task)

        record_audit_log(
            db=db,
            action="follow_up_scheduled",
            actor="follow_up_service",
            entity_type="follow_up_task",
            entity_id=str(task.id),
            details={
                "application_id": application.id,
                "sequence": next_sequence,
                "due_date": due_date.isoformat(),
                "cadence_days": working_days_delay
            }
        )
        return task

    @classmethod
    def process_due_follow_ups(cls, db: Session) -> List[Dict[str, Any]]:
        """Processes scheduled follow-ups that have reached their due date."""
        policy = db.query(AutomationPolicy).filter_by(id=1).first()
        if not policy or not policy.enable_auto_follow_ups or policy.pause_all_automation or policy.pause_applications_only:
            return []

        max_cycles = getattr(policy, "max_follow_up_cycles", 3) or settings.MAX_FOLLOW_UPS or 3
        now_ts = datetime.now(timezone.utc)
        due_tasks = db.query(FollowUpTask).filter(
            FollowUpTask.status == "SCHEDULED",
            FollowUpTask.due_date <= now_ts
        ).all()

        results = []
        for task in due_tasks:
            app = task.application
            job = app.job

            # Guard 1: Recruiter has responded or invited to interview
            has_response = db.query(RecruiterResponse).filter_by(application_id=app.id).first()
            if has_response or app.acknowledgement_received or app.interview_invited or app.rejection_received:
                task.status = "CANCELLED_BY_REPLY"
                task.notes = "Cancelled: Recruiter has already responded or interview invitation was received."
                db.commit()
                continue

            # Step 1 Rule: FAIL CLOSED
            # If thread_id is missing OR the Gmail check raises any error, do NOT send.
            # Set task.status = "BLOCKED_UNVERIFIED" and log the reason.
            if not app.thread_id:
                task.status = "BLOCKED_UNVERIFIED"
                task.notes = "Blocked: Missing thread_id on application record. Cannot safely verify recruiter thread without thread_id."
                record_audit_log(
                    db=db,
                    action="follow_up_blocked_unverified",
                    actor="follow_up_service",
                    entity_type="follow_up_task",
                    entity_id=str(task.id),
                    details={"reason": "Missing thread_id on application record", "application_id": app.id}
                )
                db.commit()
                continue

            try:
                from app.services.gmail_service import GmailService
                thread_msgs = GmailService.check_thread_messages(app.thread_id)
                candidate_email = (settings.CAREER_EMAIL or settings.EMAIL_FROM or "").lower()
                for m in thread_msgs:
                    headers = {h.get("name", "").lower(): h.get("value", "") for h in m.get("payload", {}).get("headers", [])}
                    from_hdr = headers.get("from", "").lower()
                    is_auto = any(h in headers for h in ["auto-submitted", "x-autoreply", "x-failed-recipients"])
                    # If message came from someone other than candidate or is auto-reply/bounce
                    if (from_hdr and candidate_email and candidate_email not in from_hdr) or is_auto:
                        task.status = "CANCELLED_BY_REPLY"
                        task.notes = f"Cancelled: Recruiter reply, bounce, or auto-reply detected in Gmail thread '{app.thread_id}'."
                        record_audit_log(
                            db=db,
                            action="follow_up_cancelled_by_reply",
                            actor="follow_up_service",
                            entity_type="follow_up_task",
                            entity_id=str(task.id),
                            details={"reason": "Recruiter reply or bounce detected", "thread_id": app.thread_id}
                        )
                        db.commit()
                        break
            except Exception as e:
                task.status = "BLOCKED_UNVERIFIED"
                task.notes = f"Blocked: Gmail thread check failed ({str(e)}). Refusing to send unverified follow-up."
                record_audit_log(
                    db=db,
                    action="follow_up_blocked_unverified",
                    actor="follow_up_service",
                    entity_type="follow_up_task",
                    entity_id=str(task.id),
                    details={"reason": f"Gmail check error: {str(e)}", "thread_id": app.thread_id}
                )
                db.commit()
                continue

            if task.status in ["CANCELLED_BY_REPLY", "BLOCKED_UNVERIFIED"]:
                continue

            # Guard 2: Vacancy is closed, expired, or application was terminated
            if (job and job.vacancy_status in ["CLOSED", "EXPIRED", "SUSPICIOUS"]) or app.current_status in ["WITHDRAWN", "CLOSED", "REJECTED_BY_EMPLOYER"]:
                task.status = "CANCELLED_BY_POLICY"
                task.notes = "Cancelled: Vacancy closed or application was terminated."
                db.commit()
                continue

            # Guard 3: Recipient email must exist
            recipient = app.primary_recipient
            if not recipient:
                task.status = "CANCELLED_BY_POLICY"
                task.notes = "Cancelled: No valid recipient email address on application record."
                db.commit()
                continue

            # Dispatch real follow-up email via EmailOutreachService
            try:
                res = EmailOutreachService.send_follow_up_email(task, db)
                task.status = "SENT"
                task.sent_at = now_ts
                task.notes = res.get("message", "Follow-up delivered.")
                db.commit()

                record_audit_log(
                    db=db,
                    action="follow_up_sent",
                    actor="follow_up_service",
                    entity_type="follow_up_task",
                    entity_id=str(task.id),
                    details={
                        "application_id": app.id,
                        "recipient": recipient,
                        "sequence": task.follow_up_sequence,
                        "delivery_result": res
                    }
                )

                # If more follow-up cycles remain, schedule next cycle (e.g. sequence 2 at +15 days)
                if task.follow_up_sequence < max_cycles:
                    cls.schedule_follow_up_if_eligible(app, db)

                results.append({"task_id": task.id, "status": "SENT", "recipient": recipient, "sequence": task.follow_up_sequence})
            except Exception as e:
                task.notes = f"Error sending follow-up: {e}"
                db.commit()

        return results
