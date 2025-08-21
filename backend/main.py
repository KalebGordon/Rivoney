# # app.py — FastAPI + sqlite3 storage, JSON Resume aware
# from __future__ import annotations
# from difflib import get_close_matches
# from typing import Dict, List, Optional, Literal
# from datetime import datetime
# from fastapi import FastAPI, HTTPException, Query
# from fastapi.middleware.cors import CORSMiddleware
# from pydantic import BaseModel, ValidationError
# import sqlite3, json, os
# import copy

# from dotenv import load_dotenv
# load_dotenv()

# from openai import OpenAI, APIConnectionError, RateLimitError, APIStatusError

# # ----- Config -----
# client = OpenAI(timeout=60, max_retries=2)

# DB_PATH = os.environ.get("RESUME_DB", "resumes.db")
# # Good defaults for question generation: gpt-5-mini (fast/cheap) or gpt-5 (highest adherence)
# OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-5-mini")

# # ----- DB -----
# def get_conn():
#     return sqlite3.connect(DB_PATH)

# def init_db():
#     with get_conn() as con:
#         con.execute(
#             """
#             CREATE TABLE IF NOT EXISTS resumes (
#               id INTEGER PRIMARY KEY AUTOINCREMENT,
#               user_id TEXT NOT NULL,
#               version INTEGER NOT NULL,
#               json_resume TEXT NOT NULL,
#               created_at TEXT NOT NULL
#             )
#             """
#         )
# init_db()

# def next_version_for(user_id: str) -> int:
#     with get_conn() as con:
#         cur = con.execute("SELECT MAX(version) FROM resumes WHERE user_id = ?", (user_id,))
#         row = cur.fetchone()
#         return (row[0] or 0) + 1

# def load_latest_resume(user_id: str) -> Dict:
#     with get_conn() as con:
#         cur = con.execute(
#             "SELECT json_resume FROM resumes WHERE user_id = ? ORDER BY version DESC LIMIT 1",
#             (user_id,),
#         )
#         row = cur.fetchone()
#         if not row:
#             raise HTTPException(status_code=404, detail="No resume found for user")
#         return json.loads(row[0])
    
# def _ensure_list(obj, key):
#     val = obj.get(key)
#     if not isinstance(val, list):
#         val = []
#         obj[key] = val
#     return val

# def _find_or_create_work_entry(tailored: Dict, experience_hint: Optional[str]) -> Dict:
#     work = tailored.setdefault("work", [])
#     if not isinstance(work, list):
#         work = []
#         tailored["work"] = work

#     if not work:
#         work.append({})

#     if experience_hint:
#         # Try exact or fuzzy match on name/company
#         names = []
#         for w in work:
#             nm = w.get("name") or w.get("company")
#             if nm:
#                 names.append(nm)
#         match = None
#         if experience_hint in names:
#             idx = names.index(experience_hint)
#             match = work[idx]
#         else:
#             close = get_close_matches(experience_hint, names, n=1, cutoff=0.6)
#             if close:
#                 idx = names.index(close[0])
#                 match = work[idx]
#         if match:
#             return match

#     return work[0]

# def merge_resumes(base: dict, generated: dict) -> dict:
#     """
#     Non-destructive merge: keep all identity/contact from base; append
#     new highlights/skills/projects/certificates from generated (deduped).
#     """
#     merged = copy.deepcopy(base)

#     # --- Basics.summary: enrich without overwriting ---
#     gen_summary = (generated.get("basics") or {}).get("summary", "").strip()
#     if gen_summary:
#         merged.setdefault("basics", {})
#         base_summary = (merged["basics"].get("summary") or "").strip()
#         if gen_summary and gen_summary not in base_summary:
#             merged["basics"]["summary"] = (base_summary + (" • " if base_summary else "") + gen_summary)[:1000]

#     # --- Work: append non-duplicate highlights (match by name/company) ---
#     merged.setdefault("work", [])
#     for gen_w in (generated.get("work") or []):
#         gen_name = gen_w.get("name") or gen_w.get("company")
#         gen_hls = list(gen_w.get("highlights") or [])
#         if not gen_hls:
#             continue

#         if gen_name:
#             target = next((w for w in merged["work"] if (w.get("name") or w.get("company")) == gen_name), None)
#             if target is None:
#                 target = {"name": gen_name, "highlights": []}
#                 merged["work"].append(target)
#         else:
#             # no name provided: fall back to first entry; create if needed
#             if not merged["work"]:
#                 merged["work"].append({"name": "", "highlights": []})
#             target = merged["work"][0]

#         target.setdefault("highlights", [])
#         for h in gen_hls:
#             h = (h or "").strip()
#             if h and h not in target["highlights"]:
#                 target["highlights"].append(h)

#     # --- Projects: merge by name; append highlights or add project ---
#     merged.setdefault("projects", [])
#     for gen_p in (generated.get("projects") or []):
#         pname = gen_p.get("name") or ""
#         if not pname:
#             # unnamed project: append as-is if unique by highlight set
#             if gen_p.get("highlights"):
#                 merged["projects"].append(gen_p)
#             continue
#         tgt = next((p for p in merged["projects"] if p.get("name") == pname), None)
#         if tgt is None:
#             merged["projects"].append(gen_p)
#         else:
#             tgt.setdefault("highlights", [])
#             for h in (gen_p.get("highlights") or []):
#                 if h not in tgt["highlights"]:
#                     tgt["highlights"].append(h)

#     # --- Skills: convert generated keywords into flat skills if needed ---
#     merged.setdefault("skills", [])
#     existing_skill_names = { (s.get("name") or "").strip() for s in merged["skills"] if isinstance(s, dict) }

#     for gs in (generated.get("skills") or []):
#         if isinstance(gs, dict) and "keywords" in gs:
#             for kw in (gs.get("keywords") or []):
#                 name = (kw or "").strip()
#                 if name and name not in existing_skill_names:
#                     merged["skills"].append(name)
#                     existing_skill_names.add(name)
#         elif isinstance(gs, dict) and gs.get("name"):
#             name = gs["name"].strip()
#             if name and name not in existing_skill_names:
#                 merged["skills"].append(gs)
#                 existing_skill_names.add(name)

