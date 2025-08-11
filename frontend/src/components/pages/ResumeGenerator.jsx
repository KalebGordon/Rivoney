import React, { useEffect, useMemo, useRef, useState } from "react";
import "../styles/ResumeGenerator.css"; // consolidated styles

export default function ResumeBuilder() {
  // ---------- API ----------
  const API_BASE = process.env.REACT_APP_API_BASE ?? "http://localhost:8000";

  async function fetchJSON(path, options = {}) {
    const res = await fetch(`${API_BASE}${path}`, {
      headers: { "Content-Type": "application/json", ...(options.headers || {}) },
      ...options,
    });
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new Error(`HTTP ${res.status} ${res.statusText}: ${text}`);
    }
    return res.json();
  }

  // --- Section 1: Job Post ---
  const [jobPost, setJobPost] = useState("");
  const [touched, setTouched] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const saveTimer = useRef(null);

  // --- Section 2: Gap Analysis ---
  const [gapQuestions, setGapQuestions] = useState([]);
  const [answers, setAnswers] = useState({}); // map: questionIndex -> row[]
  const [gapStatus, setGapStatus] = useState("idle"); // idle | generating | ready | error
  const [gapError, setGapError] = useState("");

  // experience/education dropdown options (fetched)
  const [experienceOptions, setExperienceOptions] = useState([
    "Leidos",
    "City of Mansfield",
    "RAIC Labs",
  ]);
  const newRow = () => ({
    text: "",
    experience: experienceOptions[0] ?? "",
    enhance: false,
  });

  // --- Section 3: Resume Generation (JSON preview for testing) ---
  const [previewJSON, setPreviewJSON] = useState(null);
  const [genStatus, setGenStatus] = useState("idle"); // idle | generating | ready | error
  const [genError, setGenError] = useState("");
  const [isEditingPreview, setIsEditingPreview] = useState(false);
  const [editedPreviewText, setEditedPreviewText] = useState("");

  // Refs for smooth scrolling between sections
  const section1Ref = useRef(null);
  const section2Ref = useRef(null);
  const section3Ref = useRef(null);

  // Local storage keys
  const LS_JOB = "resume_builder.job_description";
  const LS_ANS = "resume_builder.answers";
  const LS_PRE = "resume_builder.preview_json";

  // ---------- Helpers: normalize old answers + extract texts ----------
  const toRows = (v) =>
    Array.isArray(v)
      ? v.map((r) => ({ text: "", experience: experienceOptions[0] ?? "", enhance: false, ...r }))
      : v
        ? [{ text: String(v), experience: experienceOptions[0] ?? "", enhance: false }]
        : [];

  const getAnswerTexts = (obj) =>
    Object.values(obj || {})
      .flatMap((v) => toRows(v))
      .map((r) => r.text || "")
      .filter(Boolean);

  // ---------- Hydrate from localStorage on mount (with migration) ----------
  useEffect(() => {
    const savedJob = localStorage.getItem(LS_JOB);
    if (savedJob) setJobPost(savedJob);

    const savedAns = localStorage.getItem(LS_ANS);
    if (savedAns) {
      try {
        const raw = JSON.parse(savedAns);
        const migrated = Object.fromEntries(
          Object.entries(raw).map(([k, v]) => [k, toRows(v)])
        );
        setAnswers(migrated);
        localStorage.setItem(LS_ANS, JSON.stringify(migrated)); // persist migration
      } catch {
        // ignore parse errors; start fresh
      }
    }

    const savedPreview = localStorage.getItem(LS_PRE);
    if (savedPreview) {
      setPreviewJSON(JSON.parse(savedPreview));
      setGenStatus("ready");
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ---------- Fetch dropdown options on mount ----------
  useEffect(() => {
    (async () => {
      try {
        const data = await fetchJSON("/template/options", { method: "GET" });
        if (Array.isArray(data?.options) && data.options.length) {
          setExperienceOptions(data.options);
          // ensure any existing rows have a valid option selected
          setAnswers((prev) => {
            const next = { ...prev };
            Object.keys(next).forEach((k) => {
              next[k] = toRows(next[k]).map((r) => ({
                ...r,
                experience: r.experience || data.options[0],
              }));
            });
            localStorage.setItem(LS_ANS, JSON.stringify(next));
            return next;
          });
        }
      } catch (e) {
        // fall back to defaults; optional: console.warn
      }
    })();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ---------- Debounced save of the job post ----------
  useEffect(() => {
    if (!touched) return;
    setIsSaving(true);
    if (saveTimer.current) clearTimeout(saveTimer.current);
    saveTimer.current = setTimeout(() => {
      localStorage.setItem(LS_JOB, jobPost);
      setIsSaving(false);
    }, 400);
    return () => clearTimeout(saveTimer.current);
  }, [jobPost, touched]);

  const words = useMemo(
    () => (jobPost.trim() ? jobPost.trim().split(/\s+/).length : 0),
    [jobPost]
  );
  const chars = jobPost.length;
  const minChars = 240;
  const isValid = chars >= minChars;

  function handleChange(e) {
    if (!touched) setTouched(true);
    setJobPost(e.target.value);
  }

  async function handlePasteFromClipboard() {
    try {
      const text = await navigator.clipboard.readText();
      if (text) {
        setTouched(true);
        setJobPost((prev) => (prev ? prev + "\n\n" + text : text));
      }
    } catch (err) {
      console.warn("Clipboard read failed:", err);
    }
  }

  function handleClear() {
    setJobPost("");
    localStorage.removeItem(LS_JOB);
    setTouched(true);

    // Reset downstream state if user clears job post
    setGapQuestions([]);
    setGapStatus("idle");
    setGapError("");
    setAnswers({});
    localStorage.removeItem(LS_ANS);
    setPreviewJSON(null);
    setGenStatus("idle");
    setGenError("");
    localStorage.removeItem(LS_PRE);
  }

  // --- Smooth scroll helper ---
  function scrollTo(ref) {
    ref?.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  // --- Row change handlers (array-of-rows shape) ---
  function handleRowChange(qIdx, rowIdx, field, value) {
    setAnswers((prev) => {
      const next = { ...prev };
      const rows = (next[qIdx] || [newRow()]).map((r, i) =>
        i === rowIdx ? { ...r, [field]: value } : r
      );
      next[qIdx] = rows;
      localStorage.setItem(LS_ANS, JSON.stringify(next));
      return next;
    });
  }

  function addAnswerRow(qIdx) {
    setAnswers((prev) => {
      const next = { ...prev };
      next[qIdx] = [...(next[qIdx] || []), newRow()];
      localStorage.setItem(LS_ANS, JSON.stringify(next));
      return next;
    });
  }

  function removeAnswerRow(qIdx) {
    setAnswers((prev) => {
      const next = { ...prev };
      const rows = toRows(next[qIdx]);
      if (rows.length > 1) {
        rows.pop();
      } else {
        rows[0] = { ...rows[0], text: "" };
      }
      next[qIdx] = rows;
      localStorage.setItem(LS_ANS, JSON.stringify(next));
      return next;
    });
  }

  // --- API-backed functions ---
  async function analyzeGaps(jobText) {
    // TODO: supply user's actual stored template here
    const resume_template = {
      user_id: "demo",
      summary: "",
      experiences: [], // [{id, label, description, skills: []}]
      education: [],
    };

    const data = await fetchJSON("/analyze/gaps", {
      method: "POST",
      body: JSON.stringify({
        job_description: jobText,
        resume_template,
      }),
    });

    // Accept either [{prompt: "..."}] or ["..."]
    return (data?.questions || []).map((q) => (typeof q === "string" ? q : q?.prompt)).filter(Boolean);
  }

  async function generateResume(jobText, answersPayload) {
    const resume_template = {
      user_id: "demo",
      summary: "",
      experiences: [],
      education: [],
    };

    return fetchJSON("/generate", {
      method: "POST",
      body: JSON.stringify({
        job_description: jobText,
        answers: answersPayload, // map of questionIndex -> [{text, experience, enhance}]
        resume_template,
      }),
    });
  }

  // --- Section 1 -> Section 2 ---
  async function handleContinue() {
    if (!isValid || gapStatus === "generating") return;

    setGapStatus("generating");
    setGapQuestions([]);
    setGapError("");
    setAnswers((prev) => (Object.keys(prev).length ? prev : {}));

    try {
      const qs = await analyzeGaps(jobPost);
      setGapQuestions(qs);

      // initialize one row per question if missing
      setAnswers((prev) => {
        const next = { ...prev };
        qs.forEach((_, qi) => {
          next[qi] = toRows(next[qi]);
          if (next[qi].length === 0) next[qi] = [newRow()];
        });
        localStorage.setItem(LS_ANS, JSON.stringify(next));
        return next;
      });

      setGapStatus("ready");
      requestAnimationFrame(() => scrollTo(section2Ref));
    } catch (e) {
      console.error(e);
      setGapError(e.message || "Failed to analyze gaps.");
      setGapStatus("error");
    }
  }

  // At least one non-empty answer (>= 8 chars) per question
  const allAnswered =
    gapQuestions.length > 0 &&
    gapQuestions.every((_, qi) =>
      toRows(answers[qi]).some((r) => (r.text || "").trim().length >= 8)
    );

  const showPreview = genStatus !== "idle" && allAnswered;

  // --- Generate preview JSON ---
  async function handleGenerate() {
    if (!allAnswered || genStatus === "generating") return;

    setGenStatus("generating");
    setGenError("");
    setPreviewJSON(null);
    setIsEditingPreview(false);
    setEditedPreviewText("");

    try {
      const payload = await generateResume(jobPost, answers);
      setPreviewJSON(payload);
      localStorage.setItem(LS_PRE, JSON.stringify(payload));
      setGenStatus("ready");
      requestAnimationFrame(() => scrollTo(section3Ref));
    } catch (e) {
      console.error(e);
      setGenError(e.message || "Failed to generate resume.");
      setGenStatus("error");
    }
  }

  function handleEditToggle() {
    if (!previewJSON) return;
    if (!isEditingPreview) {
      setEditedPreviewText(JSON.stringify(previewJSON, null, 2));
    }
    setIsEditingPreview((v) => !v);
  }

  function handleSaveEditedPreview() {
    try {
      const parsed = JSON.parse(editedPreviewText);
      setPreviewJSON(parsed);
      localStorage.setItem(LS_PRE, JSON.stringify(parsed));
      setIsEditingPreview(false);
    } catch (e) {
      alert("Invalid JSON. Please fix formatting.");
    }
  }

  // --- UI ---
  return (
    <div className="resume-form">
      {/* SECTION 1: Job Post */}
      <section ref={section1Ref} className="section-card appear">
        <h1>Job Post</h1>
        <p>
          Paste the full job listing below. We’ll analyze it against your stored resume,
          ask clarifying questions, and tailor your resume for this role.
        </p>

        <label htmlFor="jobPost">Job description</label>
        <textarea
          id="jobPost"
          value={jobPost}
          placeholder="Paste the full job post here."
          onChange={handleChange}
          rows={18}
          spellCheck
        />

        <div className="resume-status">
          <span>
            {chars.toLocaleString()} chars • {words.toLocaleString()} words
          </span>
          {!isValid && (
            <span className="resume-hint">
              Add at least {minChars - chars} more characters for best results.
            </span>
          )}
          {isSaving && <span> Saving…</span>}
        </div>

        <div className="button-row">
          <button type="button" onClick={handlePasteFromClipboard}>
            Paste from clipboard
          </button>
          <button type="button" onClick={handleClear} disabled={!jobPost}>
            Clear
          </button>
          <button
            type="button"
            onClick={handleContinue}
            disabled={!isValid || gapStatus === "generating"}
          >
            {gapStatus === "generating" ? "Analyzing…" : "Continue"}
          </button>
        </div>
      </section>

      {/* SECTION 2: Gap Analysis */}
      <section
        ref={section2Ref}
        className={`section-card ${gapStatus !== "idle" ? "appear" : "hidden"}`}
        aria-hidden={gapStatus === "idle"}
      >
        <h2>Gap Analysis</h2>
        {gapStatus === "generating" && <p className="muted">Creating questions…</p>}
        {gapStatus === "error" && <p className="error">{gapError || "Something went wrong. Try again."}</p>}

        {gapStatus === "ready" && (
          <>
            <p>Answer the questions below so we can tailor your resume.</p>
            <ol className="qa-list">
              {gapQuestions.map((q, i) => (
                <li key={i} className="qa-item">
                  <div className="q">{q}</div>

                  {(answers[i] || [newRow()]).map((row, rIdx) => (
                    <div key={rIdx} className="qa-row">
                      <span className="answer-label">Answer {rIdx + 1}</span>
                      <textarea
                        aria-label={`Answer ${i + 1} - response ${rIdx + 1}`}
                        value={row.text}
                        onChange={(e) => handleRowChange(i, rIdx, "text", e.target.value)}
                        rows={4}
                        placeholder="Your answer…"
                      />

                      <div className="qa-controls">
                        <label className="select-wrap" aria-label="Link to experience or education">
                          <span className="mini-label">Link to:</span>
                          <select
                            value={row.experience}
                            onChange={(e) => handleRowChange(i, rIdx, "experience", e.target.value)}
                          >
                            {experienceOptions.map((opt) => (
                              <option key={opt} value={opt}>
                                {opt}
                              </option>
                            ))}
                          </select>
                        </label>

                        <label className="ai-toggle">
                          <input
                            type="checkbox"
                            checked={row.enhance}
                            onChange={(e) => handleRowChange(i, rIdx, "enhance", e.target.checked)}
                          />
                          <span>AI Enhance</span>
                        </label>
                      </div>
                    </div>
                  ))}

                  <div className="qa-actions">
                    <button
                      type="button"
                      className="remove-btn"
                      onClick={() => removeAnswerRow(i)}
                      disabled={toRows(answers[i]).length <= 1}
                    >
                      Remove answer
                    </button>

                    <button
                      type="button"
                      onClick={() => addAnswerRow(i)}
                    >
                      Add answer
                    </button>
                  </div>
                </li>
              ))}
            </ol>

            <div className="button-row">
              <button
                type="button"
                onClick={handleGenerate}
                disabled={!allAnswered || genStatus === "generating"}
              >
                {genStatus === "generating" ? "Generating…" : "Generate resume"}
              </button>
            </div>
          </>
        )}
      </section>

      {/* SECTION 3: Resume Generation (JSON preview) */}
      <section
        ref={section3Ref}
        className={`section-card ${showPreview ? "appear" : "hidden"}`}
        aria-hidden={!showPreview}
      >
        <h2>Tailored Resume Preview (JSON)</h2>
        {genStatus === "generating" && <p className="muted">Building tailored resume…</p>}
        {genStatus === "error" && <p className="error">{genError || "Couldn’t generate preview. Please try again."}</p>}

        {genStatus === "ready" && previewJSON && (
          <>
            {!isEditingPreview ? (
              <pre className="preview-block" aria-live="polite">
                {JSON.stringify(previewJSON, null, 2)}
              </pre>
            ) : (
              <textarea
                className="preview-edit"
                value={editedPreviewText}
                onChange={(e) => setEditedPreviewText(e.target.value)}
                rows={18}
                spellCheck={false}
              />
            )}

            <div className="button-row">
              <button type="button" onClick={handleEditToggle}>
                {isEditingPreview ? "Cancel edit" : "Edit JSON"}
              </button>
              {isEditingPreview ? (
                <button type="button" onClick={handleSaveEditedPreview}>
                  Save JSON
                </button>
              ) : (
                <button
                  type="button"
                  onClick={() => {
                    alert("Saved!");
                    localStorage.setItem(LS_PRE, JSON.stringify(previewJSON));
                  }}
                >
                  Save
                </button>
              )}
            </div>
          </>
        )}
      </section>
    </div>
  );
}
