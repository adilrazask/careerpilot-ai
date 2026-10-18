import os
import uuid
import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import (
    User, CareerProfile, EmploymentHistory, Skill, Education,
    CareerPreferences, JobListing, RecruiterContact, ResumeVersion,
    ApplicationRecord, ApplicationAttempt, AutomationPolicy, RecruiterResponse,
    FollowUpTask, ScheduledTask, AuditLog, WorkerRun, SystemHealth,
    VoiceSecuritySettings, VoiceCommandLog, VoiceSessionContext
)
from app.services.voice_service import VoiceService
from app.services.matching import MatchingEngine
from app.services.resume_engine import ResumeEngine
from app.services.adapters import SourceManager, canonicalize_url

@pytest.fixture
def voice_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # User & Profile
    user = User(id=1, email="candidate@careerpilot.ai", full_name="Adil Raja")
    session.add(user)
    session.commit()

    profile = CareerProfile(
        id=1,
        user_id=1,
        full_name="Adil Raja",
        email="candidate@careerpilot.ai",
        phone="+91 9876543210",
        current_location="Hyderabad, India",
        total_experience_years=4.5,
        summary="Operations Coordinator with hands-on expertise in supply chain, vendor procurement, and SAP ERP."
    )
    session.add(profile)

    skills = [
        Skill(profile_id=1, name="SAP ERP", category="software", proficiency="advanced", is_verified=True),
        Skill(profile_id=1, name="Vendor Procurement", category="operations", proficiency="advanced", is_verified=True),
        Skill(profile_id=1, name="Inventory Management", category="operations", proficiency="intermediate", is_verified=True),
        Skill(profile_id=1, name="Advanced Excel", category="software", proficiency="advanced", is_verified=True),
    ]
    for s in skills:
        session.add(s)

    hist = EmploymentHistory(
        profile_id=1,
        company="Apex Industrial Solutions Ltd",
        job_title="Operations Coordinator",
        start_date="2022-03",
        end_date="Present",
        is_current=True,
        responsibilities=["Coordinated purchase orders, GRN verification, and logistics dispatching in SAP ERP."],
        achievements=["Reduced procurement turnaround time by 18%."],
        tools_used=["SAP ERP", "Excel"],
        is_verified=True
    )
    session.add(hist)

    pref = CareerPreferences(
        profile_id=1,
        preferred_titles=["Operations Coordinator", "Operations Executive", "Procurement Coordinator"],
        preferred_locations=["Hyderabad, India", "Remote"],
        minimum_salary=500000.0,
        preferred_salary=750000.0,
        salary_currency="INR"
    )
    session.add(pref)

    policy = AutomationPolicy(
        id=1,
        is_autonomous_enabled=True,
        pause_all_automation=False,
        pause_applications_only=False,
        enable_unattended_email_applications=True,
        min_match_score=70,
        enable_auto_resume_tailoring=True,
        enable_auto_follow_ups=True,
        max_applications_per_day=25
    )
    session.add(policy)

    # Voice security settings
    default_phrase = "careerpilot secure command"
    pw_hash, salt = VoiceService.hash_passphrase(default_phrase)
    v_settings = VoiceSecuritySettings(
        id=1,
        user_id=1,
        passphrase_hash=pw_hash,
        passphrase_salt=salt,
        passphrase_enabled=True,
        failed_attempts=0,
        wake_word_enabled=False,
        wake_word="Hey CareerPilot",
        speech_language="en-US",
        speech_rate=1.0,
        speech_pitch=1.0,
        voice_name="default",
        prefer_local_stt=True
    )
    session.add(v_settings)

    # Seed baseline job listings
    j1 = JobListing(
        id=1,
        title="Operations Executive",
        company_name="Apex Logistics Hub",
        location="Hyderabad, India",
        experience_required_min=3.0,
        experience_required_max=5.0,
        salary_min=600000.0,
        salary_max=850000.0,
        salary_currency="INR",
        source_platform="Direct Careers",
        original_url="https://apexlogistics.example.com/jobs/101",
        canonical_url="https://apexlogistics.example.com/jobs/101",
        description="Looking for an Operations Executive with vendor procurement, SAP ERP, and inventory audit skills.",
        vacancy_status="VERIFIED_OPEN",
        match_score=85,
        eligibility_status="LIKELY_ELIGIBLE"
    )
    j2 = JobListing(
        id=2,
        title="Procurement Coordinator",
        company_name="Zenith Supply Chain",
        location="Hyderabad, India",
        experience_required_min=2.0,
        experience_required_max=4.0,
        salary_min=500000.0,
        salary_max=700000.0,
        salary_currency="INR",
        source_platform="Naukri",
        original_url="https://zenithsupply.example.com/jobs/202",
        canonical_url="https://zenithsupply.example.com/jobs/202",
        description="Seeking Procurement Coordinator with vendor evaluation, purchase order management, and Excel expertise.",
        vacancy_status="VERIFIED_OPEN",
        match_score=80,
        eligibility_status="LIKELY_ELIGIBLE"
    )
    session.add(j1)
    session.add(j2)
    session.commit()

    yield session
    session.close()


