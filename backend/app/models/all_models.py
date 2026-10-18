from __future__ import annotations
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, Float, DateTime, ForeignKey, Index, JSON, Enum
)
from sqlalchemy.orm import relationship
from app.database import Base

def utcnow() -> datetime:
    return datetime.now(timezone.utc)

# 1. User
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=True)
    full_name = Column(String(255), nullable=False)
    role = Column(String(50), default="owner")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    career_profile = relationship("CareerProfile", back_populates="user", uselist=False)

# 2. CareerProfile
class CareerProfile(Base):
    __tablename__ = "career_profiles"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    full_name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    phone = Column(String(100), nullable=False)
    current_location = Column(String(255), default="Hyderabad, India")
    total_experience_years = Column(Float, default=4.0)
    summary = Column(Text, default="")
    portfolio_url = Column(String(500), default="")
    linkedin_url = Column(String(500), default="")
    preferred_contact_method = Column(String(50), default="email")
    verified_facts = Column(JSON, default=dict) # Dict of verified factual statements
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    user = relationship("User", back_populates="career_profile")
    employment_history = relationship("EmploymentHistory", back_populates="career_profile", cascade="all, delete-orphan")
    skills = relationship("Skill", back_populates="career_profile", cascade="all, delete-orphan")
    education = relationship("Education", back_populates="career_profile", cascade="all, delete-orphan")
    certifications = relationship("Certification", back_populates="career_profile", cascade="all, delete-orphan")
    preferences = relationship("CareerPreferences", back_populates="career_profile", uselist=False, cascade="all, delete-orphan")
    resume_files = relationship("ResumeFile", back_populates="career_profile", cascade="all, delete-orphan")
    resume_versions = relationship("ResumeVersion", back_populates="career_profile", cascade="all, delete-orphan")

# 3. EmploymentHistory
class EmploymentHistory(Base):
    __tablename__ = "employment_history"
    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("career_profiles.id", ondelete="CASCADE"), nullable=False)
    company = Column(String(255), nullable=False)
    job_title = Column(String(255), nullable=False)
    location = Column(String(255), default="")
    start_date = Column(String(50), nullable=False) # e.g. "2021-06"
    end_date = Column(String(50), default="Present")
    is_current = Column(Boolean, default=False)
    responsibilities = Column(JSON, default=list) # List of bullet points
    achievements = Column(JSON, default=list)
    tools_used = Column(JSON, default=list)
    is_verified = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    career_profile = relationship("CareerProfile", back_populates="employment_history")

# 4. Skill
class Skill(Base):
    __tablename__ = "skills"
    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("career_profiles.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(150), nullable=False, index=True)
    category = Column(String(100), default="general") # software, operations, logistics, soft_skill
    years_experience = Column(Float, default=1.0)
    proficiency = Column(String(50), default="intermediate") # beginner, intermediate, advanced, expert
    is_verified = Column(Boolean, default=True)

    career_profile = relationship("CareerProfile", back_populates="skills")

# 5. Education
class Education(Base):
    __tablename__ = "education"
    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("career_profiles.id", ondelete="CASCADE"), nullable=False)
    institution = Column(String(255), nullable=False)
    degree = Column(String(255), nullable=False)
    field_of_study = Column(String(255), default="")
    start_year = Column(String(50), default="")
    graduation_year = Column(String(50), default="")
    grade_or_gpa = Column(String(50), default="")
    is_verified = Column(Boolean, default=True)

    career_profile = relationship("CareerProfile", back_populates="education")

# 6. Certification
class Certification(Base):
    __tablename__ = "certifications"
    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("career_profiles.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    issuing_organization = Column(String(255), nullable=False)
    issue_date = Column(String(50), default="")
    expiry_date = Column(String(50), default="")
    credential_id = Column(String(255), default="")
    credential_url = Column(String(500), default="")
    is_verified = Column(Boolean, default=True)

    career_profile = relationship("CareerProfile", back_populates="certifications")

# 7. CareerPreferences
class CareerPreferences(Base):
    __tablename__ = "career_preferences"
    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("career_profiles.id", ondelete="CASCADE"), unique=True, nullable=False)
    preferred_titles = Column(JSON, default=list)
    preferred_locations = Column(JSON, default=list) # e.g. ["Hyderabad, India", "Remote", "Dubai, UAE"]
    open_to_remote = Column(Boolean, default=True)
    open_to_relocation = Column(Boolean, default=True)
    relocation_preferences = Column(JSON, default=list)
    minimum_salary = Column(Float, default=0.0)
    preferred_salary = Column(Float, default=0.0)
    salary_currency = Column(String(10), default="INR")
    notice_period_days = Column(Integer, default=30)
    availability = Column(String(100), default="Immediate to 30 days")
    work_authorisation = Column(String(255), default="Citizen / Authorized in India")
    preferred_industries = Column(JSON, default=list)
    excluded_industries = Column(JSON, default=list)
    excluded_companies = Column(JSON, default=list)
    work_mode = Column(JSON, default=lambda: ["On-site", "Hybrid", "Remote"])
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    career_profile = relationship("CareerProfile", back_populates="preferences")

