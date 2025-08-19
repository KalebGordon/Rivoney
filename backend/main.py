# app.py — FastAPI + sqlite3 storage, JSON Resume aware
from __future__ import annotations
from difflib import get_close_matches
from typing import Dict, List, Optional, Literal
from datetime import datetime
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ValidationError
import sqlite3, json, os
import copy

from dotenv import load_dotenv
load_dotenv()

from openai import OpenAI, APIConnectionError, RateLimitError, APIStatusError

# ----- Config -----
client = OpenAI(timeout=60, max_retries=2)

DB_PATH = os.environ.get("RESUME_DB", "resumes.db")
# Good defaults for question generation: gpt-5-mini (fast/cheap) or gpt-5 (highest adherence)
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-5-mini")

# ----- DB -----
def get_conn():
    return sqlite3.connect(DB_PATH)

def init_db():
    with get_conn() as con:
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS resumes (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              user_id TEXT NOT NULL,
              version INTEGER NOT NULL,
              json_resume TEXT NOT NULL,
              created_at TEXT NOT NULL
            )
            """
        )
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
    
def _ensure_list(obj, key):
    val = obj.get(key)
    if not isinstance(val, list):
        val = []
        obj[key] = val
    return val

def _find_or_create_work_entry(tailored: Dict, experience_hint: Optional[str]) -> Dict:
    work = tailored.setdefault("work", [])
    if not isinstance(work, list):
        work = []
        tailored["work"] = work

    if not work:
        work.append({})

    if experience_hint:
        # Try exact or fuzzy match on name/company
        names = []
        for w in work:
            nm = w.get("name") or w.get("company")
            if nm:
                names.append(nm)
        match = None
        if experience_hint in names:
            idx = names.index(experience_hint)
            match = work[idx]
        else:
            close = get_close_matches(experience_hint, names, n=1, cutoff=0.6)
            if close:
                idx = names.index(close[0])
                match = work[idx]
        if match:
            return match

    return work[0]

def merge_resumes(base: dict, generated: dict) -> dict:
    """
    Non-destructive merge: keep all identity/contact from base; append
    new highlights/skills/projects/certificates from generated (deduped).
    """
    merged = copy.deepcopy(base)

    # --- Basics.summary: enrich without overwriting ---
    gen_summary = (generated.get("basics") or {}).get("summary", "").strip()
    if gen_summary:
        merged.setdefault("basics", {})
        base_summary = (merged["basics"].get("summary") or "").strip()
        if gen_summary and gen_summary not in base_summary:
            merged["basics"]["summary"] = (base_summary + (" • " if base_summary else "") + gen_summary)[:1000]

    # --- Work: append non-duplicate highlights (match by name/company) ---
    merged.setdefault("work", [])
    for gen_w in (generated.get("work") or []):
        gen_name = gen_w.get("name") or gen_w.get("company")
        gen_hls = list(gen_w.get("highlights") or [])
        if not gen_hls:
            continue

        if gen_name:
            target = next((w for w in merged["work"] if (w.get("name") or w.get("company")) == gen_name), None)
            if target is None:
                target = {"name": gen_name, "highlights": []}
                merged["work"].append(target)
        else:
            # no name provided: fall back to first entry; create if needed
            if not merged["work"]:
                merged["work"].append({"name": "", "highlights": []})
            target = merged["work"][0]

        target.setdefault("highlights", [])
        for h in gen_hls:
            h = (h or "").strip()
            if h and h not in target["highlights"]:
                target["highlights"].append(h)

    # --- Projects: merge by name; append highlights or add project ---
    merged.setdefault("projects", [])
    for gen_p in (generated.get("projects") or []):
        pname = gen_p.get("name") or ""
        if not pname:
            # unnamed project: append as-is if unique by highlight set
            if gen_p.get("highlights"):
                merged["projects"].append(gen_p)
            continue
        tgt = next((p for p in merged["projects"] if p.get("name") == pname), None)
        if tgt is None:
            merged["projects"].append(gen_p)
        else:
            tgt.setdefault("highlights", [])
            for h in (gen_p.get("highlights") or []):
                if h not in tgt["highlights"]:
                    tgt["highlights"].append(h)

    # --- Skills: convert generated keywords into flat skills if needed ---
    merged.setdefault("skills", [])
    existing_skill_names = { (s.get("name") or "").strip() for s in merged["skills"] if isinstance(s, dict) }

    for gs in (generated.get("skills") or []):
        if isinstance(gs, dict) and "keywords" in gs:
            for kw in (gs.get("keywords") or []):
                name = (kw or "").strip()
                if name and name not in existing_skill_names:
                    merged["skills"].append({"name": name, "level": "Intermediate"})
                    existing_skill_names.add(name)
        elif isinstance(gs, dict) and gs.get("name"):
            name = gs["name"].strip()
            if name and name not in existing_skill_names:
                merged["skills"].append(gs)
                existing_skill_names.add(name)

    # --- Certificates: JSON Resume uses "certificates" ---
    merged.setdefault("certificates", [])
    existing_certs = { (c.get("name") or "").strip() for c in merged["certificates"] if isinstance(c, dict) }
    for cert in (generated.get("certificates") or []):
        nm = (cert.get("name") or "").strip()
        if nm and nm not in existing_certs:
            merged["certificates"].append(cert)
            existing_certs.add(nm)

    # Leave education/publications/awards untouched unless generated adds explicit items.
    return merged

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

    # Gap context (NEW)
    jd_gap: Optional[str] = None
    gap_reason: Optional[str] = None
    coverage_status: Optional[Literal["missing", "weak"]] = None

    # Bullet-ready guidance helpers
    answer_hint: Optional[str] = None
    bullet_skeleton: Optional[str] = None
    example_bullet: Optional[str] = None

    # Mapping
    target_section: Optional[
        Literal["work", "projects", "skills", "education", "certifications"]
    ] = None
    target_anchor: Optional[str] = None
    suggested_fields: Optional[List[str]] = None
    skill_tags: Optional[List[str]] = None
    evidence_type: Optional[
        Literal["metric", "artifact", "responsibility", "toolstack", "scope", "outcome", "compliance"]
    ] = None
    priority: Optional[Literal["high", "medium"]] = "medium"

    # NEW: response tier recommendation (Section #3)
    response_tier: Optional[Literal["skill", "context", "highlight"]] = None

class AnalyzeGapsResponse(BaseModel):
    questions: List[QuestionItem]

class AnswerRow(BaseModel):
    text: str
    experience: Optional[str] = None
    enhance: bool = False  # can be ignored by UI; kept for backward compat

class GenerateRequest(BaseModel):
    user_id: Optional[str] = None
    job_description: str
    answers: Dict[int, List[AnswerRow]]
    resume: Optional[Dict] = None
    # NEW: pass the same questions you got from /analyze/gaps
    questions: Optional[List[QuestionItem]] = None

class GenerateResponse(BaseModel):
    resume: Dict  # JSON Resume tailored copy

# ---------- LLM helper ----------
def generate_gap_questions(resume: Dict, job_description: str, max_q: int = 5) -> List[QuestionItem]:
    """
    Uses OpenAI to analyze resume + JD and produce up to max_q structured question objects (QuestionItem).
    Returns [] if no meaningful gaps or if parsing fails.
    """
    # Keep the resume compact to save tokens
    resume_snippet = json.dumps(resume, ensure_ascii=False, separators=(",", ":"))

    system_msg = """
        You analyze a candidate’s JSON Resume and a job description to propose only meaningful, atomic follow-up questions
        that will improve the résumé for this role AND remain reusable for future roles.

        Optimization goals (in order):
        1) Prefer portable, résumé-worthy facts (tools used, scope/scale, measurable impact, artifacts, compliance) over JD-specific one-offs.
        2) Each question should elicit a single bullet-ready fragment (no first-person; past tense if completed, present for ongoing).
        3) Maximize searchability (keywords), credibility (metrics/artifacts), and clarity (scope/role).

        Do NOT ask:
        - Logistics/personal items (commute, relocation, schedule, salary, authorization, culture fit).
        - Tenure confirmations (“X years of Y”). Instead, elicit evidence (projects, outcomes, responsibilities).
        - Anything already present or generic duplicates.
        - Cover-letter prompts (“describe your passion…”, “are you comfortable with…”).

        Output rules:
        - Return at most {max_q} questions; return [] if no high-value gaps.
        - No preambles/explanations. No duplicates.
        - For each question, also include:
        - jd_gap: a short verbatim excerpt from the job description (<=160 chars) that motivated this question (no added punctuation; trim whitespace).
        - gap_reason: one line explaining why this is missing or weak in the resume (e.g., “mentions governance but no metrics or tools”).
        - coverage_status: “missing” if absent in resume; “weak” if present but lacks metrics/scope/tools.
        - response_tier: one of "skill", "context", or "highlight".

        Return STRICT JSON with the fields described in the schema.
    """.strip().format(max_q=max_q)

    user_msg = (
        "JOB DESCRIPTION:\n"
        f"{job_description}\n\n"
        "JSON RESUME:\n"
        f"{resume_snippet}\n\n"
        "Return strictly the JSON object with the fields described in the system message."
    )

    # JSON Schema (for response_format)
    schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "questions": {
                "type": "array",
                "maxItems": max_q,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "question": {"type": "string", "minLength": 3},

                        # NEW gap context fields
                        "jd_gap": {"type": "string"},
                        "gap_reason": {"type": "string"},
                        "coverage_status": {"type": "string", "enum": ["missing", "weak"]},

                        # Guidance fields
                        "answer_hint": {"type": "string"},
                        "bullet_skeleton": {"type": "string"},
                        "example_bullet": {"type": "string"},

                        "target_section": {
                            "type": "string",
                            "enum": ["work", "projects", "skills", "education", "certifications"],
                        },
                        "target_anchor": {"type": ["string", "null"]},
                        "suggested_fields": {"type": "array", "items": {"type": "string"}},
                        "skill_tags": {"type": "array", "items": {"type": "string"}},
                        "evidence_type": {
                            "type": "string",
                            "enum": ["metric", "artifact", "responsibility", "toolstack", "scope", "outcome", "compliance"],
                        },
                        "priority": {"type": "string", "enum": ["high", "medium"]},
                    },
                    "required": ["question", "jd_gap", "gap_reason", "coverage_status"],
                },
            }
        },
        "required": ["questions"],
    }

    def _call_openai(response_format):
        return client.chat.completions.create(
            model=OPENAI_MODEL,
            response_format=response_format,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg},
            ],
        )

    # Prefer json_schema; fallback to json_object if unsupported
    try:
        resp = _call_openai(
            {
                "type": "json_schema",
                "json_schema": {
                    "name": "GapQuestions",
                    "schema": schema,
                    "strict": True,  # disallow extra tokens outside the JSON
                },
            }
        )
    except APIStatusError as e:
        if e.status_code == 400:
            # Some model variants might not support json_schema — fallback
            resp = _call_openai({"type": "json_object"})
        else:
            raise
    except RateLimitError as e:
        raise HTTPException(status_code=429, detail="OpenAI rate limit. Please retry shortly.") from e
    except APIConnectionError as e:
        raise HTTPException(
            status_code=502,
            detail="Could not reach OpenAI (network/TLS). Check VPN/proxy, allowlist api.openai.com:443, or set HTTPS_PROXY.",
        ) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail="Unexpected error calling OpenAI.") from e

    content = resp.choices[0].message.content or "{}"

    # Parse & validate into QuestionItem[]
    try:
        data = json.loads(content)
        raw_items = data.get("questions", [])
        items: List[QuestionItem] = []
        seen = set()

        for it in raw_items:
            if isinstance(it, str):
                qtext = it.strip()
                if not qtext or qtext in seen:
                    continue
                items.append(QuestionItem(question=qtext))
                seen.add(qtext)
            elif isinstance(it, dict):
                qtext = str(it.get("question", "")).strip()
                if not qtext or qtext in seen:
                    continue
                try:
                    items.append(QuestionItem(**{**it, "question": qtext}))
                except ValidationError:
                    # Keep minimally valid if extras are malformed
                    items.append(QuestionItem(question=qtext))
                seen.add(qtext)

        return items[:max_q]
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
    # Default user
    if not req.user_id:
        req.user_id = "demo"

    resume = req.resume or (load_latest_resume(req.user_id) if req.user_id else None)
    if not resume:
        raise HTTPException(status_code=400, detail="Provide resume or user_id with a saved resume")

    qs = generate_gap_questions(resume=resume, job_description=req.job_description, max_q=5)
    return AnalyzeGapsResponse(questions=qs)

@app.post("/generate", response_model=GenerateResponse)
def generate(req: GenerateRequest):
    # Default user
    if not req.user_id:
        req.user_id = "demo"

    # Load the authoritative baseline (user's saved resume)
    baseline = load_latest_resume(req.user_id)

    # Start from baseline to build tailored content (your current logic adapted)
    tailored = json.loads(json.dumps(baseline))  # deep copy

    # Ensure standard sections
    tailored.setdefault("basics", {})
    tailored.setdefault("work", [])
    tailored.setdefault("projects", [])
    tailored.setdefault("skills", [])
    tailored.setdefault("education", [])
    tailored.setdefault("certificates", [])

    # Convenience references
    basics = tailored["basics"]
    work = tailored["work"]
    projects = tailored["projects"]
    skills = tailored["skills"]

    # Utilities (same as before)
    def _ensure_list(obj, key):
        val = obj.get(key)
        if not isinstance(val, list):
            val = []
            obj[key] = val
        return val

    from difflib import get_close_matches
    def _find_or_create_work_entry(tail: Dict, experience_hint: Optional[str]) -> Dict:
        wk = tail.setdefault("work", [])
        if not isinstance(wk, list):
            wk = []
            tail["work"] = wk
        if not wk:
            wk.append({})
        if experience_hint:
            names = []
            for w in wk:
                nm = w.get("name") or w.get("company")
                if nm:
                    names.append(nm)
            match = None
            if experience_hint in names:
                idx = names.index(experience_hint)
                match = wk[idx]
            else:
                close = get_close_matches(experience_hint, names, n=1, cutoff=0.6)
                if close:
                    idx = names.index(close[0])
                    match = wk[idx]
            if match:
                return match
        return wk[0]

    def _append_unique(lst: List[str], text: str, cap: Optional[int] = None):
        t = (text or "").strip()
        if not t:
            return
        if t not in lst:
            lst.append(t if t.endswith(".") else t + ".")
        if cap is not None and len(lst) > cap:
            del lst[cap:]

    def _add_skill_keywords(tags: List[str]):
        if not tags:
            return
        bucket = None
        for s in skills:
            if isinstance(s, dict) and isinstance(s.get("keywords"), list):
                bucket = s
                break
        if bucket is None:
            bucket = {"name": "Core Skills", "keywords": []}
            skills.append(bucket)
        kw = bucket["keywords"]
        for t in tags:
            v = (t or "").strip()
            if v and v not in kw:
                kw.append(v)

    # Pull suggestions if present
    questions = req.questions or []
    qmap: Dict[int, QuestionItem] = {i: q for i, q in enumerate(questions) if isinstance(q, QuestionItem)}

    def _infer_tier(text: str, q_item: Optional[QuestionItem]) -> str:
        if q_item and q_item.response_tier:
            return q_item.response_tier
        ln = len((text or "").strip())
        if ln < 70: return "skill"
        if ln < 140: return "context"
        return "highlight"

    # Collect snippets to enrich summary if empty
    summary_snips: List[str] = []

    # Distribute answers into tailored resume
    for q_idx, rows in (req.answers or {}).items():
        q = qmap.get(q_idx)
        for r in (rows or []):
            text = (r.text or "").strip()
            if not text:
                continue

            target_section = (q.target_section if q else None) or "work"
            tier = _infer_tier(text, q)
            experience_hint = (r.experience or "").strip() or ((q.target_anchor or "") if q else "")

            if target_section in ("work", "projects"):
                if target_section == "projects":
                    if not projects:
                        projects.append({"name": "Project A", "highlights": []})
                    proj = projects[0]
                    highlights = _ensure_list(proj, "highlights")
                    if tier == "skill":
                        _add_skill_keywords([text]); summary_snips.append(text)
                    else:
                        _append_unique(highlights, text, cap=8)
                else:
                    entry = _find_or_create_work_entry(tailored, experience_hint)
                    highlights = _ensure_list(entry, "highlights")
                    if tier == "skill":
                        _add_skill_keywords([text]); summary_snips.append(text)
                    else:
                        _append_unique(highlights, text, cap=10)

            elif target_section == "skills":
                if q and q.skill_tags:
                    _add_skill_keywords(q.skill_tags)
                else:
                    _add_skill_keywords([text])
                summary_snips.append(text)

            elif target_section == "education":
                tailored.setdefault("education", [])
                if not tailored["education"]:
                    tailored["education"].append({})
                edu = tailored["education"][0]
                hl = _ensure_list(edu, "highlights")
                if tier == "skill":
                    _add_skill_keywords([text])
                else:
                    _append_unique(hl, text, cap=6)

            elif target_section == "certifications":
                tailored.setdefault("certificates", [])
                if tier == "skill":
                    tailored["certificates"].append({"name": text})
                else:
                    tailored["certificates"].append({"name": "Credential", "summary": text})

    if not basics.get("summary") and summary_snips:
        basics["summary"] = " • ".join(summary_snips[:3])[:600]

    # Provenance
    meta = tailored.setdefault("meta", {})
    meta["generatedAt"] = datetime.utcnow().isoformat() + "Z"
    meta["source"] = "rivoney"

    # --- NEW: merge tailored back into the full baseline resume ---
    merged = merge_resumes(baseline, tailored)

    return GenerateResponse(resume=merged)