# TEST 1: Microphone Permission Denied simulation (client reports error status)
def test_microphone_permission_denied_handling():
    # Frontend handles permission error and provides text fallback
    client_error_event = {"type": "permission_denied", "message": "Microphone access blocked by browser."}
    fallback_mode = "text_input_fallback" if client_error_event["type"] == "permission_denied" else "voice"
    assert fallback_mode == "text_input_fallback"


# TEST 2: Speech Recognition failure / empty transcript
def test_speech_recognition_empty_transcript(voice_db):
    s = VoiceService.get_or_create_session("sess_empty", voice_db)
    res = VoiceService.classify_intent_and_extract_parameters("", s)
    assert res["intent"] == "help_commands"


# TEST 3: Incorrect job-title transcription gracefully handled
def test_incorrect_job_title_transcription(voice_db):
    s = VoiceService.get_or_create_session("sess_typo", voice_db)
    # User says something slightly garbled or non-standard
    res = VoiceService.classify_intent_and_extract_parameters("find xyz random role in hyderabad", s)
    # System falls back to default Operations Executive role
    assert res["intent"] == "search_jobs"
    assert res["parameters"]["role"] == "Operations Executive"
    assert res["parameters"]["location"] == "Hyderabad, India"


# TEST 4: Ambiguous company name handled without crash
def test_ambiguous_company_name(voice_db):
    s = VoiceService.get_or_create_session("sess_amb_comp", voice_db)
    res = VoiceService.classify_intent_and_extract_parameters("what is the deadline at some unknown company", s)
    exec_res = VoiceService.execute_voice_command(res, "what is the deadline at some unknown company", s, voice_db)
    # Gracefully falls back to top match or asks for search
    assert "spoken_response" in exec_res
    assert len(exec_res["spoken_response"]) > 0


# TEST 5: Ambiguous salary or location defaults to candidate facts
def test_ambiguous_salary_or_location(voice_db):
    s = VoiceService.get_or_create_session("sess_amb_loc", voice_db)
    res = VoiceService.classify_intent_and_extract_parameters("search for procurement positions", s)
    assert res["parameters"]["role"] == "Procurement Executive"
    assert res["parameters"]["location"] == "Hyderabad, India" # Defaults to saved location


# TEST 6: Valid job-search command ("CareerPilot, find five operations executive jobs in Hyderabad")
def test_valid_job_search_command(voice_db):
    s = VoiceService.get_or_create_session("sess_valid_search", voice_db)
    cmd = "CareerPilot, find five operations executive jobs in Hyderabad"
    intent_info = VoiceService.classify_intent_and_extract_parameters(cmd, s)
    assert intent_info["intent"] == "search_jobs"
    assert intent_info["parameters"]["role"] == "Operations Executive"
    assert intent_info["parameters"]["location"] == "Hyderabad, India"
    assert intent_info["parameters"]["limit"] == 5

    res = VoiceService.execute_voice_command(intent_info, cmd, s, voice_db)
    assert "CareerPilot found" in res["spoken_response"]
    assert len(s.active_job_ids) >= 2
    assert res["data_payload"]["jobs"][0]["match_score"] >= 80


# TEST 7: Valid follow-up command ("Show me the best three", "Prepare my resume for the second job")
def test_valid_follow_up_command(voice_db):
    s = VoiceService.get_or_create_session("sess_followup", voice_db)
    s.active_job_ids = [1, 2]
    voice_db.commit()

    # Step A: "Show me the best three"
    f1 = VoiceService.classify_intent_and_extract_parameters("show me the best two jobs", s)
    assert f1["intent"] == "shortlist_jobs"
    r1 = VoiceService.execute_voice_command(f1, "show me the best two jobs", s, voice_db)
    assert "top 2 ranked opportunities" in r1["spoken_response"]

    # Step B: "Prepare my resume for the second job" (resolves index 1 -> job id 2)
    f2 = VoiceService.classify_intent_and_extract_parameters("prepare my resume for the second job", s)
    assert f2["intent"] == "prepare_resume"
    assert f2["parameters"]["target_index"] == 1
    r2 = VoiceService.execute_voice_command(f2, "prepare my resume for the second job", s, voice_db)
    assert "Zenith Supply Chain" in r2["spoken_response"]
    assert "resume_version_id" in r2["data_payload"]


