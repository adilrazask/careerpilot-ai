from __future__ import annotations
from datetime import datetime, timezone
from sqlalchemy.orm import Session
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
    
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True
        
    try:
        # 1. Default User
        user = db.query(User).filter_by(id=1).first()
        if not user:
            user = User(
                id=1,
                email="owner@careerpilot.ai",
                full_name="Operations Professional",
                role="owner",
                is_active=True
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        # 2. Default Career Profile
        profile = db.query(CareerProfile).filter_by(id=1).first()
        if not profile:
            profile = CareerProfile(
                id=1,
                user_id=user.id,
                full_name="Adil Raja",
                email="adil.raja.operations@gmail.com",
                phone="+91 98765 43210",
                current_location="Hyderabad, India",
                total_experience_years=4.5,
                summary=(
                    "Results-oriented Business Operations and Procurement Executive with 4+ years of cross-functional "
                    "experience in supply chain coordination, vendor procurement, ERP/CRM administration, GRN verification, "
                    "sales coordination, and export dispatch documentation. Proven track record of streamlining purchase orders, "
                    "maintaining accurate inventory databases, and collaborating with cross-functional teams to drive operational efficiency."
                ),
                linkedin_url="https://linkedin.com/in/adil-raja-operations",
                preferred_contact_method="email",
                verified_facts={
                    "confirmed_experience_years": 4.5,
                    "target_sector": "Operations, Manufacturing, Logistics, Corporate Services",
                    "citizenship": "Indian Citizen (Authorized to work in India; open to UAE sponsorship)",
                    "highest_education": "Bachelor of Commerce (B.Com) / Business Administration"
                }
            )
            db.add(profile)
            db.commit()
            db.refresh(profile)

            # Add default employment history
            job1 = EmploymentHistory(
                profile_id=profile.id,
                company="Apex Industrial Solutions Ltd",
                job_title="Business Operations & Procurement Executive",
                location="Hyderabad, India",
                start_date="2022-03",
                end_date="Present",
                is_current=True,
                responsibilities=[
                    "Coordinate end-to-end procurement processes, evaluating vendor quotations and negotiating cost-effective supplier contracts.",
                    "Manage daily ERP/CRM entries for purchase orders, goods receipt notes (GRN), and inventory movements with 99.5% accuracy.",
                    "Supervise warehouse logistics, dispatch schedules, and freight documentation for domestic and international shipments.",
                    "Liaise between sales, accounts, and factory operations to expedite client order fulfillments and track overdue payments."
                ],
                achievements=[
                    "Reduced monthly vendor lead times by 18% through automated purchase requisition tracking.",
                    "Recognized with 'Excellence in Operational Reliability' award in Q3 2024."
                ],
                tools_used=["SAP ERP", "Microsoft Excel", "Tally Prime", "Zoho CRM", "Google Workspace"]
            )
            job2 = EmploymentHistory(
                profile_id=profile.id,
                company="TransLogix Supply Chain Services",
                job_title="Operations & Logistics Coordinator",
                location="Hyderabad, India",
                start_date="2020-07",
                end_date="2022-02",
                is_current=False,
                responsibilities=[
                    "Maintained stock registers, processed vendor invoices, and tracked incoming consignments across regional hubs.",
                    "Prepared sales quotations, purchase orders, and export shipment documentation adhering to regulatory requirements.",
                    "Managed customer enquiries and resolved delivery delays via coordinated communication with freight forwarders."
                ],
                achievements=[
                    "Spearheaded digitisation of paper dispatch registers into centralized spreadsheet system."
                ],
                tools_used=["Tally ERP 9", "MS Excel", "Custom WMS"]
            )
            db.add_all([job1, job2])

            # Add default skills
            for s in DEFAULT_SKILLS:
                db.add(Skill(
                    profile_id=profile.id,
                    name=s["name"],
                    category=s["category"],
                    years_experience=s["years_experience"],
                    proficiency=s["proficiency"],
                    is_verified=True
                ))

            # Add education
            db.add(Education(
                profile_id=profile.id,
                institution="Osmania University",
                degree="Bachelor of Commerce (B.Com)",
                field_of_study="Business Management & Accounting",
                graduation_year="2020",
                is_verified=True
            ))

            # Add certification
            db.add(Certification(
                profile_id=profile.id,
                name="Certified Supply Chain & Procurement Specialist (CSCP)",
                issuing_organization="Institute of Supply Management",
                issue_date="2023-05",
                is_verified=True
            ))

            # Add preferences
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
        components = ["database", "scheduler", "worker", "email_outbound", "email_inbound", "ai_engine", "job_discovery"]
        for c in components:
            sh = db.query(SystemHealth).filter_by(component=c).first()
            if not sh:
                db.add(SystemHealth(
                    component=c,
                    status="HEALTHY" if c in ["database", "scheduler"] else "UNCONFIGURED",
                    message="Initialized"
                ))
        db.commit()

    finally:
        if close_db:
            db.close()