#     # --- Certificates: JSON Resume uses "certificates" ---
#     merged.setdefault("certificates", [])
#     existing_certs = { (c.get("name") or "").strip() for c in merged["certificates"] if isinstance(c, dict) }
#     for cert in (generated.get("certificates") or []):
#         nm = (cert.get("name") or "").strip()
#         if nm and nm not in existing_certs:
#             merged["certificates"].append(cert)
#             existing_certs.add(nm)

#     # Leave education/publications/awards untouched unless generated adds explicit items.
#     return merged

# # ---------- Schemas ----------
# class SaveResumeRequest(BaseModel):
#     user_id: str
#     resume: Dict  # JSON Resume document

# class SaveResumeResponse(BaseModel):
#     user_id: str
#     version: int
#     created_at: str

# class AnalyzeGapsRequest(BaseModel):
#     user_id: Optional[str] = None
#     job_description: str
#     resume: Optional[Dict] = None  # optional, otherwise load via user_id

# class QuestionItem(BaseModel):
#     question: str

#     # Gap context (NEW)
#     jd_gap: Optional[str] = None
#     gap_reason: Optional[str] = None
#     coverage_status: Optional[Literal["missing", "weak"]] = None

#     # Bullet-ready guidance helpers
#     answer_hint: Optional[str] = None
#     bullet_skeleton: Optional[str] = None
#     example_bullet: Optional[str] = None

#     # Mapping
#     target_section: Optional[
#         Literal["work", "projects", "skills", "education", "certifications"]
#     ] = None
#     target_anchor: Optional[str] = None
#     suggested_fields: Optional[List[str]] = None
#     skill_tags: Optional[List[str]] = None
#     evidence_type: Optional[
#         Literal["metric", "artifact", "responsibility", "toolstack", "scope", "outcome", "compliance"]
#     ] = None
#     priority: Optional[Literal["high", "medium"]] = "medium"

#     # NEW: response tier recommendation (Section #3)
#     response_tier: Optional[Literal["skill", "context", "highlight"]] = None

# class AnalyzeGapsResponse(BaseModel):
#     questions: List[QuestionItem]

# class AnswerRow(BaseModel):
#     text: str
#     experience: Optional[str] = None
#     enhance: bool = False  # can be ignored by UI; kept for backward compat

# class GenerateRequest(BaseModel):
#     user_id: Optional[str] = None
#     job_description: str
#     answers: Dict[int, List[AnswerRow]]
#     resume: Optional[Dict] = None
#     # NEW: pass the same questions you got from /analyze/gaps
#     questions: Optional[List[QuestionItem]] = None

# class GenerateResponse(BaseModel):
#     resume: Dict  # JSON Resume tailored copy

# # ---------- LLM helper ----------
# def generate_gap_questions(resume: Dict, job_description: str, max_q: int = 5) -> List[QuestionItem]:
#     """
#     Uses OpenAI to analyze resume + JD and produce up to max_q structured question objects (QuestionItem).
#     Returns [] if no meaningful gaps or if parsing fails.
#     """
#     # Keep the resume compact to save tokens
#     resume_snippet = json.dumps(resume, ensure_ascii=False, separators=(",", ":"))

#     system_msg = """
#         You analyze a candidate’s JSON Resume and a job description to propose only meaningful, atomic follow-up questions
#         that will improve the résumé for this role AND remain reusable for future roles.

#         Optimization goals (in order):
#         1) Prefer portable, résumé-worthy facts (tools used, scope/scale, measurable impact, artifacts, compliance) over JD-specific one-offs.
#         2) Each question should elicit a single bullet-ready fragment (no first-person; past tense if completed, present for ongoing).
#         3) Maximize searchability (keywords), credibility (metrics/artifacts), and clarity (scope/role).

#         Do NOT ask:
#         - Logistics/personal items (commute, relocation, schedule, salary, authorization, culture fit).
#         - Tenure confirmations (“X years of Y”). Instead, elicit evidence (projects, outcomes, responsibilities).
#         - Anything already present or generic duplicates.
#         - Cover-letter prompts (“describe your passion…”, “are you comfortable with…”).

#         Output rules:
#         - Return at most {max_q} questions; return [] if no high-value gaps.
#         - No preambles/explanations. No duplicates.
#         - For each question, also include:
#         - jd_gap: a short verbatim excerpt from the job description (<=160 chars) that motivated this question (no added punctuation; trim whitespace).
#         - gap_reason: one line explaining why this is missing or weak in the resume (e.g., “mentions governance but no metrics or tools”).
#         - coverage_status: “missing” if absent in resume; “weak” if present but lacks metrics/scope/tools.
#         - response_tier: one of "skill", "context", or "highlight".

#         Return STRICT JSON with the fields described in the schema.
#     """.strip().format(max_q=max_q)

#     user_msg = (
#         "JOB DESCRIPTION:\n"
#         f"{job_description}\n\n"
#         "JSON RESUME:\n"
#         f"{resume_snippet}\n\n"
#         "Return strictly the JSON object with the fields described in the system message."
#     )

#     # JSON Schema (for response_format)
#     schema = {
#         "type": "object",
#         "additionalProperties": False,
#         "properties": {
#             "questions": {
#                 "type": "array",
#                 "maxItems": max_q,
#                 "items": {
#                     "type": "object",
#                     "additionalProperties": False,
#                     "properties": {
#                         "question": {"type": "string", "minLength": 3},

#                         # NEW gap context fields
#                         "jd_gap": {"type": "string"},
#                         "gap_reason": {"type": "string"},
#                         "coverage_status": {"type": "string", "enum": ["missing", "weak"]},

#                         # Guidance fields
#                         "answer_hint": {"type": "string"},
#                         "bullet_skeleton": {"type": "string"},
#                         "example_bullet": {"type": "string"},

#                         "target_section": {
#                             "type": "string",
#                             "enum": ["work", "projects", "skills", "education", "certifications"],
#                         },
#                         "target_anchor": {"type": ["string", "null"]},
#                         "suggested_fields": {"type": "array", "items": {"type": "string"}},
#                         "skill_tags": {"type": "array", "items": {"type": "string"}},
#                         "evidence_type": {
#                             "type": "string",
#                             "enum": ["metric", "artifact", "responsibility", "toolstack", "scope", "outcome", "compliance"],
#                         },
#                         "priority": {"type": "string", "enum": ["high", "medium"]},
#                     },
#                     "required": ["question", "jd_gap", "gap_reason", "coverage_status"],
#                 },
#             }
#         },
#         "required": ["questions"],
#     }

