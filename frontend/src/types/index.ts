export interface DashboardMetrics {
  agent_status: string;
  current_automation_mode: string;
  worker_is_alive: boolean;
  worker_last_heartbeat: string | null;
  total_vacancies_discovered: number;
  new_vacancies_today: number;
  verified_open_vacancies: number;
  matched_jobs: number;
  applications_prepared: number;
  applications_submitted: number;
  email_applications_sent: number;
  applications_awaiting_responses: number;
  recruiter_responses_received: number;
  interview_invitations: number;
  rejections: number;
  closed_vacancies: number;
  failed_automation_tasks: number;
  duplicate_applications_prevented: number;
  last_successful_search: string | null;
  next_scheduled_search: string | null;
  next_follow_up_due: string | null;
  integration_health_summary: Record<string, string>;
}

export interface JobMatchResult {
  match_score: number;
  eligibility_status: 'LIKELY_ELIGIBLE' | 'REVIEW_REQUIRED' | 'NOT_ELIGIBLE';
  matching_requirements: string[];
  missing_requirements: string[];
  uncertain_requirements: string[];
  location_match: boolean;
  salary_match: string;
  score_breakdown: Record<string, any>;
  explanation: string;
  recommended_action: string;
}

export interface JobListing {
  id: number;
  title: string;
  company_name: string;
  location: string;
  work_mode: string;
  employment_type: string;
  experience_required_min: number;
  experience_required_max: number;
  salary_min: number;
  salary_max: number;
  salary_currency: string;
  source_platform: string;
  original_url: string;
  description: string;
  date_discovered: string;
  publication_date: string | null;
  last_verified_date: string;
  vacancy_status: string;
  match_score: number;
  eligibility_status: string;
  application_method: string;
  hr_contact_status: string;
  application_status: string;
  notes: string;
  match_result?: JobMatchResult | null;
}

export interface EmploymentHistory {
  id?: number;
  company: string;
  job_title: string;
  location?: string;
  start_date: string;
  end_date?: string;
  is_current: boolean;
  responsibilities: string[];
  achievements: string[];
  tools_used: string[];
  is_verified: boolean;
}

export interface Skill {
  id?: number;
  name: string;
  category: string;
  years_experience: number;
  proficiency: string;
  is_verified: boolean;
}

export interface Education {
  id?: number;
  institution: string;
  degree: string;
  field_of_study?: string;
  graduation_year?: string;
  grade_or_gpa?: string;
  is_verified: boolean;
}

export interface Certification {
  id?: number;
  name: string;
  issuing_organization: string;
  issue_date?: string;
  expiry_date?: string;
  credential_id?: string;
  credential_url?: string;
  is_verified: boolean;
}

export interface CareerPreferences {
  preferred_titles: string[];
  preferred_locations: string[];
  open_to_remote: boolean;
  open_to_relocation: boolean;
  relocation_preferences: string[];
  minimum_salary: number;
  preferred_salary: number;
  salary_currency: string;
  notice_period_days: number;
  availability: string;
  work_authorisation: string;
  preferred_industries: string[];
  excluded_industries: string[];
  excluded_companies: string[];
  work_mode: string[];
}

export interface CareerProfile {
  id: number;
  full_name: string;
  email: string;
  phone: string;
  current_location: string;
  total_experience_years: number;
  summary: string;
  linkedin_url: string;
  portfolio_url: string;
  preferred_contact_method: string;
  verified_facts: Record<string, any>;
  employment_history: EmploymentHistory[];
  skills: Skill[];
  education: Education[];
  certifications: Certification[];
  preferences?: CareerPreferences;
}

export interface ResumeVersion {
  id: number;
  job_id?: number | null;
  version_name: string;
  headline: string;
  summary: string;
  full_text: string;
  cover_letter_text: string;
  pdf_path?: string;
  docx_path?: string;
  model_used: string;
  factual_consistency_score: number;
  created_at: string;
}

export interface RecruiterContact {
  id: number;
  job_id?: number | null;
  company_name: string;
  contact_name: string;
  contact_role: string;
  email: string;
  phone: string;
  source_url: string;
  discovery_date: string;
  verification_status: string;
  verification_method: string;
  last_verification_date: string | null;
  confidence: number;
  intended_use: string;
  notes: string;
}

export interface ApplicationRecord {
  id: number;
  job_id: number;
  job_title: string;
  company_name: string;
  current_status: string;
  submission_method: string;
  primary_recipient: string;
  external_confirmation_id: string;
  delivery_evidence: Record<string, any>;
  acknowledgement_received: boolean;
  interview_invited: boolean;
  rejection_received: boolean;
  unattended_approved: boolean;
  created_at: string;
  updated_at: string;
  resume_version_id?: number | null;
}

export interface AutomationPolicy {
  is_autonomous_enabled: boolean;
  pause_all_automation: boolean;
  pause_applications_only: boolean;
  enable_auto_discovery: boolean;
  enable_auto_matching: boolean;
  enable_auto_resume_tailoring: boolean;
  enable_auto_contact_discovery: boolean;
  enable_unattended_email_applications: boolean;
  enable_unattended_portal_applications: boolean;
  enable_auto_follow_ups: boolean;
  enable_response_monitoring: boolean;
  max_applications_per_day: number;
  max_applications_per_company_per_month: number;
  min_match_score: number;
  max_emails_per_hour: number;
  search_interval_minutes: number;
  allowed_locations: string[];
  allowed_job_families: string[];
  allowed_salary_min: number;
  excluded_companies: string[];
  excluded_employers: string[];
  search_query: string;
  search_location: string;
  last_search_at: string | null;
  next_search_at: string | null;
}

export interface AgentInstruction {
  id: number;
  objective: string;
  extracted_filters: Record<string, any>;
  search_plan: Record<string, any>;
  status: string;
  leads_found: number;
  applications_created: number;
  created_at: string;
}

export interface IntegrationMetadata {
  id: number;
  provider_name: string;
  category: string;
  is_configured: boolean;
  is_active: boolean;
  masked_key_hint: string;
  supported_capabilities: string[];
  permissions_granted: string[];
  last_successful_operation: string | null;
  last_error: string;
}

export interface AuditLog {
  id: number;
  action: string;
  actor: string;
  entity_type: string;
  entity_id: string;
  details: Record<string, any>;
  created_at: string;
}

export interface SystemHealthItem {
  id: number;
  component: string;
  status: string;
  message: string;
  latency_ms: number;
  checked_at: string;
}

export interface VoiceSettings {
  passphrase_enabled: boolean;
  is_locked: boolean;
  lock_time_remaining_seconds: number;
  wake_word_enabled: boolean;
  wake_word: string;
  speech_language: string;
  speech_rate: number;
  speech_pitch: number;
  voice_name: string;
  prefer_local_stt: boolean;
}

export interface VoiceCommandResponse {
  session_id: string;
  raw_transcript: string;
  interpreted_intent: string;
  extracted_parameters: Record<string, any>;
  risk_level: 'LEVEL_1_LOW' | 'LEVEL_2_CONTROLLED' | 'LEVEL_3_PROTECTED' | string;
  requires_confirmation: boolean;
  confirmation_token?: string | null;
  confirmation_prompt?: string | null;
  spoken_response: string;
  display_text: string;
  data_payload: Record<string, any>;
  conversation_turns: number;
}

export interface VoiceLogItem {
  id: number;
  session_id: string;
  raw_transcript: string;
  detected_intent: string;
  risk_level: string;
  spoken_response: string;
  created_at: string | null;
}
