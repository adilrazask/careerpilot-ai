from __future__ import annotations
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import get_db
from app.models import JobListing, JobMatchResult, CareerProfile
from app.schemas.schemas import JobListingResponse, JobListingCreate, JobSearchQuery, JobMatchResultSchema
from app.services.adapters import SourceManager, canonicalize_url
from app.services.matching import MatchingEngine
from app.services.audit import record_audit_log

router = APIRouter(prefix="/api/jobs", tags=["Job Discovery"])

@router.get("", response_model=List[JobListingResponse])
def get_jobs(
    q: Optional[str] = None,
    location: Optional[str] = None,
    platform: Optional[str] = None,
    min_score: Optional[int] = None,
    status: Optional[str] = None,
    vacancy_status: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    query = db.query(JobListing)
    if q:
        query = query.filter((JobListing.title.ilike(f"%{q}%")) | (JobListing.company_name.ilike(f"%{q}%")))
    if location:
        query = query.filter(JobListing.location.ilike(f"%{location}%"))
    if platform:
        query = query.filter(JobListing.source_platform.ilike(f"%{platform}%"))
    if min_score is not None:
        query = query.filter(JobListing.match_score >= min_score)
    if status:
        query = query.filter(JobListing.application_status == status)
    if vacancy_status:
        query = query.filter(JobListing.vacancy_status == vacancy_status)

    jobs = query.order_by(desc(JobListing.match_score), desc(JobListing.id)).limit(limit).all()

    results = []
    for j in jobs:
        mr = j.match_results[-1] if j.match_results else None
        mr_schema = None
        if mr:
            mr_schema = JobMatchResultSchema(
                match_score=mr.match_score,
                eligibility_status=mr.eligibility_status,
                matching_requirements=mr.matching_requirements or [],
                missing_requirements=mr.missing_requirements or [],
                uncertain_requirements=mr.uncertain_requirements or [],
                location_match=mr.location_match,
                salary_match=mr.salary_match,
                score_breakdown=mr.score_breakdown or {},
                explanation=mr.explanation,
                recommended_action=mr.recommended_action
            )
        results.append(JobListingResponse(
            id=j.id,
            title=j.title,
            company_name=j.company_name,
            location=j.location,
            work_mode=j.work_mode,
            employment_type=j.employment_type,
            experience_required_min=j.experience_required_min,
            experience_required_max=j.experience_required_max,
            salary_min=j.salary_min,
            salary_max=j.salary_max,
            salary_currency=j.salary_currency,
            source_platform=j.source_platform,
            original_url=j.original_url,
            description=j.description,
            date_discovered=j.date_discovered,
            publication_date=j.publication_date,
            last_verified_date=j.last_verified_date,
            vacancy_status=j.vacancy_status,
            match_score=j.match_score,
            eligibility_status=j.eligibility_status,
            application_method=j.application_method,
            hr_contact_status=j.hr_contact_status,
            application_status=j.application_status,
            notes=j.notes,
            match_result=mr_schema
        ))
    return results

@router.get("/{job_id}", response_model=JobListingResponse)
def get_job_detail(job_id: int, db: Session = Depends(get_db)):
    j = db.query(JobListing).filter_by(id=job_id).first()
    if not j:
        raise HTTPException(status_code=404, detail="Job listing not found.")
    
    mr = j.match_results[-1] if j.match_results else None
    mr_schema = None
    if mr:
        mr_schema = JobMatchResultSchema(
            match_score=mr.match_score,
            eligibility_status=mr.eligibility_status,
            matching_requirements=mr.matching_requirements or [],
            missing_requirements=mr.missing_requirements or [],
            uncertain_requirements=mr.uncertain_requirements or [],
            location_match=mr.location_match,
            salary_match=mr.salary_match,
            score_breakdown=mr.score_breakdown or {},
            explanation=mr.explanation,
            recommended_action=mr.recommended_action
        )
    return JobListingResponse(
        id=j.id,
        title=j.title,
        company_name=j.company_name,
        location=j.location,
        work_mode=j.work_mode,
        employment_type=j.employment_type,
        experience_required_min=j.experience_required_min,
        experience_required_max=j.experience_required_max,
        salary_min=j.salary_min,
        salary_max=j.salary_max,
        salary_currency=j.salary_currency,
        source_platform=j.source_platform,
        original_url=j.original_url,
        description=j.description,
        date_discovered=j.date_discovered,
        publication_date=j.publication_date,
        last_verified_date=j.last_verified_date,
        vacancy_status=j.vacancy_status,
        match_score=j.match_score,
        eligibility_status=j.eligibility_status,
        application_method=j.application_method,
        hr_contact_status=j.hr_contact_status,
        application_status=j.application_status,
        notes=j.notes,
        match_result=mr_schema
    )

@router.post("/search")
def trigger_search(payload: JobSearchQuery, db: Session = Depends(get_db)):
    tavily = SourceManager.get_adapter("tavily_search")
    if not tavily:
        raise HTTPException(status_code=500, detail="Search adapter not available.")

    leads = tavily.search_jobs(payload.query, payload.location, limit=payload.max_results)
    existing = db.query(JobListing).all()
    profile = db.query(CareerProfile).filter_by(id=1).first()

    added = 0
    for lead in leads:
        if not SourceManager.is_duplicate(lead, existing):
            jl = JobListing(
                title=lead["title"],
                company_name=lead["company_name"],
                location=lead["location"],
                work_mode=lead.get("work_mode", "On-site"),
                employment_type=lead.get("employment_type", "Full-time"),
                source_platform=lead["source_platform"],
                original_url=lead["original_url"],
                canonical_url=lead["canonical_url"],
                description=lead["description"],
                vacancy_status="VERIFIED_OPEN",
                application_method="email",
                date_discovered=datetime.now(timezone.utc)
            )
            db.add(jl)
            db.commit()
            db.refresh(jl)

            if profile:
                eval_res = MatchingEngine.evaluate(jl, profile)
                jl.match_score = eval_res["match_score"]
                jl.eligibility_status = eval_res["eligibility_status"]
                db.add(JobMatchResult(
                    job_id=jl.id,
                    match_score=eval_res["match_score"],
                    eligibility_status=eval_res["eligibility_status"],
                    matching_requirements=eval_res["matching_requirements"],
                    missing_requirements=eval_res["missing_requirements"],
                    uncertain_requirements=eval_res["uncertain_requirements"],
                    location_match=eval_res["location_match"],
                    salary_match=eval_res["salary_match"],
                    score_breakdown=eval_res["score_breakdown"],
                    explanation=eval_res["explanation"],
                    recommended_action=eval_res["recommended_action"]
                ))
                db.commit()

            existing.append(jl)
            added += 1

    record_audit_log(
        db=db,
        action="manual_job_search",
        actor="owner",
        details={"query": payload.query, "location": payload.location, "added": added}
    )
    return {"status": "SUCCESS", "leads_found": len(leads), "leads_added": added}

@router.post("/create", response_model=JobListingResponse)
def create_job_manually(payload: JobListingCreate, db: Session = Depends(get_db)):
    canon_url = canonicalize_url(payload.original_url)
    existing = db.query(JobListing).filter((JobListing.original_url == payload.original_url) | (JobListing.canonical_url == canon_url)).first()
    if existing:
        raise HTTPException(status_code=400, detail="A job vacancy with this URL already exists.")

    jl = JobListing(
        title=payload.title,
        company_name=payload.company_name,
        location=payload.location,
        work_mode=payload.work_mode,
        employment_type=payload.employment_type,
        experience_required_min=payload.experience_required_min,
        experience_required_max=payload.experience_required_max,
        salary_min=payload.salary_min,
        salary_max=payload.salary_max,
        salary_currency=payload.salary_currency,
        source_platform=payload.source_platform,
        original_url=payload.original_url,
        canonical_url=canon_url,
        description=payload.description,
        vacancy_status="VERIFIED_OPEN",
        application_method="email",
        notes=payload.notes or "",
        date_discovered=datetime.now(timezone.utc)
    )
    db.add(jl)
    db.commit()
    db.refresh(jl)

    profile = db.query(CareerProfile).filter_by(id=1).first()
    mr_schema = None
    if profile:
        eval_res = MatchingEngine.evaluate(jl, profile)
        jl.match_score = eval_res["match_score"]
        jl.eligibility_status = eval_res["eligibility_status"]
        mr = JobMatchResult(
            job_id=jl.id,
            match_score=eval_res["match_score"],
            eligibility_status=eval_res["eligibility_status"],
            matching_requirements=eval_res["matching_requirements"],
            missing_requirements=eval_res["missing_requirements"],
            uncertain_requirements=eval_res["uncertain_requirements"],
            location_match=eval_res["location_match"],
            salary_match=eval_res["salary_match"],
            score_breakdown=eval_res["score_breakdown"],
            explanation=eval_res["explanation"],
            recommended_action=eval_res["recommended_action"]
        )
        db.add(mr)
        db.commit()
        mr_schema = JobMatchResultSchema(
            match_score=mr.match_score,
            eligibility_status=mr.eligibility_status,
            matching_requirements=mr.matching_requirements,
            missing_requirements=mr.missing_requirements,
            uncertain_requirements=mr.uncertain_requirements,
            location_match=mr.location_match,
            salary_match=mr.salary_match,
            score_breakdown=mr.score_breakdown,
            explanation=mr.explanation,
            recommended_action=mr.recommended_action
        )

    record_audit_log(db, "manual_job_created", actor="owner", entity_type="job_listing", entity_id=str(jl.id))
    return JobListingResponse(
        id=jl.id,
        title=jl.title,
        company_name=jl.company_name,
        location=jl.location,
        work_mode=jl.work_mode,
        employment_type=jl.employment_type,
        experience_required_min=jl.experience_required_min,
        experience_required_max=jl.experience_required_max,
        salary_min=jl.salary_min,
        salary_max=jl.salary_max,
        salary_currency=jl.salary_currency,
        source_platform=jl.source_platform,
        original_url=jl.original_url,
        description=jl.description,
        date_discovered=jl.date_discovered,
        publication_date=jl.publication_date,
        last_verified_date=jl.last_verified_date,
        vacancy_status=jl.vacancy_status,
        match_score=jl.match_score,
        eligibility_status=jl.eligibility_status,
        application_method=jl.application_method,
        hr_contact_status=jl.hr_contact_status,
        application_status=jl.application_status,
        notes=jl.notes,
        match_result=mr_schema
    )

@router.post("/{job_id}/revalidate")
def revalidate_job(job_id: int, db: Session = Depends(get_db)):
    jl = db.query(JobListing).filter_by(id=job_id).first()
    if not jl:
        raise HTTPException(status_code=404, detail="Job not found.")

    adapter = SourceManager.get_adapter("tavily_search")
    new_status = adapter.verify_job_status(jl.original_url) if adapter else "VERIFIED_OPEN"
    jl.vacancy_status = new_status
    jl.last_verified_date = datetime.now(timezone.utc)
    db.commit()

    record_audit_log(db, "job_vacancy_revalidated", actor="owner", entity_type="job_listing", entity_id=str(jl.id), details={"status": new_status})
    return {"status": "SUCCESS", "job_id": jl.id, "vacancy_status": new_status}
