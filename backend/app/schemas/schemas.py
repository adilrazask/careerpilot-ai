from __future__ import annotations
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, EmailStr

# --- Profile Schemas ---
class EmploymentHistorySchema(BaseModel):
    id: Optional[int] = None
    company: str
    job_title: str
    location: Optional[str] = ""
    start_date: str
    end_date: Optional[str] = "Present"
    is_current: bool = False
    responsibilities: List[str] = Field(default_factory=list)
    achievements: List[str] = Field(default_factory=list)
    tools_used: List[str] = Field(default_factory=list)
    is_verified: bool = True

class SkillSchema(BaseModel):
    id: Optional[int] = None
    name: str
    category: str = "general"
    years_experience: float = 1.0
    proficiency: str = "intermediate"
    is_verified: bool = True

class EducationSchema(BaseModel):
    id: Optional[int] = None
    institution: str
    degree: str
    field_of_study: Optional[str] = ""
    graduation_year: Optional[str] = ""
    grade_or_gpa: Optional[str] = ""
    is_verified: bool = True

class CertificationSchema(BaseModel):
    id: Optional[int] = None
    name: str
    issuing_organization: str
    issue_date: Optional[str] = ""
    expiry_date: Optional[str] = ""
    credential_id: Optional[str] = ""
    credential_url: Optional[str] = ""
    is_verified: bool = True

class CareerPreferencesSchema(BaseModel):
    preferred_titles: List[str] = Field(default_factory=list)
    preferred_locations: List[str] = Field(default_factory=list)
    open_to_remote: bool = True
    open_to_relocation: bool = True
    relocation_preferences: List[str] = Field(default_factory=list)
    minimum_salary: float = 0.0
    preferred_salary: float = 0.0
    salary_currency: str = "INR"
    notice_period_days: int = 30
    availability: str = "30 days"
    work_authorisation: str = "Citizen of India"
    preferred_industries: List[str] = Field(default_factory=list)
    excluded_industries: List[str] = Field(default_factory=list)
    excluded_companies: List[str] = Field(default_factory=list)
    work_mode: List[str] = Field(default_factory=lambda: ["On-site", "Hybrid", "Remote"])

class CareerProfileResponse(BaseModel):
    id: int
    full_name: str
    email: str
    phone: str
    current_location: str
    total_experience_years: float
    summary: str
    linkedin_url: str
    portfolio_url: str
    preferred_contact_method: str
    verified_facts: Dict[str, Any]
    employment_history: List[EmploymentHistorySchema] = Field(default_factory=list)
    skills: List[SkillSchema] = Field(default_factory=list)
    education: List[EducationSchema] = Field(default_factory=list)
    certifications: List[CertificationSchema] = Field(default_factory=list)
    preferences: Optional[CareerPreferencesSchema] = None

class CareerProfileUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    current_location: Optional[str] = None
    total_experience_years: Optional[float] = None
    summary: Optional[str] = None
    linkedin_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    preferred_contact_method: Optional[str] = None
    verified_facts: Optional[Dict[str, Any]] = None

# --- Job Discovery & Search Schemas ---
class JobSearchQuery(BaseModel):
    query: str = "Operations Executive"
    location: str = "Hyderabad, India"
    portals: List[str] = Field(default_factory=lambda: ["linkedin", "naukri", "indeed", "workindia", "company_career_pages", "tavily_search"])
    experience_years: Optional[float] = None
    min_salary: Optional[float] = None
    max_results: int = 10

class JobListingCreate(BaseModel):
    title: str
    company_name: str
    location: str = "Hyderabad, India"
    work_mode: str = "On-site"
    employment_type: str = "Full-time"
    experience_required_min: float = 0.0
    experience_required_max: float = 0.0
    salary_min: float = 0.0
    salary_max: float = 0.0
    salary_currency: str = "INR"
    source_platform: str = "Manual"
    original_url: str
    description: str
    contact_email: Optional[str] = ""
    contact_phone: Optional[str] = ""
    notes: Optional[str] = ""

class JobRequirementSchema(BaseModel):
    id: int
    requirement_text: str
    category: str
    is_mandatory: bool

class JobMatchResultSchema(BaseModel):
    match_score: int
    eligibility_status: str # LIKELY_ELIGIBLE, REVIEW_REQUIRED, NOT_ELIGIBLE
    matching_requirements: List[str] = Field(default_factory=list)
    missing_requirements: List[str] = Field(default_factory=list)
    uncertain_requirements: List[str] = Field(default_factory=list)
    location_match: bool = True
    salary_match: str = "UNKNOWN"
    score_breakdown: Dict[str, Any] = Field(default_factory=dict)
    explanation: str = ""
    recommended_action: str = "REVIEW"

class JobListingResponse(BaseModel):
    id: int
    title: str
    company_name: str
    location: str
    work_mode: str
    employment_type: str
    experience_required_min: float
    experience_required_max: float
    salary_min: float
    salary_max: float
    salary_currency: str
    source_platform: str
    original_url: str
    description: str
    date_discovered: datetime
    publication_date: Optional[datetime] = None
    last_verified_date: datetime
    vacancy_status: str
    match_score: int
    eligibility_status: str
    application_method: str
    hr_contact_status: str
    application_status: str
    notes: Optional[str] = ""
    match_result: Optional[JobMatchResultSchema] = None

