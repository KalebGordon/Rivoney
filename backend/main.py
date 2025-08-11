# app.py — FastAPI + sqlite3 storage, JSON Resume aware

from typing import Dict, List, Optional
from datetime import datetime
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3, json, os

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

    system_msg = f"""
        You analyze a candidate's JSON Resume and a job description to propose only *meaningful* follow-up questions that would materially improve a tailored résumé for this role.

        Output rules:
        - Return at most {max_q} questions; return an empty list if none are needed.
        - Questions must be concise, résumé-focused, and answerable with the candidate’s professional history (work, projects, skills, education, certifications).
        - Prefer questions that elicit quantifiable impact, scope/scale, specific tools/tech, domain context, constraints, outcomes, or verifiable artifacts (e.g., links to repos, publications, portfolios).

        Do NOT ask about:
        - Personal preferences or logistics (commute, relocation, hybrid/remote, schedule, availability, culture fit, salary, work authorization).
        - Confirmations of tenure (e.g., “Do you have X years of Y?”). If tenure is relevant, ask for concrete examples that demonstrate proficiency instead.
        - Anything already stated clearly in the résumé/JD, or generic/boilerplate questions.
        - Soft, subjective prompts without résumé value (e.g., “Are you comfortable with …?”).

        Quality constraints:
        - No explanations or preambles—only the questions.
        - No duplicates; each question should target a distinct, high-value gap.
        - If coverage is sufficient, return [].

        Return format is a JSON object with a single key "questions" mapping to an array of strings.
        """.strip()

    user_msg = (
        "JOB DESCRIPTION:\n"
        f"{job_description}\n\n"
        "JSON RESUME:\n"
        f"{resume_snippet}\n\n"
        "Output strictly as a JSON object with a single key `questions` whose value is an array of strings."
    )

    # Ask the model to strictly return JSON
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
        # Network/TLS/proxy/VPN issues reaching OpenAI
        raise HTTPException(
            status_code=502,
            detail="Could not reach OpenAI (network/TLS). Check internet/VPN/firewall and API key."
        ) from e
    except RateLimitError as e:
        # Too many requests / quota
        raise HTTPException(status_code=429, detail="OpenAI rate limit. Please retry shortly.") from e
    except APIStatusError as e:
        # Surfaces upstream HTTP status from OpenAI (e.g., 401 if key is invalid)
        raise HTTPException(status_code=e.status_code, detail=f"OpenAI error: {e.message}") from e
    except Exception as e:
        # Any other unexpected client error
        raise HTTPException(status_code=500, detail="Unexpected error calling OpenAI.") from e

    content = resp.choices[0].message.content or "{}"
    try:
        data = json.loads(content)
        items = data.get("questions", [])
        # normalize: strings only, unique, trimmed, <= max_q
        seen, clean = set(), []
        for q in items:
            if not isinstance(q, str):
                continue
            q = q.strip()
            if q and q not in seen:
                clean.append(q)
                seen.add(q)
            if len(clean) >= max_q:
                break
        return clean
    except Exception:
        # Fallback: if the model somehow returns non-JSON, return empty
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

class AnalyzeGapsResponse(BaseModel):
    questions: List[str]

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
    # Hardcode default for now
    if not req.user_id:
        req.user_id = "demo"

    resume = req.resume or (load_latest_resume(req.user_id) if req.user_id else None)
    if not resume:
        raise HTTPException(status_code=400, detail="Provide resume or user_id with a saved resume")

    # NEW: call OpenAI to produce up to 10 questions (or none)
    qs = generate_gap_questions(resume=resume, job_description=req.job_description, max_q=10)

    return AnalyzeGapsResponse(questions=qs)

@app.post("/generate", response_model=GenerateResponse)
def generate(req: GenerateRequest):
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
