import json
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger("gigpilot_db")

# In-memory data structures
workers = {}
jobs = [
    {"job_id": "J001", "title": "Solar Panel Installation Helper", "required_skill": "solar panel installation", "hourly_pay": 320, "location": "Pune, MH", "safety_flag": False},
    {"job_id": "J002", "title": "Residential Electrician", "required_skill": "electrical wiring", "hourly_pay": 280, "location": "Pune, MH", "safety_flag": False},
    {"job_id": "J003", "title": "Delivery Rider (Gig)", "required_skill": "two-wheeler driving", "hourly_pay": 150, "location": "Mumbai, MH", "safety_flag": False},
    {"job_id": "J004", "title": "Unregulated Mine Laborer", "required_skill": "manual labor", "hourly_pay": 500, "location": "Jharkhand", "safety_flag": True},
    {"job_id": "J005", "title": "Plumbing Technician", "required_skill": "plumbing", "hourly_pay": 260, "location": "Pune, MH", "safety_flag": False},
    {"job_id": "J006", "title": "Solar Site Surveyor", "required_skill": "solar panel installation", "hourly_pay": 300, "location": "Nashik, MH", "safety_flag": False},
    {"job_id": "J007", "title": "AC Repair Technician", "required_skill": "hvac repair", "hourly_pay": 310, "location": "Pune, MH", "safety_flag": False},
]
courses = {
    "solar panel installation": {
        "micro_lessons": ["Understand basic photovoltaic (PV) cell principles", "Learn mounting and racking system installation", "Practice DC/AC wiring and inverter connections", "Study rooftop safety harness and fall-protection protocol"],
        "quiz_question": "What safety equipment is mandatory before working on a rooftop solar installation?",
        "quiz_answer": "A fall-protection harness anchored to a secure point",
    },
    "electrical wiring": {
        "micro_lessons": ["Learn color-coding standards for residential wiring", "Practice safe circuit breaker isolation (lock-out/tag-out)", "Understand load calculation basics"],
        "quiz_question": "What is the first step before touching any wiring in a panel?",
        "quiz_answer": "Isolate and lock out the circuit breaker",
    },
    "plumbing": {
        "micro_lessons": ["Learn pipe-fitting and sealing techniques", "Understand water pressure testing", "Practice leak detection methods"],
        "quiz_question": "What tool is used to detect a hidden pipe leak?",
        "quiz_answer": "A pressure gauge or moisture meter",
    },
    "hvac repair": {
        "micro_lessons": ["Understand refrigerant handling regulations", "Learn compressor diagnostics basics", "Practice safe gas cylinder handling"],
        "quiz_question": "Why must refrigerant handling be certified?",
        "quiz_answer": "Because refrigerants are regulated substances that can harm health/environment if mishandled",
    },
}
worker_progress = {}

# Mock classes to mimic the old ORM behavior
class MockDB:
    def query(self, model): return self
    def filter(self, *args): return self
    def first(self): return None
    def all(self): return []
    def count(self): return 0
    def add(self, *args): pass
    def commit(self): pass
    def close(self): pass
    def execute(self, query): pass

def init_db():
    logger.info("Database initialized in-memory (no-op).")

def get_db():
    yield MockDB()
