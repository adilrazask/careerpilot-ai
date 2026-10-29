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

def is_within_business_hours(policy: AutomationPolicy) -> bool:
    """Checks whether current time is within 10:00 AM - 6:00 PM local time (IST)."""
    if not getattr(policy, "enforce_business_hours", True):
        return True

    start_hour = getattr(policy, "email_window_start_hour", 10) or 10
    end_hour = getattr(policy, "email_window_end_hour", 18) or 18
    tz_offset = getattr(policy, "timezone_offset_hours", 5.5) or 5.5

    now_utc = datetime.now(timezone.utc)
    local_time = now_utc + timedelta(hours=tz_offset)

    return start_hour <= local_time.hour < end_hour

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
            query = policy.search_query or "Operations Executive"
            loc = policy.search_location or "Hyderabad, India"
            new_leads = []

            # A. Live LinkedIn public job ingestion
            linkedin = SourceManager.get_adapter("linkedin")
            if linkedin:
                new_leads.extend(linkedin.search_jobs(query, loc, limit=5))

            # B. Tavily search (if configured)
            tavily = SourceManager.get_adapter("tavily_search")
            if tavily and settings.TAVILY_API_KEY:
                new_leads.extend(tavily.search_jobs(query, loc, limit=5))

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

        # Step 5: Unattended Applications (ONLY if within 10:00 AM - 6:00 PM IST business window)
        can_send_emails = is_within_business_hours(policy)
        if not can_send_emails:
            print("[Outreach Guard] Current local time is outside business hours (10:00 AM - 6:00 PM IST). Applications and follow-up emails are held until 10:00 AM.", flush=True)

        if can_send_emails and policy.is_autonomous_enabled and policy.enable_unattended_email_applications and not policy.pause_applications_only:
            # Check daily application cap (max 15 emails/day)
            today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            apps_today = db.query(ApplicationRecord).filter(
                ApplicationRecord.created_at >= today_start,
                ApplicationRecord.current_status.in_(["SUBMITTED", "EMAIL_SENT", "MOCK_SENT", "DELIVERY_CONFIRMED"])
            ).count()

            max_today = min(policy.max_applications_per_day or 15, 15)
            remaining_allowance = max(0, max_today - apps_today)
            if remaining_allowance > 0:
                # Find qualifying jobs: verified open, verified contact, match score >= threshold, not previously applied
                qualifying = db.query(JobListing).filter(
                    JobListing.vacancy_status == "VERIFIED_OPEN",
                    JobListing.is_seed == False,
                    JobListing.hr_contact_status == "VERIFIED",
                    JobListing.match_score >= policy.min_match_score
                ).limit(remaining_allowance).all()

                for qj in qualifying:
                    # Verify no prior submitted application
                    prior_app = db.query(ApplicationRecord).filter_by(job_id=qj.id).first()
                    if prior_app and prior_app.current_status in ["SUBMITTED", "EMAIL_SENT", "MOCK_SENT", "DELIVERY_CONFIRMED", "SUBMISSION_IN_PROGRESS"]:
                        continue

                    # Get contact
                    contact = db.query(RecruiterContact).filter_by(job_id=qj.id).first()
                    if not contact or getattr(contact, "is_seed", False) or contact.verification_status not in ["EMAIL_VALIDATED", "SOURCE_VERIFIED"]:
                        continue

                    # Get resume version
                    rv = db.query(ResumeVersion).filter_by(job_id=qj.id).first()
                    if not rv:
                        tailored = ResumeEngine.tailor(qj, profile, use_ai=False)
                        pdf_out = f"./data/resumes/resume_job_{qj.id}.pdf"
                        docx_out = f"./data/resumes/resume_job_{qj.id}.docx"
                        ResumeEngine.generate_pdf(tailored, pdf_out, profile)
                        ResumeEngine.generate_docx(tailored, docx_out, profile)
                        rv = ResumeVersion(
                            profile_id=profile.id,
                            job_id=qj.id,
                            version_name=tailored["version_name"],
                            headline=tailored["headline"],
                            summary=tailored["summary"],
                            full_text=tailored["full_text"],
                            cover_letter_text=tailored["cover_letter_text"],
                            pdf_path=pdf_out,
                            docx_path=docx_out,
                            model_used="rules-conservative-verified",
                            factual_consistency_score=100.0
                        )
                        db.add(rv)
                        db.commit()
                        db.refresh(rv)

                    if prior_app and prior_app.current_status in ["APPLICATION_READY", "APPROVED_BY_USER"]:
                        app_rec = prior_app
                        app_rec.unattended_approved = True
                        app_rec.current_status = "APPROVED_BY_USER"
                        if not app_rec.resume_version_id:
                            app_rec.resume_version_id = rv.id
                        if not app_rec.primary_recipient:
                            app_rec.primary_recipient = contact.email
                    else:
                        # Create Application Record
                        app_rec = ApplicationRecord(
                            job_id=qj.id,
                            resume_version_id=rv.id,
                            current_status="APPROVED_BY_USER",
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

        # Step 7: Process Due Follow-ups (ONLY within 10am - 6pm window)
        if can_send_emails and policy.enable_auto_follow_ups and not policy.pause_applications_only:
            fu_results = FollowUpService.process_due_follow_ups(db)
            summary["follow_ups_processed"] = len(fu_results)

        cls.register_or_update_heartbeat(db, current_task="IDLE")
        return {"status": "SUCCESS", "summary": summary}

    @classmethod
    def dispatch_prepared_batch(cls, db: Session, max_count: int = 10, force: bool = False) -> Dict[str, Any]:
        """One-click batch application dispatch: applies up to remaining daily limit (max 10) with strict company deduplication."""
        policy = db.query(AutomationPolicy).filter_by(id=1).first()
        if not policy:
            return {"status": "ERROR", "message": "Automation policy not found."}

        # Check operating hours (10:00 AM - 6:00 PM IST) unless forced
        if not force and not is_within_business_hours(policy):
            return {
                "status": "PAUSED_HOURS",
                "message": "Outbound emails are paused outside business hours (10:00 AM - 6:00 PM IST). Use Force Dispatch to override or wait until 10:00 AM.",
                "dispatched_count": 0
            }

        # Daily limit check (max 15 emails/day)
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        apps_today = db.query(ApplicationRecord).filter(
            ApplicationRecord.created_at >= today_start,
            ApplicationRecord.current_status.in_(["SUBMITTED", "EMAIL_SENT", "MOCK_SENT", "DELIVERY_CONFIRMED"])
        ).count()

        daily_limit = min(policy.max_applications_per_day or 15, 15)
        remaining_today = max(0, daily_limit - apps_today)
        if remaining_today <= 0 and not force:
            return {
                "status": "DAILY_LIMIT_REACHED",
                "message": f"Daily limit of {daily_limit} emails reached for today. Next emails will send tomorrow at 10:00 AM.",
                "dispatched_count": 0
            }

        # Track already applied companies (zero duplicate company outreach)
        applied_apps = db.query(ApplicationRecord).all()
        applied_companies = set()
        for a in applied_apps:
            if a.job and a.job.company_name and a.current_status in ["SUBMITTED", "EMAIL_SENT", "MOCK_SENT", "DELIVERY_CONFIRMED"]:
                applied_companies.add(a.job.company_name.lower().strip())

        # Select prepared jobs that have verified contact
        target_count = min(remaining_today if not force else max_count, max_count)
        candidates = db.query(JobListing).filter(
            JobListing.vacancy_status == "VERIFIED_OPEN",
            JobListing.is_seed == False,
            JobListing.hr_contact_status == "VERIFIED"
        ).order_by(JobListing.match_score.desc()).all()

        dispatched = []
        for job in candidates:
            if len(dispatched) >= target_count:
                break

            company_key = (job.company_name or "").lower().strip()
            if company_key in applied_companies:
                continue

            contact = db.query(RecruiterContact).filter_by(job_id=job.id).first()
            if not contact or not contact.email or getattr(contact, "is_seed", False):
                continue

            rv = db.query(ResumeVersion).filter_by(job_id=job.id).first()
            if not rv:
                profile = db.query(CareerProfile).first()
                if profile:
                    tailored = ResumeEngine.tailor(job, profile, use_ai=False)
                    rv = ResumeVersion(
                        profile_id=profile.id,
                        job_id=job.id,
                        version_name=tailored["version_name"],
                        headline=tailored["headline"],
                        summary=tailored["summary"],
                        full_text=tailored["full_text"],
                        pdf_path="./data/resumes/SK_Adil_Raja_Resume.pdf"
                    )
                    db.add(rv)
                    db.commit()

            # Create or update application record
            prior_app = db.query(ApplicationRecord).filter_by(job_id=job.id).first()
            if prior_app and prior_app.current_status in ["SUBMITTED", "EMAIL_SENT", "MOCK_SENT", "DELIVERY_CONFIRMED"]:
                continue

            if not prior_app:
                prior_app = ApplicationRecord(
                    job_id=job.id,
                    resume_version_id=rv.id if rv else None,
                    current_status="APPROVED_BY_USER",
                    submission_method="email",
                    primary_recipient=contact.email,
                    unattended_approved=True
                )
                db.add(prior_app)
            else:
                prior_app.current_status = "APPROVED_BY_USER"
                prior_app.unattended_approved = True

            db.commit()
            db.refresh(prior_app)

            # Transmit application email using user's exact PDF
            try:
                res = EmailOutreachService.send_application_email(prior_app, rv, db, is_unattended=False)
                job.application_status = prior_app.current_status
                applied_companies.add(company_key)

                # Schedule the 3 follow-ups: Tomorrow, +15d, +30d
                FollowUpService.schedule_follow_up_if_eligible(prior_app, db)

                dispatched.append({
                    "company": job.company_name,
                    "title": job.title,
                    "recipient": contact.email,
                    "status": "SENT"
                })
            except Exception as e:
                job.notes = f"Failed to send: {e}"
            db.commit()

        return {
            "status": "SUCCESS",
            "dispatched_count": len(dispatched),
            "dispatched_jobs": dispatched,
            "remaining_daily_allowance": max(0, daily_limit - (apps_today + len(dispatched)))
        }
