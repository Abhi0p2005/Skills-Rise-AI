"""
job_provider.py — Real job data via the Adzuna Jobs API (SDG 8 alignment)
==========================================================================

Replaces the previous approach of asking an LLM to invent job listings
(hallucinated titles, pay, and locations) with real, current postings
pulled from Adzuna's public REST API — no scraping, no browser
automation, no ToS ambiguity.

Setup:
    1. Register a free account at https://developer.adzuna.com/
    2. Grab your APP_ID and APP_KEY from the dashboard
    3. Add to your .env file:
           ADZUNA_APP_ID=your_app_id
           ADZUNA_APP_KEY=your_app_key

If the keys are missing, or the API call fails for any reason
(network error, rate limit, malformed response), this module returns
an empty list rather than raising — the caller (job_matcher_node) is
responsible for falling back to FALLBACK_JOBS in that case, exactly as
the LLM-generation path did before.

Design notes:
- One HTTP call per skill query, so job_matcher_node should call this
  once per target skill (current skill + in-progress skill), not once
  per keyword variant — keep it to 1-3 calls per user request.
- Adzuna's `what` param takes free-text search terms. We map GigPilot's
  internal skill names (e.g. "cnc machining") to more natural search
  phrases via SEARCH_TERM_OVERRIDES, since Adzuna's index is built on
  how real postings are worded, not our internal skill taxonomy.
- Results are normalized into GigPilot's existing job schema
  (job_id, title, required_skill, hourly_pay, location, tasks,
  sdg_aligned, source) so job_matcher_node and the frontend don't need
  to change shape.
- A deterministic safety re-check (same HAZARDOUS_KEYWORDS logic used
  on career goals) is applied to every listing's title + description
  before it's returned — external data is never trusted blindly, even
  from a legitimate source.
"""

from __future__ import annotations

import os
import logging
from typing import List, Dict, Any, Optional

import requests

logger = logging.getLogger("gigpilot_job_provider")

ADZUNA_APP_ID = os.getenv("ADZUNA_APP_ID")
ADZUNA_APP_KEY = os.getenv("ADZUNA_APP_KEY")
ADZUNA_COUNTRY = "in"  # India
ADZUNA_BASE_URL = f"https://api.adzuna.com/v1/api/jobs/{ADZUNA_COUNTRY}/search/1"

REQUEST_TIMEOUT_SECONDS = 6

# Map GigPilot's internal skill names -> natural-language Adzuna search
# terms. Adzuna's index is built from real job-ad text, so a phrase like
# "cnc machining" (our taxonomy) searches better as "cnc machinist".
SEARCH_TERM_OVERRIDES: Dict[str, str] = {
    "solar panel installation": "solar panel installer",
    "electrical wiring": "electrician",
    "plumbing": "plumber",
    "hvac repair": "hvac technician",
    "semiconductor manufacturing": "semiconductor technician",
    "cnc machining": "cnc machinist",
    "automation & plc": "plc technician",
}

# Re-uses the same hard safety net applied to career goals — external
# data is never trusted blindly, even from a legitimate API.
HAZARDOUS_KEYWORDS = [
    "scam", "fraud", "unregulated mine", "illegal mining", "cash mule",
    "money mule", "hazardous waste cleaning", "human trafficking", "smuggl",
    "drug running", "loan shark", "unlicensed firearm", "black market",
    "money laundering", "illegal logging",
]


def _contains_hazardous_keyword(text: str) -> Optional[str]:
    lowered = (text or "").lower()
    for kw in HAZARDOUS_KEYWORDS:
        if kw in lowered:
            return kw
    return None


def _is_configured() -> bool:
    return bool(ADZUNA_APP_ID and ADZUNA_APP_KEY)


def _search_term_for_skill(skill_name: str) -> str:
    return SEARCH_TERM_OVERRIDES.get(skill_name.lower(), skill_name)


def _normalize_listing(raw: Dict[str, Any], required_skill: str, index: int) -> Optional[Dict[str, Any]]:
    """Convert a raw Adzuna result into GigPilot's job schema. Returns
    None if the listing fails the safety re-check."""
    title = raw.get("title", "").strip()
    description = raw.get("description", "").strip()

    matched_kw = _contains_hazardous_keyword(f"{title} {description}")
    if matched_kw:
        logger.warning(
            "job_provider: dropped listing '%s' — matched hazardous term '%s'",
            title, matched_kw,
        )
        return None

    company = (raw.get("company") or {}).get("display_name", "Unknown Employer")
    location = (raw.get("location") or {}).get("display_name", "India")

    salary_min = raw.get("salary_min")
    salary_max = raw.get("salary_max")
    hourly_pay = None
    if salary_min and salary_max:
        # Adzuna salaries are annual INR figures; convert to an approximate
        # hourly rate assuming a 2,080-hour work year, to match GigPilot's
        # existing hourly_pay field.
        hourly_pay = round(((salary_min + salary_max) / 2) / 2080)
    elif salary_min:
        hourly_pay = round(salary_min / 2080)

    return {
        "job_id": f"ADZ{index:04d}",
        "title": title or "Untitled Listing",
        "required_skill": required_skill,
        "company": company,
        "hourly_pay": hourly_pay,
        "location": location,
        "tasks": [description[:280]] if description else [],
        "sdg_aligned": True,  # safety re-check above is the enforcement point
        "source": "adzuna",
        "apply_url": raw.get("redirect_url"),
    }


def fetch_jobs_for_skill(
    skill_name: str,
    location: Optional[str] = None,
    max_results: int = 5,
) -> List[Dict[str, Any]]:
    """Fetch real, current job listings for a given skill from Adzuna.

    Returns an empty list (never raises) if the API isn't configured or
    the request fails — callers should fall back to FALLBACK_JOBS in
    that case, same as the previous LLM-generation failure path.
    """
    if not _is_configured():
        logger.warning(
            "job_provider: ADZUNA_APP_ID / ADZUNA_APP_KEY not set — skipping live fetch."
        )
        return []

    params = {
        "app_id": ADZUNA_APP_ID,
        "app_key": ADZUNA_APP_KEY,
        "what": _search_term_for_skill(skill_name),
        "results_per_page": max_results,
        "content-type": "application/json",
    }
    if location:
        params["where"] = location

    try:
        response = requests.get(ADZUNA_BASE_URL, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as e:
        logger.error("job_provider: Adzuna request failed for skill '%s': %s", skill_name, e)
        return []
    except ValueError as e:
        logger.error("job_provider: Adzuna returned non-JSON response for skill '%s': %s", skill_name, e)
        return []

    raw_results = data.get("results", [])
    normalized = []
    for i, raw in enumerate(raw_results):
        listing = _normalize_listing(raw, required_skill=skill_name, index=i)
        if listing:
            normalized.append(listing)

    logger.info(
        "job_provider: fetched %d/%d usable listings for skill '%s'",
        len(normalized), len(raw_results), skill_name,
    )
    return normalized


def fetch_jobs_for_skills(
    skill_names: List[str],
    location: Optional[str] = None,
    max_results_per_skill: int = 3,
) -> List[Dict[str, Any]]:
    """Fetch and merge listings across multiple skills (e.g. current
    skills + the skill the worker is actively learning). Keeps total
    API calls to len(skill_names) — one request per skill, not per
    keyword variant."""
    all_jobs: List[Dict[str, Any]] = []
    for skill in skill_names:
        all_jobs.extend(
            fetch_jobs_for_skill(skill, location=location, max_results=max_results_per_skill)
        )
    return all_jobs