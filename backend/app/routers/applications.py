from __future__ import annotations
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    ApplicationRecord, ApplicationAttempt, JobListing, RecruiterContact,
    ResumeVersion, CareerProfile
)
from app.schemas.schemas import ApplicationRecordResponse, ApplicationTransitionRequest
from app.services.email_service import EmailOutreachService
from app.services.portal_service import EmployerPortalService
from app.services.follow_up_service import FollowUpService
from app.services.audit import record_audit_log

router = APIRouter(prefix="/api/applications", tags=["Application Pipeline"])

VALID_21_STATUSES = [
    "DISCOVERED",
    "UNDER_EVALUATION",
    "MATCHED",
    "REJECTED_BY_FILTER",
    "VACANCY_VERIFICATION_PENDING",
    "VERIFIED_OPEN",
    "RESUME_PENDING",
    "RESUME_READY",
    "CONTACT_PENDING",
    "APPLICATION_READY",
    "AWAITING_SUBMISSION",
    "SUBMISSION_IN_PROGRESS",
    "SUBMITTED",
    "EMAIL_SENT",
    "DELIVERY_CONFIRMED",
    "DELIVERY_FAILED",
    "APPLICATION_ACKNOWLEDGED",
    "RECRUITER_RESPONSE_RECEIVED",
    "INTERVIEW_INVITED",
    "REJECTED_BY_EMPLOYER",
    "WITHDRAWN",
    "CLOSED"
]

