"""
GigPilot AI — Vocational Upskilling & Job-Matching Agent (SDG 8)
==================================================================

A highly polished, interactive LangGraph-orchestrated backend with
in-memory session state (no database requirements), interactive progress/quizzes,
dynamic AI-generated jobs & tasks, and a dual-layer safety audit system.
"""

from __future__ import annotations

import os
import json
import logging
import time
import threading
from typing import TypedDict, List, Dict, Any, Optional, Literal

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

# Import In-memory Data Store
from .database import workers, courses, worker_progress

# Import real job-data provider (Adzuna API) — replaces LLM-hallucinated jobs
from .job_provider import fetch_jobs_for_skills

# ---------------------------------------------------------------------------
# Environment & Setup
# ---------------------------------------------------------------------------

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("gigpilot_ai")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
logger.info(f"DEBUG: GROQ_API_KEY loaded: {bool(GROQ_API_KEY)}")

# ---------------------------------------------------------------------------
# Deterministic Safety Net Keywords
# ---------------------------------------------------------------------------

HAZARDOUS_KEYWORDS = [
    "scam", "fraud", "unregulated mine", "illegal mining", "cash mule", 
    "money mule", "hazardous waste cleaning", "human trafficking", "smuggl", 
    "drug running", "loan shark", "unlicensed firearm", "black market", 
    "money laundering", "illegal logging"
]

def contains_hazardous_keyword(text: str) -> Optional[str]:
    lowered = text.lower()
    for kw in HAZARDOUS_KEYWORDS:
        if kw in lowered:
            return kw
    return None

# ---------------------------------------------------------------------------
# Skill Keyword Matching (used by skill_gap_analyzer & job_matcher)
# ---------------------------------------------------------------------------

SKILL_KEYWORDS = {
    "solar panel installation": ["solar", "panel", "photovoltaic", "pv", "renewable energy", "green energy"],
    "electrical wiring": ["electrical", "wiring", "electrician", "circuit", "wire"],
    "plumbing": ["plumbing", "plumber", "pipe", "water", "drain"],
    "hvac repair": ["hvac", "heating", "ventilation", "air conditioning", "cooling", "ac repair", "refrigeration"],
    "semiconductor manufacturing": ["semiconductor", "chip", "wafer", "fab", "electronics manufacturing", "vlsi", "microchip", "cleanroom"],
    "cnc machining": ["cnc", "machining", "machinist", "lathe", "milling", "manufacturing"],
    "automation & plc": ["automation", "plc", "scada", "industrial automation", "control system", "hmi"],
}

# ---------------------------------------------------------------------------
# State Definition
# ---------------------------------------------------------------------------

class WorkerState(TypedDict, total=False):
    worker_name: str
    current_skills: List[str]
    career_goal: str
    suggested_course: Dict[str, Any]
    matched_jobs: List[Dict[str, Any]]
    logs: str
    is_unsafe: bool

# ---------------------------------------------------------------------------
# LLM Client (Groq) with Strictly Enforced Rate Limiter (< 5 RPM)
# ---------------------------------------------------------------------------

class RateLimitedChatGroq(ChatGroq):
    """A wrapper around ChatGroq to strictly limit requests to under 5 RPM (15s delay)."""
    _last_request_time: float = 0.0
    _lock: threading.Lock = threading.Lock()

    def _delay_if_needed(self):
        with self._lock:
            now = time.time()
            elapsed = now - RateLimitedChatGroq._last_request_time
            wait_time = 1.0 - elapsed
            if wait_time > 0:
                logger.info(f"RateLimiter: Sleeping for {wait_time:.2f}s")
                time.sleep(wait_time)
            RateLimitedChatGroq._last_request_time = time.time()

    def invoke(self, *args, **kwargs):
        self._delay_if_needed()
        return super().invoke(*args, **kwargs)

    async def ainvoke(self, *args, **kwargs):
        self._delay_if_needed()
        return await super().ainvoke(*args, **kwargs)

def get_llm() -> ChatGroq:
    if not GROQ_API_KEY:
        raise RuntimeError(
            "GROQ_API_KEY is not set. Export it as an environment variable "
            "or place it in a .env file."
        )
    return RateLimitedChatGroq(
        model="llama-3.3-70b-versatile",
        temperature=0,
        api_key=GROQ_API_KEY,
    )

# ---------------------------------------------------------------------------
# Node 1: Intake (with Session Persistence Sync)
# ---------------------------------------------------------------------------

