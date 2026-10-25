from __future__ import annotations
import os
import shutil
from pathlib import Path
from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    CareerProfile, EmploymentHistory, Skill, Education, Certification,
    CareerPreferences, ResumeFile
)
from app.schemas.schemas import (
    CareerProfileResponse, CareerProfileUpdateRequest, CareerPreferencesSchema,
    EmploymentHistorySchema, SkillSchema, EducationSchema, CertificationSchema
)
from app.services.resume_engine import ResumeEngine
from app.services.audit import record_audit_log

router = APIRouter(prefix="/api/profile", tags=["Career Profile"])

def _build_profile_response(profile: CareerProfile) -> CareerProfileResponse:
    pref_schema = None
    if profile.preferences:
        p = profile.preferences
        pref_schema = CareerPreferencesSchema(
            preferred_titles=p.preferred_titles or [],
            preferred_locations=p.preferred_locations or [],
            open_to_remote=p.open_to_remote,
            open_to_relocation=p.open_to_relocation,
            relocation_preferences=p.relocation_preferences or [],
            minimum_salary=p.minimum_salary or 0.0,
            preferred_salary=p.preferred_salary or 0.0,
            salary_currency=p.salary_currency or "INR",
            notice_period_days=p.notice_period_days or 30,
            availability=p.availability or "30 days",
            work_authorisation=p.work_authorisation or "Citizen of India",
            preferred_industries=p.preferred_industries or [],
            excluded_industries=p.excluded_industries or [],
            excluded_companies=p.excluded_companies or [],
            work_mode=p.work_mode or ["On-site", "Hybrid", "Remote"]
        )

    return CareerProfileResponse(
        id=profile.id,
        full_name=profile.full_name,
        email=profile.email,
        phone=profile.phone,
        current_location=profile.current_location,
        total_experience_years=profile.total_experience_years,
        summary=profile.summary,
        linkedin_url=profile.linkedin_url,
        portfolio_url=profile.portfolio_url,
        avatar_url=getattr(profile, "avatar_url", "/profile_photo.jpg") or "/profile_photo.jpg",
        preferred_contact_method=profile.preferred_contact_method,
        verified_facts=profile.verified_facts or {},
        employment_history=[
            EmploymentHistorySchema(
                id=e.id,
                company=e.company,
                job_title=e.job_title,
                location=e.location,
                start_date=e.start_date,
                end_date=e.end_date,
                is_current=e.is_current,
                responsibilities=e.responsibilities or [],
                achievements=e.achievements or [],
                tools_used=e.tools_used or [],
                is_verified=e.is_verified
            ) for e in profile.employment_history
        ],
        skills=[
            SkillSchema(
                id=s.id,
                name=s.name,
                category=s.category,
                years_experience=s.years_experience,
                proficiency=s.proficiency,
                is_verified=s.is_verified
            ) for s in profile.skills
        ],
        education=[
            EducationSchema(
                id=ed.id,
                institution=ed.institution,
                degree=ed.degree,
                field_of_study=ed.field_of_study,
                graduation_year=ed.graduation_year,
                grade_or_gpa=ed.grade_or_gpa,
                is_verified=ed.is_verified
            ) for ed in profile.education
        ],
        certifications=[
            CertificationSchema(
                id=c.id,
                name=c.name,
                issuing_organization=c.issuing_organization,
                issue_date=c.issue_date,
                expiry_date=c.expiry_date,
                credential_id=c.credential_id,
                credential_url=c.credential_url,
                is_verified=c.is_verified
            ) for c in profile.certifications
        ],
        preferences=pref_schema
    )

@router.get("", response_model=CareerProfileResponse)
def get_career_profile(db: Session = Depends(get_db)):
    profile = db.query(CareerProfile).filter_by(id=1).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Career profile not found.")
    return _build_profile_response(profile)

@router.put("", response_model=CareerProfileResponse)
def update_career_profile(payload: CareerProfileUpdateRequest, db: Session = Depends(get_db)):
    profile = db.query(CareerProfile).filter_by(id=1).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Career profile not found.")

    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(profile, k, v)

    db.commit()
    db.refresh(profile)
    record_audit_log(db, "career_profile_updated", actor="owner", entity_type="career_profile", entity_id=str(profile.id))
    return _build_profile_response(profile)

@router.put("/preferences", response_model=CareerPreferencesSchema)
def update_preferences(payload: CareerPreferencesSchema, db: Session = Depends(get_db)):
    profile = db.query(CareerProfile).filter_by(id=1).first()
    if not profile or not profile.preferences:
        raise HTTPException(status_code=404, detail="Career preferences not found.")

    p = profile.preferences
    for k, v in payload.model_dump().items():
        setattr(p, k, v)

    db.commit()
    db.refresh(p)
    record_audit_log(db, "career_preferences_updated", actor="owner", entity_type="career_preferences")
    return payload

@router.post("/upload-resume")
async def upload_resume(file: UploadFile = File(...), db: Session = Depends(get_db)):
    profile = db.query(CareerProfile).filter_by(id=1).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Career profile not found.")

    filename = file.filename or "resume.pdf"
    ext = filename.split(".")[-1].lower()
    if ext not in ["pdf", "docx", "doc", "txt"]:
        raise HTTPException(status_code=400, detail="Allowed file types: PDF, DOCX, TXT.")

    upload_dir = Path("./data/uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / f"profile_resume_{profile.id}.{ext}"

    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Parse resume
    parsed = ResumeEngine.parse_uploaded_resume(str(file_path), ext)
    
    # Store ResumeFile
    rf = ResumeFile(
        profile_id=profile.id,
        filename=filename,
        file_path=str(file_path),
        file_type=ext,
        extracted_text=parsed["raw_text"],
        is_primary=True,
        parsed_data=parsed
    )
    db.add(rf)
    db.commit()

    record_audit_log(
        db=db,
        action="resume_uploaded_and_parsed",
        actor="owner",
        entity_type="resume_file",
        entity_id=str(rf.id),
        details={"filename": filename, "extracted_lines": parsed["line_count"]}
    )

    return {
        "status": "SUCCESS",
        "message": f"Resume '{filename}' parsed successfully.",
        "extracted_email": parsed.get("extracted_email"),
        "extracted_phone": parsed.get("extracted_phone"),
        "extracted_preview": parsed["raw_text"][:800]
    }

@router.post("/skills", response_model=SkillSchema)
def add_skill(payload: SkillSchema, db: Session = Depends(get_db)):
    profile = db.query(CareerProfile).filter_by(id=1).first()
    s = Skill(
        profile_id=profile.id,
        name=payload.name,
        category=payload.category,
        years_experience=payload.years_experience,
        proficiency=payload.proficiency,
        is_verified=True
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return SkillSchema(
        id=s.id,
        name=s.name,
        category=s.category,
        years_experience=s.years_experience,
        proficiency=s.proficiency,
        is_verified=s.is_verified
    )

@router.delete("/skills/{skill_id}")
def delete_skill(skill_id: int, db: Session = Depends(get_db)):
    s = db.query(Skill).filter_by(id=skill_id).first()
    if s:
        db.delete(s)
        db.commit()
    return {"status": "SUCCESS"}