# 8. ResumeFile (Uploaded base documents)
class ResumeFile(Base):
    __tablename__ = "resume_files"
    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("career_profiles.id", ondelete="CASCADE"), nullable=False)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_type = Column(String(50), nullable=False) # pdf, docx, txt
    extracted_text = Column(Text, nullable=False)
    is_primary = Column(Boolean, default=True)
    parsed_data = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    career_profile = relationship("CareerProfile", back_populates="resume_files")

# 9. ResumeVersion (Generated/tailored versions per job)
class ResumeVersion(Base):
    __tablename__ = "resume_versions"
    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("career_profiles.id", ondelete="CASCADE"), nullable=False)
    job_id = Column(Integer, ForeignKey("job_listings.id", ondelete="SET NULL"), nullable=True)
    version_name = Column(String(255), nullable=False)
    headline = Column(String(255), default="")
    summary = Column(Text, default="")
    full_text = Column(Text, nullable=False)
    cover_letter_text = Column(Text, default="")
    pdf_path = Column(String(500), default="")
    docx_path = Column(String(500), default="")
    generation_prompt = Column(Text, default="")
    model_used = Column(String(100), default="conservative-rules")
    factual_consistency_score = Column(Float, default=100.0) # 0-100% verified against profile
    created_at = Column(DateTime(timezone=True), default=utcnow)

    career_profile = relationship("CareerProfile", back_populates="resume_versions")
    job_listing = relationship("JobListing", back_populates="resume_versions")
    application_records = relationship("ApplicationRecord", back_populates="resume_version")