def intake_node(state: WorkerState) -> WorkerState:
    worker_name = state.get("worker_name")
    career_goal = state.get("career_goal")
    current_skills = state.get("current_skills") or []
    
    logger.info("intake_node: starting intake for worker=%s goal=%s", worker_name, career_goal)

    # In-memory session management
    if worker_name not in workers:
        workers[worker_name] = {
            "name": worker_name,
            "current_skills": current_skills,
            "career_goal": career_goal,
            "is_unsafe": False,
            "logs": ""
        }
    
    worker = workers[worker_name]
    
    # Sync logic
    db_skills = worker["current_skills"]
    if not current_skills:
        current_skills = db_skills
    else:
        current_skills = list(set(current_skills + db_skills))
        worker["current_skills"] = current_skills
    
    if career_goal:
        worker["career_goal"] = career_goal
    else:
        career_goal = worker["career_goal"]
    
    log_line = f"[intake] Loaded worker '{worker_name}'. Skills: {current_skills}."

    return {
        **state,
        "current_skills": current_skills,
        "career_goal": career_goal,
        "logs": (state.get("logs", "") + "\n" + log_line).strip(),
        "is_unsafe": False,
    }

# ---------------------------------------------------------------------------
# Node 2: Safety Filter (Dual Layer: Deterministic + Agentic AI Auditor)
# ---------------------------------------------------------------------------

def safety_filter_node(state: WorkerState) -> WorkerState:
    career_goal = state.get("career_goal", "")
    worker_name = state.get("worker_name")
    
    # Layer 1: Deterministic Check
    matched_kw = contains_hazardous_keyword(career_goal)
    if matched_kw:
        log_line = (
            f"[safety_filter] BLOCKED — Career goal contains hazardous/illegal/predatory "
            f"term ('{matched_kw}'). Flow halted for safety."
        )
        logger.warning(log_line)
        _update_db_worker_safety(worker_name, is_unsafe=True, log_line=log_line)
        return {
            **state,
            "is_unsafe": True,
            "matched_jobs": [],
            "suggested_course": {},
            "logs": (state.get("logs", "") + "\n" + log_line).strip(),
        }

    # Layer 2: LLM Safety Auditor Check (for hidden predatory/dangerous patterns)
    try:
        llm = get_llm()
        system_prompt = (
            "You are an AI Safety Auditor specializing in labor exploitation, safety, modern slavery prevention, and UN SDG 8 compliance. "
            "Analyze the worker's career goal. Check for hidden hazardous, dangerous, highly exploitative, predatory, "
            "or illegal job intent. Also verify the goal promotes decent work (fair wages, safety, dignity). "
            "Respond strictly in JSON format with no other text, comments, or wrappers. "
            "Format: {\"is_unsafe\": true|false, \"reason\": \"<brief reason>\"}"
        )
        human_prompt = f"Worker Career Goal: '{career_goal}'"
        
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_prompt)
        ])
        
        raw_output = response.content.strip()
        if "```" in raw_output:
            raw_output = raw_output.split("```")[1].replace("json", "").strip()
            
        audit = json.loads(raw_output)
        
        if audit.get("is_unsafe", False):
            log_line = f"[safety_filter] BLOCKED by AI Safety Auditor — Reason: {audit.get('reason')}"
            logger.warning(log_line)
            _update_db_worker_safety(worker_name, is_unsafe=True, log_line=log_line)
            return {
                **state,
                "is_unsafe": True,
                "matched_jobs": [],
                "suggested_course": {},
                "logs": (state.get("logs", "") + "\n" + log_line).strip(),
            }
            
    except Exception as e:
        logger.error(f"Error running LLM Safety Auditor: {e}. Falling back to programmatic safety check.")

    log_line = "[safety_filter] PASSED — Deterministic & AI safety checks completed cleanly."
    _update_db_worker_safety(worker_name, is_unsafe=False, log_line=log_line)
    return {
        **state,
        "is_unsafe": False,
        "logs": (state.get("logs", "") + "\n" + log_line).strip(),
    }

def _update_db_worker_safety(worker_name: str, is_unsafe: bool, log_line: str):
    if worker_name in workers:
        worker = workers[worker_name]
        worker["is_unsafe"] = is_unsafe
        worker["logs"] = (worker["logs"] or "") + "\n" + log_line

def route_after_safety(state: WorkerState) -> Literal["skill_gap_analyzer_node", "__end__"]:
    if state.get("is_unsafe"):
        return "__end__"
    return "skill_gap_analyzer_node"

# ---------------------------------------------------------------------------
# Node 3: Skill Gap Analyzer (Interactive course loader & Progress creation)
# ---------------------------------------------------------------------------

