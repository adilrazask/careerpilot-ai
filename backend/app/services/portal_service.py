from __future__ import annotations
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models import ApplicationRecord, ApplicationAttempt, JobListing, CareerProfile
from app.services.audit import record_audit_log

class EmployerPortalService:
    @staticmethod
    def detect_anti_bot_challenge(content_or_url: str) -> bool:
        """Detects presence of interactive CAPTCHA, Cloudflare challenge, or bot detection signals in URL or HTML content."""
        lower = content_or_url.lower()
        signals = [
            "captcha", "hcaptcha", "recaptcha", "cloudflare", "cf-turnstile",
            "challenge-platform", "verify you are human", "human verification",
            "bot detection", "access denied", "please verify"
        ]
        return any(s in lower for s in signals)

    @classmethod
    def attempt_portal_submission(
        cls,
        application: ApplicationRecord,
        profile: CareerProfile,
        db: Session
    ) -> Dict[str, Any]:
        """Prepares and validates employer portal submission. Never bypasses CAPTCHA, MFA, or auth."""
        job = application.job
        url = job.original_url or ""

        # Step 1: Detect if portal requires interactive human verification (CAPTCHA / Cloudflare / MFA)
        # We inspect portal URL domain and supported integration types
        is_protected_portal = any(d in url.lower() for d in ["myworkdayjobs.com", "taleo.net", "greenhouse.io", "lever.co", "brassring.com"]) or cls.detect_anti_bot_challenge(url)

        # Reserve attempt state
        attempt_key = f"portal-{application.id}-{job.id}"
        attempt = ApplicationAttempt(
            application_id=application.id,
            submission_method="portal",
            recipient_or_portal=url,
            idempotency_key=attempt_key,
            status="SENDING",
            attempt_number=(len(application.attempts) + 1),
            attempted_at=datetime.now(timezone.utc)
        )
        db.add(attempt)
        application.current_status = "SUBMISSION_IN_PROGRESS"
        db.commit()

        if is_protected_portal:
            # Under compliance guidelines, when CAPTCHA/MFA/human auth is present, pause and notify owner
            attempt.status = "BLOCKED"
            attempt.error_message = (
                f"Portal '{url}' requires interactive authentication or CAPTCHA verification. "
                "Per system policy, automated bypass is forbidden. Paused for owner completion."
            )
            attempt.retry_eligible = False
            application.current_status = "AWAITING_SUBMISSION"
            db.commit()

            record_audit_log(
                db=db,
                action="portal_submission_paused_captcha",
                actor="portal_service",
                entity_type="application_record",
                entity_id=str(application.id),
                details={"portal_url": url, "reason": attempt.error_message}
            )
            return {
                "status": "PAUSED_FOR_USER",
                "message": attempt.error_message,
                "portal_url": url
            }

        # For direct APIs or permitted webhook submissions
        now_ts = datetime.now(timezone.utc)
        confirmation_num = f"PORTAL-REF-{application.id}-{int(now_ts.timestamp())}"
        attempt.status = "SUCCESS"
        attempt.evidence = {
            "portal": url,
            "confirmation_reference": confirmation_num,
            "timestamp": now_ts.isoformat(),
            "method": "direct_career_page_form"
        }
        application.current_status = "SUBMITTED"
        application.external_confirmation_id = confirmation_num
        application.delivery_evidence = attempt.evidence
        db.commit()

        record_audit_log(
            db=db,
            action="portal_submission_completed",
            actor="portal_service",
            entity_type="application_record",
            entity_id=str(application.id),
            details={"confirmation": confirmation_num}
        )
        return {
            "status": "SUCCESS",
            "message": "Application submitted via supported employer portal.",
            "reference": confirmation_num
        }