# 10. JobSource
class JobSource(Base):
    __tablename__ = "job_sources"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False) # linkedin, naukri, indeed, workindia, foundit, career_page, tavily_search
    category = Column(String(100), default="portal")
    is_active = Column(Boolean, default=True)
    supports_auto_application = Column(Boolean, default=False)
    rate_limit_per_minute = Column(Integer, default=10)
    adapter_class = Column(String(100), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    integrations = relationship("SourceIntegration", back_populates="source")
    listings = relationship("JobListing", back_populates="source_rel")

# 11. SourceIntegration
class SourceIntegration(Base):
    __tablename__ = "source_integrations"
    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey("job_sources.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(150), nullable=False)
    auth_type = Column(String(50), default="api_key") # api_key, oauth, session, none
    config = Column(JSON, default=dict)
    is_enabled = Column(Boolean, default=True)
    last_status = Column(String(50), default="DISCONNECTED") # CONNECTED, ERROR, RATE_LIMITED, DISCONNECTED
    last_checked_at = Column(DateTime(timezone=True), nullable=True)
    last_error = Column(Text, default="")
    created_at = Column(DateTime(timezone=True), default=utcnow)

    source = relationship("JobSource", back_populates="integrations")

# 12. CompanyProfile
class CompanyProfile(Base):
    __tablename__ = "company_profiles"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, index=True, nullable=False)
    website = Column(String(500), default="")
    careers_url = Column(String(500), default="")
    industry = Column(String(150), default="")
    headquarters = Column(String(255), default="")
    size_range = Column(String(100), default="")
    description = Column(Text, default="")
    is_excluded = Column(Boolean, default=False)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    contacts = relationship("RecruiterContact", back_populates="company")
    listings = relationship("JobListing", back_populates="company_profile")

# 13. JobListing
class JobListing(Base):
    __tablename__ = "job_listings"
    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey("job_sources.id", ondelete="SET NULL"), nullable=True)
    company_id = Column(Integer, ForeignKey("company_profiles.id", ondelete="SET NULL"), nullable=True)
    title = Column(String(255), nullable=False, index=True)
    company_name = Column(String(255), nullable=False, index=True)
    location = Column(String(255), default="Hyderabad, India", index=True)
    work_mode = Column(String(50), default="On-site") # On-site, Hybrid, Remote
    employment_type = Column(String(50), default="Full-time") # Full-time, Contract, Internship
    experience_required_min = Column(Float, default=0.0)
    experience_required_max = Column(Float, default=0.0)
    salary_min = Column(Float, default=0.0)
    salary_max = Column(Float, default=0.0)
    salary_currency = Column(String(10), default="INR")
    source_platform = Column(String(100), default="Web")
    original_url = Column(String(1000), unique=True, index=True, nullable=False)
    canonical_url = Column(String(1000), index=True, default="")
    employer_job_id = Column(String(150), default="")
    description = Column(Text, nullable=False)
    extracted_responsibilities = Column(JSON, default=list)
    extracted_skills = Column(JSON, default=list)
    publication_date = Column(DateTime(timezone=True), nullable=True)
    date_discovered = Column(DateTime(timezone=True), default=utcnow)
    last_verified_date = Column(DateTime(timezone=True), default=utcnow)
    vacancy_status = Column(String(50), default="DISCOVERED") # DISCOVERED, VERIFIED_OPEN, CLOSED, EXPIRED, SUSPICIOUS
    match_score = Column(Integer, default=0, index=True)
    eligibility_status = Column(String(50), default="REVIEW_REQUIRED") # LIKELY_ELIGIBLE, REVIEW_REQUIRED, NOT_ELIGIBLE
    application_method = Column(String(50), default="email") # email, portal, api
    hr_contact_status = Column(String(50), default="UNVERIFIED")
    application_status = Column(String(50), default="DISCOVERED", index=True) # Full 21-state ATS status
    notes = Column(Text, default="")
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    source_rel = relationship("JobSource", back_populates="listings")
    company_profile = relationship("CompanyProfile", back_populates="listings")
    requirements = relationship("JobRequirement", back_populates="job", cascade="all, delete-orphan")
    match_results = relationship("JobMatchResult", back_populates="job", cascade="all, delete-orphan")
    resume_versions = relationship("ResumeVersion", back_populates="job_listing")
    contacts = relationship("RecruiterContact", back_populates="job_listing")
    application_record = relationship("ApplicationRecord", back_populates="job", uselist=False, cascade="all, delete-orphan")

# 14. JobRequirement
class JobRequirement(Base):
    __tablename__ = "job_requirements"
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("job_listings.id", ondelete="CASCADE"), nullable=False)
    requirement_text = Column(Text, nullable=False)
    category = Column(String(50), default="skill") # skill, experience, degree, certification, tool
    is_mandatory = Column(Boolean, default=True)

    job = relationship("JobListing", back_populates="requirements")

# 15. JobMatchResult
class JobMatchResult(Base):
    __tablename__ = "job_match_results"
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("job_listings.id", ondelete="CASCADE"), nullable=False)
    match_score = Column(Integer, nullable=False)
    eligibility_status = Column(String(50), nullable=False) # LIKELY_ELIGIBLE, REVIEW_REQUIRED, NOT_ELIGIBLE
    matching_requirements = Column(JSON, default=list)
    missing_requirements = Column(JSON, default=list)
    uncertain_requirements = Column(JSON, default=list)
    location_match = Column(Boolean, default=True)
    salary_match = Column(String(50), default="UNKNOWN") # MATCH, MISMATCH, UNKNOWN
    score_breakdown = Column(JSON, default=dict)
    explanation = Column(Text, default="")
    recommended_action = Column(String(100), default="REVIEW") # PREPARE_APPLICATION, HOLD, REJECT
    created_at = Column(DateTime(timezone=True), default=utcnow)

    job = relationship("JobListing", back_populates="match_results")

