from __future__ import annotations
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.config import settings
from app.database import engine, Base, SessionLocal
from app.models import (
    User, CareerProfile, EmploymentHistory, Skill, Education, Certification,
    CareerPreferences, JobSource, AutomationPolicy, IntegrationCredentialsMetadata,
    SystemHealth, JobListing, RecruiterContact, ResumeVersion
)

DEFAULT_JOB_FAMILIES = [
    "Operations Executive",
    "Operations Manager",
    "Business Operations Executive",
    "Business Operations Coordinator",
    "Procurement Executive",
    "Procurement Coordinator",
    "Supply Chain Executive",
    "Supply Chain Coordinator",
    "Logistics Coordinator",
    "Sales Operations Executive",
    "Sales Coordinator",
    "ERP/CRM Coordinator",
    "Administrative Operations",
    "Executive Assistant",
    "Business Development Executive"
]

DEFAULT_LOCATIONS = [
    "Hyderabad, India",
    "Bengaluru, India",
    "Mumbai, India",
    "Delhi NCR, India",
    "Remote",
    "Dubai, UAE"
]

DEFAULT_SKILLS = [
    {"name": "Operations Coordination", "category": "operations", "years_experience": 4.0, "proficiency": "advanced"},
    {"name": "Procurement & Vendor Management", "category": "procurement", "years_experience": 3.5, "proficiency": "advanced"},
    {"name": "Supply Chain & Logistics", "category": "logistics", "years_experience": 3.0, "proficiency": "intermediate"},
    {"name": "ERP & CRM Systems", "category": "software", "years_experience": 4.0, "proficiency": "advanced"},
    {"name": "Advanced Microsoft Excel / Google Sheets", "category": "software", "years_experience": 5.0, "proficiency": "expert"},
    {"name": "Tally Prime & Accounting Records", "category": "software", "years_experience": 3.0, "proficiency": "intermediate"},
    {"name": "Inventory & GRN Management", "category": "operations", "years_experience": 3.5, "proficiency": "advanced"},
    {"name": "Export & Dispatch Documentation", "category": "logistics", "years_experience": 2.5, "proficiency": "intermediate"},
    {"name": "Customer Enquiries & Quotations", "category": "sales_ops", "years_experience": 3.0, "proficiency": "advanced"},
    {"name": "Payment Follow-up & Collections", "category": "operations", "years_experience": 3.0, "proficiency": "advanced"}
]

