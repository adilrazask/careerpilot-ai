from __future__ import annotations
import secrets
import json
import base64
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Header, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.all_models import User, UserSession, utcnow

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

ALL_FEATURES = [
    "dashboard", "voice", "agent", "jobs", "profile", "resumes",
    "contacts", "pipeline", "policy", "integrations", "audit", "admin"
]

def parse_user_agent(ua_string: str) -> str:
    if not ua_string:
        return "Unknown Device"
    ua = ua_string.lower()
    os_name = "Desktop"
    if "macintosh" in ua or "mac os" in ua:
        os_name = "macOS"
    elif "windows" in ua:
        os_name = "Windows"
    elif "android" in ua:
        os_name = "Android"
    elif "iphone" in ua or "ipad" in ua:
        os_name = "iOS"
    elif "linux" in ua:
        os_name = "Linux"

    browser = "Browser"
    if "edg" in ua:
        browser = "Edge"
    elif "chrome" in ua:
        browser = "Chrome"
    elif "firefox" in ua:
        browser = "Firefox"
    elif "safari" in ua:
        browser = "Safari"

    return f"{browser} on {os_name}"

def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"


class GoogleAuthRequest(BaseModel):
    credential: Optional[str] = None
    email: Optional[str] = None
    name: Optional[str] = None
    google_id: Optional[str] = None
    avatar: Optional[str] = None

class LoginRequest(BaseModel):
    email: str
    password: Optional[str] = ""

class RegisterRequest(BaseModel):
    email: str
    full_name: str
    password: Optional[str] = ""

def create_user_session(db: Session, user: User, request: Request, auth_provider: str) -> str:
    token = secrets.token_urlsafe(32)
    user_agent_str = request.headers.get("user-agent", "Unknown")
    device_name = parse_user_agent(user_agent_str)
    client_ip = get_client_ip(request)

    session = UserSession(
        user_id=user.id,
        session_token=token,
        ip_address=client_ip,
        user_agent=user_agent_str[:500],
        device_name=device_name,
        auth_provider=auth_provider,
        is_active=True,
        logged_in_at=utcnow(),
        last_active_at=utcnow()
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return token

def serialize_user(user: User) -> dict:
    allowed = user.allowed_features
    if isinstance(allowed, str):
        try:
            allowed = json.loads(allowed)
        except Exception:
            allowed = [allowed]
    if allowed == ["*"] or "*" in (allowed or []):
        allowed = ALL_FEATURES

    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "avatar_url": user.avatar_url or "/profile_photo.jpg",
        "allowed_features": allowed,
        "is_active": user.is_active
    }

@router.post("/google")
def google_auth(payload: GoogleAuthRequest, request: Request, db: Session = Depends(get_db)):
    email = payload.email
    name = payload.name
    avatar = payload.avatar
    google_id = payload.google_id

    # If Google JWT credential provided, attempt to decode payload claims
    if payload.credential:
        try:
            parts = payload.credential.split(".")
            if len(parts) >= 2:
                # Add padding if missing
                padded = parts[1] + "=" * ((4 - len(parts[1]) % 4) % 4)
                decoded_bytes = base64.urlsafe_b64decode(padded)
                claims = json.loads(decoded_bytes.decode("utf-8"))
                email = claims.get("email", email)
                name = claims.get("name", name)
                avatar = claims.get("picture", avatar)
                google_id = claims.get("sub", google_id)
        except Exception:
            pass

    if not email:
        email = "adilrazask@gmail.com"
        name = "SK Adil Raja"

    # Match user
    user = db.query(User).filter(User.email.ilike(email)).first()
    if not user:
        is_super_admin = (email.lower() == "adilrazask@gmail.com")
        user = User(
            email=email.lower(),
            full_name=name or ("SK Adil Raja" if is_super_admin else email.split("@")[0].title()),
            role="admin" if is_super_admin else "member",
            avatar_url=avatar or "/profile_photo.jpg",
            google_id=google_id,
            allowed_features=["*"] if is_super_admin else ["dashboard", "jobs", "resumes", "contacts"],
            is_active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        # If Adil Raja, ensure admin privileges
        if user.email.lower() == "adilrazask@gmail.com":
            user.role = "admin"
            user.allowed_features = ["*"]
        if avatar and not user.avatar_url:
            user.avatar_url = avatar
        if google_id:
            user.google_id = google_id
        db.commit()
        db.refresh(user)

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")

    token = create_user_session(db, user, request, auth_provider="google")
    return {
        "token": token,
        "user": serialize_user(user)
    }

@router.post("/login")
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()
    user = db.query(User).filter(User.email.ilike(email)).first()

    # If logging in as adilrazask@gmail.com and user doesn't exist yet, create
    if not user and email == "adilrazask@gmail.com":
        user = User(
            email="adilrazask@gmail.com",
            full_name="SK Adil Raja",
            role="admin",
            avatar_url="/profile_photo.jpg",
            allowed_features=["*"],
            is_active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="User account is deactivated")

    # Ensure adil is admin
    if user.email.lower() == "adilrazask@gmail.com":
        user.role = "admin"
        user.allowed_features = ["*"]
        db.commit()

    token = create_user_session(db, user, request, auth_provider="password")
    return {
        "token": token,
        "user": serialize_user(user)
    }

@router.post("/register")
def register(payload: RegisterRequest, request: Request, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()
    existing = db.query(User).filter(User.email.ilike(email)).first()
    if existing:
        raise HTTPException(status_code=400, detail="User with this email already exists")

    is_super_admin = (email == "adilrazask@gmail.com")
    user = User(
        email=email,
        full_name=payload.full_name,
        role="admin" if is_super_admin else "member",
        avatar_url="/profile_photo.jpg",
        allowed_features=["*"] if is_super_admin else ["dashboard", "jobs", "resumes", "contacts"],
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_user_session(db, user, request, auth_provider="password")
    return {
        "token": token,
        "user": serialize_user(user)
    }

@router.get("/me")
def get_me(request: Request, authorization: Optional[str] = Header(None), db: Session = Depends(get_db)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authentication token")

    token = authorization.split("Bearer ")[1].strip()
    session = db.query(UserSession).filter_by(session_token=token).first()

    if not session or not session.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Your session has been terminated by administrator or expired"
        )

    # Update last active timestamp
    session.last_active_at = utcnow()
    db.commit()

    user = session.user
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User account is inactive")

    return {
        "user": serialize_user(user),
        "session_id": session.id,
        "auth_provider": session.auth_provider,
        "logged_in_at": session.logged_in_at.isoformat() if session.logged_in_at else None
    }

@router.post("/logout")
def logout(authorization: Optional[str] = Header(None), db: Session = Depends(get_db)):
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split("Bearer ")[1].strip()
        session = db.query(UserSession).filter_by(session_token=token).first()
        if session:
            session.is_active = False
            session.revoked_at = utcnow()
            db.commit()
    return {"status": "success", "message": "Logged out successfully"}