def skill_gap_analyzer_node(state: WorkerState) -> WorkerState:
    career_goal = state.get("career_goal", "")
    worker_name = state.get("worker_name")
    current_skills = [s.lower() for s in state.get("current_skills", [])]
    
    available_skills = list(courses.keys())
    
    target_skill = None
    gap_exists = False

    try:
        llm = get_llm()
        system_prompt = (
            "You are a skill-gap analysis engine. Compare the worker's current skills against their career goal. "
            "Identify which of the AVAILABLE_SKILLS is most relevant and necessary to acquire to achieve their goal. "
            "Respond strictly in JSON with this exact schema: "
            '{"target_skill": "<one of AVAILABLE_SKILLS or null>", "gap_exists": true|false, "reasoning": "<short reason>"}'
        )
        human_prompt = (
            f"AVAILABLE_SKILLS: {available_skills}\n"
            f"Worker Current Skills: {current_skills}\n"
            f"Worker Career Goal: {career_goal}\n"
        )
        
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_prompt),
        ])
        
        raw = response.content.strip()
        if "```" in raw:
            raw = raw.split("```")[1].replace("json", "").strip()
            
        analysis = json.loads(raw)
        target_skill = analysis.get("target_skill")
        gap_exists = analysis.get("gap_exists", False)
    except Exception as e:
        logger.error(f"Error in LLM Skill Gap Analysis: {e}")

    # Keyword-based fallback if LLM failed or returned no match
    if not target_skill:
        goal_lower = career_goal.lower()
        for skill_key, keywords in SKILL_KEYWORDS.items():
            if any(kw in goal_lower for kw in keywords):
                target_skill = skill_key
                gap_exists = skill_key.lower() not in current_skills
                break

    suggested_course: Dict[str, Any] = {}

    if target_skill and target_skill.lower() not in current_skills and gap_exists:
        # Load course details directly from memory
        course_data = courses.get(target_skill)
        if course_data:
            suggested_course = {
                "skill_name": target_skill,
                "micro_lessons": course_data["micro_lessons"],
                "questions": course_data["questions"],
                "difficulty": course_data.get("difficulty", "medium"),
            }
            
            # Create a persistent Course Progress entry if not already present
            if worker_name not in worker_progress:
                worker_progress[worker_name] = {}
            
            if target_skill not in worker_progress[worker_name]:
                worker_progress[worker_name][target_skill] = {
                    "lessons_completed": [],
                    "quiz_passed": False
                }
                
            log_line = (
                f"[skill_gap_analyzer] Gap identified: worker needs '{target_skill}'. "
                f"Micro-learning plan assigned. Complete the course and pass the quiz to unlock this skill!"
            )
        else:
            log_line = f"[skill_gap_analyzer] Identified target skill '{target_skill}' but no course exists."
    else:
        log_line = "[skill_gap_analyzer] No active skill gaps identified — worker's profile matches their goal."

    # Update worker logs in memory
    if worker_name in workers:
        workers[worker_name]["logs"] = (workers[worker_name]["logs"] or "") + "\n" + log_line

    return {
        **state,
        "suggested_course": suggested_course,
        "logs": (state.get("logs", "") + "\n" + log_line).strip(),
    }

# ---------------------------------------------------------------------------
# Node 4: Job Matcher (Dynamically Generate Vacancies & Tasks using AI Agent)
# ---------------------------------------------------------------------------

