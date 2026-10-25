from __future__ import annotations
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import WorkerRun
from app.services.scheduler import DurableScheduler

router = APIRouter(prefix="/api/worker", tags=["Background Worker"])

@router.get("/status")
def get_worker_status(db: Session = Depends(get_db)):
    workers = db.query(WorkerRun).order_by(WorkerRun.heartbeat_at.desc()).limit(5).all()
    return [
        {
            "id": w.id,
            "worker_id": w.worker_id,
            "hostname": w.hostname,
            "status": w.status,
            "heartbeat_at": w.heartbeat_at,
            "started_at": w.started_at,
            "tasks_processed": w.tasks_processed,
            "current_task": w.current_task
        } for w in workers
    ]

@router.post("/run-cycle")
def run_manual_worker_cycle(db: Session = Depends(get_db)):
    res = DurableScheduler.execute_autonomous_cycle(db)
    return res

@router.post("/dispatch-batch")
def dispatch_batch(max_count: int = 10, force: bool = False, db: Session = Depends(get_db)):
    """One-click execution: dispatches prepared applications up to daily limit (max 10) respecting 10am-6pm IST."""
    return DurableScheduler.dispatch_prepared_batch(db, max_count=max_count, force=force)
