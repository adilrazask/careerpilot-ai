from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AutomationPolicy
from app.schemas.schemas import AutomationPolicySchema
from app.services.audit import record_audit_log

router = APIRouter(prefix="/api/policy", tags=["Automation Policy"])

@router.get("", response_model=AutomationPolicySchema)
def get_policy(db: Session = Depends(get_db)):
    policy = db.query(AutomationPolicy).filter_by(id=1).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Automation policy not found.")
    return AutomationPolicySchema(
        is_autonomous_enabled=policy.is_autonomous_enabled,
        pause_all_automation=policy.pause_all_automation,
        pause_applications_only=policy.pause_applications_only,
        enable_auto_discovery=policy.enable_auto_discovery,
        enable_auto_matching=policy.enable_auto_matching,
        enable_auto_resume_tailoring=policy.enable_auto_resume_tailoring,
        enable_auto_contact_discovery=policy.enable_auto_contact_discovery,
        enable_unattended_email_applications=policy.enable_unattended_email_applications,
        enable_unattended_portal_applications=policy.enable_unattended_portal_applications,
        enable_auto_follow_ups=policy.enable_auto_follow_ups,
        enable_response_monitoring=policy.enable_response_monitoring,
        max_applications_per_day=policy.max_applications_per_day,
        max_applications_per_company_per_month=policy.max_applications_per_company_per_month,
        min_match_score=policy.min_match_score,
        max_emails_per_hour=policy.max_emails_per_hour,
        search_interval_minutes=policy.search_interval_minutes,
        follow_up_interval_days=getattr(policy, "follow_up_interval_days", 15) or 15,
        max_follow_up_cycles=getattr(policy, "max_follow_up_cycles", 3) or 3,
        allowed_locations=policy.allowed_locations or [],
        allowed_job_families=policy.allowed_job_families or [],
        allowed_salary_min=policy.allowed_salary_min or 0.0,
        excluded_companies=policy.excluded_companies or [],
        excluded_employers=policy.excluded_employers or [],
        search_query=policy.search_query or "",
        search_location=policy.search_location or "",
        last_search_at=policy.last_search_at,
        next_search_at=policy.next_search_at,
        custom_application_subject=getattr(policy, "custom_application_subject", None),
        custom_application_body=getattr(policy, "custom_application_body", None),
        custom_follow_up_1_body=getattr(policy, "custom_follow_up_1_body", None),
        custom_follow_up_2_body=getattr(policy, "custom_follow_up_2_body", None),
        custom_follow_up_3_body=getattr(policy, "custom_follow_up_3_body", None)
    )

@router.put("", response_model=AutomationPolicySchema)
def update_policy(payload: AutomationPolicySchema, db: Session = Depends(get_db)):
    policy = db.query(AutomationPolicy).filter_by(id=1).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Automation policy not found.")

    for k, v in payload.model_dump().items():
        setattr(policy, k, v)

    db.commit()
    db.refresh(policy)

    record_audit_log(
        db=db,
        action="automation_policy_updated",
        actor="owner",
        entity_type="automation_policy",
        entity_id=str(policy.id),
        details={"unattended_enabled": policy.enable_unattended_email_applications, "daily_cap": policy.max_applications_per_day}
    )
    return payload


from pydantic import BaseModel
from typing import Optional, Dict, Any
from app.models import CareerProfile

class EmailTemplatesPayload(BaseModel):
    candidate_phone: Optional[str] = "+91 9583029294"
    candidate_email: Optional[str] = "adilrazask@gmail.com"
    candidate_linkedin: Optional[str] = "https://www.linkedin.com/in/"
    domestic_job_subject: Optional[str] = None
    domestic_job_body: Optional[str] = None
    outside_portal_subject: Optional[str] = None
    outside_portal_body: Optional[str] = None
    partnership_pitch_subject: Optional[str] = None
    partnership_pitch_body: Optional[str] = None
    international_subject: Optional[str] = None
    international_body: Optional[str] = None


