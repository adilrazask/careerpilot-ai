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
        allowed_locations=policy.allowed_locations or [],
        allowed_job_families=policy.allowed_job_families or [],
        allowed_salary_min=policy.allowed_salary_min or 0.0,
        excluded_companies=policy.excluded_companies or [],
        excluded_employers=policy.excluded_employers or [],
        search_query=policy.search_query or "",
        search_location=policy.search_location or "",
        last_search_at=policy.last_search_at,
        next_search_at=policy.next_search_at
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