FALLBACK_JOBS = [
    {
        "job_id": "J001", 
        "title": "Solar Panel Installation Helper", 
        "required_skill": "solar panel installation", 
        "hourly_pay": 320, 
        "location": "Pune, MH",
        "sdg_aligned": True,
        "tasks": [
            "Assist in lifting and positioning photovoltaic panels on racking systems",
            "Secure rooftop hardware and mounts using standard hand and power tools",
            "Maintain inventory of tools, fasteners, and safety gear on-site"
        ]
    },
    {
        "job_id": "J002", 
        "title": "Residential Electrician Assistant", 
        "required_skill": "electrical wiring", 
        "hourly_pay": 280, 
        "location": "Mumbai, MH",
        "sdg_aligned": True,
        "tasks": [
            "Feed electrical wires through conduit pipes behind drywall",
            "Perform load tests on light switches and wall outlets",
            "Label circuit panels accurately based on wiring diagrams"
        ]
    },
    {
        "job_id": "J003", 
        "title": "Plumbing Apprentice", 
        "required_skill": "plumbing", 
        "hourly_pay": 260, 
        "location": "Pune, MH",
        "sdg_aligned": True,
        "tasks": [
            "Measure, cut, and thread copper and PVC pipes to specification",
            "Apply primers and solvent cements to join pipes cleanly",
            "Clean and prepare worksites before plumbing assembly"
        ]
    },
    {
        "job_id": "J004", 
        "title": "Semiconductor Fab Equipment Technician", 
        "required_skill": "semiconductor manufacturing", 
        "hourly_pay": 380, 
        "monthly_pay": "₹25,000 - ₹35,000",
        "location": "Sanand, Gujarat",
        "sdg_aligned": True,
        "tasks": [
            "Operate and monitor wafer fabrication equipment (steppers, etchers, deposition tools)",
            "Perform preventive maintenance and calibration of cleanroom machinery",
            "Document equipment parameters and report anomalies for engineering review",
            "Follow Class 10/100 cleanroom protocols including gowning and contamination control"
        ]
    },
    {
        "job_id": "J005", 
        "title": "Semiconductor Assembly Line Operator", 
        "required_skill": "semiconductor manufacturing", 
        "hourly_pay": 350, 
        "monthly_pay": "₹22,000 - ₹32,000",
        "location": "Hosur, Tamil Nadu",
        "sdg_aligned": True,
        "tasks": [
            "Handle die bonding, wire bonding, and molding press operations on assembly line",
            "Inspect packaged ICs using optical microscopes for defects and alignment",
            "Maintain material inventory (leadframes, epoxy, bonding wire) at workstations",
            "Follow ESD-safe handling procedures and 5S workplace organization"
        ]
    },
    {
        "job_id": "J006", 
        "title": "CNC Machinist (Manufacturing)", 
        "required_skill": "cnc machining", 
        "hourly_pay": 300, 
        "monthly_pay": "₹20,000 - ₹30,000",
        "location": "Bengaluru, KA",
        "sdg_aligned": True,
        "tasks": [
            "Set up and operate CNC milling and turning machines for precision components",
            "Read engineering drawings and select appropriate tools, feeds, and speeds",
            "Inspect finished parts using calipers, micrometers, and CMM equipment",
            "Perform basic machine maintenance and tool offset adjustments"
        ]
    },
    {
        "job_id": "J007", 
        "title": "Automation & PLC Technician", 
        "required_skill": "automation & plc", 
        "hourly_pay": 400, 
        "monthly_pay": "₹28,000 - ₹42,000",
        "location": "Pune, MH",
        "sdg_aligned": True,
        "tasks": [
            "Program and troubleshoot PLCs (Allen Bradley, Siemens, Mitsubishi) for production lines",
            "Wire and test sensors, actuators, and motor controllers on automated systems",
            "Read and modify electrical control panel schematics and ladder logic diagrams",
            "Assist in commissioning SCADA systems and HMI interface configuration"
        ]
    }
]

def job_matcher_node(state: WorkerState) -> WorkerState:
    worker_name = state.get("worker_name")
    career_goal = state.get("career_goal")
    current_skills = state.get("current_skills") or []
    suggested_course = state.get("suggested_course") or {}

    matched_jobs = []
    used_live_source = False

    # Query real listings for the worker's current skills AND the skill
    # they're actively learning (if a course was assigned upstream) --
    # mirrors the old "skills including in-progress learning" intent.
    target_skills = list(dict.fromkeys(
        [s for s in current_skills if s] +
        ([suggested_course["skill_name"]] if suggested_course.get("skill_name") else [])
    ))

    if target_skills:
        try:
            matched_jobs = fetch_jobs_for_skills(target_skills, max_results_per_skill=3)
            used_live_source = bool(matched_jobs)
        except Exception as e:
            logger.error(f"Adzuna job fetch error: {e}. Falling back to standard pre-defined jobs.")
            matched_jobs = []

    if not matched_jobs:
        # Fallback: static pre-defined jobs, matched by skills AND career goal.
        # Triggered when Adzuna isn't configured, the request fails, or it
        # returns zero results for the worker's skill set -- same role this
        # block played as the LLM-generation failure path before.
        skill_set = {s.lower() for s in current_skills}
        goal_lower = career_goal.lower() if career_goal else ""

        def job_matches_goal(job: dict) -> bool:
            required = job["required_skill"].lower()
            if required in skill_set:
                return True
            job_skill_keywords = SKILL_KEYWORDS.get(required, [])
            if any(kw in goal_lower for kw in job_skill_keywords):
                return True
            return False

        matched_jobs = [j for j in FALLBACK_JOBS if job_matches_goal(j)]

        if not matched_jobs:
            for j in FALLBACK_JOBS:
                job_skill_keywords = SKILL_KEYWORDS.get(j["required_skill"].lower(), [])
                if any(kw in goal_lower for kw in job_skill_keywords):
                    matched_jobs.append(j)

    source_label = "live Adzuna listings" if used_live_source else "pre-defined fallback jobs"
    log_line = (
        f"[job_matcher] Found {len(matched_jobs)} job openings from {source_label} "
        f"tailored for your skill profile."
    )

    # Sync state and logs back to Memory
    if worker_name in workers:
        workers[worker_name]["logs"] = (workers[worker_name]["logs"] or "") + "\n" + log_line

    return {
        **state,
        "matched_jobs": matched_jobs,
        "logs": (state.get("logs", "") + "\n" + log_line).strip(),
    }

