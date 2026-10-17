import os
import tempfile
import pytest
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import (
    User, CareerProfile, EmploymentHistory, Skill, Education, Certification,
    CareerPreferences, JobListing, RecruiterContact, ResumeVersion,
    ApplicationRecord, ApplicationAttempt, AutomationPolicy, RecruiterResponse,
    FollowUpTask, AuditLog, ScheduledTask
)
from app.services.matching import MatchingEngine
from app.services.resume_engine import ResumeEngine
from app.services.contact_service import ContactService
from app.services.adapters import SourceManager, canonicalize_url, normalize_title
from app.services.email_service import EmailOutreachService, classify_recruiter_email
from app.services.follow_up_service import FollowUpService
from app.services.scheduler import DurableScheduler
from app.services.audit import record_audit_log

@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Seed baseline profile
    user = User(id=1, email="test@careerpilot.ai", full_name="Test Candidate")
    session.add(user)
    session.commit()

    profile = CareerProfile(
        id=1,
        user_id=1,
        full_name="Adil Raja",
        email="adil.raja@test.com",
        phone="+91 9876543210",
        current_location="Hyderabad, India",
        total_experience_years=4.0,
        summary="Experienced operations coordinator with procurement, ERP and inventory background."
    )
    session.add(profile)
    session.commit()

    # Add experience
    emp = EmploymentHistory(
        profile_id=1,
        company="Apex Industrial Ltd",
        job_title="Operations Coordinator",
        location="Hyderabad, India",
        start_date="2021-01",
        end_date="Present",
        responsibilities=[
            "Coordinated vendor procurement and purchase orders in SAP ERP.",
            "Managed warehouse inventory and goods receipt notes (GRN)."
        ],
        achievements=["Cut vendor delay by 15%"]
    )
    session.add(emp)

    # Add skills
    for s_name in ["Operations Coordination", "Procurement & Vendor Management", "ERP Systems", "Advanced Excel"]:
        session.add(Skill(profile_id=1, name=s_name, category="operations", proficiency="advanced"))

    # Add preferences
    pref = CareerPreferences(
        profile_id=1,
        preferred_titles=["Operations Executive", "Procurement Executive", "Logistics Coordinator"],
        preferred_locations=["Hyderabad, India", "Remote"],
        minimum_salary=500000.0,
        excluded_companies=["Excluded Corp"]
    )
    session.add(pref)

    # Add policy
    policy = AutomationPolicy(
        id=1,
        is_autonomous_enabled=False,
        max_applications_per_day=3,
        min_match_score=65
    )
    session.add(policy)
    session.commit()

    yield session
    session.close()

# 1. Career Profile & Preferences
def test_profile_initialization(test_db):
    prof = test_db.query(CareerProfile).filter_by(id=1).first()
    assert prof.full_name == "Adil Raja"
    assert len(prof.skills) == 4
    assert prof.preferences.minimum_salary == 500000.0

# 2. URL Canonicalization & Normalization
def test_canonicalize_url_strips_tracking():
    url = "https://www.linkedin.com/jobs/view/123456/?utm_source=share&utm_medium=member_desktop&refId=abc789"
    cleaned = canonicalize_url(url)
    assert "utm_source" not in cleaned
    assert "refId" not in cleaned
    assert cleaned == "https://www.linkedin.com/jobs/view/123456"

def test_normalize_title():
    t1 = normalize_title("Urgent Hiring: Operations Executive - Hyderabad")
    assert "operations executive" in t1
    assert "urgent" not in t1

# 3. Deduplication Logic
def test_duplicate_detection(test_db):
    j1 = JobListing(
        title="Operations Executive",
        company_name="Apex Global",
        location="Hyderabad, India",
        original_url="https://example.com/job1?utm_medium=email",
        canonical_url="https://example.com/job1",
        description="Operations and procurement role"
    )
    test_db.add(j1)
    test_db.commit()

    # Exact canonical URL duplicate
    duplicate_lead = {
        "title": "Operations Executive",
        "company_name": "Apex Global",
        "location": "Hyderabad, India",
        "original_url": "https://example.com/job1?ref=jobboard"
    }
    assert SourceManager.is_duplicate(duplicate_lead, [j1]) is True

    # Same company + title in Hyderabad
    duplicate_lead2 = {
        "title": "Operations Executive - Immediate",
        "company_name": "Apex Global",
        "location": "Hyderabad, Telangana",
        "original_url": "https://differentportal.com/job999"
    }
    assert SourceManager.is_duplicate(duplicate_lead2, [j1]) is True

    # Distinct job
    different_lead = {
        "title": "Software Developer",
        "company_name": "Tech Corp",
        "location": "Bengaluru, India",
        "original_url": "https://example.com/devjob"
    }
    assert SourceManager.is_duplicate(different_lead, [j1]) is False