# --- Resume Intelligence Schemas ---
class TailorResumeRequest(BaseModel):
    job_id: int
    focus_notes: Optional[str] = ""
    use_ai: bool = True
    model_override: Optional[str] = None

class ResumeVersionResponse(BaseModel):
    id: int
    job_id: Optional[int]
    version_name: str
    headline: str
    summary: str
    full_text: str
    cover_letter_text: str
    pdf_path: Optional[str] = ""
    docx_path: Optional[str] = ""
    model_used: str
    factual_consistency_score: float
    created_at: datetime

# --- Recruiter Contact Schemas ---
class RecruiterContactCreate(BaseModel):
    job_id: Optional[int] = None
    company_name: str
    contact_name: str = "Hiring Team"
    contact_role: str = "Talent Acquisition"
    email: str
    phone: Optional[str] = ""
    source_url: str
    intended_use: str = "application_outreach"
    notes: Optional[str] = ""

class RecruiterContactResponse(BaseModel):
    id: int
    job_id: Optional[int]
    company_name: str
    contact_name: str
    contact_role: str
    email: str
    phone: str
    source_url: str
    discovery_date: datetime
    verification_status: str
    verification_method: str
    last_verification_date: Optional[datetime]
    confidence: float
    intended_use: str
    notes: str

class VerifyContactRequest(BaseModel):
    contact_id: int

# --- Application Pipeline Schemas ---
class ApplicationTransitionRequest(BaseModel):
    new_status: str
    reason: str
    evidence: Optional[Dict[str, Any]] = None

class ApplicationRecordResponse(BaseModel):
    id: int
    job_id: int
    job_title: str
    company_name: str
    current_status: str
    submission_method: str
    primary_recipient: str
    external_confirmation_id: str
    delivery_evidence: Dict[str, Any]
    acknowledgement_received: bool
    interview_invited: bool
    rejection_received: bool
    unattended_approved: bool
    created_at: datetime
    updated_at: datetime
    resume_version_id: Optional[int] = None

# --- Automation Policy Schemas ---
class AutomationPolicySchema(BaseModel):
    is_autonomous_enabled: bool = False
    pause_all_automation: bool = False
    pause_applications_only: bool = False
    enable_auto_discovery: bool = True
    enable_auto_matching: bool = True
    enable_auto_resume_tailoring: bool = True
    enable_auto_contact_discovery: bool = True
    enable_unattended_email_applications: bool = False
    enable_unattended_portal_applications: bool = False
    enable_auto_follow_ups: bool = False
    enable_response_monitoring: bool = True
    max_applications_per_day: int = 5
    max_applications_per_company_per_month: int = 2
    min_match_score: int = 65
    max_emails_per_hour: int = 10
    search_interval_minutes: int = 240
    allowed_locations: List[str] = Field(default_factory=list)
    allowed_job_families: List[str] = Field(default_factory=list)
    allowed_salary_min: float = 0.0
    excluded_companies: List[str] = Field(default_factory=list)
    excluded_employers: List[str] = Field(default_factory=list)
    search_query: str = "Operations Executive"
    search_location: str = "Hyderabad, India"
    last_search_at: Optional[datetime] = None
    next_search_at: Optional[datetime] = None

# --- AI Agent Workspace Schemas ---
class AgentInstructionRequest(BaseModel):
    prompt: str

class AgentInstructionResponse(BaseModel):
    id: int
    objective: str
    extracted_filters: Dict[str, Any]
    search_plan: Dict[str, Any]
    status: str
    leads_found: int
    applications_created: int
    created_at: datetime

# --- Integration Marketplace Schemas ---
class IntegrationMetadataResponse(BaseModel):
    id: int
    provider_name: str
    category: str
    is_configured: bool
    is_active: bool
    masked_key_hint: str
    supported_capabilities: List[str]
    permissions_granted: List[str]
    last_successful_operation: Optional[datetime]
    last_error: str

class TestIntegrationRequest(BaseModel):
    provider_name: str
    config: Optional[Dict[str, Any]] = None

class ToggleIntegrationRequest(BaseModel):
    provider_name: str
    enable: bool

# --- Dashboard & Activity Metrics ---
class DashboardMetricsResponse(BaseModel):
    agent_status: str # RUNNING, PAUSED, IDLE, STOPPED
    current_automation_mode: str # ATTENDED, SEMI_AUTONOMOUS, FULL_AUTOPILOT
    worker_is_alive: bool
    worker_last_heartbeat: Optional[datetime]
    total_vacancies_discovered: int
    new_vacancies_today: int
    verified_open_vacancies: int
    matched_jobs: int
    applications_prepared: int
    applications_submitted: int
    email_applications_sent: int
    applications_awaiting_responses: int
    recruiter_responses_received: int
    interview_invitations: int
    rejections: int
    closed_vacancies: int
    failed_automation_tasks: int
    duplicate_applications_prevented: int
    last_successful_search: Optional[datetime]
    next_scheduled_search: Optional[datetime]
    next_follow_up_due: Optional[datetime]
    integration_health_summary: Dict[str, str]
