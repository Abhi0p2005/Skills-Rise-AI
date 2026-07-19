"""
test_job_provider.py — Offline tests for the Adzuna job provider.

These tests never hit the real network: requests.get is mocked in
every case. That means they run in CI, on a laptop with no internet,
or before you've even registered an Adzuna account — they check the
LOGIC (safety filtering, normalization, fallback behavior), not
whether Adzuna itself is reachable.

Run:
    cd backend
    pip install pytest --break-system-packages
    pytest tests/test_job_provider.py -v
"""

import sys
import os
import importlib.util
from unittest.mock import patch, MagicMock

import pytest

# Load job_provider.py directly by path so this test file works whether
# or not the package is installed / has an __init__.py chain set up.
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_MODULE_PATH = os.path.join(_THIS_DIR, "..", "job_provider.py")


def _load_job_provider(env_overrides=None):
    """Fresh import of job_provider with a controlled environment, so
    module-level ADZUNA_APP_ID / ADZUNA_APP_KEY reflect what each test
    needs (they're read once at import time)."""
    env_overrides = env_overrides or {}
    with patch.dict(os.environ, env_overrides, clear=False):
        for key in ("ADZUNA_APP_ID", "ADZUNA_APP_KEY"):
            if key not in env_overrides:
                os.environ.pop(key, None)
        spec = importlib.util.spec_from_file_location("job_provider_test_instance", _MODULE_PATH)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module


# ---------------------------------------------------------------------------
# Configuration / fail-safe behavior
# ---------------------------------------------------------------------------

def test_unconfigured_returns_empty_list_not_exception():
    """No ADZUNA_APP_ID/KEY set -> must return [], never raise."""
    jp = _load_job_provider(env_overrides={})
    result = jp.fetch_jobs_for_skill("electrical wiring")
    assert result == []


def test_network_failure_returns_empty_list():
    """requests.get raising a connection error -> caller sees [], not a crash."""
    jp = _load_job_provider(env_overrides={"ADZUNA_APP_ID": "x", "ADZUNA_APP_KEY": "y"})
    with patch.object(jp.requests, "get", side_effect=jp.requests.exceptions.ConnectionError("boom")):
        result = jp.fetch_jobs_for_skill("electrical wiring")
    assert result == []


def test_malformed_json_response_returns_empty_list():
    """API returns 200 but non-JSON body -> handled, not a crash."""
    jp = _load_job_provider(env_overrides={"ADZUNA_APP_ID": "x", "ADZUNA_APP_KEY": "y"})
    fake_response = MagicMock()
    fake_response.raise_for_status.return_value = None
    fake_response.json.side_effect = ValueError("not json")
    with patch.object(jp.requests, "get", return_value=fake_response):
        result = jp.fetch_jobs_for_skill("electrical wiring")
    assert result == []


def test_http_error_status_returns_empty_list():
    """API returns 4xx/5xx -> raise_for_status raises -> handled as []."""
    jp = _load_job_provider(env_overrides={"ADZUNA_APP_ID": "x", "ADZUNA_APP_KEY": "y"})
    fake_response = MagicMock()
    fake_response.raise_for_status.side_effect = jp.requests.exceptions.HTTPError("429 rate limited")
    with patch.object(jp.requests, "get", return_value=fake_response):
        result = jp.fetch_jobs_for_skill("electrical wiring")
    assert result == []


# ---------------------------------------------------------------------------
# Safety filtering (this is the important one)
# ---------------------------------------------------------------------------

def test_hazardous_listing_is_dropped():
    jp = _load_job_provider(env_overrides={"ADZUNA_APP_ID": "x", "ADZUNA_APP_KEY": "y"})
    fake_raw = {
        "title": "Cash mule needed urgently, easy money",
        "description": "No questions asked, just move packages.",
        "company": {"display_name": "Shady Co"},
        "location": {"display_name": "Pune, MH"},
    }
    listing = jp._normalize_listing(fake_raw, required_skill="electrical wiring", index=0)
    assert listing is None


def test_hazardous_term_in_description_only_still_dropped():
    """The keyword only needs to appear in the description, not the title."""
    jp = _load_job_provider(env_overrides={"ADZUNA_APP_ID": "x", "ADZUNA_APP_KEY": "y"})
    fake_raw = {
        "title": "General Helper Wanted",
        "description": "Work involves hazardous waste cleaning, no training provided.",
        "company": {"display_name": "Anon Corp"},
        "location": {"display_name": "Mumbai, MH"},
    }
    listing = jp._normalize_listing(fake_raw, required_skill="plumbing", index=0)
    assert listing is None


