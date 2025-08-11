# app.py — FastAPI + sqlite3 storage, JSON Resume aware

from typing import Dict, List, Optional
from datetime import datetime
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3, json, os

DB_PATH = os.environ.get("RESUME_DB", "resumes.db")

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

# ---------- FastAPI ----------
app = FastAPI(title="Resume API (JSON Resume)")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
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

@app.post("/analyze/gaps", response_model=AnalyzeGapsResponse)
def analyze_gaps(req: AnalyzeGapsRequest):
    resume = req.resume or (load_latest_resume(req.user_id) if req.user_id else None)
    if not resume:
        raise HTTPException(status_code=400, detail="Provide resume or user_id with a saved resume")

    # Minimal, generic questions (you’ll plug your own logic here)
    qs = [
        "Which 2–3 accomplishments best match this role?",
        "Provide 2–3 metrics that show impact relevant to this job.",
        "Describe your most relevant project (scope, stack, impact).",
        "List tools/tech you’ve used that map to the posting.",
        "Any certifications or training that apply?",
        "What domain expertise should be emphasized?",
        "Which soft skills are strongest and demonstrable here?",
        "Preferred location/work setup and availability?",
        "Any gaps to explain (dates, tool, industry)?",
        "Anything to de-emphasize for this role?",
    ]

    # Optional: nudge work-specific prompts
    work_names = [w.get("name") for w in (resume.get("work") or []) if isinstance(w, dict) and w.get("name")]
    for n in work_names[:3]:
        qs.insert(0, f"Give a quantified example from '{n}' relevant to this role.")

    return AnalyzeGapsResponse(questions=qs[:10])

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
