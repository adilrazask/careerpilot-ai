"""
Cleanup Service:
1. Sets status CANCELLED_MOCK for all follow_up_tasks whose application has no real sent email
   (provider mock/MOCK or missing message_id_header).
2. Archives or deletes application_records built from is_seed jobs.
"""
from typing import Dict, Any
from sqlalchemy.orm import Session
from app.models import FollowUpTask, ApplicationRecord, EmailMessage, JobListing

def run_mock_and_seed_cleanup(db: Session, delete_seed_apps: bool = False) -> Dict[str, Any]:
    """
    Cleans up mock follow up tasks and seed applications.
    Returns counts before and after.
    """
    # Counts before
    tasks_before_total = db.query(FollowUpTask).count()
    tasks_before_scheduled = db.query(FollowUpTask).filter_by(status='SCHEDULED').count()
    tasks_before_cancelled_mock = db.query(FollowUpTask).filter_by(status='CANCELLED_MOCK').count()

    apps_before_total = db.query(ApplicationRecord).count()
    apps_before_archived = db.query(ApplicationRecord).filter_by(current_status='ARCHIVED_SEED').count()

    # 1. Update follow up tasks
    tasks = db.query(FollowUpTask).all()
    tasks_cancelled_count = 0
    for t in tasks:
        app = t.application
        has_real_sent = False
        if app:
            emails = db.query(EmailMessage).filter_by(application_id=app.id).all()
            for em in emails:
                prov = (em.provider or '').upper()
                stat = (em.status or '').upper()
                if prov not in ['MOCK', 'MOCK_SMTP'] and stat not in ['MOCK_SENT'] and em.message_id_header:
                    has_real_sent = True
                    break
        if not has_real_sent:
            t.status = 'CANCELLED_MOCK'
            t.notes = 'Cancelled: Application has no real sent email (provider mock/MOCK or missing message_id_header).'
            tasks_cancelled_count += 1

    # 2. Archive or delete application records built from is_seed jobs
    apps = db.query(ApplicationRecord).all()
    apps_seed_count = 0
    for a in apps:
        if not a.job or a.job.is_seed:
            if delete_seed_apps:
                db.delete(a)
            else:
                a.current_status = 'ARCHIVED_SEED'
            apps_seed_count += 1

    db.commit()

    # Counts after
    tasks_after_total = db.query(FollowUpTask).count()
    tasks_after_scheduled = db.query(FollowUpTask).filter_by(status='SCHEDULED').count()
    tasks_after_cancelled_mock = db.query(FollowUpTask).filter_by(status='CANCELLED_MOCK').count()

    apps_after_total = db.query(ApplicationRecord).count()
    apps_after_archived = db.query(ApplicationRecord).filter_by(current_status='ARCHIVED_SEED').count()

    return {
        "follow_up_tasks": {
            "before": {
                "total": tasks_before_total,
                "scheduled": tasks_before_scheduled,
                "cancelled_mock": tasks_before_cancelled_mock
            },
            "after": {
                "total": tasks_after_total,
                "scheduled": tasks_after_scheduled,
                "cancelled_mock": tasks_after_cancelled_mock
            },
            "updated_to_cancelled_mock": tasks_cancelled_count
        },
        "applications": {
            "before": {
                "total": apps_before_total,
                "archived_seed": apps_before_archived,
                "active": apps_before_total - apps_before_archived
            },
            "after": {
                "total": apps_after_total,
                "archived_seed": apps_after_archived,
                "active": apps_after_total - apps_after_archived
            },
            "processed_seed_apps": apps_seed_count
        }
    }