#     def _call_openai(response_format):
#         return client.chat.completions.create(
#             model=OPENAI_MODEL,
#             response_format=response_format,
#             messages=[
#                 {"role": "system", "content": system_msg},
#                 {"role": "user", "content": user_msg},
#             ],
#         )

#     # Prefer json_schema; fallback to json_object if unsupported
#     try:
#         resp = _call_openai(
#             {
#                 "type": "json_schema",
#                 "json_schema": {
#                     "name": "GapQuestions",
#                     "schema": schema,
#                     "strict": True,  # disallow extra tokens outside the JSON
#                 },
#             }
#         )
#     except APIStatusError as e:
#         if e.status_code == 400:
#             # Some model variants might not support json_schema — fallback
#             resp = _call_openai({"type": "json_object"})
#         else:
#             raise
#     except RateLimitError as e:
#         raise HTTPException(status_code=429, detail="OpenAI rate limit. Please retry shortly.") from e
#     except APIConnectionError as e:
#         raise HTTPException(
#             status_code=502,
#             detail="Could not reach OpenAI (network/TLS). Check VPN/proxy, allowlist api.openai.com:443, or set HTTPS_PROXY.",
#         ) from e
#     except Exception as e:
#         raise HTTPException(status_code=500, detail="Unexpected error calling OpenAI.") from e

#     content = resp.choices[0].message.content or "{}"

#     # Parse & validate into QuestionItem[]
#     try:
#         data = json.loads(content)
#         raw_items = data.get("questions", [])
#         items: List[QuestionItem] = []
#         seen = set()

#         for it in raw_items:
#             if isinstance(it, str):
#                 qtext = it.strip()
#                 if not qtext or qtext in seen:
#                     continue
#                 items.append(QuestionItem(question=qtext))
#                 seen.add(qtext)
#             elif isinstance(it, dict):
#                 qtext = str(it.get("question", "")).strip()
#                 if not qtext or qtext in seen:
#                     continue
#                 try:
#                     items.append(QuestionItem(**{**it, "question": qtext}))
#                 except ValidationError:
#                     # Keep minimally valid if extras are malformed
#                     items.append(QuestionItem(question=qtext))
#                 seen.add(qtext)

#         return items[:max_q]
#     except Exception:
#         return []