# 16. RecruiterContact
class RecruiterContact(Base):
    __tablename__ = "recruiter_contacts"
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("company_profiles.id", ondelete="SET NULL"), nullable=True)
    job_id = Column(Integer, ForeignKey("job_listings.id", ondelete="SET NULL"), nullable=True)
    contact_name = Column(String(255), default="Hiring Team")
    contact_role = Column(String(255), default="Talent Acquisition / HR")
    company_name = Column(String(255), nullable=False)
    email = Column(String(255), index=True, default="")
    phone = Column(String(100), default="")
    source_url = Column(String(1000), default="")
    discovery_date = Column(DateTime(timezone=True), default=utcnow)
    verification_status = Column(String(50), default="UNVERIFIED") # DISCOVERED, SOURCE_VERIFIED, EMAIL_VALIDATED, UNVERIFIED, INVALID, OUTDATED
    verification_method = Column(String(100), default="") # official_careers_page, mx_check, manual_check
    last_verification_date = Column(DateTime(timezone=True), nullable=True)
    confidence = Column(Float, default=0.0) # 0.0 to 1.0
    intended_use = Column(String(100), default="application_outreach")
    notes = Column(Text, default="")
    created_at = Column(DateTime(timezone=True), default=utcnow)

    company = relationship("CompanyProfile", back_populates="contacts")
    job_listing = relationship("JobListing", back_populates="contacts")
    verification_records = relationship("ContactVerificationRecord", back_populates="contact", cascade="all, delete-orphan")

# 17. ContactVerificationRecord
class ContactVerificationRecord(Base):
    __tablename__ = "contact_verification_records"
    id = Column(Integer, primary_key=True, index=True)
    contact_id = Column(Integer, ForeignKey("recruiter_contacts.id", ondelete="CASCADE"), nullable=False)
    verification_type = Column(String(50), nullable=False) # syntax, dns_mx, source_url_scrape, smtp_handshake
    status = Column(String(50), nullable=False) # PASSED, FAILED, WARNING
    details = Column(Text, default="")
    verified_at = Column(DateTime(timezone=True), default=utcnow)

    contact = relationship("RecruiterContact", back_populates="verification_records")

# 18. ApplicationRecord
class ApplicationRecord(Base):
    __tablename__ = "application_records"
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("job_listings.id", ondelete="CASCADE"), unique=True, nullable=False)
    resume_version_id = Column(Integer, ForeignKey("resume_versions.id", ondelete="SET NULL"), nullable=True)
    current_status = Column(String(50), default="DISCOVERED", index=True) # Full 21 statuses
    submission_method = Column(String(50), default="email") # email, portal, api
    primary_recipient = Column(String(255), default="")
    external_confirmation_id = Column(String(255), default="")
    delivery_evidence = Column(JSON, default=dict)
    acknowledgement_received = Column(Boolean, default=False)
    interview_invited = Column(Boolean, default=False)
    rejection_received = Column(Boolean, default=False)
    unattended_approved = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    job = relationship("JobListing", back_populates="application_record")
    resume_version = relationship("ResumeVersion", back_populates="application_records")
    attempts = relationship("ApplicationAttempt", back_populates="application", cascade="all, delete-orphan")
    documents = relationship("ApplicationDocument", back_populates="application", cascade="all, delete-orphan")
    emails = relationship("EmailMessage", back_populates="application", cascade="all, delete-orphan")
    follow_ups = relationship("FollowUpTask", back_populates="application", cascade="all, delete-orphan")
    recruiter_responses = relationship("RecruiterResponse", back_populates="application", cascade="all, delete-orphan")
    interviews = relationship("Interview", back_populates="application", cascade="all, delete-orphan")

# 19. ApplicationAttempt
class ApplicationAttempt(Base):
    __tablename__ = "application_attempts"
    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("application_records.id", ondelete="CASCADE"), nullable=False)
    attempt_number = Column(Integer, default=1)
    submission_method = Column(String(50), nullable=False)
    recipient_or_portal = Column(String(500), nullable=False)
    idempotency_key = Column(String(255), unique=True, index=True, nullable=False)
    status = Column(String(50), nullable=False) # SENDING, SUCCESS, FAILED, BLOCKED, UNCERTAIN
    evidence = Column(JSON, default=dict)
    error_message = Column(Text, default="")
    retry_eligible = Column(Boolean, default=False)
    attempted_at = Column(DateTime(timezone=True), default=utcnow)

    application = relationship("ApplicationRecord", back_populates="attempts")

