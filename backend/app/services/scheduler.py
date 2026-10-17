from __future__ import annotations
import os
import uuid
import socket
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.config import settings
from app.models import (
    ScheduledTask, WorkerRun, AutomationPolicy, JobListing, CareerProfile,
    RecruiterContact, ApplicationRecord, ResumeVersion, SystemHealth, TaskEvent
)
from app.services.adapters import SourceManager
from app.services.matching import MatchingEngine
from app.services.resume_engine import ResumeEngine
from app.services.contact_service import ContactService
from app.services.email_service import EmailOutreachService
from app.services.follow_up_service import FollowUpService
from app.services.audit import record_audit_log

WORKER_ID = f"worker-{socket.gethostname()}-{os.getpid()}-{uuid.uuid4().hex[:6]}"

class DurableScheduler:
    """Coordinates durable task execution, distributed worker leases, crash recovery, and scheduled cycles."""

    @classmethod
    def register_or_update_heartbeat(cls, db: Session, current_task: str = "IDLE") -> WorkerRun:
        """Records worker heartbeat to ensure live monitoring."""
        now_ts = datetime.now(timezone.utc)
        run = db.query(WorkerRun).filter_by(worker_id=WORKER_ID).first()
        if not run:
            run = WorkerRun(
                worker_id=WORKER_ID,
                hostname=socket.gethostname(),
                status="RUNNING",
                started_at=now_ts,
                heartbeat_at=now_ts,
                current_task=current_task
            )
            db.add(run)
        else:
            run.heartbeat_at = now_ts
            run.status = "RUNNING"
            run.current_task = current_task

        # Update SystemHealth
        sh = db.query(SystemHealth).filter_by(component="worker").first()
        if sh:
            sh.status = "HEALTHY"
            sh.message = f"Active worker {WORKER_ID} heartbeat OK"
            sh.checked_at = now_ts

        db.commit()
        db.refresh(run)
        return run

    @classmethod
    def reconcile_crashed_tasks(cls, db: Session):
        """Crash Recovery: Identifies tasks left locked by expired worker heartbeats and safely resets them."""
        threshold = datetime.now(timezone.utc) - timedelta(minutes=5)
        stale_tasks = db.query(ScheduledTask).filter(
            ScheduledTask.status == "RUNNING",
            ScheduledTask.locked_until < threshold
        ).all()

        for t in stale_tasks:
            t.status = "RETRYING"
            t.locked_by = None
            t.locked_until = None
            t.retry_count += 1
            db.add(TaskEvent(
                task_id=t.id,
                worker_id=WORKER_ID,
                event_type="crash_recovery_reset",
                message=f"Task {t.task_name} was left locked; reconciled and released for retry."
            ))
        db.commit()

        # Reconcile in-progress applications: If any application was left 'SUBMISSION_IN_PROGRESS' or attempt 'SENDING'
        # do NOT auto-retry blindly (prevents duplicate applications)
        stale_attempts = db.query(ApplicationRecord).filter(
            ApplicationRecord.current_status == "SUBMISSION_IN_PROGRESS"
        ).all()
        for app in stale_attempts:
            app.current_status = "AWAITING_SUBMISSION"
            record_audit_log(
                db=db,
                action="reconcile_uncertain_application",
                actor="scheduler",
                entity_type="application_record",
                entity_id=str(app.id),
                details={"reason": "Submission interrupted; reconciled to AWAITING_SUBMISSION without blind retry."}
            )
        db.commit()

    @classmethod
    def execute_autonomous_cycle(cls, db: Session) -> Dict[str, Any]:
        """Runs one complete autonomous cycle: discovery -> matching -> tailoring -> contact verification -> application -> follow-ups."""
        cls.register_or_update_heartbeat(db, current_task="AUTONOMOUS_CYCLE")
        cls.reconcile_crashed_tasks(db)

        policy = db.query(AutomationPolicy).filter_by(id=1).first()
        if not policy:
            return {"status": "NO_POLICY", "message": "No automation policy found"}

        if policy.pause_all_automation:
            return {"status": "PAUSED", "message": "All automation is globally paused by owner."}

        profile = db.query(CareerProfile).filter_by(id=1).first()
        if not profile:
            return {"status": "NO_PROFILE", "message": "Career profile not configured."}

        summary = {
            "vacancies_discovered": 0,
            "jobs_evaluated": 0,
            "contacts_verified": 0,
            "resumes_tailored": 0,
            "applications_submitted": 0,
            "inbound_emails_processed": 0,
            "follow_ups_processed": 0
        }

        # Step 1: Autonomous Vacancy Discovery (if enabled)
        if policy.enable_auto_discovery:
            tavily = SourceManager.get_adapter("tavily_search")
            if tavily and settings.TAVILY_API_KEY:
                query = policy.search_query or "Operations Executive"
                loc = policy.search_location or "Hyderabad, India"
                new_leads = tavily.search_jobs(query, loc, limit=5)
                existing = db.query(JobListing).all()
                for lead in new_leads:
                    if not SourceManager.is_duplicate(lead, existing):
                        jl = JobListing(
                            title=lead["title"],
                            company_name=lead["company_name"],
                            location=lead["location"],
                            source_platform=lead["source_platform"],
                            original_url=lead["original_url"],
                            canonical_url=lead["canonical_url"],
                            description=lead["description"],
                            vacancy_status="VERIFIED_OPEN",
                            application_method="email",
                            date_discovered=datetime.now(timezone.utc)
                        )
                        db.add(jl)
                        db.commit()
                        existing.append(jl)
                        summary["vacancies_discovered"] += 1

                policy.last_search_at = datetime.now(timezone.utc)
                policy.next_search_at = policy.last_search_at + timedelta(minutes=policy.search_interval_minutes)
                db.commit()

        # Step 2: Autonomous Job Matching
        if policy.enable_auto_matching:
            unmatched_jobs = db.query(JobListing).filter(JobListing.match_score == 0).limit(10).all()
            for j in unmatched_jobs:
                eval_res = MatchingEngine.evaluate(j, profile)
                j.match_score = eval_res["match_score"]
                j.eligibility_status = eval_res["eligibility_status"]
                summary["jobs_evaluated"] += 1
            db.commit()

        # Step 3: Autonomous HR Contact Discovery & Verification
        if policy.enable_auto_contact_discovery:
            eligible_jobs = db.query(JobListing).filter(
                JobListing.match_score >= policy.min_match_score,
                JobListing.hr_contact_status == "UNVERIFIED"
            ).limit(5).all()

            for ej in eligible_jobs:
                contacts = ContactService.discover_public_contacts(ej.company_name, ej.location, db, job_id=ej.id)
                for c in contacts:
                    ContactService.verify_contact(c, db)
                    if c.verification_status in ["EMAIL_VALIDATED", "SOURCE_VERIFIED"]:
                        ej.hr_contact_status = "VERIFIED"
                        summary["contacts_verified"] += 1
                db.commit()

        # Step 4: Autonomous Resume Tailoring
        if policy.enable_auto_resume_tailoring:
            ready_jobs = db.query(JobListing).filter(
                JobListing.match_score >= policy.min_match_score,
                JobListing.vacancy_status == "VERIFIED_OPEN"
            ).limit(3).all()

            for rj in ready_jobs:
                has_resume = db.query(ResumeVersion).filter_by(job_id=rj.id).first()
                if not has_resume:
                    tailored = ResumeEngine.tailor(rj, profile, use_ai=True)
                    # Generate PDF and DOCX
                    pdf_out = f"./data/resumes/resume_job_{rj.id}.pdf"
                    docx_out = f"./data/resumes/resume_job_{rj.id}.docx"
                    ResumeEngine.generate_pdf(tailored, pdf_out, profile)
                    ResumeEngine.generate_docx(tailored, docx_out, profile)

                    rv = ResumeVersion(
                        profile_id=profile.id,
                        job_id=rj.id,
                        version_name=tailored["version_name"],
                        headline=tailored["headline"],
                        summary=tailored["summary"],
                        full_text=tailored["full_text"],
                        cover_letter_text=tailored["cover_letter_text"],
                        pdf_path=pdf_out,
                        docx_path=docx_out,
                        model_used=tailored["model_used"],
                        factual_consistency_score=tailored["factual_consistency_score"]
                    )
                    db.add(rv)
                    db.commit()
                    summary["resumes_tailored"] += 1

        # Step 5: Unattended Applications (ONLY if enabled by explicit owner policy)
        if policy.is_autonomous_enabled and policy.enable_unattended_email_applications and not policy.pause_applications_only:
            # Check daily application cap
            today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            apps_today = db.query(ApplicationRecord).filter(
                ApplicationRecord.created_at >= today_start,
                ApplicationRecord.current_status.in_(["SUBMITTED", "EMAIL_SENT", "DELIVERY_CONFIRMED"])
            ).count()

            remaining_allowance = max(0, policy.max_applications_per_day - apps_today)
            if remaining_allowance > 0:
                # Find qualifying jobs: verified open, verified contact, match score >= threshold, not previously applied
                qualifying = db.query(JobListing).filter(
                    JobListing.vacancy_status == "VERIFIED_OPEN",
                    JobListing.hr_contact_status == "VERIFIED",
                    JobListing.match_score >= policy.min_match_score
                ).limit(remaining_allowance).all()

                for qj in qualifying:
                    # Verify no prior application
                    prior_app = db.query(ApplicationRecord).filter_by(job_id=qj.id).first()
                    if prior_app:
                        continue

                    # Get contact
                    contact = db.query(RecruiterContact).filter_by(job_id=qj.id).first()
                    if not contact or contact.verification_status not in ["EMAIL_VALIDATED", "SOURCE_VERIFIED"]:
                        continue

                    # Get resume version
                    rv = db.query(ResumeVersion).filter_by(job_id=qj.id).first()
                    if not rv:
                        continue

                    # Create Application Record
                    app_rec = ApplicationRecord(
                        job_id=qj.id,
                        resume_version_id=rv.id,
                        current_status="APPLICATION_READY",
                        submission_method="email",
                        primary_recipient=contact.email,
                        unattended_approved=True
                    )
                    db.add(app_rec)
                    db.commit()
                    db.refresh(app_rec)

                    # Send Email Application
                    try:
                        EmailOutreachService.send_application_email(app_rec, rv, db, is_unattended=True)
                        qj.application_status = app_rec.current_status
                        summary["applications_submitted"] += 1
                        
                        # Schedule follow-up task
                        FollowUpService.schedule_follow_up_if_eligible(app_rec, db)
                    except Exception as e:
                        qj.notes = f"Application send failed: {e}"
                    db.commit()

        # Step 6: Recruiter Response Monitoring
        if policy.enable_response_monitoring:
            inbox_results = EmailOutreachService.poll_inbound_recruiter_replies(db)
            summary["inbound_emails_processed"] = len(inbox_results)

        # Step 7: Process Due Follow-ups
        if policy.enable_auto_follow_ups:
            fu_results = FollowUpService.process_due_follow_ups(db)
            summary["follow_ups_processed"] = len(fu_results)

        cls.register_or_update_heartbeat(db, current_task="IDLE")
        return {"status": "SUCCESS", "summary": summary}
