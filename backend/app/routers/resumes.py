from __future__ import annotations
import os
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ResumeVersion, JobListing, CareerProfile
from app.schemas.schemas import TailorResumeRequest, ResumeVersionResponse
from app.services.resume_engine import ResumeEngine
from app.services.audit import record_audit_log

router = APIRouter(prefix="/api/resumes", tags=["Resume Intelligence"])

@router.post("/tailor", response_model=ResumeVersionResponse)
def tailor_resume_for_job(payload: TailorResumeRequest, db: Session = Depends(get_db)):
    job = db.query(JobListing).filter_by(id=payload.job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job listing not found.")
    profile = db.query(CareerProfile).filter_by(id=1).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Career profile not found.")

    tailored = ResumeEngine.tailor(job, profile, use_ai=payload.use_ai)

    # Generate documents
    resumes_dir = "./data/resumes"
    os.makedirs(resumes_dir, exist_ok=True)
    pdf_path = os.path.join(resumes_dir, f"resume_job_{job.id}.pdf")
    docx_path = os.path.join(resumes_dir, f"resume_job_{job.id}.docx")

    ResumeEngine.generate_pdf(tailored, pdf_path, profile)
    ResumeEngine.generate_docx(tailored, docx_path, profile)

    rv = ResumeVersion(
        profile_id=profile.id,
        job_id=job.id,
        version_name=tailored["version_name"],
        headline=tailored["headline"],
        summary=tailored["summary"],
        full_text=tailored["full_text"],
        cover_letter_text=tailored["cover_letter_text"],
        pdf_path=pdf_path,
        docx_path=docx_path,
        model_used=tailored["model_used"],
        factual_consistency_score=tailored["factual_consistency_score"]
    )
    db.add(rv)
    job.application_status = "RESUME_READY"
    db.commit()
    db.refresh(rv)

    record_audit_log(
        db=db,
        action="resume_tailored",
        actor="owner",
        entity_type="resume_version",
        entity_id=str(rv.id),
        details={"job_id": job.id, "company": job.company_name}
    )

    return ResumeVersionResponse(
        id=rv.id,
        job_id=rv.job_id,
        version_name=rv.version_name,
        headline=rv.headline,
        summary=rv.summary,
        full_text=rv.full_text,
        cover_letter_text=rv.cover_letter_text,
        pdf_path=rv.pdf_path,
        docx_path=rv.docx_path,
        model_used=rv.model_used,
        factual_consistency_score=rv.factual_consistency_score,
        created_at=rv.created_at
    )

@router.get("/versions/{job_id}", response_model=List[ResumeVersionResponse])
def get_versions_for_job(job_id: int, db: Session = Depends(get_db)):
    versions = db.query(ResumeVersion).filter_by(job_id=job_id).order_by(ResumeVersion.id.desc()).all()
    return [
        ResumeVersionResponse(
            id=v.id,
            job_id=v.job_id,
            version_name=v.version_name,
            headline=v.headline,
            summary=v.summary,
            full_text=v.full_text,
            cover_letter_text=v.cover_letter_text,
            pdf_path=v.pdf_path,
            docx_path=v.docx_path,
            model_used=v.model_used,
            factual_consistency_score=v.factual_consistency_score,
            created_at=v.created_at
        ) for v in versions
    ]

@router.get("/download/{version_id}/{doc_format}")
def download_resume(version_id: int, doc_format: str, db: Session = Depends(get_db)):
    rv = db.query(ResumeVersion).filter_by(id=version_id).first()
    if not rv:
        raise HTTPException(status_code=404, detail="Resume version not found.")

    if doc_format.lower() == "pdf":
        if not rv.pdf_path or not os.path.exists(rv.pdf_path):
            raise HTTPException(status_code=404, detail="PDF file not found on disk.")
        return FileResponse(rv.pdf_path, media_type="application/pdf", filename=f"Resume_{rv.version_name}.pdf")
    elif doc_format.lower() in ["docx", "doc"]:
        if not rv.docx_path or not os.path.exists(rv.docx_path):
            raise HTTPException(status_code=404, detail="DOCX file not found on disk.")
        return FileResponse(rv.docx_path, media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document", filename=f"Resume_{rv.version_name}.docx")
    else:
        raise HTTPException(status_code=400, detail="Invalid format requested; specify pdf or docx.")
