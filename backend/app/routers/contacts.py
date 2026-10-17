from __future__ import annotations
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import RecruiterContact, JobListing
from app.schemas.schemas import RecruiterContactResponse, RecruiterContactCreate, VerifyContactRequest
from app.services.contact_service import ContactService
from app.services.audit import record_audit_log

router = APIRouter(prefix="/api/contacts", tags=["HR & Recruiter Contacts"])

@router.get("", response_model=List[RecruiterContactResponse])
def get_contacts(job_id: Optional[int] = None, db: Session = Depends(get_db)):
    query = db.query(RecruiterContact)
    if job_id:
        query = query.filter_by(job_id=job_id)
    contacts = query.order_by(RecruiterContact.id.desc()).all()
    return [
        RecruiterContactResponse(
            id=c.id,
            job_id=c.job_id,
            company_name=c.company_name,
            contact_name=c.contact_name,
            contact_role=c.contact_role,
            email=c.email,
            phone=c.phone,
            source_url=c.source_url,
            discovery_date=c.discovery_date,
            verification_status=c.verification_status,
            verification_method=c.verification_method,
            last_verification_date=c.last_verification_date,
            confidence=c.confidence,
            intended_use=c.intended_use,
            notes=c.notes or ""
        ) for c in contacts
    ]

@router.post("/discover/{job_id}", response_model=List[RecruiterContactResponse])
def discover_contacts(job_id: int, db: Session = Depends(get_db)):
    job = db.query(JobListing).filter_by(id=job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job listing not found.")

    discovered = ContactService.discover_public_contacts(job.company_name, job.location, db, job_id=job.id)
    verified_list = []
    for c in discovered:
        verified_contact = ContactService.verify_contact(c, db)
        verified_list.append(verified_contact)

    if any(vc.verification_status in ["EMAIL_VALIDATED", "SOURCE_VERIFIED"] for vc in verified_list):
        job.hr_contact_status = "VERIFIED"
        db.commit()

    return [
        RecruiterContactResponse(
            id=c.id,
            job_id=c.job_id,
            company_name=c.company_name,
            contact_name=c.contact_name,
            contact_role=c.contact_role,
            email=c.email,
            phone=c.phone,
            source_url=c.source_url,
            discovery_date=c.discovery_date,
            verification_status=c.verification_status,
            verification_method=c.verification_method,
            last_verification_date=c.last_verification_date,
            confidence=c.confidence,
            intended_use=c.intended_use,
            notes=c.notes or ""
        ) for c in verified_list
    ]

@router.post("/verify/{contact_id}", response_model=RecruiterContactResponse)
def verify_contact_by_id(contact_id: int, db: Session = Depends(get_db)):
    contact = db.query(RecruiterContact).filter_by(id=contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Recruiter contact not found.")

    vc = ContactService.verify_contact(contact, db)
    return RecruiterContactResponse(
        id=vc.id,
        job_id=vc.job_id,
        company_name=vc.company_name,
        contact_name=vc.contact_name,
        contact_role=vc.contact_role,
        email=vc.email,
        phone=vc.phone,
        source_url=vc.source_url,
        discovery_date=vc.discovery_date,
        verification_status=vc.verification_status,
        verification_method=vc.verification_method,
        last_verification_date=vc.last_verification_date,
        confidence=vc.confidence,
        intended_use=vc.intended_use,
        notes=vc.notes or ""
    )

@router.post("/create", response_model=RecruiterContactResponse)
def create_manual_contact(payload: RecruiterContactCreate, db: Session = Depends(get_db)):
    c = RecruiterContact(
        job_id=payload.job_id,
        company_name=payload.company_name,
        contact_name=payload.contact_name,
        contact_role=payload.contact_role,
        email=payload.email,
        phone=payload.phone or "",
        source_url=payload.source_url,
        verification_status="DISCOVERED",
        confidence=0.5,
        intended_use=payload.intended_use,
        notes=payload.notes or ""
    )
    db.add(c)
    db.commit()
    db.refresh(c)

    # Immediately run verification
    vc = ContactService.verify_contact(c, db)
    if payload.job_id and vc.verification_status in ["EMAIL_VALIDATED", "SOURCE_VERIFIED"]:
        j = db.query(JobListing).filter_by(id=payload.job_id).first()
        if j:
            j.hr_contact_status = "VERIFIED"
            db.commit()

    record_audit_log(db, "manual_contact_created", actor="owner", entity_type="recruiter_contact", entity_id=str(vc.id))
    return RecruiterContactResponse(
        id=vc.id,
        job_id=vc.job_id,
        company_name=vc.company_name,
        contact_name=vc.contact_name,
        contact_role=vc.contact_role,
        email=vc.email,
        phone=vc.phone,
        source_url=vc.source_url,
        discovery_date=vc.discovery_date,
        verification_status=vc.verification_status,
        verification_method=vc.verification_method,
        last_verification_date=vc.last_verification_date,
        confidence=vc.confidence,
        intended_use=vc.intended_use,
        notes=vc.notes or ""
    )