# # ---------- FastAPI ----------
# app = FastAPI(title="Resume API (JSON Resume)")

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=[
#         "http://localhost:3000",
#         "http://127.0.0.1:3000",
#         # add more if needed: "http://localhost:5173", "http://127.0.0.1:5173",
#     ],
#     allow_methods=["*"],
#     allow_headers=["*"],
#     allow_credentials=True,
#     max_age=3600,
# )

# # ---------- Endpoints ----------
# @app.post("/resume/save", response_model=SaveResumeResponse)
# def save_resume(req: SaveResumeRequest):
#     version = next_version_for(req.user_id)
#     now = datetime.utcnow().isoformat() + "Z"
#     with get_conn() as con:
#         con.execute(
#             "INSERT INTO resumes (user_id, version, json_resume, created_at) VALUES (?, ?, ?, ?)",
#             (req.user_id, version, json.dumps(req.resume), now),
#         )
#     return SaveResumeResponse(user_id=req.user_id, version=version, created_at=now)

# @app.get("/resume/latest")
# def get_latest_resume(user_id: str = Query(...)):
#     return {"resume": load_latest_resume(user_id)}

# @app.get("/template/options")
# def template_options(user_id: str = Query("demo")):
#     try:
#         resume = load_latest_resume(user_id)
#         names = []
#         for w in (resume.get("work") or []):
#             if isinstance(w, dict):
#                 name = w.get("name") or w.get("company")
#                 if name:
#                     names.append(name)
#         # unique, keep order
#         seen, opts = set(), []
#         for n in names:
#             if n not in seen:
#                 seen.add(n)
#                 opts.append(n)
#         return {"options": opts or ["Experience 1"]}
#     except HTTPException:
#         # If no resume yet, return a harmless default
#         return {"options": ["Experience 1"]}

# @app.post("/analyze/gaps", response_model=AnalyzeGapsResponse)
# def analyze_gaps(req: AnalyzeGapsRequest):
#     # Default user
#     if not req.user_id:
#         req.user_id = "demo"

#     resume = req.resume or (load_latest_resume(req.user_id) if req.user_id else None)
#     if not resume:
#         raise HTTPException(status_code=400, detail="Provide resume or user_id with a saved resume")

#     qs = generate_gap_questions(resume=resume, job_description=req.job_description, max_q=5)
#     return AnalyzeGapsResponse(questions=qs)

# @app.post("/generate", response_model=GenerateResponse)
# def generate(req: GenerateRequest):
#     # Default user
#     if not req.user_id:
#         req.user_id = "demo"

#     # Load the authoritative baseline (user's saved resume)
#     baseline = load_latest_resume(req.user_id)

#     # Start from baseline to build tailored content (your current logic adapted)
#     tailored = json.loads(json.dumps(baseline))  # deep copy

#     # Ensure standard sections
#     tailored.setdefault("basics", {})
#     tailored.setdefault("work", [])
#     tailored.setdefault("projects", [])
#     tailored.setdefault("skills", [])
#     tailored.setdefault("education", [])
#     tailored.setdefault("certificates", [])

#     # Convenience references
#     basics = tailored["basics"]
#     work = tailored["work"]
#     projects = tailored["projects"]
#     skills = tailored["skills"]

#     # Utilities (same as before)
#     def _ensure_list(obj, key):
#         val = obj.get(key)
#         if not isinstance(val, list):
#             val = []
#             obj[key] = val
#         return val

#     from difflib import get_close_matches
#     def _find_or_create_work_entry(tail: Dict, experience_hint: Optional[str]) -> Dict:
#         wk = tail.setdefault("work", [])
#         if not isinstance(wk, list):
#             wk = []
#             tail["work"] = wk
#         if not wk:
#             wk.append({})
#         if experience_hint:
#             names = []
#             for w in wk:
#                 nm = w.get("name") or w.get("company")
#                 if nm:
#                     names.append(nm)
#             match = None
#             if experience_hint in names:
#                 idx = names.index(experience_hint)
#                 match = wk[idx]
#             else:
#                 close = get_close_matches(experience_hint, names, n=1, cutoff=0.6)
#                 if close:
#                     idx = names.index(close[0])
#                     match = wk[idx]
#             if match:
#                 return match
#         return wk[0]

#     def _append_unique(lst: List[str], text: str, cap: Optional[int] = None):
#         t = (text or "").strip()
#         if not t:
#             return
#         if t not in lst:
#             lst.append(t if t.endswith(".") else t + ".")
#         if cap is not None and len(lst) > cap:
#             del lst[cap:]

#     def _add_skill_keywords(tags: List[str]):
#         if not tags:
#             return
#         bucket = None
#         for s in skills:
#             if isinstance(s, dict) and isinstance(s.get("keywords"), list):
#                 bucket = s
#                 break
#         if bucket is None:
#             bucket = {"name": "Core Skills", "keywords": []}
#             skills.append(bucket)
#         kw = bucket["keywords"]
#         for t in tags:
#             v = (t or "").strip()
#             if v and v not in kw:
#                 kw.append(v)

#     def classify_answer(text: str) -> str:
#         """
#         Use GPT to classify whether an answer should be a 'highlight' bullet,
#         a 'skill' keyword, or 'context'. Defaults to 'highlight'.
#         """
#         try:
#             resp = client.chat.completions.create(
#                 model="gpt-4o-mini",
#                 messages=[
#                     {"role": "system", "content": "Classify resume fragments."},
#                     {"role": "user", "content": f"Decide category for resume fragment:\n\n{text}\n\nReturn only one of: highlight, skill, context."}
#                 ],
#                 response_format={"type": "json_object"},
#             )
#             content = json.loads(resp.choices[0].message.content)
#             cat = (content.get("category") or "").lower()
#             return cat if cat in ("highlight", "skill", "context") else "highlight"
#         except Exception:
#             return "highlight"

#     # Pull suggestions if present
#     questions = req.questions or []
#     qmap: Dict[int, QuestionItem] = {i: q for i, q in enumerate(questions) if isinstance(q, QuestionItem)}

#     def _infer_tier(text: str, q_item: Optional[QuestionItem]) -> str:
#         if q_item and q_item.response_tier:
#             return q_item.response_tier
#         ln = len((text or "").strip())
#         if ln < 70: return "skill"
#         if ln < 140: return "context"
#         return "highlight"

#     # Collect snippets to enrich summary if empty
#     summary_snips: List[str] = []

#     # Distribute answers into tailored resume
#     for q_idx, rows in (req.answers or {}).items():
#         q = qmap.get(q_idx)
#         for r in (rows or []):
#             text = (r.text or "").strip()
#             if not text:
#                 continue

#             target_section = (q.target_section if q else None) or "work"
#             tier = classify_answer(text)
#             experience_hint = (r.experience or "").strip() or ((q.target_anchor or "") if q else "")

#             if target_section in ("work", "projects"):
#                 if target_section == "projects":
#                     if not projects:
#                         projects.append({"name": "Project A", "highlights": []})
#                     proj = projects[0]
#                     highlights = _ensure_list(proj, "highlights")
#                     if tier == "skill":
#                         _add_skill_keywords([text]); summary_snips.append(text)
#                     else:
#                         _append_unique(highlights, text, cap=8)
#                 else:
#                     entry = _find_or_create_work_entry(tailored, experience_hint)
#                     highlights = _ensure_list(entry, "highlights")
#                     if tier == "skill":
#                         _add_skill_keywords([text]); summary_snips.append(text)
#                     else:
#                         _append_unique(highlights, text, cap=10)

#             elif target_section == "skills":
#                 if q and q.skill_tags:
#                     _add_skill_keywords(q.skill_tags)
#                 else:
#                     _add_skill_keywords([text])
#                 summary_snips.append(text)

#             elif target_section == "education":
#                 tailored.setdefault("education", [])
#                 if not tailored["education"]:
#                     tailored["education"].append({})
#                 edu = tailored["education"][0]
#                 hl = _ensure_list(edu, "highlights")
#                 if tier == "skill":
#                     _add_skill_keywords([text])
#                 else:
#                     _append_unique(hl, text, cap=6)

#             elif target_section == "certifications":
#                 tailored.setdefault("certificates", [])
#                 if tier == "skill":
#                     tailored["certificates"].append({"name": text})
#                 else:
#                     tailored["certificates"].append({"name": "Credential", "summary": text})

#     if not basics.get("summary") and summary_snips:
#         basics["summary"] = " • ".join(summary_snips[:3])[:600]

#     # Provenance
#     meta = tailored.setdefault("meta", {})
#     meta["generatedAt"] = datetime.utcnow().isoformat() + "Z"
#     meta["source"] = "rivoney"

#     # --- NEW: merge tailored back into the full baseline resume ---
#     merged = merge_resumes(baseline, tailored)

#     return GenerateResponse(resume=merged)

# app.py — FastAPI + sqlite3 storage, JSON Resume aware
from __future__ import annotations
from difflib import get_close_matches
from typing import Dict, List, Optional, Literal, Tuple
from datetime import datetime
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ValidationError
import sqlite3, json, os, copy, re
DEBUG_GAPS = os.environ.get("DEBUG_GAPS", "0") == "1"

from dotenv import load_dotenv
load_dotenv()

from openai import OpenAI, APIConnectionError, RateLimitError, APIStatusError

# ----- Config -----
client = OpenAI(timeout=60, max_retries=2)

DB_PATH = os.environ.get("RESUME_DB", "resumes.db")
# For question generation
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-5-mini")
# For answer application/routing (deliberate reasoning)
APPLY_MODEL = os.environ.get("OPENAI_APPLY_MODEL", "gpt-5-thinking")

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

# ----- Utilities -----
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

def _normalize_skill_item(x):
    # Accepts strings, dict with name, or dict with keywords bucket.
    if isinstance(x, str):
        return x.strip()
    if isinstance(x, dict):
        if "name" in x and isinstance(x["name"], str):
            return x["name"].strip()
    return None

def _add_skill_keywords_bucket(skills_list: List, tags: List[str]):
    """Add keywords into a single 'Core Skills' bucket without levels."""
    if not tags:
        return
    bucket = None
    for s in skills_list:
        if isinstance(s, dict) and isinstance(s.get("keywords"), list):
            bucket = s
            break
    if bucket is None:
        bucket = {"name": "Core Skills", "keywords": []}
        skills_list.append(bucket)
    kw = bucket["keywords"]
    for t in tags:
        v = (t or "").strip()
        if v and v not in kw:
            kw.append(v)

def _append_unique(lst: List[str], text: str, cap: Optional[int] = None):
    t = (text or "").strip()
    if not t:
        return
    # Ensure end punctuation and no duplicates
    t_fmt = t if re.search(r"[.!?]$", t) else t + "."
    if t_fmt not in lst:
        lst.append(t_fmt)
    if cap is not None and len(lst) > cap:
        del lst[cap:]

def _rewrite_or_add_highlight(entry: Dict, new_text: str, find_match: Optional[str] = None, cap: int = 10):
    highlights = _ensure_list(entry, "highlights")
    if find_match:
        # Fuzzy replace: find the closest existing highlight
        target = None
        if highlights:
            close = get_close_matches(find_match, highlights, n=1, cutoff=0.55)
            if close:
                target = close[0]
        if target:
            idx = highlights.index(target)
            highlights[idx] = new_text if re.search(r"[.!?]$", new_text) else new_text + "."
            return
    _append_unique(highlights, new_text, cap=cap)

def _dedupe_keep_order(seq: List[str]) -> List[str]:
    seen = set()
    out = []
    for x in seq:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out

# ----- Merge -----
def merge_resumes(base: dict, generated: dict) -> dict:
    """
    Non-destructive merge: keep all identity/contact from base; append
    new highlights/skills/projects/certificates from generated (deduped).
    """
    merged = copy.deepcopy(base)

    # Basics.summary: enrich without overwriting
    gen_summary = (generated.get("basics") or {}).get("summary", "").strip()
    if gen_summary:
        merged.setdefault("basics", {})
        base_summary = (merged["basics"].get("summary") or "").strip()
        if gen_summary and gen_summary not in base_summary:
            merged["basics"]["summary"] = (base_summary + (" • " if base_summary else "") + gen_summary)[:1000]

    # Work: append non-duplicate highlights (match by name/company)
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
            if not merged["work"]:
                merged["work"].append({"name": "", "highlights": []})
            target = merged["work"][0]

        target.setdefault("highlights", [])
        for h in gen_hls:
            h = (h or "").strip()
            if h and h not in target["highlights"]:
                target["highlights"].append(h)

    # Projects: merge by name; append highlights or add project
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

    # Skills: flatten into strings and keywords bucket only (no levels)
    merged.setdefault("skills", [])
    # Normalize existing skills
    flat_existing = []
    buckets = []
    for s in merged["skills"]:
        if isinstance(s, dict) and "keywords" in s:
            buckets.append(s)
        else:
            nm = _normalize_skill_item(s)
            if nm:
                flat_existing.append(nm)

    # Add generated
    for gs in (generated.get("skills") or []):
        if isinstance(gs, dict) and "keywords" in gs:
            _add_skill_keywords_bucket(merged["skills"], gs.get("keywords") or [])
        elif isinstance(gs, dict) and gs.get("name"):
            nm = (gs.get("name") or "").strip()
            if nm and nm not in flat_existing:
                merged["skills"].append(nm)
                flat_existing.append(nm)
        elif isinstance(gs, str):
            nm = gs.strip()
            if nm and nm not in flat_existing:
                merged["skills"].append(nm)
                flat_existing.append(nm)

    # Dedupe flat skills, preserve buckets
    new_flat = [x for x in merged["skills"] if not (isinstance(x, dict) and "keywords" in x)]
    new_buckets = [x for x in merged["skills"] if isinstance(x, dict) and "keywords" in x]
    merged["skills"] = _dedupe_keep_order(new_flat) + new_buckets

    # Certificates
    merged.setdefault("certificates", [])
    existing_certs = {(c.get("name") or "").strip() for c in merged["certificates"] if isinstance(c, dict)}
    for cert in (generated.get("certificates") or []):
        nm = (cert.get("name") or "").strip()
        if nm and nm not in existing_certs:
            merged["certificates"].append(cert)
            existing_certs.add(nm)

    return merged

# ---------- Schemas ----------
class SaveResumeRequest(BaseModel):
    user_id: str
    resume: Dict

class SaveResumeResponse(BaseModel):
    user_id: str
    version: int
    created_at: str

class AnalyzeGapsRequest(BaseModel):
    user_id: Optional[str] = None
    job_description: str
    resume: Optional[Dict] = None

class QuestionItem(BaseModel):
    question: str
    jd_gap: Optional[str] = None
    gap_reason: Optional[str] = None
    coverage_status: Optional[Literal["missing", "weak"]] = None
    answer_hint: Optional[str] = None
    bullet_skeleton: Optional[str] = None
    example_bullet: Optional[str] = None
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
    response_tier: Optional[Literal["skill", "context", "highlight"]] = None

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
    questions: Optional[List[QuestionItem]] = None

class GenerateResponse(BaseModel):
    resume: Dict

# ---------- LLM: Generate gap questions ----------
def generate_gap_questions(resume: Dict, job_description: str, max_q: int = 5) -> List[QuestionItem]:
    resume_snippet = json.dumps(resume, ensure_ascii=False, separators=(",", ":"))

    system_msg = """
        You analyze a candidate’s JSON Resume and a job description to propose only meaningful, atomic follow-up questions
        that will improve the résumé for this role AND remain reusable for future roles.

        Optimization goals (in order):
        1) Prefer portable, résumé-worthy facts (tools used, scope/scale, measurable impact, artifacts, compliance) over JD-specific one-offs.
        2) Each question should elicit a concise fact/evidence fragment (e.g., tools, scope, metric, artifact). Do NOT instruct the user to "provide a bullet".
        3) Maximize searchability (keywords), credibility (metrics/artifacts), and clarity (scope/role).

        Do NOT ask:
        - Logistics/personal items (commute, relocation, schedule, salary, authorization, culture fit).
        - Tenure confirmations (“X years of Y”). Instead, elicit evidence (projects, outcomes, responsibilities).
        - Anything already present or generic duplicates.
        - Cover-letter prompts.

        Output rules (STRICT JSON):
        - Return at most {max_q} items in an array under key "questions".
        - Each item MUST include: question, jd_gap, gap_reason, coverage_status (one of: "missing","weak").
        - Optional: response_tier ("skill","context","highlight"), target_section, target_anchor, skill_tags, answer_hint.
        - Keep values concise (<= 220 chars where sensible).
    """.strip().format(max_q=max_q)

    user_msg = (
        "JOB DESCRIPTION:\n"
        f"{job_description}\n\n"
        "JSON RESUME:\n"
        f"{resume_snippet}\n\n"
        "Return strictly the JSON object with the fields described."
    )

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
                        "jd_gap": {"type": "string"},
                        "gap_reason": {"type": "string"},
                        "coverage_status": {"type": "string", "enum": ["missing", "weak"]},
                        "answer_hint": {"type": "string"},
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
                        "response_tier": {"type": "string", "enum": ["skill", "context", "highlight"]},
                        # We still accept skeleton/example if the model sends them, but we won't render them.
                        "bullet_skeleton": {"type": "string"},
                        "example_bullet": {"type": "string"},
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

    # Prefer schema; fallback to lenient json_object
    def _fetch_raw_json(prefer_schema=True) -> str:
        if prefer_schema:
            try:
                resp = _call_openai(
                    {
                        "type": "json_schema",
                        "json_schema": {
                            "name": "GapQuestions",
                            "schema": schema,
                            "strict": True,
                        },
                    }
                )
                return resp.choices[0].message.content or "{}"
            except APIStatusError as e:
                if e.status_code != 400:
                    raise
        resp2 = _call_openai({"type": "json_object"})
        return resp2.choices[0].message.content or "{}"

    content = _fetch_raw_json(prefer_schema=True)
    if DEBUG_GAPS:
        print("\n--- [GAPS RAW CONTENT] ---")
        print(content[:2000])
        print("--- [END RAW CONTENT] ---\n")

    # Normalizers
    def norm_cov(v: Optional[str]) -> str:
        s = (v or "").strip().lower()
        if s in ("missing", "absent", "not_covered", "not covered", "none"):
            return "missing"
        if s.startswith("partial") or "weak" in s or s == "weak":
            return "weak"
        return "weak"

    def norm_tier(v: Optional[str], text: str) -> Optional[str]:
        s = (v or "").strip().lower()
        if s in ("skill", "context", "highlight"):
            return s
        n = len(text or "")
        if n < 80: return "skill"
        if n < 160: return "context"
        return "highlight"

    def norm_anchor(a: Optional[str]) -> Optional[str]:
        if not a:
            return a
        s = a.strip().replace("—", "-").replace("–", "-")
        return s.split("-")[0].strip() if "-" in s else s

    def clamp(s: Optional[str], n: int) -> Optional[str]:
        return (s or "")[:n] if s else s

    # Cleaner synthesized questions, no "provide a bullet"
    def synthesize_question(it: dict) -> str:
        q = (it.get("question") or "").strip()
        if q:
            return q
        jd = (it.get("jd_gap") or "").strip()
        if jd:
            return f"{jd} — include tools, scale, artifact, and one metric."
        return "Add concise evidence: tools used, scope/scale, artifact, and one measurable outcome."

    # Parse + normalize
    try:
        data = json.loads(content)
    except Exception as e:
        if DEBUG_GAPS:
            print("[GAPS PARSE ERROR 1]", repr(e))
        data = {}

    raw_items = data.get("questions", []) if isinstance(data, dict) else []
    if DEBUG_GAPS:
        print(f"[GAPS] raw_items count: {len(raw_items)}")

    items: List[QuestionItem] = []
    seen = set()

    for it in (raw_items or []):
        if not isinstance(it, dict):
            continue
        qtext = clamp(synthesize_question(it), 220)
        jd_gap = clamp((it.get("jd_gap") or "").strip(), 220)
        gap_reason = clamp((it.get("gap_reason") or "").strip(), 220)
        cov = norm_cov(it.get("coverage_status"))
        tier = norm_tier(it.get("response_tier"), qtext or jd_gap)

        section = it.get("target_section") if it.get("target_section") in ("work","projects","skills","education","certifications") else None
        anchor = norm_anchor(it.get("target_anchor"))

        payload = {
            "question": qtext,
            "jd_gap": jd_gap,
            "gap_reason": gap_reason,
            "coverage_status": cov,
            "answer_hint": clamp(it.get("answer_hint"), 220),
            "bullet_skeleton": clamp(it.get("bullet_skeleton"), 260),  # accepted but not used in UI
            "example_bullet": clamp(it.get("example_bullet"), 260),    # accepted but not used in UI
            "target_section": section,
            "target_anchor": anchor,
            "suggested_fields": it.get("suggested_fields"),
            "skill_tags": it.get("skill_tags"),
            "evidence_type": it.get("evidence_type"),
            "priority": it.get("priority") if it.get("priority") in ("high","medium") else "medium",
            "response_tier": tier,
        }

        if qtext and qtext not in seen:
            try:
                items.append(QuestionItem(**payload))
                seen.add(qtext)
            except ValidationError:
                # fallback minimal
                try:
                    items.append(QuestionItem(
                        question=qtext,
                        jd_gap=jd_gap,
                        gap_reason=gap_reason,
                        coverage_status=cov
                    ))
                    seen.add(qtext)
                except Exception as ve:
                    if DEBUG_GAPS:
                        print("[GAPS] Dropped item after validation:", ve)

    if not items:
        if DEBUG_GAPS:
            print("[GAPS] Empty after first pass. Retrying with json_object fallback.")
        content2 = _fetch_raw_json(prefer_schema=False)
        if DEBUG_GAPS:
            print("\n--- [GAPS RAW CONTENT 2] ---")
            print(content2[:2000])
            print("--- [END RAW CONTENT 2] ---\n")
        try:
            data2 = json.loads(content2)
        except Exception as e:
            if DEBUG_GAPS:
                print("[GAPS PARSE ERROR 2]", repr(e))
            data2 = {}
        # Re-run same normalization on fallback
        for it in (data2.get("questions", []) if isinstance(data2, dict) else []):
            if not isinstance(it, dict):
                continue
            qtext = clamp(synthesize_question(it), 220)
            jd_gap = clamp((it.get("jd_gap") or "").strip(), 220)
            gap_reason = clamp((it.get("gap_reason") or "").strip(), 220)
            cov = norm_cov(it.get("coverage_status"))
            tier = norm_tier(it.get("response_tier"), qtext or jd_gap)
            section = it.get("target_section") if it.get("target_section") in ("work","projects","skills","education","certifications") else None
            anchor = norm_anchor(it.get("target_anchor"))
            if qtext and qtext not in seen:
                try:
                    items.append(QuestionItem(
                        question=qtext,
                        jd_gap=jd_gap,
                        gap_reason=gap_reason,
                        coverage_status=cov,
                        response_tier=tier,
                        target_section=section,
                        target_anchor=anchor,
                        answer_hint=clamp(it.get("answer_hint"), 220),
                        skill_tags=it.get("skill_tags"),
                    ))
                    seen.add(qtext)
                except Exception:
                    pass

    if DEBUG_GAPS:
        print(f"[GAPS] normalized items count: {len(items)}")
        for i, it in enumerate(items):
            print(f"  - Q{i+1}: {it.question[:140]}")

    return items[:max_q]

# ---------- LLM: Apply answers as operations ----------
def apply_answers_with_llm(baseline: Dict, job_description: str, questions: List[QuestionItem], answers: Dict[int, List[AnswerRow]]) -> Dict:
    """
    Ask the model (GPT-5 Thinking) to return a list of operations that intelligently
    add/merge bullets, add skills, and optionally update summary/education/certs.
    Then deterministically apply those operations.
    """
    # Compact baseline and QA payload
    baseline_snip = json.dumps(baseline, ensure_ascii=False, separators=(",", ":"))
    qa = []
    for idx, rows in (answers or {}).items():
        q = questions[idx].question if (questions and idx < len(questions) and isinstance(questions[idx], QuestionItem)) else ""
        qa.append({
            "q_index": idx,
            "question": q,
            "rows": [{"text": r.text, "experience": r.experience or ""} for r in (rows or []) if (r.text or "").strip()]
        })
    payload = {
        "job_description": job_description,
        "baseline_resume": json.loads(baseline_snip),
        "qa": qa
    }

    system_msg = """
You are a resume editor. Given a baseline JSON Resume and Q&A answers, produce a compact set of OPERATIONS to improve the resume for this role while keeping it broadly reusable.

Rules:
- Use new highlights only if the answer is impactful (action + scope + tool + metric/outcome). Otherwise either (a) merge/rewrite an EXISTING highlight to include the info concisely, or (b) extract 1–3 skill keywords.
- Prefer adding to WORK (by company anchor) over creating Projects unless the content is truly a standalone project.
- Keep highlights crisp, job-relevant, and non-duplicative.
- Never invent facts; rewrite only with provided content.
- Skills: no levels. Add keywords only (single or bucket).
- Do not remove existing content.

Return STRICT JSON with an operations list. Each item must be one of:
1) {"op":"add_highlight","section":"work"|"projects","anchor": "<company or project name>","text":"..."}
2) {"op":"rewrite_highlight","section":"work"|"projects","anchor":"<company or project name>","find":"<short snippet to match>","text":"<rewritten bullet>"}
3) {"op":"add_skill_keywords","keywords":["kw1","kw2",...]}
4) {"op":"add_education_highlight","anchor":"<institution or empty>","text":"..."}
5) {"op":"add_certificate","name":"<credential>","summary":"<optional>"}
6) {"op":"update_summary","mode":"append","text":"<<=120 chars, portable>"}

Constraints:
- At most 2 ops per answer row.
- Highlights must be <= 220 chars each.
- If unsure between highlight vs skills, choose skills.
""".strip()

    schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "operations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "oneOf": [
                        {
                            "type":"object",
                            "properties":{
                                "op":{"const":"add_highlight"},
                                "section":{"type":"string","enum":["work","projects"]},
                                "anchor":{"type":"string"},
                                "text":{"type":"string","minLength":6,"maxLength":300}
                            },
                            "required":["op","section","anchor","text"]
                        },
                        {
                            "type":"object",
                            "properties":{
                                "op":{"const":"rewrite_highlight"},
                                "section":{"type":"string","enum":["work","projects"]},
                                "anchor":{"type":"string"},
                                "find":{"type":"string","minLength":3},
                                "text":{"type":"string","minLength":6,"maxLength":300}
                            },
                            "required":["op","section","anchor","find","text"]
                        },
                        {
                            "type":"object",
                            "properties":{
                                "op":{"const":"add_skill_keywords"},
                                "keywords":{"type":"array","items":{"type":"string"}}
                            },
                            "required":["op","keywords"]
                        },
                        {
                            "type":"object",
                            "properties":{
                                "op":{"const":"add_education_highlight"},
                                "anchor":{"type":"string"},
                                "text":{"type":"string","minLength":6,"maxLength":300}
                            },
                            "required":["op","anchor","text"]
                        },
                        {
                            "type":"object",
                            "properties":{
                                "op":{"const":"add_certificate"},
                                "name":{"type":"string","minLength":2},
                                "summary":{"type":"string"}
                            },
                            "required":["op","name"]
                        },
                        {
                            "type":"object",
                            "properties":{
                                "op":{"const":"update_summary"},
                                "mode":{"type":"string","enum":["append"]},
                                "text":{"type":"string","minLength":6,"maxLength":140}
                            },
                            "required":["op","mode","text"]
                        }
                    ]
                }
            }
        },
        "required":["operations"]
    }

    try:
        resp = client.chat.completions.create(
            model=APPLY_MODEL,
            response_format={
                "type":"json_schema",
                "json_schema":{"name":"ApplyOps","schema":schema,"strict":True}
            },
            messages=[
                {"role":"system","content":system_msg},
                {"role":"user","content":json.dumps(payload, ensure_ascii=False)}
            ]
        )
        content = resp.choices[0].message.content or "{}"
        data = json.loads(content)
        ops = data.get("operations", [])
    except Exception:
        # Fallback: simple routing (very conservative)
        ops = []
        for item in qa:
            for row in item["rows"]:
                txt = (row["text"] or "").strip()
                if not txt:
                    continue
                # If it looks like a bullet (starts with verb, has tool/metric), add highlight; else skills
                is_bullety = bool(re.match(r"^(Built|Led|Designed|Developed|Automated|Deployed|Implemented|Created|Optimized|Migrated|Analyzed|Engineered)\b", txt, re.I))
                has_signal = bool(re.search(r"\b(\d+%|\d+/\d+|SQL|Python|AWS|S3|ETL|LIMS|pipeline|dashboard|indexing|PowerShell|SSMS|Server|Tableau|model|accuracy)\b", txt, re.I))
                if is_bullety and has_signal and len(txt) >= 50:
                    ops.append({"op":"add_highlight","section":"work","anchor":row.get("experience") or "", "text":txt[:220]})
                else:
                    # extract up to 3 words as keywords
                    tokens = re.split(r"[,/;•]| and |\s{2,}", txt)
                    kws = []
                    for tok in tokens:
                        t = tok.strip()
                        if 2 <= len(t) <= 40 and re.search(r"[A-Za-z]", t):
                            kws.append(t)
                        if len(kws) >= 3:
                            break
                    if kws:
                        ops.append({"op":"add_skill_keywords","keywords":kws})

    # Deterministically apply ops to a working copy
    tailored = copy.deepcopy(baseline)

    def _anchor_entry(section: str, anchor: str) -> Dict:
        anchor = (anchor or "").strip()
        if section == "work":
            if not tailored.get("work"):
                tailored["work"] = [{"name": anchor or "", "highlights": []}]
            # find closest by name/company
            pool = tailored["work"]
            names = [(w.get("name") or w.get("company") or "") for w in pool]
            if anchor and anchor in names:
                return pool[names.index(anchor)]
            if anchor and names:
                close = get_close_matches(anchor, names, n=1, cutoff=0.6)
                if close:
                    return pool[names.index(close[0])]
            # fallback: first
            return pool[0]
        else:
            # projects
            tailored.setdefault("projects", [])
            pool = tailored["projects"]
            if anchor:
                tgt = next((p for p in pool if (p.get("name") or "") == anchor), None)
                if tgt is None:
                    tgt = {"name": anchor, "highlights": []}
                    pool.append(tgt)
                return tgt
            # unnamed project
            if not pool:
                pool.append({"name":"Project A","highlights":[]})
            return pool[0]

    for op in ops:
        try:
            if op.get("op") == "add_highlight":
                section = op["section"]
                anchor = op.get("anchor") or ""
                text = op["text"]
                entry = _anchor_entry(section, anchor)
                _rewrite_or_add_highlight(entry, text, find_match=None, cap=10 if section=="work" else 8)

            elif op.get("op") == "rewrite_highlight":
                section = op["section"]
                anchor = op.get("anchor") or ""
                text = op["text"]
                find = op.get("find") or ""
                entry = _anchor_entry(section, anchor)
                _rewrite_or_add_highlight(entry, text, find_match=find, cap=10 if section=="work" else 8)

            elif op.get("op") == "add_skill_keywords":
                kws = [k.strip() for k in (op.get("keywords") or []) if isinstance(k, str) and k.strip()]
                if kws:
                    tailored.setdefault("skills", [])
                    _add_skill_keywords_bucket(tailored["skills"], kws)

            elif op.get("op") == "add_education_highlight":
                anchor = (op.get("anchor") or "").strip()
                tailored.setdefault("education", [])
                edu = None
                if anchor:
                    edu = next((e for e in tailored["education"] if (e.get("institution") or "").strip() == anchor), None)
                if edu is None:
                    if not tailored["education"]:
                        tailored["education"].append({"institution": anchor or ""})
                    edu = tailored["education"][0]
                hl = _ensure_list(edu, "highlights")
                _append_unique(hl, op["text"], cap=6)

            elif op.get("op") == "add_certificate":
                name = (op.get("name") or "").strip()
                if name:
                    tailored.setdefault("certificates", [])
                    summary = (op.get("summary") or "").strip()
                    item = {"name": name}
                    if summary:
                        item["summary"] = summary
                    # de-dupe by name
                    names = {(c.get("name") or "").strip() for c in tailored["certificates"]}
                    if name not in names:
                        tailored["certificates"].append(item)

            elif op.get("op") == "update_summary":
                text = (op.get("text") or "").strip()
                if text:
                    tailored.setdefault("basics", {})
                    base_summary = (tailored["basics"].get("summary") or "").strip()
                    if text not in base_summary:
                        new_sum = (base_summary + (" • " if base_summary else "") + text)
                        tailored["basics"]["summary"] = new_sum[:1000]

        except Exception:
            # Skip malformed op; continue safely
            continue

    return tailored

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
        seen, opts = set(), []
        for n in names:
            if n not in seen:
                seen.add(n)
                opts.append(n)
        return {"options": opts or ["Experience 1"]}
    except HTTPException:
        return {"options": ["Experience 1"]}