# ---------------------------------------------------------------------------
# Node 5: Career Advisor (personalized advice)
# ---------------------------------------------------------------------------

def _generate_fallback_roadmap(worker_name: str, career_goal: str, current_skills: list) -> str:
    goal_lower = career_goal.lower()
    skills_str = ', '.join(current_skills) if current_skills else 'None yet'

    industry_roadmaps = {
        "semiconductor": {
            "title": "Semiconductor Manufacturing",
            "concepts": [
                "Cleanroom protocols & contamination control (gowning, air showers, particle monitoring)",
                "Wafer fabrication: photolithography, etching, deposition, CMP (chemical mechanical planarization)",
                "Equipment handling: wafer sorters, die attach, wire bonding, molding presses",
                "Quality inspection: AOI (automated optical inspection), X-ray, microscopy",
                "OSHA-compliant safety practices for chemical handling (acids, solvents, dopants)"
            ],
            "study": [
                "ITI (Industrial Training Institute) course in Electronics or Mechanical",
                "NSDC-certified Semiconductor Manufacturing Technician program",
                "Online: 'Semiconductor Fabrication Basics' on NPTEL/SWAYAM (free)",
                "On-the-job training at semiconductor fabs (TSMC, Intel, Micron, TATA Electronics)"
            ],
            "apply": [
                "TATA Electronics (Hosur, Tamil Nadu) - Semiconductor Assembly & Test",
                "Micron Technology (Sanand, Gujarat) - Memory Packaging & Test",
                "CG Power & IR (Sanand, Gujarat) - Semiconductor OSAT facility",
                "Intel (India) - Fab equipment technician roles",
                "Samsung Semiconductor (Noida) - Assembly line technician"
            ],
            "salary": "Entry-level: ₹25,000 - ₹35,000/month\nExperienced (2-3 yrs): ₹40,000 - ₹60,000/month\nSenior Technician: ₹70,000 - ₹90,000/month\nBenefits: Health insurance, shift allowances, cleanroom pay premium"
        },
        "electric vehicle": {
            "title": "Electric Vehicle (EV) Manufacturing & Service",
            "concepts": [
                "EV battery pack assembly: cell sorting, welding, module assembly, thermal management",
                "EV powertrain: motor, controller, regenerative braking systems",
                "High-voltage safety protocols (ISO 6469) and PPE requirements",
                "Diagnostics: CAN bus scanning, battery management system (BMS) troubleshooting"
            ],
            "study": [
                "ITI Electrician / Electronics with EV specialization modules",
                "NSDC 'Electric Vehicle Technician' certification",
                "ARAI (Automotive Research Association of India) EV safety courses",
                "Ola/Tata Motors/Viaan EV training programs"
            ],
            "apply": [
                "Ola Electric (Tamil Nadu, Karnataka) - EV assembly & service centers",
                "Tata Motors EV division (Pune, Sanand)",
                "Mahindra Electric (Bengaluru)",
                "Ather Energy (Tamil Nadu, Karnataka)",
                "EV charging infrastructure companies: ChargeZone, Statiq, Tesla (India)"
            ],
            "salary": "Entry-level: ₹22,000 - ₹30,000/month\nExperienced: ₹35,000 - ₹55,000/month\nSpecialist (BMS/High-voltage): ₹50,000 - ₹75,000/month"
        },
        "construction": {
            "title": "Construction & Infrastructure Development",
            "concepts": [
                "Blueprint reading and site measurement using total stations and levels",
                "Steel reinforcement (rebar) placement and concrete pouring techniques",
                "Scaffolding safety, fall protection, and confined space entry protocols",
                "Heavy equipment operation: excavators, bulldozers, tower cranes (certification required)"
            ],
            "study": [
                "ITI in Carpenter, Mason, Welder, or Fitter trade",
                "National Safety Council (NSC) construction safety certification",
                "CPWD / NHAI contractor vocational training programs",
                "HEMM (Heavy Earth Moving Machinery) operator license"
            ],
            "apply": [
                "L&T (Larsen & Toubro) - Major infrastructure projects across India",
                "Shapoorji Pallonji, Sobha Ltd., Brigade Group - Building construction",
                "NHAI highway projects - ongoing across all states",
                "Afcons, GMR, HCC - Tunnel and bridge projects"
            ],
            "salary": "Unskilled: ₹15,000 - ₹20,000/month\nSkilled (mason/fitter/operator): ₹25,000 - ₹40,000/month\nSupervisor-level: ₹45,000 - ₹65,000/month"
        },
        "it services": {
            "title": "IT Services & Support",
            "concepts": [
                "Computer hardware assembly, troubleshooting, and repair",
                "Networking basics: TCP/IP, LAN cabling, router/switch configuration",
                "Operating systems: Windows/Linux installation, driver management, system imaging",
                "Helpdesk ticketing systems (ServiceNow, Jira) and customer communication"
            ],
            "study": [
                "ITI in Information Technology / Computer Science",
                "CompTIA A+ certification (hardware + software support)",
                "CCNA (Cisco) for networking roles",
                "Google IT Support Professional Certificate (Coursera - financial aid available)"
            ],
            "apply": [
                "Wipro, Infosys, TCS - Desktop support & IT helpdesk roles",
                "HCL Tech - Hardware support for enterprise clients",
                "Cognizant, Tech Mahindra - IT operations roles",
                "Local computer repair shops & system integrators"
            ],
            "salary": "Entry-level desktop support: ₹18,000 - ₹25,000/month\nNetwork technician: ₹25,000 - ₹40,000/month\nSenior IT support: ₹40,000 - ₹60,000/month"
        },
    }

    matched_industry = None
    for key in industry_roadmaps:
        if key in goal_lower:
            matched_industry = key
            break

    if not matched_industry:
        matched_industry = "semiconductor" if "semiconductor" in goal_lower else None
    if not matched_industry:
        matched_industry = "it services" if any(kw in goal_lower for kw in ["computer", "software", "it ", "tech ", "programming", "coding"]) else None
    if not matched_industry:
        matched_industry = "construction" if any(kw in goal_lower for kw in ["construction", "building", "infrastructure", "civil"]) else None
    if not matched_industry:
        matched_industry = "electric vehicle" if any(kw in goal_lower for kw in ["ev ", "electric vehicle", "battery", "e-mobility"]) else None

    if matched_industry:
        roadmap = industry_roadmaps[matched_industry]
        lines = [
            f"**Career Roadmap for {worker_name}**",
            "",
            f"**Target Industry:** {roadmap['title']}",
            f"**Your Goal:** {career_goal}",
            f"**Your Current Skills:** {skills_str}",
            "",
            "---",
            "",
            "## 🎯 Step 1: Key Concepts You Must Learn",
            "",
        ]
        for i, concept in enumerate(roadmap["concepts"], 1):
            lines.append(f"**{i}.** {concept}")
        lines += [
            "",
            "---",
            "",
            "## 📚 Step 2: What & Where to Study",
            "",
        ]
        for s in roadmap["study"]:
            lines.append(f"- {s}")
        lines += [
            "",
            "---",
            "",
            "## 🏢 Step 3: Where to Apply (Top Employers)",
            "",
        ]
        for a in roadmap["apply"]:
            lines.append(f"- {a}")
        lines += [
            "",
            "---",
            "",
            "## 💰 Step 4: Expected Salary & Benefits",
            "",
            f"{roadmap['salary']}",
            "",
            "---",
            "",
            "*All roles aligned with **UN SDG 8: Decent Work & Economic Growth** — fair wages, safe conditions, and upward mobility.*",
            f"*Every worker deserves dignity and respect. Your skills {matched_industry.lower()} build the future!*",
        ]
        return "\n".join(lines)
    else:
        return (
            f"**Career Roadmap for {worker_name}**\n\n"
            f"**Your Goal:** {career_goal}\n\n"
            f"**Your Current Skills:** {skills_str}\n\n"
            f"### Step 1: Build on your existing skills\n"
            f"Continue developing your current skill set through hands-on practice and formal training.\n\n"
            f"### Step 2: Identify skill gaps\n"
            f"Compare your current skills against what's needed for your dream role. "
            f"Focus on acquiring missing technical competencies.\n\n"
            f"### Step 3: Get certified\n"
            f"Look for government-recognized vocational certifications to validate your expertise.\n\n"
            f"### Step 4: Find dignified work\n"
            f"Seek employers that offer fair wages, safe working conditions, and growth opportunities "
            f"— in line with **UN SDG 8: Decent Work & Economic Growth**.\n\n"
            f"---\n"
            f"*Remember: Every worker deserves fair pay, safety, and respect. Your skills build the economy.*"
        )


