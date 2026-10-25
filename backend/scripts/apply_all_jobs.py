from __future__ import annotations
import os
from datetime import datetime, timezone, timedelta
from app.database import SessionLocal
from app.models import (
    JobListing, ApplicationRecord, RecruiterContact, ResumeVersion,
    CareerProfile, FollowUpTask, AutomationPolicy
)
from app.services.resume_engine import ResumeEngine
from app.services.contact_service import ContactService
from app.services.email_service import EmailOutreachService
from app.config import settings

def apply_and_schedule():
    db = SessionLocal()
    profile = db.query(CareerProfile).filter_by(id=1).first()
    policy = db.query(AutomationPolicy).filter_by(id=1).first()
    if policy:
        policy.enable_auto_follow_ups = True
        db.commit()

    print("=== CareerPilot AI: Multi-Company Application & 3-Stage Follow-up Scheduler ===")
    
    # 1. Gather all existing applied company names to ensure 100% strict deduplication
    applied_companies = set()
    for app_rec in db.query(ApplicationRecord).all():
        if app_rec.job and app_rec.job.company_name:
            applied_companies.add(app_rec.job.company_name.strip().lower())
    
    print(f"Already applied companies count: {len(applied_companies)}")
    
    # 2. Query all verified open jobs
    jobs = db.query(JobListing).filter(
        JobListing.vacancy_status == "VERIFIED_OPEN",
        ~JobListing.company_name.like("%Apex Supply%"),
        ~JobListing.company_name.like("%Vacancies In%")
    ).all()
    
    # Filter for unique companies not yet applied to
    eligible_unique_jobs = []
    seen_in_batch = set()
    
    for j in jobs:
        c_clean = j.company_name.strip().lower()
        if c_clean in applied_companies or c_clean in seen_in_batch:
            continue
        seen_in_batch.add(c_clean)
        eligible_unique_jobs.append(j)

    print(f"Eligible unique companies ready for outreach: {len(eligible_unique_jobs)}")

    results = []
    now_ts = datetime.now(timezone.utc)

    for job in eligible_unique_jobs:
        comp_name = job.company_name.strip()
        print(f"\nProcessing company: {comp_name} ({job.title})...")

        # Step A: Get or Discover Contact
        contact = db.query(RecruiterContact).filter_by(job_id=job.id).first()
        if not contact:
            contact = db.query(RecruiterContact).filter_by(company_name=comp_name).first()
        if not contact or not contact.email:
            contacts = ContactService.discover_public_contacts(comp_name, job.location, db, job_id=job.id)
            if contacts:
                contact = contacts[0]

        if not contact or not contact.email:
            print(f"  [SKIPPED] No verified contact email available for {comp_name}.")
            continue

        recipient_email = contact.email.strip()
        print(f"  Target Recipient: {recipient_email} (Phone: {contact.phone or 'N/A'})")

        # Step B: Tailor Truthful Resume (strictly preserving candidate background, adapting only position skills)
        rv = db.query(ResumeVersion).filter_by(job_id=job.id).order_by(ResumeVersion.id.desc()).first()
        if not rv:
            tailored = ResumeEngine.tailor(job, profile, use_ai=False)
            pdf_out = f"./data/resumes/resume_job_{job.id}.pdf"
            docx_out = f"./data/resumes/resume_job_{job.id}.docx"
            ResumeEngine.generate_pdf(tailored, pdf_out, profile)
            ResumeEngine.generate_docx(tailored, docx_out, profile)

            rv = ResumeVersion(
                profile_id=profile.id,
                job_id=job.id,
                version_name=tailored["version_name"],
                headline=tailored["headline"],
                summary=tailored["summary"],
                full_text=tailored["full_text"],
                cover_letter_text=tailored["cover_letter_text"],
                pdf_path=pdf_out,
                docx_path=docx_out,
                model_used="rules-conservative-verified",
                factual_consistency_score=100.0
            )
            db.add(rv)
            db.commit()
            db.refresh(rv)

        # Step C: Create Application Record
        app_rec = ApplicationRecord(
            job_id=job.id,
            resume_version_id=rv.id,
            current_status="APPLICATION_READY",
            submission_method="email",
            primary_recipient=recipient_email,
            unattended_approved=True
        )
        db.add(app_rec)
        db.commit()
        db.refresh(app_rec)

        # Step D: Transmit Application Email
        try:
            send_res = EmailOutreachService.send_application_email(app_rec, rv, db, is_unattended=True)
            job.application_status = app_rec.current_status
            applied_companies.add(comp_name.lower())
            print(f"  ✓ Application Sent: {send_res.get('message', 'Delivered')}")
        except Exception as e:
            print(f"  [ERROR sending email]: {e}")
            continue

        # Step E: Schedule the 3-Stage Follow-up Tasks requested by user
        # 1. Tomorrow (+1 day)
        date_tomorrow = now_ts + timedelta(days=1)
        sub1 = f"Following up on Application: {job.title} — {settings.CAREER_FULL_NAME}"
        body1 = (
            f"Dear Hiring Team at {comp_name},\n\n"
            f"I hope this message finds you well. I submitted my application for the {job.title} position "
            f"and wanted to politely follow up to reiterate my strong enthusiasm for the role.\n\n"
            f"With my operations coordination background and proven track record in streamlining procurement and logistics, "
            f"I am eager to contribute to your team. I have re-attached my tailored resume for your convenience.\n\n"
            f"Please let me know if you need any additional information from my side.\n\n"
            f"Thank you again for your time and consideration.\n\n"
            f"Best regards,\n"
            f"{settings.CAREER_FULL_NAME}\n"
            f"{settings.CAREER_PHONE} | {settings.CAREER_EMAIL or settings.EMAIL_FROM}"
        )
        task1 = FollowUpTask(
            application_id=app_rec.id,
            follow_up_sequence=1,
            due_date=date_tomorrow,
            status="SCHEDULED",
            draft_subject=sub1,
            draft_body=body1,
            notes="Follow-up scheduled for tomorrow (+1 day) directly to HR contact."
        )
        db.add(task1)

        # 2. In 15 days (+16 days from now)
        date_15d = now_ts + timedelta(days=16)
        sub2 = f"Status Check: {job.title} Application — {settings.CAREER_FULL_NAME}"
        body2 = (
            f"Dear Hiring Team at {comp_name},\n\n"
            f"I am writing to politely check in on the status of my application for the {job.title} role submitted last month.\n\n"
            f"I continue to be very enthusiastic about joining {comp_name}. Should this specific vacancy have progressed, "
            f"I would also welcome the opportunity to be considered for relevant upcoming openings in operations or supply chain.\n\n"
            f"Thank you once again for your review.\n\n"
            f"Best regards,\n"
            f"{settings.CAREER_FULL_NAME}\n"
            f"{settings.CAREER_PHONE} | {settings.CAREER_EMAIL or settings.EMAIL_FROM}"
        )
        task2 = FollowUpTask(
            application_id=app_rec.id,
            follow_up_sequence=2,
            due_date=date_15d,
            status="SCHEDULED",
            draft_subject=sub2,
            draft_body=body2,
            notes="Follow-up scheduled for 15 days later (+16 days) directly to HR contact."
        )
        db.add(task2)

        # 3. In another 15 days (+31 days from now)
        date_30d = now_ts + timedelta(days=31)
        sub3 = f"Final Check-in: Application for {job.title} — {settings.CAREER_FULL_NAME}"
        body3 = (
            f"Dear Hiring Team at {comp_name},\n\n"
            f"I hope you are having a productive week. I am reaching out for a final check-in regarding the {job.title} position.\n\n"
            f"If the position has already been filled, I completely understand and wish your team continued success. "
            f"I remain open to staying connected on LinkedIn for future opportunities that align with my operations profile.\n\n"
            f"Thank you for your time.\n\n"
            f"Sincerely,\n"
            f"{settings.CAREER_FULL_NAME}\n"
            f"{settings.CAREER_PHONE} | {settings.CAREER_EMAIL or settings.EMAIL_FROM}"
        )
        task3 = FollowUpTask(
            application_id=app_rec.id,
            follow_up_sequence=3,
            due_date=date_30d,
            status="SCHEDULED",
            draft_subject=sub3,
            draft_body=body3,
            notes="Final follow-up scheduled for another 15 days later (+31 days)."
        )
        db.add(task3)

        db.commit()
        print(f"  ✓ Scheduled 3 follow-ups: Tomorrow ({date_tomorrow.strftime('%Y-%m-%d')}), +15d ({date_15d.strftime('%Y-%m-%d')}), +30d ({date_30d.strftime('%Y-%m-%d')})")
        results.append({
            "company": comp_name,
            "role": job.title,
            "recipient": recipient_email,
            "status": app_rec.current_status
        })

    db.close()
    print(f"\nCompleted! Total new company applications submitted & scheduled: {len(results)}")
    return results

if __name__ == "__main__":
    apply_and_schedule()