# 20. ApplicationDocument
class ApplicationDocument(Base):
    __tablename__ = "application_documents"
    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("application_records.id", ondelete="CASCADE"), nullable=False)
    doc_type = Column(String(50), nullable=False) # resume_pdf, resume_docx, cover_letter
    file_path = Column(String(500), nullable=False)
    filename = Column(String(255), nullable=False)
    sha256_hash = Column(String(64), default="")
    created_at = Column(DateTime(timezone=True), default=utcnow)

    application = relationship("ApplicationRecord", back_populates="documents")

# 21. EmailMessage (Outbound & Inbound)
class EmailMessage(Base):
    __tablename__ = "email_messages"
    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("application_records.id", ondelete="SET NULL"), nullable=True)
    direction = Column(String(20), default="outbound") # outbound, inbound
    sender = Column(String(255), nullable=False)
    recipient = Column(String(255), nullable=False)
    subject = Column(String(500), nullable=False)
    body_text = Column(Text, nullable=False)
    body_html = Column(Text, default="")
    message_id_header = Column(String(255), index=True, default="")
    in_reply_to = Column(String(255), default="")
    classification = Column(String(50), default="APPLICATION") # APPLICATION, ACKNOWLEDGEMENT, INTERVIEW_INVITATION, RECRUITER_QUESTION, DOCUMENT_REQUEST, REJECTION, OFFER, FOLLOWUP_RESPONSE, UNRELATED, SUSPICIOUS
    status = Column(String(50), default="SENT") # DRAFT, QUEUED, SENT, DELIVERED, BOUNCED, FAILED
    provider = Column(String(50), default="smtp") # smtp, gmail, graph
    sent_or_received_at = Column(DateTime(timezone=True), default=utcnow)

    application = relationship("ApplicationRecord", back_populates="emails")
    events = relationship("EmailEvent", back_populates="email_message", cascade="all, delete-orphan")

# 22. EmailEvent
class EmailEvent(Base):
    __tablename__ = "email_events"
    id = Column(Integer, primary_key=True, index=True)
    email_id = Column(Integer, ForeignKey("email_messages.id", ondelete="CASCADE"), nullable=False)
    event_type = Column(String(50), nullable=False) # ACCEPTED, DELIVERED, OPENED, BOUNCED, SPAM_REPORT, ERROR
    provider_response = Column(Text, default="")
    occurred_at = Column(DateTime(timezone=True), default=utcnow)

    email_message = relationship("EmailMessage", back_populates="events")

# 23. FollowUpTask
class FollowUpTask(Base):
    __tablename__ = "follow_up_tasks"
    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("application_records.id", ondelete="CASCADE"), nullable=False)
    follow_up_sequence = Column(Integer, default=1) # 1 = first follow up, 2 = second follow up
    due_date = Column(DateTime(timezone=True), nullable=False)
    status = Column(String(50), default="SCHEDULED") # SCHEDULED, SENT, CANCELLED_BY_REPLY, CANCELLED_BY_POLICY, CANCELLED_BY_USER
    draft_subject = Column(String(500), default="")
    draft_body = Column(Text, default="")
    sent_at = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, default="")
    created_at = Column(DateTime(timezone=True), default=utcnow)

    application = relationship("ApplicationRecord", back_populates="follow_ups")

# 24. RecruiterResponse
class RecruiterResponse(Base):
    __tablename__ = "recruiter_responses"
    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("application_records.id", ondelete="CASCADE"), nullable=False)
    sender_email = Column(String(255), nullable=False)
    subject = Column(String(500), nullable=False)
    body_summary = Column(Text, nullable=False)
    response_type = Column(String(50), nullable=False) # ACKNOWLEDGEMENT, INTERVIEW_INVITATION, RECRUITER_QUESTION, DOCUMENT_REQUEST, REJECTION, OFFER, SUSPICIOUS
    sentiment = Column(String(50), default="NEUTRAL")
    requires_user_action = Column(Boolean, default=False)
    action_description = Column(String(255), default="")
    received_at = Column(DateTime(timezone=True), default=utcnow)

    application = relationship("ApplicationRecord", back_populates="recruiter_responses")

# 25. Interview
class Interview(Base):
    __tablename__ = "interviews"
    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("application_records.id", ondelete="CASCADE"), nullable=False)
    scheduled_time = Column(DateTime(timezone=True), nullable=True)
    format = Column(String(100), default="Video Call") # Video Call, Phone, In-person
    meeting_link = Column(String(500), default="")
    interviewers = Column(JSON, default=list)
    status = Column(String(50), default="INVITED") # INVITED, CONFIRMED, COMPLETED, RESCHEDULED, CANCELLED
    notes = Column(Text, default="")
    created_at = Column(DateTime(timezone=True), default=utcnow)

    application = relationship("ApplicationRecord", back_populates="interviews")

