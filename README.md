# GigPilot AI

**AI-Powered Vocational Upskilling & Dignified Job Matching**

Aligning blue-collar workers with safe, fair & sustainable employment — built around **UN SDG 8: Decent Work & Economic Growth**.

![Version](https://img.shields.io/badge/version-2.1-blue)
![Status](https://img.shields.io/badge/status-prototype-orange)
![SDG](https://img.shields.io/badge/SDG-8%20Decent%20Work-green)

---

## Overview

GigPilot AI is an intelligent agent system that helps vocational and blue-collar workers identify skill gaps, complete micro-learning courses with assessments, and get matched to safe, fairly paid job opportunities.

Built with a **LangGraph-orchestrated AI pipeline** and powered by **Groq's Llama 3.3-70B**, the platform features a dual-layer safety system designed to prevent worker exploitation — something no existing vocational job platform offers.

> "The only AI agent that safely upskills vocational workers and matches them to dignified, fairly paid jobs — with built-in dual-layer safety auditing aligned with UN SDG 8."

**High-level concept:** Duolingo for vocational skills + LinkedIn for dignified blue-collar jobs — with built-in safety auditing.

---

## The Problem

Three key challenges facing vocational workers in India:

| # | Problem | Detail |
|---|---------|--------|
| 01 | **Lack of skill gap visibility** | Blue-collar workers have no structured way to assess their current skills against industry requirements or know what training they need to advance into higher-paying fields (solar, semiconductor, automation). |
| 02 | **No safety & dignity filtering** | Existing job platforms don't filter for worker safety, fair wages, or dignified conditions. Workers are vulnerable to exploitative listings and unfair labor practices. |
| 03 | **Disconnected training-to-job pipeline** | Vocational training (govt ITIs, online tutorials) operates independently from job placement, leaving workers without a direct pathway to employment. |

**Scale of the problem:**
- **400M+** informal workers in India
- **65%** of workers lack formal skilling access
- **3x** wage gap between skilled & unskilled labor
- **87%** of job platforms lack safety filters

---

## Solution Architecture

A **LangGraph AI agent pipeline** with 5 specialized nodes:

```
Worker Intake → Dual-Layer Safety Filter → Skill Gap Analyzer → Career Advisor → Job Matcher
```

1. **Worker Intake** — Worker enters name, current skills & desired career goal
2. **Dual-Layer Safety Filter** — Keyword blocklist + LLM safety auditor blocks exploitation
3. **Skill Gap Analyzer** — LLM compares skills vs. goal, assigns relevant micro-learning courses
4. **Career Advisor** — Generates a personalized 4-step career roadmap (concepts / study / employers / salary)
5. **Job Matcher** — Fetches real jobs from the Adzuna API; falls back to curated dignified jobs

**Platform building blocks:**

| Component | Detail |
|---|---|
| 7 Vocational Courses | Solar, Electrical, Plumbing, HVAC, Semiconductor, CNC, Automation/PLC |
| MCQ Quiz System | 60% passing threshold unlocks skills in worker profile |
| Dual Data Sources | Adzuna API (real-time) + 7 curated dignified fallback jobs |
| In-Memory State | No database required; state persists per worker session |

---

## Unique Value Proposition

| Pillar | What it means |
|---|---|
| **Safety First** | Dual-layer safety audit (keyword blocklist + LLM auditor) prevents exploitation before it reaches workers |
| **Integrated Pipeline** | Tight coupling of upskilling → certification → job matching in a single seamless agent flow |
| **SDG-Aligned** | Built from day one to advance UN SDG 8: Decent Work & Economic Growth |
| **AI-Powered** | LangGraph orchestration with Groq's Llama 3.3-70B for intelligent skill gap analysis & career roadmaps |

---

## Unfair Advantage

1. **Dual-Layer Safety Audit** — A deterministic keyword blocklist (Layer 1) combined with an LLM-powered safety auditor (Layer 2, Groq Llama 3.3-70B). Layer 1 catches known scam/fraud patterns instantly; Layer 2 detects subtle exploitative patterns, hidden fees, and unsafe conditions that keyword filters would miss.
2. **Tight Upskill-to-Placement Coupling** — Unlike platforms offering training *or* job matching, GigPilot AI integrates both in a single LangGraph pipeline, from intake to safety check to skill analysis to micro-learning to career roadmap to job matching in one uninterrupted flow.
3. **SDG 8 Alignment by Design** — Every design decision, from the safety audit to the curated dignified job database, serves UN SDG 8 — embedded in the architecture, not bolted on.
4. **LangGraph + Groq Architecture** — State-graph orchestration with conditional edges and graceful degradation: when the LLM is unavailable, the system falls back to deterministic keyword-based logic.

---

## Key Metrics

| Metric | What it tracks | Category |
|---|---|---|
| Workers Onboarded | Total registered workers in the system | Primary growth indicator |
| Skill Gaps Identified | Gaps detected by LLM analysis per worker | Engagement metric |
| Courses Completed | Micro-learning courses finished with 60%+ quiz | Learning outcome |
| Job Matches Served | Safe job listings presented to workers | Placement metric |
| Safety Blocks Triggered | Career goals blocked by dual-layer audit | Trust & safety |

**Additional tracking:** quiz pass rates per course, Adzuna API hit rate, career roadmaps generated, and average time-to-placement.

---

## Channels

| Channel | Status | Description |
|---|---|---|
| Direct Web Dashboard | Live | Vercel-hosted SPA (vanilla JS + Tailwind CSS), mobile-responsive, CORS-enabled |
| CSR & Govt Portal Embedding | Available | Embeddable widget for corporate CSR programs and government skilling initiatives |
| WhatsApp Chatbot | Planned | Future channel targeting India's 400K+ WhatsApp user base for rural, mobile-first outreach |
| Training Center Partnerships | In Progress | Partnerships with NSDC and ITI training centers; on-ground field agent support |

**Strategy:** Start digital (web dashboard for early adopters) → expand through B2B partnerships (CSR/govt portals for scale) → penetrate rural markets via WhatsApp + field agents.

---

## Customer Segments

**Primary — Vocational & gig workers in India:**
Electricians · Plumbers · Solar Installers · CNC Operators · HVAC Technicians · Semiconductor Technicians · Automation Technicians

**Government Skilling Initiatives:**
- NSDC (National Skill Development Corporation)
- ITI (Industrial Training Institutes)
- State-level skilling missions

**CSR Programs & Enterprises:**
- Manufacturing firms seeking skilled blue-collar talent
- Infrastructure companies (solar, construction, HVAC)
- CSR teams needing measurable SDG 8 impact reporting
- Ethical employers wanting verified, safety-checked hires

---

## Cost Structure

| Category | Item | Cost |
|---|---|---|
| Fixed | Vercel Hosting (Frontend) | $20/mo (Pro tier) |
| Fixed | Render Hosting (Backend) | $7/mo (Starter tier) |
| Fixed | Domain & DNS | $15/yr |
| Variable | Groq LLM API (Llama 3.3-70B) | ~$0.59/M input · ~$0.79/M output tokens |
| Variable | Adzuna API | Free tier (limited) · Premium ~$100/mo |
| People | Backend Engineer (Python/LangGraph) | Contract / part-time |
| People | Frontend Developer | Contract / part-time |
| People | Domain Expert (Vocational Training) | Advisory |
| Zero-cost | Database | In-memory state — no DB needed |
| Zero-cost | LLM Fallback | Deterministic keyword logic when LLM is down |
| Zero-cost | DevOps | Minimal — Vercel + Render handle infra |

**Estimated monthly run rate:** ~$50–$200 (prototype phase). Highly scalable — incremental workers add minimal marginal cost, and the in-memory architecture eliminates database overhead entirely.

---

## Revenue Streams

| Stream | Type | Model |
|---|---|---|
| B2B Licensing | Primary | Annual subscription to CSR programs, government skilling initiatives, and corporate training departments; tiered by worker volume, includes white-label & custom integration |
| Premium Job Listings | Secondary | Listing fee for ethical employers for prioritized matching, verified safety badges, and skill-match guarantees |
| API-as-a-Service | Enterprise | Usage-based access to the safety audit, skill gap analysis, and career roadmap generation pipeline |
| Free Tier (Current) | Growth & Impact | v2.1 prototype is free and open to build the user base, demonstrate SDG 8 impact, and attract grant/CSR funding |

**Roadmap:**
- **Phase 1 (2026):** Free prototype — build user base, validate impact, secure CSR/grant funding
- **Phase 2 (2027):** Launch B2B licensing with 3–5 enterprise partners
- **Phase 3 (2028):** Add premium listings & API-as-a-Service

---

## UN SDG 8 Alignment

GigPilot AI is built around **UN Sustainable Development Goal 8: Decent Work & Economic Growth**.

| Target | Focus | How GigPilot AI addresses it |
|---|---|---|
| **8.5** | Full employment and decent work | Equal pay for equal work, safe working environments for all workers including migrants and those in precarious employment |
| **8.6** | Youth NEET reduction | Substantially reduce the proportion of youth not in employment, education, or training via accessible skilling pathways |
| **8.8** | Labor rights and safe work | Protect labor rights and promote safe, secure working environments, particularly for migrant workers and women in precarious work |

**In practice, GigPilot AI:**
- ✓ Upskills marginalized blue-collar workers with industry-relevant vocational courses
- ✓ Filters job listings for safety, dignity, and fair wages using a dual-layer AI audit
- ✓ Creates a direct pathway from skill acquisition to dignified employment
- ✓ Generates personalized career roadmaps for long-term economic growth

---

## Tech Stack

- **Orchestration:** LangGraph (state-graph agent pipeline with conditional edges & fallback logic)
- **LLM:** Groq — Llama 3.3-70B
- **Frontend:** Vanilla JavaScript + Tailwind CSS (SPA), hosted on Vercel
- **Backend:** Python, hosted on Render
- **Job Data:** Adzuna API (real-time) + curated dignified job fallback list
- **State:** In-memory (no database)

---

## Project Status

| | |
|---|---|
| **Version** | 2.1 |
| **Status** | Prototype (free & open) |
| **SDG Alignment** | SDG 8 — Decent Work & Economic Growth |

---

## License

*Add your license here.*

## Contact / Team

*Add team / contact details here.*
