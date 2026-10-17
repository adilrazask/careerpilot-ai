from __future__ import annotations
from typing import List, Dict, Any
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AuditLog, SystemHealth

router = APIRouter(prefix="/api/audit", tags=["Audit & Activity"])

@router.get("/logs")
def get_audit_logs(limit: int = 150, db: Session = Depends(get_db)):
    logs = db.query(AuditLog).order_by(AuditLog.id.desc()).limit(limit).all()
    return [
        {
            "id": l.id,
            "action": l.action,
            "actor": l.actor,
            "entity_type": l.entity_type,
            "entity_id": l.entity_id,
            "details": l.details,
            "created_at": l.created_at
        } for l in logs
    ]

@router.get("/health")
def get_system_health(db: Session = Depends(get_db)):
    health_items = db.query(SystemHealth).all()
    return [
        {
            "id": h.id,
            "component": h.component,
            "status": h.status,
            "message": h.message,
            "latency_ms": h.latency_ms,
            "checked_at": h.checked_at
        } for h in health_items
    ]
