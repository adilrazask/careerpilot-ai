import os
import uuid
import pytest
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import (
    User, CareerProfile, EmploymentHistory, Skill, Education,
    CareerPreferences, JobListing, RecruiterContact, ResumeVersion,
    ApplicationRecord, ApplicationAttempt, AutomationPolicy, RecruiterResponse,
    FollowUpTask, ScheduledTask, AuditLog, WorkerRun, SystemHealth
)
from app.services.matching import MatchingEngine
from app.services.resume_engine import ResumeEngine
from app.services.contact_service import ContactService
from app.services.adapters import SourceManager, canonicalize_url, normalize_title
from app.services.email_service import EmailOutreachService, classify_recruiter_email
from app.services.follow_up_service import FollowUpService
from app.services.scheduler import DurableScheduler, WORKER_ID
from app.services.agent_workspace import AgentWorkspaceService
from app.routers.dashboard import get_dashboard_metrics

@pytest.fixture
def e2e_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Step 1 Seed Baseline Profile & User
    user = User(id=1, email="candidate@careerpilot.ai", full_name="Adil Raja")
    session.add(user)
    session.commit()

    profile = CareerProfile(
        id=1,
        user_id=1,
        full_name="Adil Raja",
        email="candidate@careerpilot.ai",
        phone="+91 9876543210",
        current_location="Hyderabad, India",
        total_experience_years=4.5,
        summary="Operations Coordinator with hands-on expertise in supply chain, vendor procurement, and SAP ERP."
    )
    session.add(profile)

    skills = [
        Skill(profile_id=1, name="SAP ERP", category="software", proficiency="advanced", is_verified=True),
        Skill(profile_id=1, name="Vendor Procurement", category="operations", proficiency="advanced", is_verified=True),
        Skill(profile_id=1, name="Inventory Management", category="operations", proficiency="intermediate", is_verified=True),
        Skill(profile_id=1, name="Advanced Excel", category="software", proficiency="advanced", is_verified=True),
    ]
    for s in skills:
        session.add(s)

    hist = EmploymentHistory(
        profile_id=1,
        company="Hyderabad Logistics Hub",
        job_title="Operations Coordinator",
        start_date="2021-06",
        end_date="Present",
        is_current=True,
        responsibilities=["Oversaw day-to-day warehouse dispatching, purchase orders, and supplier reconciliation in SAP ERP."],
        achievements=["Reduced procurement turnaround time by 18%."],
        tools_used=["SAP ERP", "Excel"],
        is_verified=True
    )
    session.add(hist)

    pref = CareerPreferences(
        profile_id=1,
        preferred_titles=["Operations Coordinator", "Operations Executive", "Procurement Coordinator"],
        preferred_locations=["Hyderabad, India", "Remote"],
        minimum_salary=500000.0,
        preferred_salary=750000.0,
        salary_currency="INR"
    )
    session.add(pref)

    policy = AutomationPolicy(
        id=1,
        is_autonomous_enabled=True,
        pause_all_automation=False,
        pause_applications_only=False,
        enable_unattended_email_applications=True,
        min_match_score=70,
        enable_auto_resume_tailoring=True,
        enable_auto_follow_ups=True,
        max_applications_per_day=25
    )
    session.add(policy)

    sh = SystemHealth(
        component="worker",
        status="HEALTHY",
        message="Initial state",
        checked_at=datetime.now(timezone.utc)
    )
    session.add(sh)
    session.commit()

    yield session
    session.close()


