from __future__ import annotations
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.models import AuditLog

def record_audit_log(
    db: Session,
    action: str,
    actor: str = "system",
    entity_type: str = "",
    entity_id: str = "",
    details: Optional[Dict[str, Any]] = None,
    ip_address: str = ""
) -> AuditLog:
    log_entry = AuditLog(
        action=action,
        actor=actor,
        entity_type=entity_type,
        entity_id=str(entity_id),
        details=details or {},
        ip_address=ip_address
    )
    db.add(log_entry)
    db.commit()
    return log_entry