# 4. Job Matching Engine & Eligibility Classification
def test_job_matching_high_fit(test_db):
    profile = test_db.query(CareerProfile).filter_by(id=1).first()
    job = JobListing(
        title="Operations Executive",
        company_name="Starlight Logistics",
        location="Hyderabad, India",
        experience_required_min=2.0,
        experience_required_max=5.0,
        description="Looking for an Operations Executive with vendor procurement, ERP, and Excel skills.",
        original_url="https://example.com/ops1"
    )
    eval_res = MatchingEngine.evaluate(job, profile)
    assert eval_res["match_score"] >= 70
    assert eval_res["eligibility_status"] == "LIKELY_ELIGIBLE"
    assert eval_res["location_match"] is True
    assert "Procurement & Vendor Management" in eval_res["matching_requirements"]

def test_job_matching_excluded_company(test_db):
    profile = test_db.query(CareerProfile).filter_by(id=1).first()
    job = JobListing(
        title="Operations Executive",
        company_name="Excluded Corp",
        location="Hyderabad, India",
        description="Operations role",
        original_url="https://example.com/ops2"
    )
    eval_res = MatchingEngine.evaluate(job, profile)
    assert eval_res["match_score"] == 0
    assert eval_res["eligibility_status"] == "NOT_ELIGIBLE"
    assert eval_res["recommended_action"] == "REJECT"

# 5. Contact Verification & Anti-Guessing
def test_contact_verification_rejects_invalid_syntax(test_db):
    c = RecruiterContact(
        company_name="Test Co",
        email="invalid-email-address",
        source_url="https://example.com/careers"
    )
    test_db.add(c)
    test_db.commit()
    vc = ContactService.verify_contact(c, test_db)
    assert vc.verification_status == "INVALID"
    assert vc.confidence == 0.1

def test_contact_verification_rejects_guesses(test_db):
    c = RecruiterContact(
        company_name="Test Co",
        email="hr@company.com",
        source_url="https://example.com/careers"
    )
    test_db.add(c)
    test_db.commit()
    vc = ContactService.verify_contact(c, test_db)
    assert vc.verification_status == "INVALID"
    assert "guessed" in vc.notes.lower()

# 6. Resume Tailoring Factual Consistency (Zero Hallucination)
def test_resume_tailoring_truthfulness(test_db):
    profile = test_db.query(CareerProfile).filter_by(id=1).first()
    job = JobListing(
        title="Procurement Executive",
        company_name="Zenith Materials",
        location="Hyderabad",
        description="Requires procurement, vendor management, and negotiation skills.",
        original_url="https://example.com/zenith"
    )
    tailored = ResumeEngine.tailor(job, profile, use_ai=False)
    assert tailored["factual_consistency_score"] == 100.0
    # Must preserve exact company name from employment history
    assert "Apex Industrial Ltd" in tailored["full_text"]
    assert "Zenith Materials" in tailored["headline"]
    assert profile.full_name.lower() in tailored["full_text"].lower()

# 7. Document Generation (PDF & DOCX)
def test_document_generation(test_db):
    profile = test_db.query(CareerProfile).filter_by(id=1).first()
    job = JobListing(
        title="Operations Lead",
        company_name="Delta Mfg",
        location="Hyderabad",
        description="Operations responsibilities.",
        original_url="https://example.com/delta"
    )
    tailored = ResumeEngine.tailor(job, profile, use_ai=False)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_path = os.path.join(tmpdir, "test_resume.pdf")
        docx_path = os.path.join(tmpdir, "test_resume.docx")
        
        ResumeEngine.generate_pdf(tailored, pdf_path, profile)
        ResumeEngine.generate_docx(tailored, docx_path, profile)
        
        assert os.path.exists(pdf_path)
        assert os.path.getsize(pdf_path) > 1000
        assert os.path.exists(docx_path)
        assert os.path.getsize(docx_path) > 1000