@app.post("/analyze/gaps", response_model=AnalyzeGapsResponse)
def analyze_gaps(req: AnalyzeGapsRequest):
    if not req.user_id:
        req.user_id = "demo"

    resume = req.resume or (load_latest_resume(req.user_id) if req.user_id else None)
    if not resume:
        raise HTTPException(status_code=400, detail="Provide resume or user_id with a saved resume")

    print(f"[GAPS] received JD length={len(req.job_description)}")
    qs = generate_gap_questions(resume=resume, job_description=req.job_description, max_q=5)
    print(f"[GAPS] model returned raw -> {qs}")
    return AnalyzeGapsResponse(questions=qs)

@app.post("/generate", response_model=GenerateResponse)
def generate(req: GenerateRequest):
    if not req.user_id:
        req.user_id = "demo"

    baseline = load_latest_resume(req.user_id)

    questions: List[QuestionItem] = []
    raw_qs = req.questions or []
    for it in raw_qs:
        if isinstance(it, QuestionItem):
            questions.append(it)
        elif isinstance(it, dict) and "question" in it:
            try:
                questions.append(QuestionItem(**it))
            except Exception:
                continue

    tailored = apply_answers_with_llm(
        baseline=baseline,
        job_description=req.job_description,
        questions=questions,
        answers=req.answers or {}
    )

    # Provenance
    meta = tailored.setdefault("meta", {})
    meta["generatedAt"] = datetime.utcnow().isoformat() + "Z"
    meta["source"] = "rivoney"

    merged = merge_resumes(baseline, tailored)
    return GenerateResponse(resume=merged)
