from __future__ import annotations
import json
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Header, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.all_models import User, UserSession, utcnow

router = APIRouter(prefix="/api/admin", tags=["Admin Operations"])

SYSTEM_FEATURES = [
    {"id": "dashboard", "label": "Command Centre", "category": "Core", "description": "High-level metrics, system health, and autonomous control switches"},
    {"id": "voice", "label": "Voice Control", "category": "Interface", "description": "Speech recognition, voice passphrase authorization, and executive voice commands"},
    {"id": "agent", "label": "AI Agent Workspace", "category": "Core", "description": "Autonomous thought cycles, prompt engineering, and agent history"},
    {"id": "jobs", "label": "Job Discovery & Apollo", "category": "Discovery", "description": "Live multi-portal job aggregation, Tavily discovery, and Apollo.io HR lookup"},
    {"id": "profile", "label": "Career Profile", "category": "Profile", "description": "Candidate work history, verified facts, skills, and resume attachments"},
    {"id": "resumes", "label": "Resume Intelligence", "category": "Intelligence", "description": "Job-specific skills tailoring and truthful resume generation"},
    {"id": "contacts", "label": "HR & Recruiter Contacts", "category": "Outreach", "description": "Apollo.io verified recruiter directory, email deliverability, and executive phone numbers"},
    {"id": "pipeline", "label": "Application Pipeline", "category": "Outreach", "description": "Application history and 15-day multi-cadence automated email scheduling"},
    {"id": "policy", "label": "Autopilot Policies", "category": "Governance", "description": "Autonomy thresholds, rate limits, daily caps, and zero-spam safety guards"},
    {"id": "integrations", "label": "Integrations Market", "category": "Platform", "description": "Live API credentials, Apollo.io key setup, Gmail SMTP/IMAP, and Tavily engine"},
    {"id": "audit", "label": "Audit & Health", "category": "Governance", "description": "System health diagnostics, audit logs, and delivery receipts"},
    {"id": "admin", "label": "Admin Panel", "category": "Governance", "description": "Live session monitoring, termination switch, and role-based feature permissions"}
]

class PermissionsUpdateRequest(BaseModel):
    role: Optional[str] = None
    allowed_features: List[str]

def get_current_admin(authorization: Optional[str] = Header(None), db: Session = Depends(get_db)) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authentication token")

    token = authorization.split("Bearer ")[1].strip()
    session = db.query(UserSession).filter_by(session_token=token).first()

    if not session or not session.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Your session has been terminated or expired"
        )

    user = session.user
    if not user or not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")

    # Only admin or adilrazask@gmail.com
    if user.role != "admin" and user.email.lower() != "adilrazask@gmail.com":
        raise HTTPException(status_code=403, detail="Access denied: Super Admin privileges required")

    return user

@router.get("/features")
def get_features(current_admin: User = Depends(get_current_admin)):
    return SYSTEM_FEATURES

@router.get("/users")
def list_users(current_admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    users = db.query(User).all()
    result = []
    for u in users:
        # Count active sessions
        active_sessions = db.query(UserSession).filter_by(user_id=u.id, is_active=True).count()
        allowed = u.allowed_features
        if isinstance(allowed, str):
            try:
                allowed = json.loads(allowed)
            except Exception:
                allowed = [allowed]
        if allowed == ["*"] or "*" in (allowed or []):
            allowed = [f["id"] for f in SYSTEM_FEATURES]

        result.append({
            "id": u.id,
            "email": u.email,
            "full_name": u.full_name,
            "role": u.role,
            "avatar_url": u.avatar_url or "/profile_photo.jpg",
            "allowed_features": allowed,
            "is_active": u.is_active,
            "active_sessions_count": active_sessions,
            "created_at": u.created_at.isoformat() if u.created_at else None
        })
    return result

@router.put("/users/{user_id}/permissions")
def update_user_permissions(
    user_id: int,
    payload: PermissionsUpdateRequest,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    target_user = db.query(User).filter_by(id=user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Protection for Super Admin: adilrazask@gmail.com cannot have admin stripped
    if target_user.email.lower() == "adilrazask@gmail.com":
        target_user.role = "admin"
        target_user.allowed_features = ["*"]
    else:
        if payload.role:
            target_user.role = payload.role
        target_user.allowed_features = payload.allowed_features

    db.commit()
    db.refresh(target_user)

    allowed = target_user.allowed_features
    if allowed == ["*"] or "*" in (allowed or []):
        allowed = [f["id"] for f in SYSTEM_FEATURES]

    return {
        "id": target_user.id,
        "email": target_user.email,
        "full_name": target_user.full_name,
        "role": target_user.role,
        "allowed_features": allowed,
        "message": f"Updated permissions for {target_user.full_name}"
    }

@router.get("/sessions")
def list_sessions(
    authorization: Optional[str] = Header(None),
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    current_token = authorization.split("Bearer ")[1].strip() if authorization and "Bearer " in authorization else ""
    sessions = db.query(UserSession).order_by(UserSession.last_active_at.desc()).limit(100).all()

    result = []
    for s in sessions:
        user = s.user
        result.append({
            "id": s.id,
            "user_id": s.user_id,
            "user_email": user.email if user else "Unknown",
            "user_name": user.full_name if user else "Unknown",
            "user_role": user.role if user else "member",
            "avatar_url": (user.avatar_url if user and user.avatar_url else "/profile_photo.jpg"),
            "ip_address": s.ip_address,
            "device_name": s.device_name,
            "user_agent": s.user_agent,
            "auth_provider": s.auth_provider,
            "is_active": s.is_active,
            "logged_in_at": s.logged_in_at.isoformat() if s.logged_in_at else None,
            "last_active_at": s.last_active_at.isoformat() if s.last_active_at else None,
            "revoked_at": s.revoked_at.isoformat() if s.revoked_at else None,
            "is_current": (s.session_token == current_token)
        })
    return result

@router.post("/sessions/{session_id}/terminate")
def terminate_session(
    session_id: int,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    session = db.query(UserSession).filter_by(id=session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session.is_active = False
    session.revoked_at = utcnow()
    db.commit()

    return {
        "status": "success",
        "message": f"Session #{session_id} for {session.user.full_name if session.user else 'User'} terminated immediately.",
        "session_id": session_id
    }

@router.post("/users/{user_id}/terminate-all")
def terminate_all_user_sessions(
    user_id: int,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    sessions = db.query(UserSession).filter_by(user_id=user_id, is_active=True).all()
    count = 0
    now = utcnow()
    for s in sessions:
        s.is_active = False
        s.revoked_at = now
        count += 1
    db.commit()

    return {
        "status": "success",
        "message": f"Terminated {count} active session(s) for user ID {user_id}.",
        "terminated_count": count
    }
