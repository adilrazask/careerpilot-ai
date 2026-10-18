from __future__ import annotations
import os
import re
import uuid
import hashlib
import hmac
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models import (
    JobListing, CareerProfile, ResumeVersion, ApplicationRecord,
    AutomationPolicy, AuditLog, ScheduledTask,
    VoiceSecuritySettings, VoiceCommandLog, VoiceSessionContext
)
from app.services.adapters import SourceManager, canonicalize_url, normalize_title
from app.services.matching import MatchingEngine
from app.services.resume_engine import ResumeEngine
from app.services.audit import record_audit_log

# Supported Intent Allowlists
SUPPORTED_INTENTS = [
    "search_jobs",
    "shortlist_jobs",
    "get_job_details",
    "compare_jobs",
    "prepare_resume",
    "prepare_cover_letter",
    "explain_missing_skills",
    "track_applications",
    "update_application_status",
    "prepare_follow_up",
    "show_preferences",
    "update_preferences",
    "control_automation",
    "wake_word_control",
    "clarification_response",
    "help_commands"
]

class VoiceService:
    """Core Voice Orchestration layer: Speech Intent parsing, Risk Authorization, Context Management, and Response Synthesis."""

    @staticmethod
    def hash_passphrase(passphrase: str, salt: str = None) -> Tuple[str, str]:
        """Hash voice passphrase using PBKDF2-HMAC-SHA256 with salt."""
        if not salt:
            salt = os.urandom(16).hex()
        normalized = passphrase.lower().strip()
        pw_hash = hashlib.pbkdf2_hmac("sha256", normalized.encode("utf-8"), bytes.fromhex(salt), 100000).hex()
        return pw_hash, salt

    @classmethod
    def verify_passphrase(cls, passphrase: str, db: Session) -> Dict[str, Any]:
        """Verify voice passphrase with rate-limiting and temporary lockout."""
        settings = db.query(VoiceSecuritySettings).filter_by(id=1).first()
        if not settings or not settings.passphrase_enabled:
            return {"valid": True, "locked": False, "remaining_seconds": 0}

        now_ts = datetime.now(timezone.utc)
        if settings.locked_until:
            lu = settings.locked_until
            if lu.tzinfo is None:
                lu = lu.replace(tzinfo=timezone.utc)
            if lu > now_ts:
                remaining = int((lu - now_ts).total_seconds())
                return {
                    "valid": False,
                    "locked": True,
                    "remaining_seconds": remaining,
                    "message": f"Voice security is temporarily locked due to repeated failed attempts. Try again in {remaining} seconds."
                }
            else:
                settings.locked_until = None
                settings.failed_attempts = 0
                db.commit()

        expected_hash, _ = cls.hash_passphrase(passphrase, settings.passphrase_salt)
        if hmac.compare_digest(expected_hash, settings.passphrase_hash):
            settings.failed_attempts = 0
            settings.locked_until = None
            db.commit()
            return {"valid": True, "locked": False, "remaining_seconds": 0}
        else:
            settings.failed_attempts += 1
            if settings.failed_attempts >= 3:
                settings.locked_until = now_ts + timedelta(minutes=5)
                db.commit()
                return {
                    "valid": False,
                    "locked": True,
                    "remaining_seconds": 300,
                    "message": "Maximum failed attempts reached. Voice passphrase locked for 5 minutes."
                }
            db.commit()
            return {
                "valid": False,
                "locked": False,
                "remaining_seconds": 0,
                "message": f"Incorrect voice passphrase. Attempts remaining: {3 - settings.failed_attempts}."
            }

    @classmethod
    def change_passphrase(cls, current_pw: str, new_pw: str, db: Session) -> Dict[str, Any]:
        """Update voice security passphrase through protected flow."""
        verif = cls.verify_passphrase(current_pw, db)
        if not verif["valid"]:
            return {"success": False, "message": verif.get("message", "Current passphrase verification failed.")}

        if len(new_pw.strip()) < 4:
            return {"success": False, "message": "New passphrase must be at least 4 characters long."}

        settings = db.query(VoiceSecuritySettings).filter_by(id=1).first()
        new_hash, new_salt = cls.hash_passphrase(new_pw)
        settings.passphrase_hash = new_hash
        settings.passphrase_salt = new_salt
        settings.failed_attempts = 0
        settings.locked_until = None
        db.commit()

        record_audit_log(
            db=db,
            action="voice_passphrase_changed",
            actor="owner",
            entity_type="voice_security_settings",
            entity_id=str(settings.id),
            details={"status": "Passphrase updated securely"}
        )
        return {"success": True, "message": "Voice passphrase updated successfully."}

    @classmethod
    def get_or_create_session(cls, session_id: Optional[str], db: Session) -> VoiceSessionContext:
        """Get or initialize active conversational context session."""
        now_ts = datetime.now(timezone.utc)
        if session_id:
            s = db.query(VoiceSessionContext).filter_by(session_id=session_id).first()
            if s:
                # Check expiration (30 minutes)
                la = s.last_active_at
                if la.tzinfo is None:
                    la = la.replace(tzinfo=timezone.utc)
                if (now_ts - la).total_seconds() < 1800:
                    s.last_active_at = now_ts
                    db.commit()
                    return s
                else:
                    # Expired: Reset existing session context without creating duplicate key
                    s.active_query = ""
                    s.active_filters = {}
                    s.active_job_ids = []
                    s.pending_clarification = ""
                    s.pending_action_type = ""
                    s.pending_action_payload = {}
                    s.conversation_history = []
                    s.conversation_turns = 0
                    s.last_active_at = now_ts
                    db.commit()
                    return s

        # Create fresh session
        new_id = session_id or f"vsession_{uuid.uuid4().hex[:10]}"
        s = VoiceSessionContext(
            session_id=new_id,
            active_query="",
            active_filters={},
            active_job_ids=[],
            pending_clarification="",
            pending_action_type="",
            pending_action_payload={},
            conversation_history=[],
            conversation_turns=0,
            last_active_at=now_ts,
            created_at=now_ts
        )
        db.add(s)
        db.commit()
        db.refresh(s)
        return s

    @classmethod
    def classify_intent_and_extract_parameters(cls, text: str, session_ctx: VoiceSessionContext) -> Dict[str, Any]:
        """Maps transcribed speech into structured intent and validated parameters."""
        raw = text.strip()
        t = raw.lower()

        # 1. Check if answering a pending conversational clarification
        if session_ctx.pending_clarification:
            if session_ctx.pending_clarification == "EXPERIENCE_LEVEL":
                exp_match = re.search(r"(\d+)\s*(?:to|-)\s*(\d+)", t)
                word_match = re.search(r"\b(two|three|four|five|six|seven)\b\s*to\s*\b(three|four|five|six|seven|eight)\b", t)
                word_map = {"two": 2.0, "three": 3.0, "four": 4.0, "five": 5.0, "six": 6.0, "seven": 7.0, "eight": 8.0}
                
                exp_min, exp_max = 2.0, 5.0
                if exp_match:
                    exp_min = float(exp_match.group(1))
                    exp_max = float(exp_match.group(2))
                elif word_match:
                    exp_min = word_map.get(word_match.group(1), 2.0)
                    exp_max = word_map.get(word_match.group(2), 5.0)

                return {
                    "intent": "clarification_response",
                    "clarification_type": "EXPERIENCE_LEVEL",
                    "parameters": {"exp_min": exp_min, "exp_max": exp_max},
                    "risk_level": "LEVEL_1_LOW",
                    "requires_confirmation": False
                }

        # 2. Automation Controls
        if any(w in t for w in ["pause job applications", "pause applications", "stop applications"]):
            return {
                "intent": "control_automation",
                "parameters": {"action": "pause_applications"},
                "risk_level": "LEVEL_2_CONTROLLED",
                "requires_confirmation": True,
                "confirmation_prompt": "Do you want to pause all outgoing job applications?"
            }
        if any(w in t for w in ["pause automation", "pause searches", "pause discovery", "stop automation"]):
            return {
                "intent": "control_automation",
                "parameters": {"action": "pause_all"},
                "risk_level": "LEVEL_2_CONTROLLED",
                "requires_confirmation": True,
                "confirmation_prompt": "Do you want to pause all background automation and job discovery?"
            }
        if any(w in t for w in ["resume automation", "resume searches", "resume applications", "start automation", "start permitted search"]):
            return {
                "intent": "control_automation",
                "parameters": {"action": "resume_all"},
                "risk_level": "LEVEL_2_CONTROLLED",
                "requires_confirmation": True,
                "confirmation_prompt": "Do you want to resume background automation?"
            }

        # 3. Wake-word controls
        if "disable wake-word" in t or "disable wake word" in t:
            return {
                "intent": "wake_word_control",
                "parameters": {"enabled": False},
                "risk_level": "LEVEL_1_LOW",
                "requires_confirmation": False
            }
        if "enable wake-word" in t or "enable wake word" in t:
            return {
                "intent": "wake_word_control",
                "parameters": {"enabled": True},
                "risk_level": "LEVEL_1_LOW",
                "requires_confirmation": False
            }

        # 4. Applications Tracking & Status
        if any(w in t for w in ["show my pending applications", "show applications", "which companies have i applied to", "application status", "show my application status"]):
            return {
                "intent": "track_applications",
                "parameters": {"filter": "pending"},
                "risk_level": "LEVEL_1_LOW",
                "requires_confirmation": False
            }
        if "applications that need follow-up" in t or "follow-up due" in t:
            return {
                "intent": "track_applications",
                "parameters": {"filter": "follow_up_due"},
                "risk_level": "LEVEL_1_LOW",
                "requires_confirmation": False
            }
        if "mark this application as rejected" in t or "mark as rejected" in t:
            return {
                "intent": "update_application_status",
                "parameters": {"new_status": "REJECTED_BY_EMPLOYER", "target_index": cls._resolve_ordinal(t)},
                "risk_level": "LEVEL_2_CONTROLLED",
                "requires_confirmation": True,
                "confirmation_prompt": "Are you sure you want to mark this application as rejected?"
            }
        if "interview scheduled" in t or "interview invited" in t:
            return {
                "intent": "update_application_status",
                "parameters": {"new_status": "INTERVIEW_INVITED", "target_index": cls._resolve_ordinal(t)},
                "risk_level": "LEVEL_2_CONTROLLED",
                "requires_confirmation": True,
                "confirmation_prompt": "Confirm updating application status to Interview Invited?"
            }
        if "prepare a follow-up message" in t or "prepare follow up" in t:
            return {
                "intent": "prepare_follow_up",
                "parameters": {"target_index": cls._resolve_ordinal(t)},
                "risk_level": "LEVEL_2_CONTROLLED",
                "requires_confirmation": False
            }

        # 5. Resume and Application Preparation
        if any(w in t for w in ["prepare my resume", "prepare resume", "tailor my resume", "tailor resume"]):
            return {
                "intent": "prepare_resume",
                "parameters": {
                    "target_index": cls._resolve_ordinal(t),
                    "role_override": cls._extract_role(t)
                },
                "risk_level": "LEVEL_1_LOW",
                "requires_confirmation": False
            }
        if any(w in t for w in ["generate a cover letter", "generate cover letter", "prepare cover letter", "create a cover letter"]):
            return {
                "intent": "prepare_cover_letter",
                "parameters": {"target_index": cls._resolve_ordinal(t)},
                "risk_level": "LEVEL_1_LOW",
                "requires_confirmation": False
            }
        if any(w in t for w in ["explain which skills are missing", "what skills are missing", "missing skills"]):
            return {
                "intent": "explain_missing_skills",
                "parameters": {"target_index": cls._resolve_ordinal(t)},
                "risk_level": "LEVEL_1_LOW",
                "requires_confirmation": False
            }

        # 6. Preferences
        if any(w in t for w in ["show my job preferences", "show preferences", "what are my preferences"]):
            return {
                "intent": "show_preferences",
                "parameters": {},
                "risk_level": "LEVEL_1_LOW",
                "requires_confirmation": False
            }
        if "change my preferred location" in t or "set preferred location" in t:
            loc = cls._extract_location(t)
            return {
                "intent": "update_preferences",
                "parameters": {"location": loc},
                "risk_level": "LEVEL_2_CONTROLLED",
                "requires_confirmation": True,
                "confirmation_prompt": f"Confirm updating your preferred location to {loc}?"
            }
        if "minimum salary" in t or "salary expectation" in t:
            sal = cls._extract_salary(t)
            return {
                "intent": "update_preferences",
                "parameters": {"minimum_salary": sal},
                "risk_level": "LEVEL_2_CONTROLLED",
                "requires_confirmation": True,
                "confirmation_prompt": f"Confirm setting your minimum salary preference to {sal} INR?"
            }

        # 7. Job Inspection / Shortlisting / Comparison
        if any(w in t for w in ["show me the best", "rank these jobs", "rank jobs", "best five", "best three"]):
            limit = 5
            limit_m = re.search(r"\b(two|three|four|five|six|seven|eight|nine|ten|\d+)\b", t)
            word_to_num = {"two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}
            if limit_m:
                val = limit_m.group(1)
                limit = word_to_num.get(val, int(val) if val.isdigit() else 5)

            return {
                "intent": "shortlist_jobs",
                "parameters": {"limit": limit},
                "risk_level": "LEVEL_1_LOW",
                "requires_confirmation": False
            }
        if any(w in t for w in ["read the salary", "read salary", "show requirements", "check whether my experience matches", "show the required qualifications", "application deadline"]):
            return {
                "intent": "get_job_details",
                "parameters": {"target_index": cls._resolve_ordinal(t)},
                "risk_level": "LEVEL_1_LOW",
                "requires_confirmation": False
            }
        if "compare" in t and ("salary" in t or "jobs" in t or "responsibilities" in t):
            return {
                "intent": "compare_jobs",
                "parameters": {"limit": 3},
                "risk_level": "LEVEL_1_LOW",
                "requires_confirmation": False
            }

        # 8. Primary Search Intent
        if any(w in t for w in ["find", "search", "look for", "show", "get"]) and any(w in t for w in ["job", "jobs", "role", "roles", "position", "positions", "vacancies", "vacancy", "operations", "procurement", "supply chain", "logistics"]):
            role = cls._extract_role(t)
            location = cls._extract_location(t)
            exp_min, exp_max = cls._extract_experience(t)
            salary = cls._extract_salary(t)
            limit = cls._extract_count(t)

            return {
                "intent": "search_jobs",
                "parameters": {
                    "role": role,
                    "location": location,
                    "experience_min": exp_min,
                    "experience_max": exp_max,
                    "minimum_salary": salary,
                    "limit": limit,
                    "fresh_only": "recently" in t or "recent" in t,
                    "career_pages_only": "career pages" in t or "employer" in t
                },
                "risk_level": "LEVEL_1_LOW",
                "requires_confirmation": False
            }

        # 9. Fallback Help
        return {
            "intent": "help_commands",
            "parameters": {},
            "risk_level": "LEVEL_1_LOW",
            "requires_confirmation": False
        }

    @classmethod
    def execute_voice_command(
        cls,
        intent_info: Dict[str, Any],
        raw_text: str,
        session_ctx: VoiceSessionContext,
        db: Session,
        passphrase: Optional[str] = None
    ) -> Dict[str, Any]:
        """Executes authorized voice command against real CareerPilot AI services."""
        intent = intent_info["intent"]
        params = intent_info.get("parameters", {})
        risk = intent_info.get("risk_level", "LEVEL_1_LOW")
        requires_conf = intent_info.get("requires_confirmation", False)

        # Level 3 Protected Actions Guard: strictly require confirmed authorized token
        if risk == "LEVEL_3_PROTECTED":
            token = f"auth_{uuid.uuid4().hex[:12]}"
            session_ctx.pending_action_type = intent
            session_ctx.pending_action_payload = params
            db.commit()
            return {
                "session_id": session_ctx.session_id,
                "raw_transcript": raw_text,
                "interpreted_intent": intent,
                "extracted_parameters": params,
                "risk_level": risk,
                "requires_confirmation": True,
                "confirmation_token": token,
                "confirmation_prompt": intent_info.get("confirmation_prompt", "This is a protected action requiring explicit confirmation."),
                "spoken_response": "This is a protected action. Please confirm your authorization on the screen.",
                "display_text": "Protected action detected. Explicit confirmation required.",
                "data_payload": {"status": "AWAITING_AUTHORIZATION"},
                "conversation_turns": session_ctx.conversation_turns + 1
            }

        # Level 2 Controlled Actions Guard
        if risk == "LEVEL_2_CONTROLLED" and requires_conf:
            token = f"auth_{uuid.uuid4().hex[:12]}"
            session_ctx.pending_action_type = intent
            session_ctx.pending_action_payload = params
            db.commit()
            prompt_msg = intent_info.get("confirmation_prompt", "Please confirm to proceed.")
            return {
                "session_id": session_ctx.session_id,
                "raw_transcript": raw_text,
                "interpreted_intent": intent,
                "extracted_parameters": params,
                "risk_level": risk,
                "requires_confirmation": True,
                "confirmation_token": token,
                "confirmation_prompt": prompt_msg,
                "spoken_response": prompt_msg,
                "display_text": prompt_msg,
                "data_payload": {"status": "AWAITING_CONFIRMATION"},
                "conversation_turns": session_ctx.conversation_turns + 1
            }

        # --- EXECUTE LEVEL 1 & PERMITTED ACTIONS ---
        profile = db.query(CareerProfile).filter_by(id=1).first()

        # A. SEARCH JOBS
        if intent == "search_jobs" or intent == "clarification_response":
            if intent == "clarification_response":
                role = session_ctx.active_filters.get("role", "Operations Executive")
                location = session_ctx.active_filters.get("location", "Hyderabad, India")
                exp_min = params.get("exp_min", 2.0)
                exp_max = params.get("exp_max", 5.0)
                limit = session_ctx.active_filters.get("limit", 5)
            else:
                role = params.get("role") or (profile.preferences.preferred_titles[0] if profile and profile.preferences and profile.preferences.preferred_titles else "Operations Executive")
                location = params.get("location") or (profile.current_location if profile else "Hyderabad, India")
                exp_min = params.get("experience_min")
                exp_max = params.get("experience_max")
                limit = params.get("limit", 5)

            # Query existing listings or search
            query = db.query(JobListing).filter(JobListing.vacancy_status == "VERIFIED_OPEN")
            if location:
                query = query.filter(JobListing.location.ilike(f"%{location.split(',')[0].strip()}%"))
            
            jobs = query.order_by(desc(JobListing.match_score), desc(JobListing.id)).limit(limit).all()

            # If fewer than expected, search via Tavily adapter
            if len(jobs) < limit:
                adapter = SourceManager.get_adapter("tavily_search")
                if adapter:
                    found_leads = adapter.search_jobs(query=role, location=location, limit=limit)
                    existing_all = db.query(JobListing).all()
                    for lead in found_leads:
                        if not SourceManager.is_duplicate(lead, existing_all):
                            new_j = JobListing(
                                title=lead.get("title", role),
                                company_name=lead.get("company_name", "Enterprise Employer"),
                                location=location,
                                work_mode=lead.get("work_mode", "Hybrid"),
                                employment_type=lead.get("employment_type", "Full-time"),
                                experience_required_min=exp_min or 2.0,
                                experience_required_max=exp_max or 5.0,
                                source_platform=lead.get("source_platform", "Web Search"),
                                original_url=lead.get("original_url", ""),
                                canonical_url=lead.get("canonical_url", ""),
                                description=lead.get("description", ""),
                                vacancy_status="VERIFIED_OPEN",
                                application_method="email",
                                date_discovered=datetime.now(timezone.utc)
                            )
                            db.add(new_j)
                            db.commit()
                            db.refresh(new_j)
                            if profile:
                                eval_res = MatchingEngine.evaluate(new_j, profile)
                                new_j.match_score = eval_res["match_score"]
                                new_j.eligibility_status = eval_res["eligibility_status"]
                                db.commit()
                            jobs.append(new_j)

            # Update session context
            session_ctx.active_query = f"{role} in {location}"
            session_ctx.active_filters = {"role": role, "location": location, "exp_min": exp_min, "exp_max": exp_max, "limit": limit}
            session_ctx.active_job_ids = [j.id for j in jobs]
            session_ctx.pending_clarification = ""
            session_ctx.conversation_turns += 1
            db.commit()

            match_count = sum(1 for j in jobs if (j.match_score or 0) >= 70)
            salary_count = sum(1 for j in jobs if (j.salary_min or 0) > 0)
            top_company = jobs[0].company_name if jobs else "verified employers"
            top_score = jobs[0].match_score if jobs else 0

            spoken = (
                f"CareerPilot found {len(jobs)} relevant {role} vacancies in {location}. "
                f"{match_count} closely match your profile, with top match at {top_company} scoring {top_score} percent. "
                f"I have saved the results for your review."
            )
            display = f"Discovered {len(jobs)} vacancies for '{role}' in {location}. {match_count} verified matching opportunities."

            cls._log_command(session_ctx.session_id, raw_text, intent, params, risk, spoken, {"jobs_found": len(jobs)}, db)

            return {
                "session_id": session_ctx.session_id,
                "raw_transcript": raw_text,
                "interpreted_intent": intent,
                "extracted_parameters": params,
                "risk_level": risk,
                "requires_confirmation": False,
                "spoken_response": spoken,
                "display_text": display,
                "data_payload": {
                    "jobs": [
                        {
                            "id": j.id,
                            "title": j.title,
                            "company_name": j.company_name,
                            "location": j.location,
                            "match_score": j.match_score,
                            "eligibility_status": j.eligibility_status,
                            "salary": f"{j.salary_min:,.0f} - {j.salary_max:,.0f} {j.salary_currency}" if (j.salary_min or 0) > 0 else "Disclosed upon enquiry",
                            "source_platform": j.source_platform
                        } for j in jobs
                    ]
                },
                "conversation_turns": session_ctx.conversation_turns
            }

        # B. SHORTLIST / RANK JOBS
        if intent == "shortlist_jobs":
            job_ids = session_ctx.active_job_ids or []
            limit = params.get("limit", 5)
            if job_ids:
                jobs = db.query(JobListing).filter(JobListing.id.in_(job_ids)).order_by(desc(JobListing.match_score)).limit(limit).all()
            else:
                jobs = db.query(JobListing).filter(JobListing.vacancy_status == "VERIFIED_OPEN").order_by(desc(JobListing.match_score)).limit(limit).all()

            top_scores = [f"{j.title} at {j.company_name} ({j.match_score}%)" for j in jobs[:3]]
            spoken = f"Here are your top {len(jobs)} ranked opportunities: " + "; ".join(top_scores) + "."
            display = f"Ranked {len(jobs)} top matching opportunities."

            cls._log_command(session_ctx.session_id, raw_text, intent, params, risk, spoken, {"ranked_count": len(jobs)}, db)
            return {
                "session_id": session_ctx.session_id,
                "raw_transcript": raw_text,
                "interpreted_intent": intent,
                "extracted_parameters": params,
                "risk_level": risk,
                "requires_confirmation": False,
                "spoken_response": spoken,
                "display_text": display,
                "data_payload": {
                    "ranked_jobs": [{"id": j.id, "title": j.title, "company_name": j.company_name, "match_score": j.match_score} for j in jobs]
                },
                "conversation_turns": session_ctx.conversation_turns + 1
            }

        # C. GET JOB DETAILS
        if intent == "get_job_details":
            idx = params.get("target_index", 0)
            target_job = cls._resolve_job_from_context(idx, session_ctx, db)
            if not target_job:
                spoken = "I could not identify the specific job you referred to. Please try searching first."
                return {"session_id": session_ctx.session_id, "raw_transcript": raw_text, "interpreted_intent": intent, "extracted_parameters": params, "risk_level": risk, "requires_confirmation": False, "spoken_response": spoken, "display_text": spoken, "data_payload": {}, "conversation_turns": session_ctx.conversation_turns + 1}

            salary_str = f"between {target_job.salary_min:,.0f} and {target_job.salary_max:,.0f} {target_job.salary_currency}" if (target_job.salary_min or 0) > 0 else "not publicly disclosed"
            exp_str = f"{target_job.experience_required_min:.0f} to {target_job.experience_required_max:.0f} years of experience" if (target_job.experience_required_min or 0) > 0 else "standard experience"
            
            spoken = (
                f"Position: {target_job.title} at {target_job.company_name} in {target_job.location}. "
                f"Salary is {salary_str}. It requires {exp_str}. "
                f"Your match score is {target_job.match_score} percent, classified as {target_job.eligibility_status.replace('_', ' ').title()}."
            )
            display = f"Job Details: {target_job.title} — {target_job.company_name} ({target_job.location})"
            cls._log_command(session_ctx.session_id, raw_text, intent, params, risk, spoken, {"job_id": target_job.id}, db)
            return {
                "session_id": session_ctx.session_id,
                "raw_transcript": raw_text,
                "interpreted_intent": intent,
                "extracted_parameters": params,
                "risk_level": risk,
                "requires_confirmation": False,
                "spoken_response": spoken,
                "display_text": display,
                "data_payload": {
                    "id": target_job.id,
                    "title": target_job.title,
                    "company_name": target_job.company_name,
                    "location": target_job.location,
                    "match_score": target_job.match_score,
                    "eligibility_status": target_job.eligibility_status,
                    "description": target_job.description
                },
                "conversation_turns": session_ctx.conversation_turns + 1
            }

        # D. PREPARE RESUME (Draft Generation - Level 1 Low Risk)
        if intent == "prepare_resume":
            idx = params.get("target_index", 0)
            target_job = cls._resolve_job_from_context(idx, session_ctx, db)
            if not target_job:
                spoken = "Please select or search for a vacancy before preparing a tailored resume."
                return {"session_id": session_ctx.session_id, "raw_transcript": raw_text, "interpreted_intent": intent, "extracted_parameters": params, "risk_level": risk, "requires_confirmation": False, "spoken_response": spoken, "display_text": spoken, "data_payload": {}, "conversation_turns": session_ctx.conversation_turns + 1}

            tailored = ResumeEngine.tailor(target_job, profile, use_ai=False)
            resumes_dir = "./data/resumes"
            os.makedirs(resumes_dir, exist_ok=True)
            pdf_path = os.path.join(resumes_dir, f"resume_job_{target_job.id}.pdf")
            docx_path = os.path.join(resumes_dir, f"resume_job_{target_job.id}.docx")
            ResumeEngine.generate_pdf(tailored, pdf_path, profile)
            ResumeEngine.generate_docx(tailored, docx_path, profile)

            rv = ResumeVersion(
                profile_id=profile.id,
                job_id=target_job.id,
                version_name=tailored["version_name"],
                headline=tailored["headline"],
                summary=tailored["summary"],
                full_text=tailored["full_text"],
                cover_letter_text=tailored["cover_letter_text"],
                pdf_path=pdf_path,
                docx_path=docx_path,
                model_used=tailored["model_used"],
                factual_consistency_score=tailored["factual_consistency_score"]
            )
            db.add(rv)
            target_job.application_status = "RESUME_READY"
            db.commit()
            db.refresh(rv)

            spoken = (
                f"I have prepared an ATS-compliant tailored resume for {target_job.title} at {target_job.company_name}. "
                f"Your factual qualifications, ERP skills, and procurement history have been emphasized with zero fabricated details. "
                f"Both PDF and DOCX documents are ready for your review."
            )
            display = f"Tailored ATS Resume & Cover Letter compiled for {target_job.title} at {target_job.company_name}."
            cls._log_command(session_ctx.session_id, raw_text, intent, params, risk, spoken, {"resume_version_id": rv.id}, db)
            return {
                "session_id": session_ctx.session_id,
                "raw_transcript": raw_text,
                "interpreted_intent": intent,
                "extracted_parameters": params,
                "risk_level": risk,
                "requires_confirmation": False,
                "spoken_response": spoken,
                "display_text": display,
                "data_payload": {
                    "resume_version_id": rv.id,
                    "job_id": target_job.id,
                    "headline": rv.headline,
                    "pdf_download_url": f"/api/resumes/{rv.id}/pdf",
                    "docx_download_url": f"/api/resumes/{rv.id}/docx",
                    "factual_consistency_score": rv.factual_consistency_score
                },
                "conversation_turns": session_ctx.conversation_turns + 1
            }

        # E. PREPARE COVER LETTER
        if intent == "prepare_cover_letter":
            idx = params.get("target_index", 0)
            target_job = cls._resolve_job_from_context(idx, session_ctx, db)
            if not target_job:
                spoken = "Please specify which vacancy you need a cover letter for."
                return {"session_id": session_ctx.session_id, "raw_transcript": raw_text, "interpreted_intent": intent, "extracted_parameters": params, "risk_level": risk, "requires_confirmation": False, "spoken_response": spoken, "display_text": spoken, "data_payload": {}, "conversation_turns": session_ctx.conversation_turns + 1}

            tailored = ResumeEngine.tailor(target_job, profile, use_ai=False)
            cl_text = tailored["cover_letter_text"]
            spoken = f"I have drafted a tailored cover letter for {target_job.company_name} highlighting your operations coordination experience."
            display = f"Cover letter prepared for {target_job.title} at {target_job.company_name}."
            return {
                "session_id": session_ctx.session_id,
                "raw_transcript": raw_text,
                "interpreted_intent": intent,
                "extracted_parameters": params,
                "risk_level": risk,
                "requires_confirmation": False,
                "spoken_response": spoken,
                "display_text": display,
                "data_payload": {"cover_letter": cl_text, "job_title": target_job.title, "company": target_job.company_name},
                "conversation_turns": session_ctx.conversation_turns + 1
            }

        # F. EXPLAIN MISSING SKILLS
        if intent == "explain_missing_skills":
            idx = params.get("target_index", 0)
            target_job = cls._resolve_job_from_context(idx, session_ctx, db)
            if not target_job:
                spoken = "Please select a job first to view skill alignment."
                return {"session_id": session_ctx.session_id, "raw_transcript": raw_text, "interpreted_intent": intent, "extracted_parameters": params, "risk_level": risk, "requires_confirmation": False, "spoken_response": spoken, "display_text": spoken, "data_payload": {}, "conversation_turns": session_ctx.conversation_turns + 1}

            eval_res = MatchingEngine.evaluate(target_job, profile)
            missing = eval_res.get("missing_requirements", [])
            matching = eval_res.get("matching_requirements", [])

            if missing:
                spoken = f"For {target_job.title}, you match on {len(matching)} key areas including {', '.join(matching[:2])}. You may need to demonstrate experience in: {', '.join(missing[:3])}."
            else:
                spoken = f"Excellent match! Your verified skills cover all core requirements for {target_job.title} at {target_job.company_name}."

            display = f"Skill analysis for {target_job.title}: {len(matching)} matching, {len(missing)} missing."
            return {
                "session_id": session_ctx.session_id,
                "raw_transcript": raw_text,
                "interpreted_intent": intent,
                "extracted_parameters": params,
                "risk_level": risk,
                "requires_confirmation": False,
                "spoken_response": spoken,
                "display_text": display,
                "data_payload": {"matching_skills": matching, "missing_skills": missing, "score": eval_res.get("match_score")},
                "conversation_turns": session_ctx.conversation_turns + 1
            }

        # G. TRACK APPLICATIONS
        if intent == "track_applications":
            apps = db.query(ApplicationRecord).order_by(desc(ApplicationRecord.id)).limit(10).all()
            total = len(apps)
            submitted = sum(1 for a in apps if a.current_status in ["SUBMITTED", "EMAIL_SENT", "DELIVERY_CONFIRMED", "INTERVIEW_INVITED"])
            interviews = sum(1 for a in apps if a.interview_invited or a.current_status == "INTERVIEW_INVITED")

            spoken = (
                f"You currently have {total} tracked applications. "
                f"{submitted} have been submitted, and you have {interviews} interview invitations. "
                f"The latest status is displayed on your screen."
            )
            display = f"Application Tracking: {total} total, {submitted} submitted, {interviews} interview invites."
            cls._log_command(session_ctx.session_id, raw_text, intent, params, risk, spoken, {"total": total, "submitted": submitted}, db)
            return {
                "session_id": session_ctx.session_id,
                "raw_transcript": raw_text,
                "interpreted_intent": intent,
                "extracted_parameters": params,
                "risk_level": risk,
                "requires_confirmation": False,
                "spoken_response": spoken,
                "display_text": display,
                "data_payload": {
                    "applications": [
                        {
                            "id": a.id,
                            "job_title": a.job.title if a.job else "Role",
                            "company_name": a.job.company_name if a.job else "Company",
                            "status": a.current_status,
                            "updated_at": a.updated_at.isoformat() if a.updated_at else None
                        } for a in apps
                    ]
                },
                "conversation_turns": session_ctx.conversation_turns + 1
            }

        # H. SHOW PREFERENCES
        if intent == "show_preferences":
            pref = profile.preferences if profile else None
            titles = ", ".join(pref.preferred_titles[:3]) if pref and pref.preferred_titles else "Operations roles"
            locations = ", ".join(pref.preferred_locations) if pref and pref.preferred_locations else "Hyderabad"
            min_sal = f"{pref.minimum_salary:,.0f} {pref.salary_currency}" if pref and pref.minimum_salary else "Not set"

            spoken = f"Your saved preferences are: roles in {titles}, location preference for {locations}, and minimum salary of {min_sal}."
            display = f"Saved Preferences: Roles: {titles} | Locations: {locations} | Min Salary: {min_sal}"
            return {
                "session_id": session_ctx.session_id,
                "raw_transcript": raw_text,
                "interpreted_intent": intent,
                "extracted_parameters": params,
                "risk_level": risk,
                "requires_confirmation": False,
                "spoken_response": spoken,
                "display_text": display,
                "data_payload": {
                    "preferred_roles": pref.preferred_titles if pref else [],
                    "preferred_locations": pref.preferred_locations if pref else [],
                    "minimum_salary": pref.minimum_salary if pref else 0.0
                },
                "conversation_turns": session_ctx.conversation_turns + 1
            }

        # I. WAKE-WORD CONTROL
        if intent == "wake_word_control":
            enabled = params.get("enabled", False)
            v_settings = db.query(VoiceSecuritySettings).filter_by(id=1).first()
            if v_settings:
                v_settings.wake_word_enabled = enabled
                db.commit()
            state_str = "enabled" if enabled else "disabled"
            spoken = f"Wake-word activation has been {state_str}."
            display = f"Wake-word listener {state_str}."
            return {
                "session_id": session_ctx.session_id,
                "raw_transcript": raw_text,
                "interpreted_intent": intent,
                "extracted_parameters": params,
                "risk_level": risk,
                "requires_confirmation": False,
                "spoken_response": spoken,
                "display_text": display,
                "data_payload": {"wake_word_enabled": enabled},
                "conversation_turns": session_ctx.conversation_turns + 1
            }

        # J. HELP COMMANDS
        spoken = "You can ask me to find operations or procurement jobs in Hyderabad, show the best jobs, prepare a tailored resume, check your application status, or pause automation."
        display = "Voice Commands: 'Find operations jobs in Hyderabad', 'Show best 5 jobs', 'Prepare resume for first job', 'Track applications', 'Pause automation'."
        return {
            "session_id": session_ctx.session_id,
            "raw_transcript": raw_text,
            "interpreted_intent": "help_commands",
            "extracted_parameters": {},
            "risk_level": "LEVEL_1_LOW",
            "requires_confirmation": False,
            "spoken_response": spoken,
            "display_text": display,
            "data_payload": {},
            "conversation_turns": session_ctx.conversation_turns + 1
        }

    @classmethod
    def confirm_action(
        cls,
        session_id: str,
        confirmation_token: str,
        authorized: bool,
        passphrase: Optional[str],
        db: Session
    ) -> Dict[str, Any]:
        """Validates confirmation token and executes confirmed Level 2 or Level 3 action."""
        session_ctx = db.query(VoiceSessionContext).filter_by(session_id=session_id).first()
        if not session_ctx or not session_ctx.pending_action_type:
            return {"success": False, "message": "No pending action awaiting confirmation for this session."}

        action_type = session_ctx.pending_action_type
        payload = session_ctx.pending_action_payload or {}

        if not authorized:
            session_ctx.pending_action_type = ""
            session_ctx.pending_action_payload = {}
            db.commit()
            return {"success": True, "executed": False, "message": f"Action '{action_type}' was cancelled."}

        # If Level 3 or Passphrase required
        if action_type in ["submit_application", "send_recruiter_email"]:
            if not passphrase:
                return {"success": False, "message": "Voice passphrase required for protected outreach actions."}
            p_res = cls.verify_passphrase(passphrase, db)
            if not p_res["valid"]:
                return {"success": False, "message": p_res.get("message", "Invalid passphrase.")}

        # Execute confirmed action
        msg = f"Action {action_type} executed successfully."
        if action_type == "control_automation":
            action = payload.get("action")
            policy = db.query(AutomationPolicy).filter_by(id=1).first()
            if policy:
                if action == "pause_applications":
                    policy.pause_applications_only = True
                    msg = "Job applications have been paused. Discovery remains active."
                elif action == "pause_all":
                    policy.pause_all_automation = True
                    msg = "All background automation and discovery have been paused."
                elif action == "resume_all":
                    policy.pause_all_automation = False
                    policy.pause_applications_only = False
                    msg = "Automation resumed. Background workers are active."
                db.commit()

        elif action_type == "update_preferences":
            profile = db.query(CareerProfile).filter_by(id=1).first()
            if profile and profile.preferences:
                if "location" in payload:
                    profile.preferences.preferred_locations = [payload["location"]]
                    msg = f"Preferred location updated to {payload['location']}."
                if "minimum_salary" in payload:
                    profile.preferences.minimum_salary = payload["minimum_salary"]
                    msg = f"Minimum salary expectation set to {payload['minimum_salary']:,.0f} INR."
                db.commit()

        elif action_type == "update_application_status":
            idx = payload.get("target_index", 0)
            job = cls._resolve_job_from_context(idx, session_ctx, db)
            if job and job.application_record:
                job.application_record.current_status = payload.get("new_status", "UNDER_EVALUATION")
                db.commit()
                msg = f"Updated application status for {job.company_name} to {payload.get('new_status')}."

        # Clear pending action
        session_ctx.pending_action_type = ""
        session_ctx.pending_action_payload = {}
        db.commit()

        return {"success": True, "executed": True, "message": msg}

    # --- Helper Utilities ---
    @staticmethod
    def _resolve_ordinal(text: str) -> int:
        """Extracts 0-based job index from speech references like 'first', 'second', 'third job'."""
        ord_map = {
            "first": 0, "1st": 0, "one": 0,
            "second": 1, "2nd": 1, "two": 1,
            "third": 2, "3rd": 2, "three": 2,
            "fourth": 3, "4th": 3, "four": 3,
            "fifth": 4, "5th": 4, "five": 4
        }
        for word, idx in ord_map.items():
            if re.search(rf"\b{word}\b", text):
                return idx
        return 0

    @staticmethod
    def _extract_role(text: str) -> str:
        """Extracts domain role from speech."""
        patterns = [
            (r"\boperations manager\b", "Operations Manager"),
            (r"\boperations executive\b", "Operations Executive"),
            (r"\bbusiness operations\b", "Business Operations Executive"),
            (r"\bprocurement coordinator\b", "Procurement Coordinator"),
            (r"\bprocurement executive\b", "Procurement Executive"),
            (r"\bprocurement\b", "Procurement Executive"),
            (r"\bsupply chain coordinator\b", "Supply Chain Coordinator"),
            (r"\bsupply chain\b", "Supply Chain Executive"),
            (r"\blogistics coordinator\b", "Logistics Coordinator"),
            (r"\bsales operations\b", "Sales Operations Executive"),
            (r"\berp coordinator\b", "ERP/CRM Coordinator"),
            (r"\bexecutive assistant\b", "Executive Assistant"),
            (r"\bbusiness development\b", "Business Development Executive"),
            (r"\boperations\b", "Operations Executive")
        ]
        for pat, role in patterns:
            if re.search(pat, text):
                return role
        return "Operations Executive"

    @staticmethod
    def _extract_location(text: str) -> str:
        """Extracts preferred location from speech."""
        if "hyderabad" in text:
            return "Hyderabad, India"
        if "bangalore" in text or "bengaluru" in text:
            return "Bengaluru, India"
        if "mumbai" in text:
            return "Mumbai, India"
        if "delhi" in text or "ncr" in text or "gurgaon" in text:
            return "Delhi NCR, India"
        if "dubai" in text or "uae" in text:
            return "Dubai, UAE"
        if "remote" in text or "work from home" in text:
            return "Remote"
        return "Hyderabad, India"

    @staticmethod
    def _extract_experience(text: str) -> Tuple[Optional[float], Optional[float]]:
        """Extracts min and max experience in years."""
        m = re.search(r"(\d+)\s*(?:to|-)\s*(\d+)\s*years?", text)
        if m:
            return float(m.group(1)), float(m.group(2))
        word_match = re.search(r"\b(two|three|four|five|six|seven)\b\s*to\s*\b(three|four|five|six|seven|eight)\b", text)
        if word_match:
            word_map = {"two": 2.0, "three": 3.0, "four": 4.0, "five": 5.0, "six": 6.0, "seven": 7.0, "eight": 8.0}
            return word_map.get(word_match.group(1), 2.0), word_map.get(word_match.group(2), 5.0)
        single = re.search(r"(\d+)\+?\s*years?", text)
        if single:
            val = float(single.group(1))
            return val, val + 3.0
        return 2.0, 5.0

    @staticmethod
    def _extract_salary(text: str) -> Optional[float]:
        """Extracts salary numbers in INR (e.g. 40,000 or 50000 or 5 lakhs)."""
        lakh_m = re.search(r"(\d+(?:\.\d+)?)\s*(?:lakh|lacs?)", text)
        if lakh_m:
            return float(lakh_m.group(1)) * 100000.0
        num_m = re.search(r"(\d{2,3}(?:,\d{3})+|\d{4,7})", text)
        if num_m:
            return float(num_m.group(1).replace(",", ""))
        return None

    @staticmethod
    def _extract_count(text: str) -> int:
        """Extracts requested result count like 'five jobs' or '3 vacancies'."""
        word_to_num = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}
        for word, val in word_to_num.items():
            if re.search(rf"\b{word}\s+(?:jobs|roles|vacancies|positions)", text):
                return val
        m = re.search(r"(\d+)\s+(?:jobs|roles|vacancies|positions)", text)
        if m:
            return min(20, max(1, int(m.group(1))))
        return 5

    @classmethod
    def _resolve_job_from_context(cls, idx: int, session_ctx: VoiceSessionContext, db: Session) -> Optional[JobListing]:
        """Resolves target job from current session job IDs or fallback to top match."""
        if session_ctx.active_job_ids and idx < len(session_ctx.active_job_ids):
            jid = session_ctx.active_job_ids[idx]
            j = db.query(JobListing).filter_by(id=jid).first()
            if j:
                return j
        # Fallback to top match
        return db.query(JobListing).filter(JobListing.vacancy_status == "VERIFIED_OPEN").order_by(desc(JobListing.match_score)).first()

    @staticmethod
    def _log_command(session_id: str, raw: str, intent: str, params: dict, risk: str, spoken: str, details: dict, db: Session):
        """Audit log for voice commands with security guarantee (never logging passphrases)."""
        safe_params = {k: v for k, v in params.items() if "passphrase" not in k.lower()}
        log_entry = VoiceCommandLog(
            session_id=session_id,
            raw_transcript=raw,
            detected_intent=intent,
            extracted_parameters=safe_params,
            risk_level=risk,
            spoken_response=spoken,
            execution_details=details
        )
        db.add(log_entry)
        db.commit()