def test_safe_listing_passes_through():
    jp = _load_job_provider(env_overrides={"ADZUNA_APP_ID": "x", "ADZUNA_APP_KEY": "y"})
    fake_raw = {
        "title": "Residential Electrician",
        "description": "Install and repair home wiring safely.",
        "company": {"display_name": "Acme Electric"},
        "location": {"display_name": "Pune, MH"},
    }
    listing = jp._normalize_listing(fake_raw, required_skill="electrical wiring", index=0)
    assert listing is not None
    assert listing["title"] == "Residential Electrician"


def test_end_to_end_fetch_filters_hazardous_from_mixed_results():
    """A batch with one safe and one hazardous listing -> only the safe one survives."""
    jp = _load_job_provider(env_overrides={"ADZUNA_APP_ID": "x", "ADZUNA_APP_KEY": "y"})
    fake_response = MagicMock()
    fake_response.raise_for_status.return_value = None
    fake_response.json.return_value = {
        "results": [
            {
                "title": "Residential Electrician",
                "description": "Install and repair home wiring safely.",
                "company": {"display_name": "Acme Electric"},
                "location": {"display_name": "Pune, MH"},
                "salary_min": 300000, "salary_max": 400000,
                "redirect_url": "http://example.com/1",
            },
            {
                "title": "Unregulated mine laborer, cash daily",
                "description": "No safety gear needed.",
                "company": {"display_name": "??? Pvt Ltd"},
                "location": {"display_name": "Jharkhand"},
                "salary_min": 500000, "salary_max": 600000,
                "redirect_url": "http://example.com/2",
            },
        ]
    }
    with patch.object(jp.requests, "get", return_value=fake_response):
        results = jp.fetch_jobs_for_skill("electrical wiring")
    assert len(results) == 1
    assert results[0]["title"] == "Residential Electrician"


# ---------------------------------------------------------------------------
# Normalization correctness
# ---------------------------------------------------------------------------

def test_hourly_pay_computed_from_annual_salary_range():
    jp = _load_job_provider(env_overrides={"ADZUNA_APP_ID": "x", "ADZUNA_APP_KEY": "y"})
    fake_raw = {
        "title": "Plumber",
        "description": "Fix pipes.",
        "company": {"display_name": "PipeCo"},
        "location": {"display_name": "Pune, MH"},
        "salary_min": 260000, "salary_max": 260000,
    }
    listing = jp._normalize_listing(fake_raw, required_skill="plumbing", index=0)
    assert listing["hourly_pay"] == round(260000 / 2080)


def test_missing_salary_leaves_hourly_pay_none_not_fabricated():
    """No salary data -> hourly_pay should be None, not a made-up number."""
    jp = _load_job_provider(env_overrides={"ADZUNA_APP_ID": "x", "ADZUNA_APP_KEY": "y"})
    fake_raw = {
        "title": "Plumber",
        "description": "Fix pipes.",
        "company": {"display_name": "PipeCo"},
        "location": {"display_name": "Pune, MH"},
    }
    listing = jp._normalize_listing(fake_raw, required_skill="plumbing", index=0)
    assert listing["hourly_pay"] is None


# ---------------------------------------------------------------------------
# Skill -> search term mapping
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("skill,expected_term", [
    ("solar panel installation", "solar panel installer"),
    ("electrical wiring", "electrician"),
    ("plumbing", "plumber"),
    ("cnc machining", "cnc machinist"),
    ("automation & plc", "plc technician"),
    ("some totally unmapped skill", "some totally unmapped skill"),
])
def test_search_term_overrides(skill, expected_term):
    jp = _load_job_provider(env_overrides={})
    assert jp._search_term_for_skill(skill) == expected_term


# ---------------------------------------------------------------------------
# Multi-skill batching
# ---------------------------------------------------------------------------

def test_fetch_jobs_for_skills_calls_once_per_skill():
    jp = _load_job_provider(env_overrides={"ADZUNA_APP_ID": "x", "ADZUNA_APP_KEY": "y"})
    fake_response = MagicMock()
    fake_response.raise_for_status.return_value = None
    fake_response.json.return_value = {"results": []}
    with patch.object(jp.requests, "get", return_value=fake_response) as mock_get:
        jp.fetch_jobs_for_skills(["electrical wiring", "plumbing", "cnc machining"])
    assert mock_get.call_count == 3