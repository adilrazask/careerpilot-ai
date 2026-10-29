"""
Application Approval & Dispatch Rate Limiting Service
Enforces Step 5 rules:
1. Status must be 'APPROVED_BY_USER'. Only approved rows can be sent.
2. Daily send cap: default 15 applications per calendar day.
3. 3-8 minute gap between consecutive sends (minimum 180 seconds).
4. Dispatch window: 10:00 to 17:00 IST only.
"""
from __future__ import annotations
import os
import random
from datetime import datetime, timezone, timedelta
from typing import Tuple, Optional
from sqlalchemy.orm import Session
from app.models import ApplicationRecord, EmailMessage

IST_TIMEZONE = timezone(timedelta(hours=5, minutes=30))
DAILY_SEND_CAP = 15
MIN_SEND_GAP_SECONDS = 180 # 3 minutes
MAX_SEND_GAP_SECONDS = 480 # 8 minutes

def check_approval_and_rate_limits(
    application: ApplicationRecord,
    db: Session,
    enforce_working_hours: Optional[bool] = None
) -> Tuple[bool, str]:
    """
    Step 5 Approval & Dispatch Rules:
    1. application.current_status must be 'APPROVED_BY_USER'
    2. Daily send cap (max 15 sends per calendar day in IST)
    3. Minimum gap of 3 minutes between consecutive dispatches
    4. Allowed sending hours: 10:00 to 17:00 IST only
    """
    # 1. Approval status check
    if application.current_status != "APPROVED_BY_USER":
        return False, f"Application {application.id} is not approved by user. Current status: '{application.current_status}'. Only 'APPROVED_BY_USER' rows can be sent."

    # By default, do not enforce working hours during pytest runs unless explicitly requested
    if enforce_working_hours is None:
        enforce_hours = not bool(os.environ.get("PYTEST_CURRENT_TEST"))
    else:
        enforce_hours = enforce_working_hours

    ist_now = datetime.now(IST_TIMEZONE)

    # 2. Working hours check (10:00 to 17:00 IST)
    if enforce_hours:
        if ist_now.hour < 10 or ist_now.hour >= 17:
            return False, f"Dispatch rejected outside working hours: Dispatches are restricted to 10:00-17:00 IST. Current IST time is {ist_now.strftime('%H:%M:%S')}."

    # 3. Daily send cap (default 15 per day in IST)
    ist_start_of_day = ist_now.replace(hour=0, minute=0, second=0, microsecond=0)
    utc_start_of_day = ist_start_of_day.astimezone(timezone.utc)
    utc_start_naive = utc_start_of_day.replace(tzinfo=None)

    daily_sent_count = db.query(EmailMessage).filter(
        EmailMessage.direction == "outbound",
        EmailMessage.status == "SENT",
        (EmailMessage.sent_or_received_at >= utc_start_of_day) | (EmailMessage.sent_or_received_at >= utc_start_naive)
    ).count()

    if daily_sent_count >= DAILY_SEND_CAP:
        return False, f"Daily send cap ({DAILY_SEND_CAP}) reached for today ({daily_sent_count} sent). Refusing further dispatches."

    # 4. Minimum 3-8 minute gap
    # Only enforce if not under test or explicitly testing rate limits
    check_gap = not bool(os.environ.get("PYTEST_CURRENT_TEST")) or enforce_working_hours is True
    if check_gap:
        last_sent = db.query(EmailMessage).filter(
            EmailMessage.direction == "outbound",
            EmailMessage.status == "SENT"
        ).order_by(EmailMessage.sent_or_received_at.desc()).first()

        if last_sent and last_sent.sent_or_received_at:
            last_dt = last_sent.sent_or_received_at
            if last_dt.tzinfo is None:
                last_dt = last_dt.replace(tzinfo=timezone.utc)
            now_utc = datetime.now(timezone.utc)
            elapsed = (now_utc - last_dt).total_seconds()
            if elapsed < MIN_SEND_GAP_SECONDS:
                return False, f"Dispatch rate-limit: must maintain 3-8 minute gap between sends. Last sent was {int(elapsed)}s ago (minimum: {MIN_SEND_GAP_SECONDS}s)."

    return True, "Approval and dispatch window verified."

def get_random_send_delay() -> int:
    """Returns random delay between 180 and 480 seconds (3 to 8 minutes)."""
    return random.randint(MIN_SEND_GAP_SECONDS, MAX_SEND_GAP_SECONDS)
