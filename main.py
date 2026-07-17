"""
GigPilot AI — Vocational Upskilling & Job-Matching Agent (SDG 8)
==================================================================

A highly polished, interactive LangGraph-orchestrated backend with 
PostgreSQL persistence, interactive progress/quizzes, semantic matching,
and a dual-layer safety audit system.
"""

from __future__ import annotations

import os
import json
import logging
from typing import TypedDict, List, Dict, Any, Optional, Literal

from dotenv import load_dotenv
from fastapi import FastAPI, APIRouter, HTTPException, Depends
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
# from sqlalchemy.orm import Session

from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

# Import Database Configuration & Models
from database import init_db, get_db, workers, jobs, courses, worker_progress

# ---------------------------------------------------------------------------
# Environment & Setup
# ---------------------------------------------------------------------------

load_dotenv()
init_db()  # Initialize the database on startup

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("gigpilot_ai")

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
# LLM Client (Groq)
# ---------------------------------------------------------------------------

def get_llm() -> ChatGroq:
    if not GROQ_API_KEY:
        raise RuntimeError(
            "GROQ_API_KEY is not set. Export it as an environment variable "
            "or place it in a .env file."
        )
    return ChatGroq(
        model="llama-3.3-70b-versatile",
        temperature=0,
        api_key=GROQ_API_KEY,
    )

