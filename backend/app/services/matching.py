from __future__ import annotations
import re
from typing import Dict, Any, List, Set
from app.models import CareerProfile, JobListing

def tokenize(text: str) -> Set[str]:
    if not text:
        return set()
    stop_words = {
        "and", "the", "for", "with", "from", "that", "this", "will", "have", "your",
        "you", "are", "our", "job", "role", "work", "years", "year", "ability", "skills",
        "experience", "required", "preferred", "responsible", "including", "using", "good",
        "strong", "must", "should", "team", "candidate", "position", "looking", "apply"
    }
    tokens = re.findall(r"[a-zA-Z][a-zA-Z0-9+#.-]{1,}", text.lower())
    return {w for w in tokens if len(w) > 2 and w not in stop_words}

class MatchingEngine:
    """Transparent, documented multi-factor scoring and eligibility evaluation engine."""

    @staticmethod
    def evaluate(job: JobListing, profile: CareerProfile) -> Dict[str, Any]:
        # 1. Gather Profile Facts
        profile_skills = {s.name.lower(): s for s in profile.skills}
        profile_skill_tokens = set()
        for s in profile.skills:
            profile_skill_tokens |= tokenize(s.name)

        user_exp_years = float(profile.total_experience_years or 0.0)
        user_loc = (profile.current_location or "").lower()
        
        pref = profile.preferences
        preferred_titles = [t.lower() for t in (pref.preferred_titles if pref else [])]
        preferred_locations = [l.lower() for l in (pref.preferred_locations if pref else [])]
        preferred_industries = [i.lower() for i in (pref.preferred_industries if pref else [])]
        excluded_companies = [c.lower() for c in (pref.excluded_companies if pref else [])]
        
        # 2. Parse Job Properties
        job_title_lower = (job.title or "").lower()
        job_company_lower = (job.company_name or "").lower()
        job_loc_lower = (job.location or "").lower()
        job_desc_lower = (job.description or "").lower()
        job_tokens = tokenize(f"{job.title} {job.description} {job.location}")

        # Check Excluded Companies
        if any(exc in job_company_lower for exc in excluded_companies if exc):
            return {
                "match_score": 0,
                "eligibility_status": "NOT_ELIGIBLE",
                "matching_requirements": [],
                "missing_requirements": [f"Company '{job.company_name}' is in your excluded employers list."],
                "uncertain_requirements": [],
                "location_match": False,
                "salary_match": "UNKNOWN",
                "score_breakdown": {"exclusion_applied": True},
                "explanation": f"Disqualified because {job.company_name} matches your exclusion policy.",
                "recommended_action": "REJECT"
            }

        # Step 4: Disqualify based on Job Filters (Seniority, Blocked keywords, Whitelist)
        from app.services.job_filters import validate_job_filters
        is_filter_ok, filter_reason = validate_job_filters(job, min_fit_score=0)
        if not is_filter_ok:
            return {
                "match_score": 0,
                "eligibility_status": "NOT_ELIGIBLE",
                "matching_requirements": [],
                "missing_requirements": [filter_reason],
                "uncertain_requirements": [],
                "location_match": False,
                "salary_match": "UNKNOWN",
                "score_breakdown": {"job_filter_disqualified": True},
                "explanation": f"Disqualified by Job Filters: {filter_reason}",
                "recommended_action": "REJECT"
            }

        # 3. Factor A: Title / Role Family Alignment (Max 25 pts)
        title_tokens = tokenize(job.title)
        role_keywords = {
            "operations", "procurement", "supply", "chain", "logistics", "coordinator",
            "executive", "manager", "admin", "crm", "erp", "sales", "inventory", "vendor"
        }
        title_overlap = len(title_tokens & role_keywords)
        is_exact_preferred_title = any(pt in job_title_lower or job_title_lower in pt for pt in preferred_titles)
        
        if is_exact_preferred_title:
            score_title = 25.0
        elif title_overlap >= 2:
            score_title = 22.0
        elif title_overlap == 1:
            score_title = 15.0
        else:
            score_title = 5.0

        # 4. Factor B: Skills & Software Proficiency (Max 35 pts)
        matched_skills = []
        missing_skills = []
        uncertain_items = []

        standard_skills_to_check = [
            ("procurement", "Procurement & Vendor Management"),
            ("vendor", "Vendor Coordination & Quotations"),
            ("supply chain", "Supply Chain Coordination"),
            ("logistics", "Logistics & Dispatch Tracking"),
            ("erp", "ERP Systems (SAP / Custom ERP)"),
            ("crm", "CRM Platforms"),
            ("excel", "Advanced Excel & Spreadsheets"),
            ("inventory", "Inventory & GRN Management"),
            ("billing", "Billing & Store Verification"),
            ("quotation", "Sales Enquiries & Quotations"),
            ("tally", "Tally Prime Accounting")
        ]

        found_in_job = []
        for kw, display_name in standard_skills_to_check:
            if kw in job_desc_lower or kw in job_title_lower:
                found_in_job.append(display_name)
                # Check if user has this skill
                has_skill = any(kw in s_name for s_name in profile_skills)
                if has_skill:
                    matched_skills.append(display_name)
                else:
                    missing_skills.append(display_name)

        if found_in_job:
            skill_ratio = len(matched_skills) / len(found_in_job)
            score_skills = round(skill_ratio * 35.0, 1)
        else:
            # Fall back to token overlap
            common_tokens = len(profile_skill_tokens & job_tokens)
            score_skills = min(35.0, common_tokens * 3.5)

        # 5. Factor C: Experience Fit (Max 20 pts)
        req_min = float(job.experience_required_min or 0.0)
        req_max = float(job.experience_required_max or 0.0)
        
        if req_min == 0.0 and req_max == 0.0:
            # Check for patterns like "2-5 years" in description
            exp_match = re.search(r"(\d+)(?:\s*-\s*|\s+to\s+)(\d+)\s+years?", job_desc_lower)
            if exp_match:
                req_min = float(exp_match.group(1))
                req_max = float(exp_match.group(2))
            else:
                single_match = re.search(r"(\d+)\+?\s+years?", job_desc_lower)
                if single_match:
                    req_min = float(single_match.group(1))

        if req_min > 0.0 or req_max > 0.0:
            if user_exp_years >= req_min:
                if req_max > 0 and user_exp_years > (req_max + 3):
                    # Overqualified penalty
                    score_exp = 12.0
                    uncertain_items.append(f"Candidate has {user_exp_years} yrs exp; role seeks up to {req_max} yrs.")
                else:
                    score_exp = 20.0
                    matched_skills.append(f"Experience Requirement: {user_exp_years} years fits {req_min}-{req_max or 'plus'} yrs.")
            else:
                deficit = req_min - user_exp_years
                if deficit <= 1.0:
                    score_exp = 10.0
                    missing_skills.append(f"Experience deficit: Requires {req_min} yrs, candidate has {user_exp_years} yrs.")
                else:
                    score_exp = 2.0
                    missing_skills.append(f"Major experience deficit: Requires {req_min}+ yrs, candidate has {user_exp_years} yrs.")
        else:
            score_exp = 15.0 # Unspecified, assume neutral

        # 6. Factor D: Location & Work Mode (Max 15 pts)
        location_match = False
        if any(pref_loc in job_loc_lower for pref_loc in ["hyderabad", "telangana"]):
            location_match = True
            score_loc = 15.0
        elif any(pref_loc in job_loc_lower for pref_loc in ["remote", "work from home", "anywhere"]):
            location_match = True
            score_loc = 15.0
        elif any(pref_loc in job_loc_lower for pref_loc in preferred_locations if pref_loc):
            location_match = True
            score_loc = 12.0
        else:
            # Check relocation preference
            if pref and pref.open_to_relocation:
                location_match = True
                score_loc = 8.0
                uncertain_items.append(f"Location is '{job.location}'; requires relocation.")
            else:
                location_match = False
                score_loc = 2.0
                missing_skills.append(f"Location mismatch: Job is in '{job.location}' outside preferred locations.")

        # 7. Factor E: Education & Certifications (Max 5 pts)
        score_edu = 5.0
        if "degree" in job_desc_lower or "graduate" in job_desc_lower or "bachelor" in job_desc_lower:
            if profile.education:
                matched_skills.append("Degree Requirement: Verified Bachelor degree holder.")
                score_edu = 5.0
            else:
                uncertain_items.append("Job mentions degree requirement; please verify degree in profile.")
                score_edu = 2.0

        # Calculate Total Score
        total_score = int(min(100, max(0, round(score_title + score_skills + score_exp + score_loc + score_edu))))

        # Determine Eligibility
        if total_score >= 70 and len(missing_skills) <= 1:
            eligibility_status = "LIKELY_ELIGIBLE"
            recommended_action = "PREPARE_APPLICATION"
        elif total_score >= 50:
            eligibility_status = "REVIEW_REQUIRED"
            recommended_action = "REVIEW"
        else:
            eligibility_status = "NOT_ELIGIBLE"
            recommended_action = "REJECT"

        # Salary Match
        salary_match = "UNKNOWN"
        sal_min = float(job.salary_min or 0.0)
        sal_max = float(job.salary_max or 0.0)
        pref_min_sal = float(pref.minimum_salary or 0.0) if pref else 0.0
        if sal_min > 0 or sal_max > 0:
            if pref_min_sal > 0:
                if sal_max > 0 and sal_max < pref_min_sal:
                    salary_match = "MISMATCH"
                    missing_skills.append(f"Salary offering ({sal_max} {job.salary_currency}) is below minimum target ({pref_min_sal}).")
                else:
                    salary_match = "MATCH"

        # Build Explanation
        explanation = (
            f"Evaluated match score of {total_score}/100. "
            f"Title alignment: {score_title}/25. "
            f"Skills & software alignment: {score_skills}/35. "
            f"Experience compatibility: {score_exp}/20. "
            f"Location & mobility fit: {score_loc}/15. "
            f"Education baseline: {score_edu}/5."
        )

        return {
            "match_score": total_score,
            "eligibility_status": eligibility_status,
            "matching_requirements": matched_skills,
            "missing_requirements": missing_skills,
            "uncertain_requirements": uncertain_items,
            "location_match": location_match,
            "salary_match": salary_match,
            "score_breakdown": {
                "title_score": score_title,
                "skills_score": score_skills,
                "experience_score": score_exp,
                "location_score": score_loc,
                "education_score": score_edu
            },
            "explanation": explanation,
            "recommended_action": recommended_action
        }