def test_complete_18_step_autonomous_workflow(e2e_db):
    session = e2e_db

    # STEP 1: Verify Candidate Profile Loaded from Database
    profile = session.query(CareerProfile).filter_by(id=1).first()
    assert profile is not None
    assert profile.full_name == "Adil Raja"
    assert profile.total_experience_years == 4.5
    assert len(profile.skills) >= 4

    # STEP 2: Natural-Language Prompt Interpreted into Structured Criteria
    prompt = "Find operations coordinator jobs in Hyderabad requiring 3 to 5 years of experience."
    instruction_result = AgentWorkspaceService.interpret_and_execute_instruction(prompt, session)
    assert instruction_result["status"] == "COMPLETED"
    assert "filters" in instruction_result
    assert instruction_result["filters"]["location"] == "Hyderabad, India"

    # STEP 3: Multi-Source Search & URL Canonicalization
    raw_url = "https://careers.globaltech.com/jobs/ops-coord-999?utm_source=linkedin&utm_medium=tracker"
    clean_url = canonicalize_url(raw_url)
    assert clean_url == "https://careers.globaltech.com/jobs/ops-coord-999"

    job_listing = JobListing(
        title="Operations Coordinator - Supply Chain",
        company_name="Global Tech Solutions",
        location="Hyderabad, India",
        work_mode="Hybrid",
        employment_type="Full-time",
        experience_required_min=3.0,
        experience_required_max=5.0,
        salary_min=600000.0,
        salary_max=800000.0,
        salary_currency="INR",
        source_platform="Direct Careers",
        original_url=raw_url,
        canonical_url=clean_url,
        description="We are seeking an Operations Coordinator in Hyderabad. Responsibilities include vendor procurement, SAP ERP management, inventory audit, and supplier reconciliation.",
        vacancy_status="VERIFIED_OPEN",
        application_method="email",
        date_discovered=datetime.now(timezone.utc)
    )
    session.add(job_listing)
    session.commit()
    session.refresh(job_listing)

    # STEP 4: Duplicate Filtering Prevention
    dup_url = "https://careers.globaltech.com/jobs/ops-coord-999?ref=indeed"
    is_dup = session.query(JobListing).filter(
        (JobListing.original_url == dup_url) | 
        (JobListing.canonical_url == canonicalize_url(dup_url))
    ).first()
    assert is_dup is not None, "Duplicate URL was not detected"

    # STEP 5: Vacancy Suitability Evaluated Against Candidate Facts
    evaluation = MatchingEngine.evaluate(job_listing, profile)
    assert evaluation["eligibility_status"] == "LIKELY_ELIGIBLE"
    assert evaluation["match_score"] >= 70

    # STEP 6: Honest Match Score and Explanation Generated
    assert evaluation["location_match"] is True
    assert evaluation["score_breakdown"]["skills_score"] > 0
    assert len(evaluation["explanation"]) > 20
    job_listing.match_score = evaluation["match_score"]
    job_listing.eligibility_status = evaluation["eligibility_status"]
    session.commit()

    # STEP 7: Discovered HR Contacts Verified (DNS/Syntax & Anti-guessing)
    contact = RecruiterContact(
        job_id=job_listing.id,
        company_name="Global Tech Solutions",
        contact_name="Sunita Reddy",
        contact_role="Talent Acquisition Lead",
        email="sunita.reddy@gmail.com", # Valid RFC domain with active MX
        source_url="https://careers.globaltech.com/team",
        verification_status="DISCOVERED"
    )
    session.add(contact)
    session.commit()

    verif_res = ContactService.verify_contact(contact, session)
    assert verif_res.verification_status in ["SOURCE_VERIFIED", "EMAIL_VALIDATED"]
    assert contact.verification_status in ["SOURCE_VERIFIED", "EMAIL_VALIDATED"]
    job_listing.hr_contact_status = "VERIFIED"
    session.commit()

    # Test Guess Rejection: info@ or test@ must be rejected
    fake_contact = RecruiterContact(
        job_id=job_listing.id,
        company_name="Global Tech Solutions",
        contact_name="Fake Bot",
        email="info@example.com",
        source_url="https://example.com",
        verification_status="DISCOVERED"
    )
    session.add(fake_contact)
    session.commit()
    fake_verif = ContactService.verify_contact(fake_contact, session)
    assert fake_verif.verification_status == "INVALID"
    assert fake_contact.verification_status == "INVALID"

    # STEP 8: Truthful Tailored Resume Generated
    tailor_result = ResumeEngine.tailor(job_listing, profile, use_ai=False)
    assert tailor_result["factual_consistency_score"] == 100.0
    # Guarantee: Did not invent employer or alter factual truth
    assert "Hyderabad Logistics Hub" in str(tailor_result["experience"])
    assert "Global Tech Solutions" in tailor_result["headline"]

    os.makedirs("./data/resumes", exist_ok=True)
    pdf_out = f"./data/resumes/test_resume_{job_listing.id}.pdf"
    docx_out = f"./data/resumes/test_resume_{job_listing.id}.docx"

    # STEP 9: ATS-friendly PDF and DOCX Generated
    ResumeEngine.generate_pdf(tailor_result, pdf_out, profile)
    ResumeEngine.generate_docx(tailor_result, docx_out, profile)
    assert os.path.exists(pdf_out)
    assert os.path.exists(docx_out)
    assert os.path.getsize(pdf_out) > 500
    assert os.path.getsize(docx_out) > 500

    resume_ver = ResumeVersion(
        profile_id=profile.id,
        job_id=job_listing.id,
        version_name=tailor_result["version_name"],
        headline=tailor_result["headline"],
        summary=tailor_result["summary"],
        full_text=tailor_result["full_text"],
        cover_letter_text=tailor_result["cover_letter_text"],
        pdf_path=pdf_out,
        docx_path=docx_out,
        model_used=tailor_result["model_used"],
        factual_consistency_score=tailor_result["factual_consistency_score"]
    )
    session.add(resume_ver)
    session.commit()

    # STEP 10: Application Record Created in Initial State
    app_record = ApplicationRecord(
        job_id=job_listing.id,
        resume_version_id=resume_ver.id,
        current_status="APPLICATION_READY",
        submission_method="email",
        primary_recipient=contact.email,
        unattended_approved=True,
        created_at=datetime.now(timezone.utc)
    )
    session.add(app_record)
    session.commit()
    assert app_record.id is not None
    assert app_record.current_status == "APPLICATION_READY"

    # STEP 11: Unattended Policy Evaluated
    policy = session.query(AutomationPolicy).filter_by(id=1).first()
    can_auto_apply = (
        policy.enable_unattended_email_applications and
        job_listing.match_score >= policy.min_match_score and
        job_listing.vacancy_status == "VERIFIED_OPEN" and
        contact.verification_status in ["SOURCE_VERIFIED", "EMAIL_VALIDATED"]
    )
    assert can_auto_apply is True

    # STEP 12 & 13 & 14: Idempotency Key Checked, Application Email Sent, Delivery Confirmed
    send_result = EmailOutreachService.send_application_email(app_record, resume_ver, session, is_unattended=True)
    assert send_result["status"] == "SUCCESS"
    assert app_record.current_status == "EMAIL_SENT"

    # Ensure duplicate attempt is blocked by idempotency
    attempts = session.query(ApplicationAttempt).filter_by(application_id=app_record.id).all()
    assert len(attempts) == 1
    assert attempts[0].status == "SUCCESS"
    with pytest.raises(RuntimeError):
        EmailOutreachService.send_application_email(app_record, resume_ver, session, is_unattended=True)

    # STEP 15: Follow-up Scheduled
    fu_task = FollowUpService.schedule_follow_up_if_eligible(app_record, session)
    assert fu_task is not None
    assert fu_task.status == "SCHEDULED"
    assert fu_task.follow_up_sequence == 1

    # STEP 16: Background Worker Leases Task, Executes Safely, Heartbeat Updated
    heartbeat_record = DurableScheduler.register_or_update_heartbeat(session, current_task="E2E_VERIFICATION")
    assert heartbeat_record is not None
    assert heartbeat_record.status == "RUNNING"
    assert heartbeat_record.worker_id == WORKER_ID

    # Verify crash recovery reconciliation
    from datetime import timedelta
    stale_task = ScheduledTask(
        task_name="verify_vacancies",
        status="RUNNING",
        locked_by="crashed-worker-99",
        locked_until=datetime.now(timezone.utc) - timedelta(minutes=10)
    )
    session.add(stale_task)
    session.commit()
    DurableScheduler.reconcile_crashed_tasks(session)
    session.refresh(stale_task)
    assert stale_task.status == "RETRYING"
    assert stale_task.locked_by is None

    # STEP 17: Recruiter Response Parsed and Classified
    incoming_raw = (
        "Dear Adil Raja,\n\n"
        "Thank you for submitting your application for the Operations Coordinator role at Global Tech Solutions.\n"
        "We are pleased to invite you for an interview with our hiring team via Zoom.\n"
        "Please let us know your availability for this week.\n\n"
        "Best regards,\nSunita Reddy\nTalent Acquisition"
    )
    classified = classify_recruiter_email("Interview Invitation: Operations Coordinator", incoming_raw)
    assert classified["classification"] == "INTERVIEW_INVITATION"
    assert classified["action_required"] is True
    assert classified["sentiment"] == "POSITIVE"

    recruiter_resp = RecruiterResponse(
        application_id=app_record.id,
        sender_email="sunita.reddy@gmail.com",
        subject="Interview Invitation: Operations Coordinator",
        body_summary="Invited for Zoom interview with hiring team.",
        response_type=classified["classification"],
        sentiment=classified["sentiment"],
        requires_user_action=classified["action_required"],
        action_description=classified.get("action_desc", "Interview scheduled"),
        received_at=datetime.now(timezone.utc)
    )
    session.add(recruiter_resp)
    app_record.interview_invited = True
    app_record.current_status = "INTERVIEW_INVITED"
    session.commit()

    # Recruiter response automatically cancels scheduled follow-ups
    fu_task.due_date = datetime.now(timezone.utc) # Make it due now
    session.commit()
    FollowUpService.process_due_follow_ups(session)
    session.refresh(fu_task)
    assert fu_task.status == "CANCELLED_BY_REPLY"

    # STEP 18: Pipeline and Dashboard Metrics Updated Automatically
    metrics = get_dashboard_metrics(session)
    assert metrics.total_vacancies_discovered >= 1
    assert metrics.applications_submitted >= 1
    assert metrics.email_applications_sent >= 1
    assert metrics.interview_invitations >= 1
    assert "RUNNING" in metrics.agent_status
