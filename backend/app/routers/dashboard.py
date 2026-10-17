from __future__ import annotations
from datetime import datetime, timezone, timedelta
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models import (
    JobListing, ApplicationRecord, AutomationPolicy, WorkerRun, SystemHealth,
    RecruiterResponse, Interview, AuditLog, ScheduledTask
)
from app.schemas.schemas import DashboardMetricsResponse
from app.services.audit import record_audit_log

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])

@router.get("/metrics", response_model=DashboardMetricsResponse)
def get_dashboard_metrics(db: Session = Depends(get_db)):
    now_ts = datetime.now(timezone.utc)
    today_start = now_ts.replace(hour=0, minute=0, second=0, microsecond=0)

    # 1. Worker & Agent Status
    policy = db.query(AutomationPolicy).filter_by(id=1).first()
    recent_heartbeat_threshold = now_ts - timedelta(minutes=3)
    latest_worker = db.query(WorkerRun).order_by(WorkerRun.heartbeat_at.desc()).first()
    
    worker_is_alive = False
    if latest_worker and latest_worker.heartbeat_at:
        # Normalize timezone
        hb = latest_worker.heartbeat_at
        if hb.tzinfo is None:
            hb = hb.replace(tzinfo=timezone.utc)
        if hb >= recent_heartbeat_threshold:
            worker_is_alive = True

    if policy and policy.pause_all_automation:
        agent_status = "PAUSED"
    elif not worker_is_alive:
        agent_status = "IDLE (Worker Offline)"
    elif policy and policy.is_autonomous_enabled:
        agent_status = "AUTONOMOUS_RUNNING"
    else:
        agent_status = "ATTENDED_RUNNING"

    automation_mode = "ATTENDED"
    if policy:
        if policy.is_autonomous_enabled and policy.enable_unattended_email_applications:
            automation_mode = "FULL_AUTOPILOT"
        elif policy.is_autonomous_enabled:
            automation_mode = "SEMI_AUTONOMOUS"

    # 2. Pipeline Counts
    total_vacancies = db.query(JobListing).count()
    new_today = db.query(JobListing).filter(JobListing.date_discovered >= today_start).count()
    verified_open = db.query(JobListing).filter(JobListing.vacancy_status == "VERIFIED_OPEN").count()
    matched_jobs = db.query(JobListing).filter(JobListing.match_score >= (policy.min_match_score if policy else 65)).count()
    closed_vacancies = db.query(JobListing).filter(JobListing.vacancy_status.in_(["CLOSED", "EXPIRED"])).count()

    apps_prepared = db.query(ApplicationRecord).filter(ApplicationRecord.current_status == "APPLICATION_READY").count()
    submitted_statuses = [
        "SUBMITTED", "EMAIL_SENT", "DELIVERY_CONFIRMED", "ACKNOWLEDGEMENT_RECEIVED",
        "RECRUITER_CONTACTED", "INTERVIEW_INVITED", "INTERVIEW_SCHEDULED",
        "TECHNICAL_TEST_RECEIVED", "OFFER_RECEIVED", "OFFER_ACCEPTED", "OFFER_DECLINED"
    ]
    apps_submitted = db.query(ApplicationRecord).filter(ApplicationRecord.current_status.in_(submitted_statuses)).count()
    emails_sent = db.query(ApplicationRecord).filter(ApplicationRecord.submission_method == "email", ApplicationRecord.current_status.in_(submitted_statuses)).count()
    awaiting_responses = db.query(ApplicationRecord).filter(
        ApplicationRecord.current_status.in_(["EMAIL_SENT", "SUBMITTED", "DELIVERY_CONFIRMED"]),
        ApplicationRecord.acknowledgement_received == False,
        ApplicationRecord.interview_invited == False,
        ApplicationRecord.rejection_received == False
    ).count()

    responses_received = db.query(RecruiterResponse).count()
    interviews = max(db.query(Interview).count(), db.query(ApplicationRecord).filter(ApplicationRecord.interview_invited == True).count())
    rejections = db.query(ApplicationRecord).filter(ApplicationRecord.rejection_received == True).count()
    failed_tasks = db.query(ScheduledTask).filter(ScheduledTask.status == "FAILED").count()

    # Prevented duplicates count from audit logs
    duplicate_prevented = db.query(AuditLog).filter(AuditLog.action.ilike("%duplicate%")).count()

    # Integration health summary
    health_rows = db.query(SystemHealth).all()
    health_summary = {h.component: h.status for h in health_rows}

    return DashboardMetricsResponse(
        agent_status=agent_status,
        current_automation_mode=automation_mode,
        worker_is_alive=worker_is_alive,
        worker_last_heartbeat=latest_worker.heartbeat_at if latest_worker else None,
        total_vacancies_discovered=total_vacancies,
        new_vacancies_today=new_today,
        verified_open_vacancies=verified_open,
        matched_jobs=matched_jobs,
        applications_prepared=apps_prepared,
        applications_submitted=apps_submitted,
        email_applications_sent=emails_sent,
        applications_awaiting_responses=awaiting_responses,
        recruiter_responses_received=responses_received,
        interview_invitations=interviews,
        rejections=rejections,
        closed_vacancies=closed_vacancies,
        failed_automation_tasks=failed_tasks,
        duplicate_applications_prevented=duplicate_prevented,
        last_successful_search=policy.last_search_at if policy else None,
        next_scheduled_search=policy.next_search_at if policy else None,
        next_follow_up_due=None,
        integration_health_summary=health_summary
    )

@router.post("/controls/pause-all")
def pause_all_automation(db: Session = Depends(get_db)):
    policy = db.query(AutomationPolicy).filter_by(id=1).first()
    if policy:
        policy.pause_all_automation = True
        db.commit()
        record_audit_log(db, "pause_all_automation", actor="owner")
    return {"status": "SUCCESS", "message": "All automation paused."}

@router.post("/controls/resume-all")
def resume_all_automation(db: Session = Depends(get_db)):
    policy = db.query(AutomationPolicy).filter_by(id=1).first()
    if policy:
        policy.pause_all_automation = False
        policy.pause_applications_only = False
        db.commit()
        record_audit_log(db, "resume_all_automation", actor="owner")
    return {"status": "SUCCESS", "message": "Automation resumed."}

@router.post("/controls/pause-applications")
def pause_applications_only(db: Session = Depends(get_db)):
    policy = db.query(AutomationPolicy).filter_by(id=1).first()
    if policy:
        policy.pause_applications_only = True
        db.commit()
        record_audit_log(db, "pause_applications_only", actor="owner")
    return {"status": "SUCCESS", "message": "Application submissions paused. Discovery and matching remain active."}

@router.post("/controls/toggle-unattended")
def toggle_unattended(enable: bool, db: Session = Depends(get_db)):
    policy = db.query(AutomationPolicy).filter_by(id=1).first()
    if policy:
        policy.enable_unattended_email_applications = enable
        policy.is_autonomous_enabled = enable
        db.commit()
        record_audit_log(db, "toggle_unattended_applications", actor="owner", details={"enabled": enable})
    return {"status": "SUCCESS", "enable_unattended": enable}

@router.post("/controls/toggle-followups")
def toggle_followups(enable: bool, db: Session = Depends(get_db)):
    policy = db.query(AutomationPolicy).filter_by(id=1).first()
    if policy:
        policy.enable_auto_follow_ups = enable
        db.commit()
        record_audit_log(db, "toggle_auto_follow_ups", actor="owner", details={"enabled": enable})
    return {"status": "SUCCESS", "enable_follow_ups": enable}