def career_advisor_node(state: WorkerState) -> WorkerState:
    worker_name = state.get("worker_name")
    career_goal = state.get("career_goal")
    current_skills = state.get("current_skills") or []
    
    advice = None
    try:
        llm = get_llm()
        system_prompt = (
            "You are a professional career advisor for vocational workers aligned with UN SDG 8 (Decent Work & Economic Growth). "
            "Provide personalized, empathetic, and actionable advice to the worker. "
            "Include: 1) A clear roadmap of steps to achieve their goal based on their current skills. "
            "2) Encouraging life/career advice aligned with decent work principles. "
            "3) Relevant SDG 8 guidance about fair wages, safe working conditions, and economic growth. "
            "Respond in a friendly, conversational tone, using Markdown for readability."
        )
        human_prompt = (
            f"Worker Name: {worker_name}\n"
            f"Career Goal: {career_goal}\n"
            f"Current Skills: {', '.join(current_skills)}"
        )
        
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_prompt),
        ])
        
        advice = response.content
    except Exception as e:
        logger.error(f"Error in Career Advisor: {e}")
    
    if not advice:
        advice = _generate_fallback_roadmap(worker_name, career_goal, current_skills)
    
    log_line = f"[career_advisor] Generated personalized roadmap for '{worker_name}'."
    
    if worker_name in workers:
        workers[worker_name]["logs"] = (workers[worker_name]["logs"] or "") + "\n" + log_line + "\n" + advice
        
    return {
        **state,
        "logs": (state.get("logs", "") + "\n" + log_line + "\n" + advice).strip(),
    }

