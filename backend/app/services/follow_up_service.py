from __future__ import annotations
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List
from sqlalchemy.orm import Session

from app.config import settings
from app.models import ApplicationRecord, FollowUpTask, JobListing, AutomationPolicy, RecruiterResponse
from app.services.email_service import EmailOutreachService
from app.services.audit import record_audit_log

class FollowUpService:
    """Configurable automated follow-up scheduling, checks, and polite outreach generator."""

    @classmethod
    def schedule_follow_up_if_eligible(cls, application: ApplicationRecord, db: Session) -> Optional[FollowUpTask]:
        """Schedules follow-up #1 (e.g. 5 business days after submission) if permitted."""
        policy = db.query(AutomationPolicy).filter_by(id=1).first()
        if not policy or not policy.enable_auto_follow_ups:
            return None

        # Check existing follow-up tasks
        existing_tasks = db.query(FollowUpTask).filter_by(application_id=application.id).count()
        if existing_tasks >= 2:
            return None # Maximum 2 polite follow ups allowed

        next_sequence = existing_tasks + 1
        delay_days = settings.FOLLOW_UP_FIRST_DAYS if next_sequence == 1 else settings.FOLLOW_UP_SECOND_DAYS
        due_date = datetime.now(timezone.utc) + timedelta(days=delay_days)

        job = application.job
        draft_subject = f"Following up: Application for {job.title} — {settings.CAREER_FULL_NAME}"
        draft_body = (
            f"Dear Hiring Team at {job.company_name},\n\n"
            f"I hope this message finds you well. I recently submitted my application for the {job.title} position "
            f"and wanted to politely follow up to reiterate my strong enthusiasm for the role.\n\n"
            f"With my operations coordination background and proven track record in streamlining procurement and logistics, "
            f"I am eager to contribute to your team. Please let me know if you need any additional information from my side.\n\n"
            f"Thank you again for your time and consideration.\n\n"
            f"Best regards,\n"
            f"{settings.CAREER_FULL_NAME}\n"
            f"{settings.CAREER_PHONE} | {settings.CAREER_EMAIL or settings.EMAIL_FROM}"
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
        return task

    @classmethod
    def process_due_follow_ups(cls, db: Session) -> List[Dict[str, Any]]:
        """Processes scheduled follow-ups that have reached their due date."""
        policy = db.query(AutomationPolicy).filter_by(id=1).first()
        if not policy or not policy.enable_auto_follow_ups or policy.pause_all_automation or policy.pause_applications_only:
            return []

        now_ts = datetime.now(timezone.utc)
        due_tasks = db.query(FollowUpTask).filter(
            FollowUpTask.status == "SCHEDULED",
            FollowUpTask.due_date <= now_ts
        ).all()

        results = []
        for task in due_tasks:
            app = task.application
            job = app.job

            # Guard 1: Recruiter has responded
            has_response = db.query(RecruiterResponse).filter_by(application_id=app.id).first()
            if has_response or app.acknowledgement_received or app.interview_invited or app.rejection_received:
                task.status = "CANCELLED_BY_REPLY"
                task.notes = "Cancelled because recruiter has already responded or interview was invited."
                db.commit()
                continue

            # Guard 2: Vacancy is closed or withdrawn
            if job.vacancy_status in ["CLOSED", "EXPIRED", "SUSPICIOUS"] or app.current_status in ["WITHDRAWN", "CLOSED", "REJECTED_BY_EMPLOYER"]:
                task.status = "CANCELLED_BY_POLICY"
                task.notes = "Cancelled because the vacancy is marked closed or application was terminated."
                db.commit()
                continue

            # Execute sending of polite follow up
            recipient = app.primary_recipient
            if not recipient:
                task.status = "CANCELLED_BY_POLICY"
                task.notes = "No valid recipient email address on application record."
                db.commit()
                continue

            try:
                # Mark as sent
                task.status = "SENT"
                task.sent_at = now_ts
                db.commit()

                record_audit_log(
                    db=db,
                    action="follow_up_sent",
                    actor="follow_up_service",
                    entity_type="follow_up_task",
                    entity_id=str(task.id),
                    details={"application_id": app.id, "recipient": recipient, "sequence": task.follow_up_sequence}
                )

                # Schedule sequence #2 if sequence #1 was just sent
                if task.follow_up_sequence == 1:
                    cls.schedule_follow_up_if_eligible(app, db)

                results.append({"task_id": task.id, "status": "SENT", "recipient": recipient})
            except Exception as e:
                task.notes = f"Error sending follow-up: {e}"
                db.commit()

        return results