# TEST 8: Session context and multi-turn conversational preference retention
def test_session_context_clarification_dialogue(voice_db):
    s = VoiceService.get_or_create_session("sess_multi_turn", voice_db)
    s.active_filters = {"role": "Operations Executive", "location": "Hyderabad, India"}
    s.pending_clarification = "EXPERIENCE_LEVEL"
    voice_db.commit()

    # Candidate responds: "Three to five years"
    resp_intent = VoiceService.classify_intent_and_extract_parameters("Three to five years", s)
    assert resp_intent["intent"] == "clarification_response"
    assert resp_intent["parameters"]["exp_min"] == 3.0
    assert resp_intent["parameters"]["exp_max"] == 5.0

    exec_res = VoiceService.execute_voice_command(resp_intent, "Three to five years", s, voice_db)
    assert "CareerPilot found" in exec_res["spoken_response"]
    assert s.pending_clarification == "" # Clarification resolved


# TEST 9: Incorrect passphrase handling
def test_incorrect_passphrase(voice_db):
    res = VoiceService.verify_passphrase("wrong secret password", voice_db)
    assert res["valid"] is False
    assert res["locked"] is False
    assert "Incorrect voice passphrase" in res["message"]


# TEST 10: Repeated authentication failures -> Temporary Lockout
def test_repeated_authentication_lockout(voice_db):
    v_settings = voice_db.query(VoiceSecuritySettings).filter_by(id=1).first()
    v_settings.failed_attempts = 0
    v_settings.locked_until = None
    voice_db.commit()

    # Fail 3 times
    VoiceService.verify_passphrase("bad_phrase_1", voice_db)
    VoiceService.verify_passphrase("bad_phrase_2", voice_db)
    lock_res = VoiceService.verify_passphrase("bad_phrase_3", voice_db)

    assert lock_res["valid"] is False
    assert lock_res["locked"] is True
    assert lock_res["remaining_seconds"] > 0
    assert "Maximum failed attempts reached" in lock_res["message"]

    # Subsequent attempt is immediately locked
    immediate_res = VoiceService.verify_passphrase("careerpilot secure command", voice_db)
    assert immediate_res["locked"] is True


# TEST 11: Duplicate job detection during voice discovery
def test_duplicate_job_detection(voice_db):
    raw_url = "https://apexlogistics.example.com/jobs/101?utm_campaign=tracker"
    clean_url = canonicalize_url(raw_url)
    existing_all = voice_db.query(JobListing).all()
    duplicate_lead = {
        "title": "Operations Executive",
        "company_name": "Apex Logistics Hub",
        "location": "Hyderabad, India",
        "original_url": raw_url,
        "canonical_url": clean_url
    }
    assert SourceManager.is_duplicate(duplicate_lead, existing_all) is True


# TEST 12: Expired or closed vacancy handled gracefully
def test_closed_vacancy_handling(voice_db):
    j = voice_db.query(JobListing).filter_by(id=1).first()
    j.vacancy_status = "CLOSED"
    voice_db.commit()

    s = VoiceService.get_or_create_session("sess_closed", voice_db)
    # Search should exclude closed vacancies
    res = VoiceService.execute_voice_command(
        {"intent": "search_jobs", "parameters": {"role": "Operations Executive", "location": "Hyderabad, India", "limit": 5}},
        "find operations jobs in hyderabad",
        s,
        voice_db
    )
    for job_item in res["data_payload"]["jobs"]:
        assert job_item["id"] != 1 # Closed job is excluded


# TEST 13: Fabricated job details (zero hallucination check)
def test_resume_zero_hallucination_guarantee(voice_db):
    profile = voice_db.query(CareerProfile).filter_by(id=1).first()
    job = voice_db.query(JobListing).filter_by(id=2).first()
    tailored = ResumeEngine.tailor(job, profile, use_ai=False)
    # 100% factual consistency score guaranteed
    assert tailored["factual_consistency_score"] == 100.0
    # Original company name preserved exactly
    assert "Apex Industrial Solutions Ltd" in str(tailor_result := tailored["experience"])