# 8. Email Classification
def test_recruiter_email_classification():
    ack = classify_recruiter_email("Application Received", "Thank you for applying to the operations role.")
    assert ack["classification"] == "ACKNOWLEDGEMENT"

    invite = classify_recruiter_email("Interview Invitation - Operations Executive", "We would like to schedule a Zoom interview with you.")
    assert invite["classification"] == "INTERVIEW_INVITATION"
    assert invite["action_required"] is True

    rej = classify_recruiter_email("Update on your application", "Unfortunately we are pursuing other applicants.")
    assert rej["classification"] == "REJECTION"

    suspicious = classify_recruiter_email("Urgent: Interview process fee", "Please send bitcoin or wire transfer for test fee.")
    assert suspicious["classification"] == "SUSPICIOUS"

# 9. Application Idempotency & Duplicate Prevention
def test_application_idempotency(test_db):
    job = JobListing(
        id=10,
        title="Operations Executive",
        company_name="Apex Global",
        original_url="https://example.com/ops10",
        description="Operations and coordination role.",
        vacancy_status="VERIFIED_OPEN"
    )
    test_db.add(job)
    test_db.commit()

    app = ApplicationRecord(
        id=1,
        job_id=job.id,
        current_status="APPLICATION_READY",
        submission_method="email",
        primary_recipient="hr@apex-global-valid.com"
    )
    test_db.add(app)
    rv = ResumeVersion(id=1, profile_id=1, job_id=job.id, version_name="v1", full_text="Resume text")
    test_db.add(rv)
    test_db.commit()

    # First send succeeds in mock mode
    res = EmailOutreachService.send_application_email(app, rv, test_db)
    assert res["status"] == "SUCCESS"
    assert app.current_status == "EMAIL_SENT"

    # Attempting second send with same idempotency key must raise error
    with pytest.raises(RuntimeError) as exc_info:
        EmailOutreachService.send_application_email(app, rv, test_db)
    assert "Duplicate submission prevented" in str(exc_info.value)

# 10. Follow-up Cancellation after Recruiter Reply
def test_follow_up_cancellation_on_reply(test_db):
    policy = test_db.query(AutomationPolicy).filter_by(id=1).first()
    policy.enable_auto_follow_ups = True
    test_db.commit()

    job = JobListing(
        id=20,
        title="Procurement Officer",
        company_name="Alpha Tech",
        original_url="https://example.com/alpha20",
        description="Procurement officer role.",
        vacancy_status="VERIFIED_OPEN"
    )
    test_db.add(job)
    test_db.commit()

    app = ApplicationRecord(
        id=20,
        job_id=job.id,
        current_status="EMAIL_SENT",
        primary_recipient="recruiter@alpha.com"
    )
    test_db.add(app)

    # Schedule follow-up task
    task = FollowUpTask(
        application_id=app.id,
        follow_up_sequence=1,
        due_date=datetime.now(timezone.utc),
        status="SCHEDULED"
    )
    test_db.add(task)
    test_db.commit()

    # Recruiter replies
    test_db.add(RecruiterResponse(
        application_id=app.id,
        sender_email="recruiter@alpha.com",
        subject="Re: Application",
        body_summary="Thanks, let's talk next week.",
        response_type="INTERVIEW_INVITATION"
    ))
    test_db.commit()

    # Processing due follow-ups should cancel task rather than send
    FollowUpService.process_due_follow_ups(test_db)
    assert task.status == "CANCELLED_BY_REPLY"

# 11. Audit Log Persistence
def test_audit_log_persistence(test_db):
    record_audit_log(
        db=test_db,
        action="test_security_action",
        actor="unit_tester",
        entity_type="test",
        entity_id="123",
        details={"result": "passed"}
    )
    log = test_db.query(AuditLog).filter_by(action="test_security_action").first()
    assert log is not None
    assert log.actor == "unit_tester"
    assert log.details["result"] == "passed"
