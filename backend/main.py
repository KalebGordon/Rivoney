# app.py — FastAPI + sqlite3 storage, JSON Resume aware
from __future__ import annotations
from typing import Dict, List, Optional
from datetime import datetime
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3, json, os
from typing import Literal


from dotenv import load_dotenv
load_dotenv()

from openai import OpenAI, APIConnectionError, RateLimitError, APIStatusError
client = OpenAI(timeout=30, max_retries=2)

DB_PATH = os.environ.get("RESUME_DB", "resumes.db")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o")  # override if you want

def get_conn():
    return sqlite3.connect(DB_PATH)

def init_db():
    with get_conn() as con:
        con.execute("""
          CREATE TABLE IF NOT EXISTS resumes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            version INTEGER NOT NULL,
            json_resume TEXT NOT NULL,
            created_at TEXT NOT NULL
          )
        """)
init_db()

def next_version_for(user_id: str) -> int:
    with get_conn() as con:
        cur = con.execute("SELECT MAX(version) FROM resumes WHERE user_id = ?", (user_id,))
        row = cur.fetchone()
        return (row[0] or 0) + 1

def load_latest_resume(user_id: str) -> Dict:
    with get_conn() as con:
        cur = con.execute(
            "SELECT json_resume FROM resumes WHERE user_id = ? ORDER BY version DESC LIMIT 1",
            (user_id,),
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="No resume found for user")
        return json.loads(row[0])
    
def generate_gap_questions(resume: Dict, job_description: str, max_q: int = 10) -> List[str]:
    """
    Uses OpenAI to analyze resume + JD and produce up to max_q specific, non-duplicative questions.
    If there are no meaningful gaps, returns an empty list.
    """
    # Safety: keep resume brief-ish in prompt to avoid bloating tokens
    resume_snippet = json.dumps(resume, ensure_ascii=False)

    system_msg = """
        You analyze a candidate’s JSON Resume and a job description to propose only meaningful, atomic follow-up questions that will improve the résumé for this role AND remain reusable for future roles.

        Optimization goals (in order):
        1) Prefer portable, résumé-worthy facts (tools used, scope/scale, measurable impact, artifacts, compliance) over JD-specific one-offs.
        2) Each question should elicit a single bullet-ready fragment (no first-person, past tense if completed, present for ongoing).
        3) Maximize searchability (keywords), credibility (metrics/artifacts), and clarity (scope/role).

        Do NOT ask:
        - Logistics/personal items (commute, relocation, schedule, salary, authorization, culture fit).
        - Tenure confirmations (“X years of Y”). Instead, elicit evidence (projects, outcomes, responsibilities).
        - Anything already present or generic duplicates.
        - Cover-letter prompts (“describe your passion…”, “are you comfortable with…”).

        Output rules:
        - Return at most {max_q} questions; return [] if no high-value gaps.
        - No preambles/explanations. No duplicates.
        - Each question must include brief guidance telling the user to answer like a résumé bullet, plus a fill-in template and an example.

        Return STRICT JSON as:
        {{
        "questions": [
            {{
            "question": "concise, atomic prompt (e.g., 'Data quality & governance impact using specific tools?')",
            "answer_hint": "One sentence telling the user to answer as a résumé bullet (no 'I', start with verb, include tools, scope, metric, outcome, compliance if relevant).",
            "bullet_skeleton": "Verb + what + using <tools> on <scope> to <outcome> (<metric>); <compliance/standard>",
            "example_bullet": "Performed unit and schema tests on 200+ ETL jobs with PyTest & Great Expectations; reduced data defects 37%; ensured DoD/USACE/EPA compliance.",
            "target_section": "one of: work | projects | skills | education | certifications",
            "target_anchor": "company or project name if known, else null",
            "suggested_fields": ["e.g., highlights", "keywords"],
            "skill_tags": ["normalized keywords implied by the question"],
            "evidence_type": "one of: metric | artifact | responsibility | toolstack | scope | outcome | compliance",
            "priority": "high | medium"
            }}
        ]
        }}
    """.strip().format(max_q=max_q)

    user_msg = (
        "JOB DESCRIPTION:\n"
        f"{job_description}\n\n"
        "JSON RESUME:\n"
        f"{resume_snippet}\n\n"
        "Return strictly the JSON object with the fields described in the system message."
    )

    try:
        resp = client.chat.completions.create(
            model=OPENAI_MODEL,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.2,
        )
    except APIConnectionError as e:
        raise HTTPException(status_code=502, detail="Could not reach OpenAI (network/TLS). Check VPN/proxy, allowlist api.openai.com:443, or set HTTPS_PROXY.") from e
    except RateLimitError as e:
        raise HTTPException(status_code=429, detail="OpenAI rate limit. Please retry shortly.") from e
    except APIStatusError as e:
        raise HTTPException(status_code=e.status_code, detail=f"OpenAI error: {e.message}") from e
    except Exception as e:
        raise HTTPException(status_code=500, detail="Unexpected error calling OpenAI.") from e

    content = resp.choices[0].message.content or "{}"
    try:
        data = json.loads(content)
        raw_items = data.get("questions", [])
        out: List[QuestionItem] = []
        seen_texts = set()
        for item in raw_items:
            if isinstance(item, str):
                qtext = item.strip()
                if not qtext:
                    continue
                qi = QuestionItem(question=qtext)
            elif isinstance(item, dict):
                # tolerate partial objects; ensure question text exists
                qtext = str(item.get("question", "")).strip()
                if not qtext:
                    continue
                try:
                    qi = QuestionItem(**{**item, "question": qtext})
                except Exception:
                    # if fields are malformed, keep minimally valid
                    qi = QuestionItem(question=qtext)
            else:
                continue

            if qi.question not in seen_texts:
                out.append(qi)
                seen_texts.add(qi.question)
            if len(out) >= max_q:
                break
        return out
    except Exception:
        return []