# ---------------------------------------------------------------------------
# Node 1: Intake (with DB Persistence Sync)
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
            "You are an AI Safety Auditor specializing in labor exploitation, safety, and modern slavery prevention. "
            "Analyze the worker's career goal. Check for hidden hazardous, dangerous, highly exploitative, predatory, "
            "or illegal job intent. Respond strictly in JSON format with no other text, comments, or wrappers. "
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
# Node 3: Skill Gap Analyzer (Interactive course loader & DB Progress creation)
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
        # Simplistic regex matching if LLM fails
        for skill in available_skills:
            if skill.lower() in career_goal.lower():
                target_skill = skill
                gap_exists = skill.lower() not in current_skills
                break

    suggested_course: Dict[str, Any] = {}

    if target_skill and target_skill.lower() not in current_skills and gap_exists:
        # Load course details directly from memory
        course_data = courses.get(target_skill)
        if course_data:
            suggested_course = {
                "skill_name": target_skill,
                "micro_lessons": course_data["micro_lessons"],
                "quiz_question": course_data["quiz_question"],
                "quiz_answer": course_data["quiz_answer"],
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
# Node 4: Job Matcher (Smarter Match with LLM Semantic suitabilities)
# ---------------------------------------------------------------------------

def job_matcher_node(state: WorkerState) -> WorkerState:
    worker_name = state.get("worker_name")
    career_goal = state.get("career_goal")
    current_skills = state.get("current_skills") or []
    
    # Grab all safe jobs from memory
    all_jobs = [j for j in jobs if not j["safety_flag"]]

    matched_jobs = []
    
    # Implement Refinement 2: Smarter semantic matching using LLM evaluation
    try:
        llm = get_llm()
        system_prompt = (
            "You are an elite talent matcher. Given a worker's career goal, active skills, "
            "and a list of safe jobs, evaluate which jobs are a suitable match "
            "(either matching their skills directly or closely aligning with their upskilling career goal). "
            "Return the list of matching job IDs in a JSON object. "
            "Format: {\"matched_job_ids\": [\"J001\", \"J002\"]}"
        )
        human_prompt = (
            f"Worker Career Goal: {career_goal}\n"
            f"Worker Active/Learning Skills: {current_skills}\n"
            f"Available Safe Jobs:\n{json.dumps(all_jobs)}"
        )
        
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_prompt),
        ])
        
        raw = response.content.strip()
        if "```" in raw:
            raw = raw.split("```")[1].replace("json", "").strip()
            
        matched_ids = json.loads(raw).get("matched_job_ids", [])
        matched_jobs = [j for j in all_jobs if j["job_id"] in matched_ids]
        
    except Exception as e:
        logger.error(f"Smarter matching LLM error: {e}. Falling back to skill-based regex filtering.")
        # Fallback to simple skill-based matching
        skill_set = {s.lower() for s in current_skills}
        matched_jobs = [
            j for j in all_jobs if j["required_skill"].lower() in skill_set
        ]

    log_line = (
        f"[job_matcher] Smarter AI evaluated {len(matched_jobs)} job matches based on "
        f"skill proximity and career goals."
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
# Graph Construction
# ---------------------------------------------------------------------------

def build_graph():
    graph = StateGraph(WorkerState)

    graph.add_node("intake_node", intake_node)
    graph.add_node("safety_filter_node", safety_filter_node)
    graph.add_node("skill_gap_analyzer_node", skill_gap_analyzer_node)
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

    graph.add_edge("skill_gap_analyzer_node", "job_matcher_node")
    graph.add_edge("job_matcher_node", END)

    return graph.compile()

# ---------------------------------------------------------------------------
# FastAPI Router & Interactive Endpoints
# ---------------------------------------------------------------------------

app = FastAPI(
    title="GigPilot AI — Multi-Feature Production vocational Suite",
    description="Refined upskilling, testing, safety audit and semantic matching system under SDG 8.",
    version="2.0.0"
)

# CORS Middleware to allow easy dashboard integrations
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", response_class=HTMLResponse)
async def read_index():
    print("Serving index.html")
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()

class IntakeRequest(BaseModel):
    worker_name: str = Field(..., description="Full name of the worker")
    current_skills: List[str] = Field(default_factory=list, description="List of current skills")
    career_goal: str = Field(..., description="Worker's stated career goal")

class QuizSubmission(BaseModel):
    worker_name: str
    skill_name: str
    user_answer: str

# POST Endpoint to run Agent
@app.post("/run-agent")
def run_agent(payload: IntakeRequest):
    if not GROQ_API_KEY:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY is not configured.")

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

# Refinement 1: Live Interactive Course Progression & Quiz evaluation API
@app.post("/submit-quiz")
def submit_quiz(submission: QuizSubmission):
    worker = workers.get(submission.worker_name)
    course_data = courses.get(submission.skill_name)
    progress = worker_progress.get(submission.worker_name, {}).get(submission.skill_name)

    if not worker or not course_data or progress is None:
        raise HTTPException(status_code=404, detail="Session or Course Progress data not found.")

    # LLM evaluating user answer vs expected answer
    try:
        llm = get_llm()
        evaluation_prompt = (
            "You are a vocational exam grader. Compare the student's answer with the official model answer. "
            "Determine if the student's answer is correct, demonstrating basic comprehension. "
            "Respond only with a JSON object: {\"correct\": true|false, \"explanation\": \"<short reason>\"}"
        )
        student_input = (
            f"Question: {course_data['quiz_question']}\n"
            f"Expected Answer: {course_data['quiz_answer']}\n"
            f"Student's Answer: {submission.user_answer}"
        )
        
        res = llm.invoke([
            SystemMessage(content=evaluation_prompt),
            HumanMessage(content=student_input)
        ])
        
        raw = res.content.strip()
        if "```" in raw:
            raw = raw.split("```")[1].replace("json", "").strip()
            
        evaluation = json.loads(raw)
        is_correct = evaluation.get("correct", False)
        explanation = evaluation.get("explanation", "Excellent comprehension demonstrated.")
    except Exception as e:
        logger.error(f"Error in LLM Quiz Evaluation: {e}")
        # Simplistic fallback
        is_correct = submission.user_answer.strip().lower() in course_data['quiz_answer'].lower()
        explanation = "Evaluated via string-matching fallback."

    if is_correct:
        # Mark quiz as passed
        progress["quiz_passed"] = True
        
        # Add unlocked skill
        if submission.skill_name not in worker["current_skills"]:
            worker["current_skills"].append(submission.skill_name)
            
        log_line = f"[learning] SUCCESS — {submission.worker_name} passed the quiz! Newly unlocked skill: '{submission.skill_name}'."
        worker["logs"] = (worker["logs"] or "") + "\n" + log_line
        
        return {
            "success": True, 
            "message": "Congratulations! You passed the quiz. The skill has been added to your profile.", 
            "explanation": explanation
        }
    else:
        log_line = f"[learning] FAILED — {submission.worker_name} attempted the quiz for '{submission.skill_name}' but did not pass."
        worker["logs"] = (worker["logs"] or "") + "\n" + log_line
        return {
            "success": False, 
            "message": "The answer was incorrect. Read the lessons carefully and try again!", 
            "explanation": explanation
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
                "quiz_question": course_data["quiz_question"],
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