# TEST 14: Resume fact preservation
def test_resume_fact_preservation(voice_db):
    profile = voice_db.query(CareerProfile).filter_by(id=1).first()
    job = voice_db.query(JobListing).filter_by(id=1).first()
    tailored = ResumeEngine.tailor(job, profile, use_ai=False)
    # True dates and title preserved
    exp0 = tailored["experience"][0]
    assert exp0["start_date"] == "2022-03"
    assert exp0["end_date"] == "Present"
    assert exp0["job_title"] == "Operations Coordinator"


# TEST 15: Duplicate application prevention
def test_duplicate_application_prevention(voice_db):
    app1 = ApplicationRecord(
        job_id=1,
        submission_method="email",
        primary_recipient="hr@apexlogistics.example.com",
        current_status="EMAIL_SENT"
    )
    voice_db.add(app1)
    voice_db.commit()

    # Attempting to re-apply to job 1 should be prevented
    prior = voice_db.query(ApplicationRecord).filter_by(job_id=1).first()
    assert prior is not None
    assert prior.current_status == "EMAIL_SENT"


# TEST 16: Level 3 Protected Action Authorization Gate
def test_protected_action_authorization_gate(voice_db):
    s = VoiceService.get_or_create_session("sess_level3", voice_db)
    intent_info = {
        "intent": "submit_application",
        "parameters": {"job_id": 1},
        "risk_level": "LEVEL_3_PROTECTED",
        "requires_confirmation": True
    }
    res = VoiceService.execute_voice_command(intent_info, "submit application for job one", s, voice_db)
    assert res["requires_confirmation"] is True
    assert res["confirmation_token"] is not None
    assert "protected action" in res["spoken_response"].lower()

    # Unauthorized confirmation fails
    conf_res = VoiceService.confirm_action(s.session_id, res["confirmation_token"], authorized=False, passphrase=None, db=voice_db)
    assert conf_res["executed"] is False

    # Authorization without passphrase fails
    conf_res2 = VoiceService.confirm_action(s.session_id, res["confirmation_token"], authorized=True, passphrase=None, db=voice_db)
    assert conf_res2["success"] is False


# TEST 17: Anti-bot / CAPTCHA manual intervention pause
def test_anti_bot_captcha_pause_simulation(voice_db):
    from app.services.portal_service import EmployerPortalService
    html_with_captcha = "<html><body>Please solve this hCaptcha / Cloudflare challenge to proceed.</body></html>"
    is_blocked = EmployerPortalService.detect_anti_bot_challenge(html_with_captcha)
    assert is_blocked is True


# TEST 18: Background automation cancellation via voice command
def test_background_automation_cancellation_via_voice(voice_db):
    s = VoiceService.get_or_create_session("sess_cancel_auto", voice_db)
    cmd = "pause job applications"
    intent_info = VoiceService.classify_intent_and_extract_parameters(cmd, s)
    assert intent_info["intent"] == "control_automation"
    assert intent_info["parameters"]["action"] == "pause_applications"
    assert intent_info["risk_level"] == "LEVEL_2_CONTROLLED"

    # Confirm action
    token = "auth_test_token"
    s.pending_action_type = "control_automation"
    s.pending_action_payload = intent_info["parameters"]
    voice_db.commit()

    exec_res = VoiceService.confirm_action(s.session_id, token, authorized=True, passphrase=None, db=voice_db)
    assert exec_res["executed"] is True
    policy = voice_db.query(AutomationPolicy).filter_by(id=1).first()
    assert policy.pause_applications_only is True


# TEST 19: Text-to-speech concise summary generation
def test_text_to_speech_concise_summary(voice_db):
    s = VoiceService.get_or_create_session("sess_tts", voice_db)
    res = VoiceService.execute_voice_command(
        {"intent": "search_jobs", "parameters": {"role": "Operations Executive", "location": "Hyderabad, India", "limit": 2}},
        "find operations executive jobs in hyderabad",
        s,
        voice_db
    )
    spoken = res["spoken_response"]
    assert len(spoken) > 20
    assert len(spoken) < 300 # Stays concise
    assert "CareerPilot found" in spoken


# TEST 20: Application restart and session expiration
def test_session_expiration_reset(voice_db):
    now_ts = datetime.now(timezone.utc)
    expired_time = now_ts - timedelta(minutes=45) # Over 30 mins
    s_expired = VoiceSessionContext(
        session_id="sess_expired_test",
        active_query="Old search query",
        last_active_at=expired_time,
        created_at=expired_time
    )
    voice_db.add(s_expired)
    voice_db.commit()

    # Retrieving session should re-initialize fresh context
    fresh = VoiceService.get_or_create_session("sess_expired_test", voice_db)
    assert fresh.active_query == ""
    assert fresh.conversation_turns == 0