@router.get("/email-templates")
def get_email_templates(db: Session = Depends(get_db)):
    """Returns current editable templates and contact facts for all outreach categories."""
    policy = db.query(AutomationPolicy).filter_by(id=1).first()
    profile = db.query(CareerProfile).first()

    phone = (profile.phone if profile else None) or "+91 9583029294"
    email = (profile.email if profile else None) or "adilrazask@gmail.com"
    linkedin = (profile.linkedin_url if profile else None) or "https://www.linkedin.com/in/"

    default_partnership_body = f"""Dear [Name],

I’m Adil, founder of GoldMind AI, an autonomous trading platform for Gold (XAUUSD), Bitcoin and FX. I’m writing to ask for your backing for the next stage.

The problem
Most retail trading bots fire on a single indicator and have no real risk controls. They get chopped up in volatile markets and bleed accounts. GoldMind AI is built to avoid this.

How it works
Five specialised AI agents must agree before any trade reaches the market:

Atlas scans the market for multi-factor confluence.
Hermes audits every setup across 5 layers: market regime, strategy logic, memory of past failures, higher-timeframe alignment and an exhaustion check. Only trades scoring 70% or higher pass.
Aegis enforces risk: it blocks entries around high-impact news and outside the London and New York sessions, and applies a hard daily loss cap of $150.
Vulcan executes via MetaTrader 5 with fixed $50 stop / $100 target brackets (1:2 risk-to-reward), moves to breakeven at +1R and trails profits.
Chronos studies every closed trade and automatically mutes any strategy whose rolling win rate drops below 50%.

What is already built (about 80%)

• A live execution bridge running 24/7 on a cloud VPS, connected to MT5.
• A web dashboard (React and Supabase) with a full signal audit trail, broker tickets and Telegram alerts.
• A live validation run that closed at +$140.03 net.
• About six months of development invested so far, by me, with cloud VPS, data feeds and automated backtesting tools.
• System Architecture & Walkthrough: https://github.com/adilrazask

The ask and how the money is used
We are raising $150,000 to $350,000:

Use | Share | At $150K | At $350K
• Low-latency infrastructure and broker connectivity | 35% | $52,500 | $122,500
• Quant research, ML and backtesting | 35% | $52,500 | $122,500
• Compliance, legal structure and IP protection | 20% | $30,000 | $70,000
• Working capital and reserve | 10% | $15,000 | $35,000

What it delivers

• Faster execution through direct broker connectivity.
• A stronger learning engine trained on historical tick data.
• Expansion into indices, oil and major FX pairs.
• A compliant structure for managed accounts, with performance-fee settlement.

Our targets at completion are a 58–65% win rate on 1:2 setups and drawdown held under 4.5%. These are goals we will validate with a documented track record, not guarantees.

I would welcome a 20-minute call this week to show you the live system, the audit trail and the trade records.

Best regards,

SK Adil Raja
Founder, GoldMind AI | M.Sc. in Computer Science
Hyderabad, India
Phone: {phone} | Email: {email}
LinkedIn: {linkedin}"""

    default_international_body = f"""Dear Hiring Team at [Company Name],

I hope this email finds you well.

My name is SK Adil Raja. I am an experienced Operations Executive currently based in Hyderabad, India, working with Omnia Steels Pvt Ltd in Attapur, Hyderabad. I am writing to express my strong interest in Operations, Supply Chain, and Logistics opportunities with [Company Name] in [Country].

With over 2.5 years of hands-on experience orchestrating end-to-end warehouse dispatch, ERP inventory reconciliation, and client logistics, I have maintained a 99%+ on-time fulfillment track record. My academic foundation in Computer Science (M.Sc.) also enables me to streamline operational reporting, troubleshoot automated ERP/CRM workflows, and implement systematic process controls.

Key Highlights of My Qualifications:
• Daily Operations & Dispatch: Supervising steel and industrial goods dispatch, transit documentation, and vendor communication.
• Digital Systems & ERP: Advanced proficiency with CRM/ERP tools, computerized inventory tracking, and data-driven logistics management.
• International Mobility: Highly motivated to relocate to [Country], fully committed to international operations, and prepared to adapt quickly to your team's global standards.

I have attached my comprehensive resume (SK_Adil_Raja_Resume.pdf) for your review. I would welcome the opportunity to discuss how my practical operations discipline and technical background can deliver immediate value to [Company Name].

Thank you for your valuable time and consideration.

Sincerely,

SK Adil Raja
Operations Executive, Omnia Steels Pvt Ltd
Attapur, Hyderabad, India
Phone: {phone} | Email: {email}
LinkedIn: {linkedin}"""

    default_domestic_body = f"""Dear Hiring Team,

My name is Adil, and I am currently working as an Operations Executive at Omnia Steels Pvt Ltd in Attapur, Hyderabad.

With over 2.5 years of hands-on experience orchestrating end-to-end warehouse dispatch, ERP inventory reconciliation, and client logistics, I have maintained a 99%+ on-time fulfillment track record. My academic foundation in Computer Science (M.Sc.) also enables me to streamline operational reporting, troubleshoot automated ERP/CRM workflows, and implement systematic process controls.

I have attached my comprehensive resume (SK_Adil_Raja_Resume.pdf) for your review.

Warm regards,

Adil
Operations Executive | Hyderabad, India
Phone: {phone} | Email: {email}
LinkedIn: {linkedin}"""

    custom_templates = dict((profile.verified_facts or {}).get("custom_templates", {})) if profile else {}

    return {
        "status": "SUCCESS",
        "candidate": {
            "name": "SK Adil Raja",
            "phone": phone,
            "email": email,
            "linkedin": linkedin,
            "current_company": "Omnia Steels Pvt Ltd",
            "current_location": "Attapur, Hyderabad, India",
            "highest_education": "M.Sc. Computer Science"
        },
        "templates": {
            "domestic_job": {
                "title": "Domestic Job Application (India / Hyderabad)",
                "subject": custom_templates.get("domestic_job_subject") or getattr(policy, "custom_application_subject", None) or "Application: Operations Executive — SK Adil Raja | Omnia Steels Pvt Ltd",
                "body": custom_templates.get("domestic_job_body") or getattr(policy, "custom_application_body", None) or default_domestic_body,
                "resume_attached": True
            },
            "outside_portal": {
                "title": "Outside Portals & Direct Hot-Mail",
                "subject": custom_templates.get("outside_portal_subject") or "Application: Operations Executive — SK Adil Raja | Omnia Steels Pvt Ltd",
                "body": custom_templates.get("outside_portal_body") or default_domestic_body,
                "resume_attached": True
            },
            "partnership": {
                "title": "GoldMind AI: Seed Round Investor Pitch ($150K–$350K)",
                "subject": custom_templates.get("partnership_pitch_subject") or "GoldMind AI: autonomous trading system, seed round open ($150K–$350K)",
                "body": custom_templates.get("partnership_pitch_body") or default_partnership_body,
                "resume_attached": False
            },
            "international": {
                "title": "International Jobs & Direct Corporate HR (Gulf & Western)",
                "subject": custom_templates.get("international_subject") or "Application: Operations Executive — SK Adil Raja | Omnia Steels Pvt Ltd (Relocation)",
                "body": custom_templates.get("international_body") or default_international_body,
                "resume_attached": True
            }
        }
    }


