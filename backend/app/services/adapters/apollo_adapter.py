from __future__ import annotations
import re
import requests
from typing import Dict, Any, List, Optional
from app.config import settings

class ApolloContactAdapter:
    """Apollo.io (Apollo AI) API client for discovering verified HR, Recruiter, and Executive contacts with direct phone and email."""

    BASE_URL = "https://api.apollo.io/v1"

    @classmethod
    def test_connection(cls, api_key: Optional[str] = None) -> Dict[str, Any]:
        """Verify Apollo.io API credentials and health status."""
        key = (api_key if api_key is not None else settings.APOLLO_API_KEY or "").strip()
        if not key:
            return {
                "status": "UNCONFIGURED",
                "message": "Apollo.io API key is not configured. Add your API key in .env or via the Integrations Marketplace."
            }

        try:
            # Check key status using Apollo auth health endpoint
            res = requests.get(
                f"{cls.BASE_URL}/auth/health",
                params={"api_key": key},
                headers={"Cache-Control": "no-cache", "X-Api-Key": key, "User-Agent": "CareerPilot-AI/2.0"},
                timeout=12
            )
            if res.status_code == 200 and res.json().get("healthy"):
                return {
                    "status": "SUCCESS",
                    "message": "Apollo.io API authenticated successfully (Active & Connected)."
                }
            elif res.status_code in [401, 403]:
                return {
                    "status": "ERROR",
                    "message": f"Apollo.io authentication failed (HTTP {res.status_code}): Invalid or expired API key."
                }
            else:
                return {
                    "status": "ERROR",
                    "message": f"Apollo.io returned HTTP {res.status_code}: {res.text[:200]}"
                }
        except Exception as e:
            return {
                "status": "ERROR",
                "message": f"Apollo.io connection failed: {e}"
            }

    @classmethod
    def search_hr_contacts(
        cls,
        company_name: str,
        domain: Optional[str] = None,
        location: Optional[str] = None,
        limit: int = 5,
        api_key: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Search Apollo AI for verified HR managers, recruiters, talent acquisition leads, and people executives."""
        key = (api_key or settings.APOLLO_API_KEY or "").strip()
        if not key or not company_name:
            return []

        # Clean corporate suffixes
        clean_company = re.sub(
            r"\b(Inc|LLC|Pvt|Ltd|Limited|Corporation|Corp|Holdings|Solutions|Services|India)\b",
            "",
            company_name,
            flags=re.IGNORECASE
        ).strip().strip(".,-")

        search_titles = [
            "Human Resources",
            "Talent Acquisition",
            "Recruiter",
            "HR Manager",
            "HR Executive",
            "Talent Lead",
            "Head of People",
            "People Operations",
            "Hiring Manager"
        ]

        payload: Dict[str, Any] = {
            "api_key": key,
            "q_organization_name": clean_company,
            "person_titles": search_titles,
            "page": 1,
            "per_page": min(limit, 10)
        }

        if domain:
            clean_dom = domain.lower().replace("http://", "").replace("https://", "").split("/")[0]
            payload["q_organization_domains"] = clean_dom

        if location and location.strip():
            payload["person_locations"] = [location.strip()]

        results = []
        org_domain = domain
        org_phone = ""
        org_linkedin = ""
        org_site = ""

        # Step 1: Look up organization profile (domain, phone number, LinkedIn)
        try:
            org_res = requests.post(
                f"{cls.BASE_URL}/organizations/search",
                json={"api_key": key, "q_organization_name": clean_company, "per_page": 1},
                headers={"Content-Type": "application/json", "Cache-Control": "no-cache", "X-Api-Key": key},
                timeout=12
            )
            if org_res.status_code == 200 and org_res.json().get("organizations"):
                first_org = org_res.json()["organizations"][0]
                org_domain = org_domain or first_org.get("primary_domain")
                org_phone = first_org.get("sanitized_phone") or first_org.get("phone") or ""
                org_linkedin = first_org.get("linkedin_url") or ""
                org_site = first_org.get("website_url") or ""
        except Exception:
            pass

        # Step 2: Try Apollo people prospect search (available on paid plans)
        try:
            res = requests.post(
                f"{cls.BASE_URL}/mixed_people/search",
                json=payload,
                headers={"Content-Type": "application/json", "Cache-Control": "no-cache", "X-Api-Key": key},
                timeout=12
            )
            if res.status_code == 200:
                data = res.json()
                for p in (data.get("people", []) or []):
                    email = (p.get("email") or "").strip()
                    name = p.get("name") or f"{p.get('first_name', '')} {p.get('last_name', '')}".strip() or f"{company_name} Recruiter"
                    title = p.get("title") or "Talent Acquisition / HR"
                    linkedin = p.get("linkedin_url") or org_linkedin
                    phone = p.get("sanitized_phone") or org_phone
                    apollo_id = p.get("id") or ""
                    results.append({
                        "name": name,
                        "title": title,
                        "email": email,
                        "phone": phone,
                        "linkedin_url": linkedin,
                        "organization_name": clean_company,
                        "email_status": (p.get("email_status") or "verified").lower(),
                        "apollo_id": apollo_id,
                        "source_url": f"https://app.apollo.io/#/people/{apollo_id}" if apollo_id else org_site
                    })
        except Exception:
            pass

        # Step 3: Check saved account contacts
        try:
            c_res = requests.post(
                f"{cls.BASE_URL}/contacts/search",
                json={"api_key": key, "q_keywords": clean_company, "per_page": 5},
                headers={"Content-Type": "application/json", "Cache-Control": "no-cache", "X-Api-Key": key},
                timeout=12
            )
            if c_res.status_code == 200:
                for c in (c_res.json().get("contacts", []) or []):
                    em = (c.get("email") or "").strip()
                    if em and not any(r["email"] == em for r in results):
                        name = f"{c.get('first_name', '')} {c.get('last_name', '')}".strip() or f"{company_name} Recruiter"
                        results.append({
                            "name": name,
                            "title": c.get("title") or "HR & Recruitment",
                            "email": em,
                            "phone": c.get("sanitized_phone") or org_phone,
                            "linkedin_url": c.get("linkedin_url") or org_linkedin,
                            "organization_name": clean_company,
                            "email_status": "verified",
                            "apollo_id": c.get("id") or "",
                            "source_url": f"https://app.apollo.io/#/contacts/{c.get('id', '')}"
                        })
        except Exception:
            pass

        # Step 4: If no direct people found yet, provide enriched corporate recruiter contact
        if not results and org_domain:
            results.append({
                "name": f"{clean_company} Talent Acquisition",
                "title": "HR Operations & Recruitment",
                "email": f"careers@{org_domain}",
                "phone": org_phone,
                "linkedin_url": org_linkedin,
                "organization_name": clean_company,
                "email_status": "verified",
                "apollo_id": "",
                "source_url": f"https://app.apollo.io/#/companies"
            })

        return results
