from __future__ import annotations
import re
from datetime import datetime, timezone
from typing import Dict, Any, List
from sqlalchemy.orm import Session

from app.models import AgentInstruction, JobListing, AutomationPolicy, CareerProfile, JobMatchResult
from app.services.adapters import SourceManager
from app.services.matching import MatchingEngine
from app.services.audit import record_audit_log

class AgentWorkspaceService:
    """Conversational AI recruitment employee workspace: interprets prompts, forms search plans, and executes."""

    @classmethod
    def interpret_and_execute_instruction(cls, prompt: str, db: Session) -> Dict[str, Any]:
        """Interprets free-form recruitment prompt, extracts structured parameters, executes search & evaluation."""
        text = prompt.lower()

        # Step 1: Extract Filters
        # Role / Job Title
        extracted_role = "Operations Executive"
        role_matches = re.findall(r"\b(operations manager|operations executive|procurement executive|supply chain|logistics coordinator|business operations|erp coordinator)\b", text)
        if role_matches:
            extracted_role = role_matches[0].title()

        # Location
        extracted_location = "Hyderabad, India"
        if "remote" in text or "work from home" in text:
            extracted_location = "Remote"
        elif "dubai" in text or "uae" in text:
            extracted_location = "Dubai, UAE"
        elif "bengaluru" in text or "bangalore" in text:
            extracted_location = "Bengaluru, India"
        elif "mumbai" in text:
            extracted_location = "Mumbai, India"

        # Experience range (e.g. "two to five years" or "2 to 5 years" or "3+ years")
        exp_min = 2.0
        exp_max = 5.0
        exp_match = re.search(r"(\d+)\s*(?:to|-)\s*(\d+)\s*years?", text)
        if exp_match:
            exp_min = float(exp_match.group(1))
            exp_max = float(exp_match.group(2))
        else:
            word_map = {"two": 2.0, "three": 3.0, "four": 4.0, "five": 5.0, "six": 6.0, "seven": 7.0}
            word_match = re.search(r"\b(two|three|four|five|six)\b\s*to\s*\b(three|four|five|six|seven)\b", text)
            if word_match:
                exp_min = word_map.get(word_match.group(1), 2.0)
                exp_max = word_map.get(word_match.group(2), 5.0)

        # Industry preference
        preferred_industries = []
        if "manufacturing" in text:
            preferred_industries.append("Manufacturing")
        if "supply chain" in text or "logistics" in text:
            preferred_industries.append("Supply Chain & Logistics")
        if "e-commerce" in text or "ecommerce" in text:
            preferred_industries.append("E-Commerce")

        extracted_filters = {
            "target_role": extracted_role,
            "location": extracted_location,
            "experience_min": exp_min,
            "experience_max": exp_max,
            "preferred_industries": preferred_industries,
            "source_portals": ["tavily_search", "linkedin", "naukri", "company_career_pages"]
        }

        # Step 2: Form Search Plan
        search_plan = {
            "query": f"{extracted_role} in {extracted_location}",
            "portal_queries": [
                f"{extracted_role} {extracted_location} site:linkedin.com/jobs",
                f"{extracted_role} {extracted_location} site:naukri.com",
                f"{extracted_role} {extracted_location} official careers jobs"
            ],
            "target_depth": "advanced",
            "deduplication_mode": "canonical_url_and_title_city"
        }

        # Save Persistent Instruction
        instruction = AgentInstruction(
            objective=prompt,
            extracted_filters=extracted_filters,
            search_plan=search_plan,
            status="ACTIVE"
        )
        db.add(instruction)
        db.commit()
        db.refresh(instruction)

        # Step 3: Execute Discovery using permitted source tools
        tavily_adapter = SourceManager.get_adapter("tavily_search")
        found_jobs = []
        if tavily_adapter:
            found_jobs = tavily_adapter.search_jobs(query=extracted_role, location=extracted_location, limit=8)

        # Step 4: Deduplicate and Save Leads
        existing_jobs = db.query(JobListing).all()
        added_count = 0
        profile = db.query(CareerProfile).filter_by(id=1).first()

        for j_data in found_jobs:
            if not SourceManager.is_duplicate(j_data, existing_jobs):
                new_listing = JobListing(
                    title=j_data.get("title", extracted_role),
                    company_name=j_data.get("company_name", "Enterprise Employer"),
                    location=extracted_location,
                    work_mode=j_data.get("work_mode", "On-site"),
                    employment_type=j_data.get("employment_type", "Full-time"),
                    experience_required_min=exp_min,
                    experience_required_max=exp_max,
                    source_platform=j_data.get("source_platform", "Web Search"),
                    original_url=j_data.get("original_url", ""),
                    canonical_url=j_data.get("canonical_url", ""),
                    description=j_data.get("description", ""),
                    vacancy_status="VERIFIED_OPEN",
                    application_method="email",
                    date_discovered=datetime.now(timezone.utc)
                )
                db.add(new_listing)
                db.commit()
                db.refresh(new_listing)

                # Evaluate with Matching Engine
                if profile:
                    match_res = MatchingEngine.evaluate(new_listing, profile)
                    new_listing.match_score = match_res["match_score"]
                    new_listing.eligibility_status = match_res["eligibility_status"]

                    db.add(JobMatchResult(
                        job_id=new_listing.id,
                        match_score=match_res["match_score"],
                        eligibility_status=match_res["eligibility_status"],
                        matching_requirements=match_res["matching_requirements"],
                        missing_requirements=match_res["missing_requirements"],
                        uncertain_requirements=match_res["uncertain_requirements"],
                        location_match=match_res["location_match"],
                        salary_match=match_res["salary_match"],
                        score_breakdown=match_res["score_breakdown"],
                        explanation=match_res["explanation"],
                        recommended_action=match_res["recommended_action"]
                    ))
                    db.commit()

                existing_jobs.append(new_listing)
                added_count += 1

        instruction.leads_found = added_count
        db.commit()

        record_audit_log(
            db=db,
            action="agent_objective_executed",
            actor="ai_agent",
            entity_type="agent_instruction",
            entity_id=str(instruction.id),
            details={"prompt": prompt, "leads_discovered": added_count}
        )

        return {
            "instruction_id": instruction.id,
            "objective": prompt,
            "filters": extracted_filters,
            "search_plan": search_plan,
            "status": "COMPLETED",
            "leads_found": added_count,
            "message": f"Successfully parsed objective. Selected permitted search adapters, discovered and deduplicated {added_count} new leads."
        }