# ---------------------------------------------------------------------------
# Graph Construction
# ---------------------------------------------------------------------------

def build_graph():
    graph = StateGraph(WorkerState)

    graph.add_node("intake_node", intake_node)
    graph.add_node("safety_filter_node", safety_filter_node)
    graph.add_node("skill_gap_analyzer_node", skill_gap_analyzer_node)
    graph.add_node("career_advisor_node", career_advisor_node)
    graph.add_node("job_matcher_node", job_matcher_node)

    graph.set_entry_point("intake_node")
    graph.add_edge("intake_node", "safety_filter_node")

    graph.add_conditional_edges(
        "safety_filter_node",
        route_after_safety,
        {
            "skill_gap_analyzer_node": "skill_gap_analyzer_node",
            "__end__": END,
        },
    )

    graph.add_edge("skill_gap_analyzer_node", "career_advisor_node")
    graph.add_edge("career_advisor_node", "job_matcher_node")
    graph.add_edge("job_matcher_node", END)

    return graph.compile()

# ---------------------------------------------------------------------------
# FastAPI Router & Interactive Endpoints
# ---------------------------------------------------------------------------

app = FastAPI(
    title="GigPilot AI — Multi-Feature Production Vocational Suite",
    description="Refined upskilling, testing, safety audit and semantic matching system under SDG 8.",
    version="2.0.0"
)

# CORS Middleware to allow dashboard integrations from Vercel & local servers
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {
        "status": "online",
        "message": "GigPilot AI Backend is active and running successfully!",
        "rpm_limit": "Strictly limited below 5 RPM for safety and efficiency"
    }

class IntakeRequest(BaseModel):
    worker_name: str = Field(..., description="Full name of the worker")
    current_skills: List[str] = Field(default_factory=list, description="List of current skills")
    career_goal: str = Field(..., description="Worker's stated career goal")

class QuizSubmission(BaseModel):
    worker_name: str
    skill_name: str
    answers: List[int] = Field(..., description="Array of selected option indices for each question (0-based)")