@router.post("/email-templates")
def update_email_templates(payload: EmailTemplatesPayload, db: Session = Depends(get_db)):
    """Saves updated email templates and candidate contact facts."""
    policy = db.query(AutomationPolicy).filter_by(id=1).first()
    profile = db.query(CareerProfile).first()

    if profile:
        if payload.candidate_phone:
            profile.phone = payload.candidate_phone.strip()
        if payload.candidate_linkedin:
            profile.linkedin_url = payload.candidate_linkedin.strip()
        if payload.candidate_email:
            profile.email = payload.candidate_email.strip()

        facts = dict(profile.verified_facts or {})
        templates_store = dict(facts.get("custom_templates", {}))
        if payload.domestic_job_subject:
            templates_store["domestic_job_subject"] = payload.domestic_job_subject.strip()
        if payload.domestic_job_body:
            templates_store["domestic_job_body"] = payload.domestic_job_body.strip()
        if payload.outside_portal_subject:
            templates_store["outside_portal_subject"] = payload.outside_portal_subject.strip()
        if payload.outside_portal_body:
            templates_store["outside_portal_body"] = payload.outside_portal_body.strip()
        if payload.partnership_pitch_subject:
            templates_store["partnership_pitch_subject"] = payload.partnership_pitch_subject.strip()
        if payload.partnership_pitch_body:
            templates_store["partnership_pitch_body"] = payload.partnership_pitch_body.strip()
        if payload.international_subject:
            templates_store["international_subject"] = payload.international_subject.strip()
        if payload.international_body:
            templates_store["international_body"] = payload.international_body.strip()
        facts["custom_templates"] = templates_store
        profile.verified_facts = facts

    if policy:
        if payload.domestic_job_subject:
            policy.custom_application_subject = payload.domestic_job_subject.strip()
        if payload.domestic_job_body:
            policy.custom_application_body = payload.domestic_job_body.strip()

    db.commit()

    record_audit_log(
        db=db,
        action="email_templates_updated",
        actor="owner",
        entity_type="email_templates",
        entity_id="1",
        details={"phone": payload.candidate_phone, "linkedin": payload.candidate_linkedin}
    )

    return {"status": "SUCCESS", "message": "Email templates and candidate contact facts successfully updated and persisted."}