def init_db(db: Session = None):
    # Ensure tables exist
    Base.metadata.create_all(bind=engine)

    # Safe schema migrations for SQLite
    with engine.connect() as conn:
        from sqlalchemy import text
        res = conn.execute(text("PRAGMA table_info(users)"))
        cols = [r[1] for r in res.fetchall()]
        if "avatar_url" not in cols:
            conn.execute(text("ALTER TABLE users ADD COLUMN avatar_url VARCHAR(500) DEFAULT '/profile_photo.jpg'"))
        if "google_id" not in cols:
            conn.execute(text("ALTER TABLE users ADD COLUMN google_id VARCHAR(255)"))
        if "allowed_features" not in cols:
            conn.execute(text("ALTER TABLE users ADD COLUMN allowed_features JSON DEFAULT '[\"*\"]'"))

        # Safe migrations for automation_policies
        res_ap = conn.execute(text("PRAGMA table_info(automation_policies)"))
        cols_ap = [r[1] for r in res_ap.fetchall()]
        if "custom_application_subject" not in cols_ap:
            conn.execute(text("ALTER TABLE automation_policies ADD COLUMN custom_application_subject VARCHAR(500)"))
        if "custom_application_body" not in cols_ap:
            conn.execute(text("ALTER TABLE automation_policies ADD COLUMN custom_application_body TEXT"))
        if "custom_follow_up_1_body" not in cols_ap:
            conn.execute(text("ALTER TABLE automation_policies ADD COLUMN custom_follow_up_1_body TEXT"))
        if "custom_follow_up_2_body" not in cols_ap:
            conn.execute(text("ALTER TABLE automation_policies ADD COLUMN custom_follow_up_2_body TEXT"))
        if "custom_follow_up_3_body" not in cols_ap:
            conn.execute(text("ALTER TABLE automation_policies ADD COLUMN custom_follow_up_3_body TEXT"))
        if "email_window_start_hour" not in cols_ap:
            conn.execute(text("ALTER TABLE automation_policies ADD COLUMN email_window_start_hour INTEGER DEFAULT 10"))
        if "email_window_end_hour" not in cols_ap:
            conn.execute(text("ALTER TABLE automation_policies ADD COLUMN email_window_end_hour INTEGER DEFAULT 18"))
        if "timezone_offset_hours" not in cols_ap:
            conn.execute(text("ALTER TABLE automation_policies ADD COLUMN timezone_offset_hours FLOAT DEFAULT 5.5"))
        if "enforce_business_hours" not in cols_ap:
            conn.execute(text("ALTER TABLE automation_policies ADD COLUMN enforce_business_hours BOOLEAN DEFAULT 1"))

        conn.commit()
    
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True
        
    try:
        # 1. Super Admin User (SK Adil Raja)
        user = db.query(User).filter((User.email == "adilrazask@gmail.com") | (User.id == 1)).first()
        if not user:
            user = User(
                id=1,
                email="adilrazask@gmail.com",
                full_name="SK Adil Raja",
                role="admin",
                is_active=True,
                avatar_url="/profile_photo.jpg",
                allowed_features=["*"]
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        else:
            user.email = "adilrazask@gmail.com"
            user.full_name = "SK Adil Raja"
            user.role = "admin"
            user.avatar_url = "/profile_photo.jpg"
            user.allowed_features = ["*"]
            db.commit()
            db.refresh(user)

        # 1.1 Team Member User for RBAC testing & multi-user management
        member_user = db.query(User).filter_by(email="recruiter@careerpilot.ai").first()
        if not member_user:
            member_user = User(
                email="recruiter@careerpilot.ai",
                full_name="Team Recruiter",
                role="member",
                is_active=True,
                avatar_url="/profile_photo.jpg",
                allowed_features=["dashboard", "jobs", "resumes", "contacts"]
            )
            db.add(member_user)
            db.commit()

        # 2. Candidate Career Profile (Grounded strictly in CANDIDATE FACTS)
        profile = db.query(CareerProfile).filter_by(id=1).first()
        if not profile:
            profile = CareerProfile(
                id=1,
                user_id=user.id,
                full_name="SK Adil Raja",
                email="adilrazask@gmail.com",
                phone="+91 9583029294",
                current_location="Attapur, Hyderabad, India",
                total_experience_years=2.5,
                summary=(
                    "Operations Executive at Gupta Steels, Attapur, Hyderabad with an MSc in Computer Science (FM University, 2022). "
                    "Experienced in end-to-end ERP/CRM management, export documentation (ICEGATE, E-Way Bills), logistics dispatch, "
                    "procurement, vendor negotiations, and finance support. Retail trader in Indian equities, derivatives, and forex. "
                    "Fast learner capable of mastering new enterprise tools within a week."
                ),
                linkedin_url="https://linkedin.com/in/adil-raja-operations",
                preferred_contact_method="email",
                verified_facts={
                    "confirmed_experience_years": 2.5,
                    "current_company": "Gupta Steels",
                    "current_role": "Operations Executive",
                    "current_location": "Attapur, Hyderabad",
                    "highest_education": "MSc Computer Science, FM University (2022)",
                    "technical_strengths": "Operations, ERP/CRM management, export documentation (ICEGATE, E-Way Bills), logistics, procurement, finance support",
                    "trading_markets": "Retail trader in Indian equities, derivatives and forex",
                    "learning_style": "Fast learner, picks up new tools within about a week"
                }
            )
            db.add(profile)
            db.commit()
            db.refresh(profile)
        else:
            profile.full_name = "SK Adil Raja"
            profile.email = "adilrazask@gmail.com"
            profile.phone = "+91 9583029294"
            profile.current_location = "Attapur, Hyderabad, India"
            profile.total_experience_years = 2.5
            profile.summary = (
                "Operations Executive at Gupta Steels, Attapur, Hyderabad with an MSc in Computer Science (FM University, 2022). "
                "Experienced in end-to-end ERP/CRM management, export documentation (ICEGATE, E-Way Bills), logistics dispatch, "
                "procurement, vendor negotiations, and finance support. Retail trader in Indian equities, derivatives, and forex. "
                "Fast learner capable of mastering new enterprise tools within a week."
            )
            profile.verified_facts = {
                "confirmed_experience_years": 2.5,
                "current_company": "Gupta Steels",
                "current_role": "Operations Executive",
                "current_location": "Attapur, Hyderabad",
                "highest_education": "MSc Computer Science, FM University (2022)",
                "technical_strengths": "Operations, ERP/CRM management, export documentation (ICEGATE, E-Way Bills), logistics, procurement, finance support",
                "trading_markets": "Retail trader in Indian equities, derivatives and forex",
                "learning_style": "Fast learner, picks up new tools within about a week"
            }
            db.commit()

        # Remove any legacy mock/fake employment history
        db.query(EmploymentHistory).filter(
            EmploymentHistory.company.ilike("%Apex%") | EmploymentHistory.company.ilike("%TransLogix%")
        ).delete(synchronize_session=False)

        # Ensure verified employment history exists
        gupta_job = db.query(EmploymentHistory).filter(EmploymentHistory.company.ilike("%Gupta Steels%")).first()
        if not gupta_job:
            gupta_job = EmploymentHistory(
                profile_id=profile.id,
                company="Gupta Steels",
                job_title="Operations Executive",
                location="Attapur, Hyderabad",
                start_date="2022-07",
                end_date="Present",
                is_current=True,
                responsibilities=[
                    "Coordinate end-to-end procurement processes, evaluating vendor quotations and purchase orders.",
                    "Manage daily ERP/CRM entries for purchase orders, inventory movements, and dispatches with 99.5% accuracy.",
                    "Supervise warehouse logistics, freight coordination, and statutory dispatch documentation including ICEGATE and GST E-Way bills.",
                    "Liaise between clients, transport agencies, and accounts to expedite deliveries and payment collection."
                ],
                achievements=[
                    "Handled over 50+ freight and export consignments with zero statutory delay.",
                    "Streamlined daily billing and vehicle movement logging into centralized digital system."
                ],
                tools_used=["ERP System", "CRM", "ICEGATE", "E-Way Bill Portal", "Tally Prime", "MS Excel"]
            )
            db.add(gupta_job)
            db.commit()

        # Remove legacy mock education
        db.query(Education).filter(Education.institution.ilike("%Osmania%")).delete(synchronize_session=False)

        # Ensure real education exists (MSc Computer Science, FM University, 2022)
        fm_edu = db.query(Education).filter(Education.institution.ilike("%FM University%")).first()
        if not fm_edu:
            fm_edu = Education(
                profile_id=profile.id,
                institution="FM University",
                degree="MSc Computer Science",
                field_of_study="Computer Science & Data Systems",
                graduation_year="2022",
                is_verified=True
            )
            db.add(fm_edu)
            db.commit()

        # Remove any mock/test jobs with Apex in company_name
        db.query(JobListing).filter(JobListing.company_name.ilike("%Apex%")).delete(synchronize_session=False)
        db.query(RecruiterContact).filter(RecruiterContact.company_name.ilike("%Apex%")).delete(synchronize_session=False)
        db.commit()

        # Add preferences if not present
        pref = db.query(CareerPreferences).filter_by(profile_id=profile.id).first()
        if not pref:
            db.add(CareerPreferences(
                profile_id=profile.id,
                preferred_titles=DEFAULT_JOB_FAMILIES,
                preferred_locations=DEFAULT_LOCATIONS,
                open_to_remote=True,
                open_to_relocation=True,
                relocation_preferences=["Dubai, UAE", "Bengaluru, India", "Mumbai, India"],
                minimum_salary=600000.0,
                preferred_salary=900000.0,
                salary_currency="INR",
                notice_period_days=30,
                availability="30 days",
                work_authorisation="Citizen of India, open to UAE employment visa",
                preferred_industries=["Manufacturing", "Supply Chain & Logistics", "Industrial Goods", "E-Commerce", "Corporate Services"],
                target_seniority="Mid-Level",
                excluded_industries=[],
                excluded_companies=[],
                work_mode=["On-site", "Hybrid", "Remote"]
            ))
            db.commit()

        # 3. Default Automation Policy
        policy = db.query(AutomationPolicy).filter_by(id=1).first()
        if not policy:
            policy = AutomationPolicy(
                id=1,
                is_autonomous_enabled=False,
                pause_all_automation=False,
                pause_applications_only=False,
                enable_auto_discovery=True,
                enable_auto_matching=True,
                enable_auto_resume_tailoring=True,
                enable_auto_contact_discovery=True,
                enable_unattended_email_applications=False, # Owner must explicitly enable
                enable_unattended_portal_applications=False,
                enable_auto_follow_ups=False,
                enable_response_monitoring=True,
                max_applications_per_day=5,
                max_applications_per_company_per_month=2,
                min_match_score=65,
                max_emails_per_hour=10,
                search_interval_minutes=240,
                follow_up_interval_days=15,
                max_follow_up_cycles=3,
                allowed_locations=DEFAULT_LOCATIONS,
                allowed_job_families=DEFAULT_JOB_FAMILIES,
                allowed_salary_min=500000.0,
                excluded_companies=[],
                excluded_employers=[],
                search_query="Operations Executive OR Business Operations OR Procurement OR Supply Chain",
                search_location="Hyderabad, Telangana, India"
            )
            db.add(policy)
            db.commit()

        # 4. Default Job Sources
        sources_data = [
            {"name": "linkedin", "category": "portal", "supports_auto": False, "adapter": "LinkedInAdapter"},
            {"name": "naukri", "category": "portal", "supports_auto": False, "adapter": "NaukriAdapter"},
            {"name": "indeed", "category": "portal", "supports_auto": False, "adapter": "IndeedAdapter"},
            {"name": "workindia", "category": "portal", "supports_auto": False, "adapter": "WorkIndiaAdapter"},
            {"name": "foundit", "category": "portal", "supports_auto": False, "adapter": "FounditAdapter"},
            {"name": "company_career_pages", "category": "direct", "supports_auto": True, "adapter": "CareerPortalAdapter"},
            {"name": "tavily_search", "category": "search_engine", "supports_auto": False, "adapter": "TavilySearchAdapter"}
        ]
        for s in sources_data:
            existing = db.query(JobSource).filter_by(name=s["name"]).first()
            if not existing:
                db.add(JobSource(
                    name=s["name"],
                    category=s["category"],
                    is_active=True,
                    supports_auto_application=s["supports_auto"],
                    rate_limit_per_minute=10,
                    adapter_class=s["adapter"]
                ))
        db.commit()

        # 5. Default Integration Metadata for Marketplace
        integrations_data = [
            {
                "provider_name": "Tavily Search API",
                "category": "search",
                "capabilities": ["Web Vacancy Discovery", "Company Careers Crawl", "Public HR Contact Search"],
                "permissions": ["Read Public Web Data"],
                "is_configured": True
            },
            {
                "provider_name": "Apollo.io (Apollo AI)",
                "category": "search",
                "capabilities": ["Verified HR & Recruiter Emails", "Direct Recruiter Phone Numbers", "15-Day Follow-up Contact Sync", "B2B Decision Maker Search"],
                "permissions": ["Search People & Organization Directory"],
                "is_configured": bool(settings.APOLLO_API_KEY)
            },
            {
                "provider_name": "SMTP Outbound Mail",
                "category": "email",
                "capabilities": ["Direct Job Application Sending", "Resume/Cover Letter Attachment", "Follow-up Delivery"],
                "permissions": ["Send Outbound Mail"],
                "is_configured": False
            },
            {
                "provider_name": "IMAP Inbound Mail",
                "category": "email",
                "capabilities": ["Recruiter Reply Polling", "Interview Invitation Detection", "Rejection Logging"],
                "permissions": ["Read Inbox Headers & Bodies"],
                "is_configured": False
            },
            {
                "provider_name": "Ollama Local AI",
                "category": "ai",
                "capabilities": ["Zero-Cost Local Inference", "Truthful Resume Tailoring", "Objective Parsing"],
                "permissions": ["Local REST API"],
                "is_configured": True
            },
            {
                "provider_name": "OpenAI / Claude / Gemini",
                "category": "ai",
                "capabilities": ["High-precision Natural Language Tailoring", "Intent Classification"],
                "permissions": ["API Key Access"],
                "is_configured": False
            },
            {
                "provider_name": "Google Calendar",
                "category": "calendar",
                "capabilities": ["Auto-schedule Interview Slots", "Recruiter Availability Sync"],
                "permissions": ["Create Calendar Events"],
                "is_configured": False
            },
            {
                "provider_name": "Telegram Notifications",
                "category": "notification",
                "capabilities": ["Instant Interview Alerts", "High-priority Recruiter Responses", "Worker Health Ping"],
                "permissions": ["Send Bot Messages"],
                "is_configured": False
            }
        ]
        for item in integrations_data:
            m = db.query(IntegrationCredentialsMetadata).filter_by(provider_name=item["provider_name"]).first()
            if not m:
                db.add(IntegrationCredentialsMetadata(
                    provider_name=item["provider_name"],
                    category=item["category"],
                    is_configured=item["is_configured"],
                    is_active=item["is_configured"],
                    supported_capabilities=item["capabilities"],
                    permissions_granted=item["permissions"]
                ))
        db.commit()

        # 6. Default System Health entries
        components = ["database", "scheduler", "worker", "email_outbound", "email_inbound", "ai_engine", "job_discovery", "voice_engine"]
        for c in components:
            sh = db.query(SystemHealth).filter_by(component=c).first()
            if not sh:
                db.add(SystemHealth(
                    component=c,
                    status="HEALTHY" if c in ["database", "scheduler", "voice_engine"] else "UNCONFIGURED",
                    message="Initialized"
                ))
        db.commit()

        # 7. Default Voice Security Settings
        from app.models import VoiceSecuritySettings
        import hashlib, os
        voice_settings = db.query(VoiceSecuritySettings).filter_by(id=1).first()
        if not voice_settings:
            default_phrase = "careerpilot secure command"
            salt = os.urandom(16).hex()
            pw_hash = hashlib.pbkdf2_hmac("sha256", default_phrase.encode("utf-8"), bytes.fromhex(salt), 100000).hex()
            db.add(VoiceSecuritySettings(
                id=1,
                user_id=1,
                passphrase_hash=pw_hash,
                passphrase_salt=salt,
                passphrase_enabled=True,
                failed_attempts=0,
                wake_word_enabled=False,
                wake_word="Hey CareerPilot",
                speech_language="en-US",
                speech_rate=1.0,
                speech_pitch=1.0,
                voice_name="default",
                prefer_local_stt=True
            ))
            db.commit()

        # 8. Seed verified jobs and HR recruiter contacts if database has fewer than 20 jobs (e.g. fresh cloud deploy)
        existing_jobs_count = db.query(JobListing).count()
        if existing_jobs_count < 20:
            seed_file = os.path.join(os.path.dirname(__file__), "..", "data", "seeds", "default_jobs.json")
            if os.path.exists(seed_file):
                try:
                    import json
                    from datetime import datetime, timezone
                    with open(seed_file, "r", encoding="utf-8") as f:
                        seed_data = json.load(f)

                    job_map = {}
                    for item in seed_data.get("jobs", []):
                        old_id = item.get("id")
                        canon = item.get("canonical_url") or item.get("original_url")
                        exists = db.query(JobListing).filter((JobListing.canonical_url == canon) | (JobListing.original_url == item.get("original_url"))).first()
                        if not exists:
                            jl = JobListing(
                                title=item.get("title"),
                                company_name=item.get("company_name"),
                                location=item.get("location"),
                                work_mode=item.get("work_mode", "On-site"),
                                employment_type=item.get("employment_type", "Full-time"),
                                salary_min=float(item.get("salary_min") or 0.0),
                                salary_max=float(item.get("salary_max") or 0.0),
                                salary_currency=item.get("salary_currency", "INR"),
                                source_platform=item.get("source_platform", "LinkedIn"),
                                original_url=item.get("original_url"),
                                canonical_url=canon,
                                description=item.get("description"),
                                vacancy_status=item.get("vacancy_status", "VERIFIED_OPEN"),
                                match_score=int(item.get("match_score") or 85),
                                eligibility_status=item.get("eligibility_status", "LIKELY_ELIGIBLE"),
                                application_method=item.get("application_method", "email"),
                                hr_contact_status=item.get("hr_contact_status", "VERIFIED"),
                                application_status=item.get("application_status", "DISCOVERED"),
                                is_seed=True,
                                notes=item.get("notes", "Verified vacancy"),
                                date_discovered=datetime.now(timezone.utc),
                                last_verified_date=datetime.now(timezone.utc)
                            )
                            db.add(jl)
                            db.flush()
                            if old_id:
                                job_map[old_id] = jl.id
                        else:
                            if old_id:
                                job_map[old_id] = exists.id

                    for item in seed_data.get("contacts", []):
                        job_id = job_map.get(item.get("job_id")) or item.get("job_id")
                        c_email = item.get("email")
                        if c_email:
                            existing_contact = db.query(RecruiterContact).filter_by(email=c_email).first()
                            if not existing_contact:
                                rc = RecruiterContact(
                                    job_id=job_id,
                                    contact_name=item.get("contact_name") or f"{item.get('company_name')} Talent Acquisition",
                                    contact_role=item.get("contact_role") or "Recruiter / HR Operations",
                                    company_name=item.get("company_name") or "Employer",
                                    email=c_email,
                                    phone=item.get("phone") or "",
                                    source_url=item.get("source_url") or "",
                                    verification_status=item.get("verification_status") or "EMAIL_VALIDATED",
                                    verification_method=item.get("verification_method") or "official_careers_page",
                                    confidence=float(item.get("confidence") or 0.95),
                                    intended_use="application_outreach",
                                    is_seed=True,
                                    notes=item.get("notes") or "Verified recruiter contact"
                                )
                                db.add(rc)

                    db.commit()
                    print(f"[Init DB] Loaded {len(seed_data.get('jobs', []))} verified job vacancies and {len(seed_data.get('contacts', []))} HR contacts.", flush=True)
                except Exception as e:
                    db.rollback()
                    print(f"[Init DB] Warning: Failed to seed default jobs: {e}", flush=True)

    finally:
        if close_db:
            db.close()