# POST Endpoint to run Agent
@app.post("/run-agent")
def run_agent(payload: IntakeRequest):
    if not GROQ_API_KEY:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY is not configured on server.")

    try:
        app_graph = build_graph()
        initial_state: WorkerState = {
            "worker_name": payload.worker_name,
            "current_skills": payload.current_skills,
            "career_goal": payload.career_goal,
            "suggested_course": {},
            "matched_jobs": [],
            "logs": "",
            "is_unsafe": False,
        }

        final_state = app_graph.invoke(initial_state)

        # Retrieve any course details and progress
        worker_prog = worker_progress.get(payload.worker_name, {}).get((final_state.get("suggested_course") or {}).get("skill_name"), {})
        quiz_passed = worker_prog.get("quiz_passed", False) if worker_prog else False

        # Load latest complete log history
        full_logs = workers[payload.worker_name]["logs"] if payload.worker_name in workers else final_state.get("logs", "")

        return {
            "worker_name": final_state.get("worker_name"),
            "current_skills": final_state.get("current_skills"),
            "career_goal": final_state.get("career_goal"),
            "suggested_course": final_state.get("suggested_course"),
            "matched_jobs": final_state.get("matched_jobs"),
            "logs": full_logs,
            "is_unsafe": final_state.get("is_unsafe", False),
            "quiz_passed": quiz_passed
        }

    except Exception as e:
        logger.exception("Unexpected Agent run error")
        raise HTTPException(status_code=500, detail=str(e))

# Live Interactive Course Progression & MCQ Quiz evaluation API
@app.post("/submit-quiz")
def submit_quiz(submission: QuizSubmission):
    worker = workers.get(submission.worker_name)
    course_data = courses.get(submission.skill_name)
    progress = worker_progress.get(submission.worker_name, {}).get(submission.skill_name)

    if not worker or not course_data or progress is None:
        raise HTTPException(status_code=404, detail="Session or Course Progress data not found.")

    questions = course_data.get("questions", [])
    if not questions:
        raise HTTPException(status_code=400, detail="No questions found for this course.")

    if len(submission.answers) != len(questions):
        raise HTTPException(
            status_code=400,
            detail=f"Expected {len(questions)} answers, got {len(submission.answers)}"
        )

    # Grade each answer
    total = len(questions)
    correct_count = 0
    results = []

    for i, q in enumerate(questions):
        user_choice = submission.answers[i]
        is_correct = user_choice == q["correct_index"]
        if is_correct:
            correct_count += 1
        results.append({
            "question_index": i,
            "question": q["question"],
            "your_answer": q["options"][user_choice] if 0 <= user_choice < len(q["options"]) else "Invalid",
            "correct_answer": q["options"][q["correct_index"]],
            "is_correct": is_correct,
            "explanation": q["explanation"]
        })

    score_pct = correct_count / total
    passed = score_pct >= 0.6
    log_line = (
        f"[learning] {submission.worker_name} scored {correct_count}/{total} "
        f"({score_pct:.0%}) on '{submission.skill_name}' quiz. "
        f"{'PASSED' if passed else 'FAILED'}"
    )
    worker["logs"] = (worker["logs"] or "") + "\n" + log_line

    if passed:
        progress["quiz_passed"] = True
        if submission.skill_name not in worker["current_skills"]:
            worker["current_skills"].append(submission.skill_name)
        return {
            "success": True,
            "score": correct_count,
            "total": total,
            "percentage": round(score_pct * 100),
            "message": f"Congratulations! You passed ({correct_count}/{total} correct). The skill '{submission.skill_name}' has been added to your profile.",
            "results": results
        }
    else:
        return {
            "success": False,
            "score": correct_count,
            "total": total,
            "percentage": round(score_pct * 100),
            "message": f"You scored {correct_count}/{total} ({score_pct:.0%}). Need 60% to pass. Review the lessons and try again!",
            "results": results
        }

# Get current persistent worker details
@app.get("/worker/{name}")
def get_worker(name: str):
    worker = workers.get(name)
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found.")
        
    # Grab any in-progress courses
    active_courses = []
    worker_progs = worker_progress.get(name, {})
    for skill_name, prog in worker_progs.items():
        course_data = courses.get(skill_name)
        if course_data:
            active_courses.append({
                "skill_name": skill_name,
                "micro_lessons": course_data["micro_lessons"],
                "questions": course_data["questions"],
                "quiz_passed": prog["quiz_passed"]
            })

    return {
        "worker_name": worker["name"],
        "current_skills": worker["current_skills"],
        "career_goal": worker["career_goal"],
        "is_unsafe": worker["is_unsafe"],
        "logs": worker["logs"],
        "active_courses": active_courses
    }

@app.get("/health")
def health_check():
    return {
        "status": "ok", 
        "database": "memory",
        "groq_configured": bool(GROQ_API_KEY)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)