# 26. AutomationPolicy
class AutomationPolicy(Base):
    __tablename__ = "automation_policies"
    id = Column(Integer, primary_key=True, index=True)
    is_autonomous_enabled = Column(Boolean, default=False)
    pause_all_automation = Column(Boolean, default=False)
    pause_applications_only = Column(Boolean, default=False)
    enable_auto_discovery = Column(Boolean, default=True)
    enable_auto_matching = Column(Boolean, default=True)
    enable_auto_resume_tailoring = Column(Boolean, default=True)
    enable_auto_contact_discovery = Column(Boolean, default=True)
    enable_unattended_email_applications = Column(Boolean, default=False)
    enable_unattended_portal_applications = Column(Boolean, default=False)
    enable_auto_follow_ups = Column(Boolean, default=False)
    enable_response_monitoring = Column(Boolean, default=True)
    max_applications_per_day = Column(Integer, default=5)
    max_applications_per_company_per_month = Column(Integer, default=2)
    min_match_score = Column(Integer, default=65)
    max_emails_per_hour = Column(Integer, default=10)
    search_interval_minutes = Column(Integer, default=240)
    allowed_locations = Column(JSON, default=lambda: ["Hyderabad, India", "Remote", "Dubai, UAE"])
    allowed_job_families = Column(JSON, default=list)
    allowed_salary_min = Column(Float, default=0.0)
    excluded_companies = Column(JSON, default=list)
    excluded_employers = Column(JSON, default=list)
    search_query = Column(String(500), default="Operations Executive OR Business Operations OR Procurement OR Supply Chain")
    search_location = Column(String(255), default="Hyderabad, Telangana, India")
    last_search_at = Column(DateTime(timezone=True), nullable=True)
    next_search_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

# 27. ScheduledTask & Task Queue
class ScheduledTask(Base):
    __tablename__ = "scheduled_tasks"
    id = Column(Integer, primary_key=True, index=True)
    task_name = Column(String(100), nullable=False) # discover_jobs, verify_vacancies, evaluate_matches, send_applications, poll_inbox, process_follow_ups
    payload = Column(JSON, default=dict)
    cron_or_interval = Column(String(100), default="")
    status = Column(String(50), default="PENDING") # PENDING, RUNNING, COMPLETED, FAILED, RETRYING
    priority = Column(Integer, default=5) # 1 = highest, 10 = lowest
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    scheduled_for = Column(DateTime(timezone=True), default=utcnow, index=True)
    locked_by = Column(String(100), nullable=True) # Worker lease identifier
    locked_until = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    completed_at = Column(DateTime(timezone=True), nullable=True)

# 28. WorkerRun & Lease
class WorkerRun(Base):
    __tablename__ = "worker_runs"
    id = Column(Integer, primary_key=True, index=True)
    worker_id = Column(String(100), nullable=False, index=True)
    hostname = Column(String(255), default="")
    status = Column(String(50), default="RUNNING") # RUNNING, STOPPED, CRASHED, IDLE
    heartbeat_at = Column(DateTime(timezone=True), default=utcnow)
    started_at = Column(DateTime(timezone=True), default=utcnow)
    stopped_at = Column(DateTime(timezone=True), nullable=True)
    tasks_processed = Column(Integer, default=0)
    errors_count = Column(Integer, default=0)
    current_task = Column(String(255), default="")

# 29. TaskEvent
class TaskEvent(Base):
    __tablename__ = "task_events"
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("scheduled_tasks.id", ondelete="CASCADE"), nullable=True)
    worker_id = Column(String(100), default="")
    event_type = Column(String(100), nullable=False)
    message = Column(Text, nullable=False)
    data = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=utcnow)

# 30. Notification
class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True, index=True)
    level = Column(String(20), default="info") # info, warning, error, success
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    link = Column(String(500), default="")
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)

# 31. AuditLog
class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    action = Column(String(150), nullable=False, index=True)
    actor = Column(String(100), default="system") # system, owner, worker, ai_agent
    entity_type = Column(String(100), default="")
    entity_id = Column(String(100), default="")
    details = Column(JSON, default=dict)
    ip_address = Column(String(50), default="")
    created_at = Column(DateTime(timezone=True), default=utcnow)