# ---------- FastAPI ----------
app = FastAPI(title="Resume API (JSON Resume)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        # add more if needed: "http://localhost:5173", "http://127.0.0.1:5173",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
    max_age=3600,
)

# ---------- Schemas ----------
class SaveResumeRequest(BaseModel):
    user_id: str
    resume: Dict  # JSON Resume document

class SaveResumeResponse(BaseModel):
    user_id: str
    version: int
    created_at: str

class AnalyzeGapsRequest(BaseModel):
    user_id: Optional[str] = None
    job_description: str
    resume: Optional[Dict] = None  # optional, otherwise load via user_id

class QuestionItem(BaseModel):
    question: str
    target_section: Optional[Literal["work", "projects", "skills", "education", "certifications"]] = None
    target_anchor: Optional[str] = None
    suggested_fields: Optional[List[str]] = None
    skill_tags: Optional[List[str]] = None
    evidence_type: Optional[Literal["metric", "artifact", "responsibility", "toolstack", "scope", "outcome", "compliance"]] = None
    priority: Optional[Literal["high", "medium"]] = "medium"


class AnalyzeGapsResponse(BaseModel):
    questions: List[QuestionItem]

class AnswerRow(BaseModel):
    text: str
    experience: Optional[str] = None
    enhance: bool = False

class GenerateRequest(BaseModel):
    user_id: Optional[str] = None
    job_description: str
    answers: Dict[int, List[AnswerRow]]
    resume: Optional[Dict] = None

class GenerateResponse(BaseModel):
    resume: Dict  # JSON Resume tailored copy

# ---------- Endpoints ----------
@app.post("/resume/save", response_model=SaveResumeResponse)
def save_resume(req: SaveResumeRequest):
    version = next_version_for(req.user_id)
    now = datetime.utcnow().isoformat() + "Z"
    with get_conn() as con:
        con.execute(
            "INSERT INTO resumes (user_id, version, json_resume, created_at) VALUES (?, ?, ?, ?)",
            (req.user_id, version, json.dumps(req.resume), now),
        )
    return SaveResumeResponse(user_id=req.user_id, version=version, created_at=now)

@app.get("/resume/latest")
def get_latest_resume(user_id: str = Query(...)):
    return {"resume": load_latest_resume(user_id)}

@app.get("/template/options")
def template_options(user_id: str = Query("demo")):
    try:
        resume = load_latest_resume(user_id)
        names = []
        for w in (resume.get("work") or []):
            if isinstance(w, dict):
                name = w.get("name") or w.get("company")
                if name:
                    names.append(name)
        # unique, keep order
        seen, opts = set(), []
        for n in names:
            if n not in seen:
                seen.add(n)
                opts.append(n)
        return {"options": opts or ["Experience 1"]}
    except HTTPException:
        # If no resume yet, return a harmless default
        return {"options": ["Experience 1"]}


@app.post("/analyze/gaps", response_model=AnalyzeGapsResponse)
def analyze_gaps(req: AnalyzeGapsRequest):
    if not req.user_id:
        req.user_id = "demo"
    resume = req.resume or (load_latest_resume(req.user_id) if req.user_id else None)
    if not resume:
        raise HTTPException(status_code=400, detail="Provide resume or user_id with a saved resume")
    qs = generate_gap_questions(resume=resume, job_description=req.job_description, max_q=10)
    return AnalyzeGapsResponse(questions=qs)

@app.post("/generate", response_model=GenerateResponse)
def generate(req: GenerateRequest):
    # Hardcode default for now
    if not req.user_id:
        req.user_id = "demo"
        
    base = req.resume or (load_latest_resume(req.user_id) if req.user_id else None)
    if not base:
        raise HTTPException(status_code=400, detail="Provide resume or user_id with a saved resume")

    tailored = json.loads(json.dumps(base))  # deep copy

    # Merge answers into first work entry highlights; keep JSON Resume shape
    if "work" not in tailored or not isinstance(tailored["work"], list):
        tailored["work"] = [{}]
    if not tailored["work"]:
        tailored["work"].append({})
    first_work = tailored["work"][0]

    texts: List[str] = []
    for rows in req.answers.values():
        for r in rows:
            t = (r.text or "").strip()
            if t:
                texts.append(t if t.endswith(".") else t + ".")

    # ensure highlights list
    highlights = first_work.get("highlights")
    if not isinstance(highlights, list):
        highlights = []
    seen = set(highlights)
    for t in texts[:5]:
        if t not in seen:
            highlights.append(t); seen.add(t)
    first_work["highlights"] = highlights
    tailored["work"][0] = first_work

    # fill basics.summary if empty
    basics = tailored.setdefault("basics", {})
    if not basics.get("summary") and texts:
        basics["summary"] = " ".join(texts[:3])[:600]

    # attach provenance
    meta = tailored.setdefault("meta", {})
    meta["generatedAt"] = datetime.utcnow().isoformat() + "Z"
    meta["source"] = "rivoney"

    return GenerateResponse(resume=tailored)