@router.get("", response_model=List[ApplicationRecordResponse])
def get_applications(status: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(ApplicationRecord)
    if status:
        query = query.filter_by(current_status=status)
    apps = query.order_by(ApplicationRecord.id.desc()).all()
    
    return [
        ApplicationRecordResponse(
            id=a.id,
            job_id=a.job_id,
            job_title=a.job.title if a.job else "Unknown Role",
            company_name=a.job.company_name if a.job else "Unknown Employer",
            current_status=a.current_status,
            submission_method=a.submission_method,
            primary_recipient=a.primary_recipient,
            external_confirmation_id=a.external_confirmation_id,
            delivery_evidence=a.delivery_evidence or {},
            acknowledgement_received=a.acknowledgement_received,
            interview_invited=a.interview_invited,
            rejection_received=a.rejection_received,
            unattended_approved=a.unattended_approved,
            created_at=a.created_at,
            updated_at=a.updated_at,
            resume_version_id=a.resume_version_id
        ) for a in apps
    ]

@router.post("/prepare/{job_id}", response_model=ApplicationRecordResponse)
def prepare_application(job_id: int, db: Session = Depends(get_db)):
    job = db.query(JobListing).filter_by(id=job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job listing not found.")

    # Check if application record already exists
    app_rec = db.query(ApplicationRecord).filter_by(job_id=job.id).first()
    if not app_rec:
        # Find contact
        contact = db.query(RecruiterContact).filter_by(job_id=job.id).first()
        recipient = contact.email if contact else ""
        
        # Find latest tailored resume
        rv = db.query(ResumeVersion).filter_by(job_id=job.id).order_by(ResumeVersion.id.desc()).first()

        app_rec = ApplicationRecord(
            job_id=job.id,
            resume_version_id=rv.id if rv else None,
            current_status="APPLICATION_READY" if (rv and recipient) else "RESUME_PENDING",
            submission_method="email" if recipient else "portal",
            primary_recipient=recipient,
            unattended_approved=False
        )
        db.add(app_rec)
        job.application_status = app_rec.current_status
        db.commit()
        db.refresh(app_rec)

    return ApplicationRecordResponse(
        id=app_rec.id,
        job_id=app_rec.job_id,
        job_title=job.title,
        company_name=job.company_name,
        current_status=app_rec.current_status,
        submission_method=app_rec.submission_method,
        primary_recipient=app_rec.primary_recipient,
        external_confirmation_id=app_rec.external_confirmation_id,
        delivery_evidence=app_rec.delivery_evidence or {},
        acknowledgement_received=app_rec.acknowledgement_received,
        interview_invited=app_rec.interview_invited,
        rejection_received=app_rec.rejection_received,
        unattended_approved=app_rec.unattended_approved,
        created_at=app_rec.created_at,
        updated_at=app_rec.updated_at,
        resume_version_id=app_rec.resume_version_id
    )

@router.post("/submit/{app_id}")
def submit_application(app_id: int, db: Session = Depends(get_db)):
    app_rec = db.query(ApplicationRecord).filter_by(id=app_id).first()
    if not app_rec:
        raise HTTPException(status_code=404, detail="Application record not found.")

    job = app_rec.job
    profile = db.query(CareerProfile).filter_by(id=1).first()

    # Step 1: Verification guard: Vacancy must not be closed
    if job.vacancy_status in ["CLOSED", "EXPIRED", "SUSPICIOUS"]:
        raise HTTPException(status_code=400, detail=f"Cannot submit: Vacancy is marked '{job.vacancy_status}'.")

    # Step 2: Resume version must exist
    rv = app_rec.resume_version or db.query(ResumeVersion).filter_by(job_id=job.id).order_by(ResumeVersion.id.desc()).first()
    if not rv:
        raise HTTPException(status_code=400, detail="Tailored resume draft has not been generated for this vacancy yet.")

    app_rec.resume_version_id = rv.id

    # Step 3: Branch on submission method
    if app_rec.submission_method == "email":
        # Recipient must be verified
        if not app_rec.primary_recipient:
            raise HTTPException(status_code=400, detail="Primary recipient email is missing.")

        res = EmailOutreachService.send_application_email(app_rec, rv, db, is_unattended=False)
        job.application_status = app_rec.current_status
        db.commit()

        # Schedule follow-up
        FollowUpService.schedule_follow_up_if_eligible(app_rec, db)

        return {"status": "SUCCESS", "message": "Email application transmitted.", "evidence": res.get("evidence")}

    elif app_rec.submission_method == "portal":
        res = EmployerPortalService.attempt_portal_submission(app_rec, profile, db)
        job.application_status = app_rec.current_status
        db.commit()
        return res

    else:
        raise HTTPException(status_code=400, detail=f"Unsupported submission method: {app_rec.submission_method}")

@router.post("/transition/{app_id}", response_model=ApplicationRecordResponse)
def transition_status(app_id: int, payload: ApplicationTransitionRequest, db: Session = Depends(get_db)):
    app_rec = db.query(ApplicationRecord).filter_by(id=app_id).first()
    if not app_rec:
        raise HTTPException(status_code=404, detail="Application record not found.")

    if payload.new_status not in VALID_21_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status '{payload.new_status}'. Must be one of 21 standard statuses.")

    old_status = app_rec.current_status
    app_rec.current_status = payload.new_status
    if payload.evidence:
        app_rec.delivery_evidence = {**(app_rec.delivery_evidence or {}), **payload.evidence}

    if payload.new_status == "INTERVIEW_INVITED":
        app_rec.interview_invited = True
    elif payload.new_status == "APPLICATION_ACKNOWLEDGED":
        app_rec.acknowledgement_received = True
    elif payload.new_status == "REJECTED_BY_EMPLOYER":
        app_rec.rejection_received = True

    job = app_rec.job
    if job:
        job.application_status = payload.new_status

    db.commit()
    db.refresh(app_rec)

    record_audit_log(
        db=db,
        action="application_status_transitioned",
        actor="owner",
        entity_type="application_record",
        entity_id=str(app_rec.id),
        details={"from": old_status, "to": payload.new_status, "reason": payload.reason}
    )

    return ApplicationRecordResponse(
        id=app_rec.id,
        job_id=app_rec.job_id,
        job_title=job.title if job else "",
        company_name=job.company_name if job else "",
        current_status=app_rec.current_status,
        submission_method=app_rec.submission_method,
        primary_recipient=app_rec.primary_recipient,
        external_confirmation_id=app_rec.external_confirmation_id,
        delivery_evidence=app_rec.delivery_evidence or {},
        acknowledgement_received=app_rec.acknowledgement_received,
        interview_invited=app_rec.interview_invited,
        rejection_received=app_rec.rejection_received,
        unattended_approved=app_rec.unattended_approved,
        created_at=app_rec.created_at,
        updated_at=app_rec.updated_at,
        resume_version_id=app_rec.resume_version_id
    )

@router.get("/{app_id}/attempts")
def get_application_attempts(app_id: int, db: Session = Depends(get_db)):
    attempts = db.query(ApplicationAttempt).filter_by(application_id=app_id).order_by(ApplicationAttempt.attempt_number.asc()).all()
    return [
        {
            "id": a.id,
            "attempt_number": a.attempt_number,
            "method": a.submission_method,
            "recipient_or_portal": a.recipient_or_portal,
            "status": a.status,
            "idempotency_key": a.idempotency_key,
            "evidence": a.evidence,
            "error_message": a.error_message,
            "attempted_at": a.attempted_at
        } for a in attempts
    ]