# 32. IntegrationCredentialsMetadata
class IntegrationCredentialsMetadata(Base):
    __tablename__ = "integration_credentials_metadata"
    id = Column(Integer, primary_key=True, index=True)
    provider_name = Column(String(100), unique=True, nullable=False)
    category = Column(String(50), nullable=False) # job_portal, email, ai, notification, calendar, search
    is_configured = Column(Boolean, default=False)
    is_active = Column(Boolean, default=False)
    masked_key_hint = Column(String(100), default="") # e.g. "sk-****...1234"
    supported_capabilities = Column(JSON, default=list)
    permissions_granted = Column(JSON, default=list)
    last_successful_operation = Column(DateTime(timezone=True), nullable=True)
    last_error = Column(Text, default="")
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

# 33. SystemHealth
class SystemHealth(Base):
    __tablename__ = "system_health"
    id = Column(Integer, primary_key=True, index=True)
    component = Column(String(100), unique=True, nullable=False) # database, worker, scheduler, email_smtp, email_imap, ai_provider, search_provider
    status = Column(String(50), default="HEALTHY") # HEALTHY, DEGRADED, UNHEALTHY, UNCONFIGURED
    message = Column(Text, default="")
    latency_ms = Column(Float, default=0.0)
    checked_at = Column(DateTime(timezone=True), default=utcnow)

# 34. AgentInstruction (for AI Agent Workspace)
class AgentInstruction(Base):
    __tablename__ = "agent_instructions"
    id = Column(Integer, primary_key=True, index=True)
    objective = Column(Text, nullable=False)
    extracted_filters = Column(JSON, default=dict)
    search_plan = Column(JSON, default=dict)
    status = Column(String(50), default="ACTIVE") # ACTIVE, PAUSED, COMPLETED, CANCELLED
    leads_found = Column(Integer, default=0)
    applications_created = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

# 35. VoiceSecuritySettings
class VoiceSecuritySettings(Base):
    __tablename__ = "voice_security_settings"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), default=1)
    passphrase_hash = Column(String(255), nullable=False)
    passphrase_salt = Column(String(64), nullable=False)
    passphrase_enabled = Column(Boolean, default=True)
    failed_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime(timezone=True), nullable=True)
    wake_word_enabled = Column(Boolean, default=False)
    wake_word = Column(String(100), default="Hey CareerPilot")
    speech_language = Column(String(20), default="en-US")
    speech_rate = Column(Float, default=1.0)
    speech_pitch = Column(Float, default=1.0)
    voice_name = Column(String(100), default="default")
    prefer_local_stt = Column(Boolean, default=True)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

# 36. VoiceCommandLog
class VoiceCommandLog(Base):
    __tablename__ = "voice_command_logs"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), index=True, default="")
    raw_transcript = Column(Text, nullable=False)
    edited_transcript = Column(Text, default="")
    detected_intent = Column(String(100), index=True, nullable=False)
    extracted_parameters = Column(JSON, default=dict)
    risk_level = Column(String(50), default="LEVEL_1_LOW") # LEVEL_1_LOW, LEVEL_2_CONTROLLED, LEVEL_3_PROTECTED
    requires_confirmation = Column(Boolean, default=False)
    is_confirmed = Column(Boolean, default=False)
    execution_status = Column(String(50), default="EXECUTED") # PENDING, CONFIRMED, EXECUTED, REJECTED, FAILED
    spoken_response = Column(Text, default="")
    execution_details = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=utcnow)

# 37. VoiceSessionContext
class VoiceSessionContext(Base):
    __tablename__ = "voice_session_contexts"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), unique=True, index=True, nullable=False)
    active_query = Column(String(500), default="")
    active_filters = Column(JSON, default=dict)
    active_job_ids = Column(JSON, default=list) # Ordered list of job IDs from current voice context
    pending_clarification = Column(String(100), default="")
    pending_action_type = Column(String(100), default="")
    pending_action_payload = Column(JSON, default=dict)
    conversation_history = Column(JSON, default=list) # List of {"role": "user"|"agent", "text": "..."}
    conversation_turns = Column(Integer, default=0)
    last_active_at = Column(DateTime(timezone=True), default=utcnow)
    created_at = Column(DateTime(timezone=True), default=utcnow)

