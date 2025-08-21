// File: components/ResumeGenerator.jsx
import React, { useEffect, useMemo, useRef, useState } from "react";
import "../styles/ResumeGenerator.css";

export default function ResumeGenerator() {
  // ---------- API ----------
  const API_BASE = process.env.REACT_APP_API_BASE ?? "http://localhost:8000";

  async function fetchJSON(path, options = {}) {
    const hasBody = options.body != null;
    const headers = {
      ...(hasBody ? { "Content-Type": "application/json" } : {}),
      ...(options.headers || {}),
    };

    const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new Error(`HTTP ${res.status} ${res.statusText}: ${text}`);
    }
    return res.json();
  }

  // --- Section 1: Job Post (ephemeral only) ---
  const [jobPost, setJobPost] = useState("");
  const [touched, setTouched] = useState(false);

  // --- Section 2: Gap Analysis ---
  const [gapQuestions, setGapQuestions] = useState([]);
  const [answers, setAnswers] = useState({});
  const [gapStatus, setGapStatus] = useState("idle"); // idle | generating | ready | error
  const [gapError, setGapError] = useState("");

  // experience dropdown options (fetched)
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

  // --- Section 3: Resume Generation (JSON preview) ---
  const [previewJSON, setPreviewJSON] = useState(null);
  const [genStatus, setGenStatus] = useState("idle");
  const [genError, setGenError] = useState("");
  const [isEditingPreview, setIsEditingPreview] = useState(false);
  const [editedPreviewText, setEditedPreviewText] = useState("");

  // Refs for smooth scrolling between sections
  const section1Ref = useRef(null);
  const section2Ref = useRef(null);
  const section3Ref = useRef(null);

  // ---------- Helpers ----------
  const toRows = (v) =>
    Array.isArray(v)
      ? v.map((r) => ({ text: "", experience: experienceOptions[0] ?? "", enhance: false, ...r }))
      : v
      ? [{ text: String(v), experience: experienceOptions[0] ?? "", enhance: false }]
      : [];

  // ---------- Fetch dropdown options on mount ----------
  useEffect(() => {
    (async () => {
      try {
        const data = await fetchJSON("/template/options", { method: "GET" });
        if (Array.isArray(data?.options) && data.options.length) {
          setExperienceOptions(data.options);
          setAnswers((prev) => {
            const next = { ...prev };
            Object.keys(next).forEach((k) => {
              next[k] = toRows(next[k]).map((r) => ({
                ...r,
                experience: r.experience || data.options[0],
              }));
            });
            return next;
          });
        }
      } catch {
        // silent fallback to defaults
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

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
    setTouched(true);
    setGapQuestions([]);
    setGapStatus("idle");
    setGapError("");
    setAnswers({});
    setPreviewJSON(null);
    setGenStatus("idle");
    setGenError("");
  }

  function scrollTo(ref) {
    ref?.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function handleRowChange(qIdx, rowIdx, field, value) {
    setAnswers((prev) => {
      const next = { ...prev };
      const rows = (next[qIdx] || [newRow()]).map((r, i) =>
        i === rowIdx ? { ...r, [field]: value } : r
      );
      next[qIdx] = rows;
      return next;
    });
  }

  function addAnswerRow(qIdx) {
    setAnswers((prev) => {
      const next = { ...prev };
      next[qIdx] = [...(next[qIdx] || []), newRow()];
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
      return next;
    });
  }

  async function analyzeGaps(jobText) {
    const data = await fetchJSON("/analyze/gaps", {
      method: "POST",
      body: JSON.stringify({
        user_id: "demo",
        job_description: jobText,
      }),
    });
    return Array.isArray(data?.questions) ? data.questions : [];
  }

  async function generateResume(jobText, answersPayload, questionsPayload) {
    return fetchJSON("/generate", {
      method: "POST",
      body: JSON.stringify({
        job_description: jobText,
        answers: answersPayload,
        questions: questionsPayload ?? [],
      }),
    });
  }

  async function handleContinue() {
    if (!isValid || gapStatus === "generating") return;

    setGapStatus("generating");
    setGapQuestions([]);
    setGapError("");
    setAnswers((prev) => (Object.keys(prev).length ? prev : {}));

    try {
      const qs = await analyzeGaps(jobPost);
      setGapQuestions(qs);

      setAnswers((prev) => {
        const next = { ...prev };
        qs.forEach((_, qi) => {
          next[qi] = toRows(next[qi]);
          if (next[qi].length === 0) next[qi] = [newRow()];
        });
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

  const allAnswered =
    gapQuestions.length === 0 ||
    gapQuestions.every((_, qi) =>
      toRows(answers[qi]).some((r) => (r.text || "").trim().length >= 8)
    );

  const showPreview = genStatus !== "idle" && allAnswered;

  async function handleGenerate() {
    if (!allAnswered || genStatus === "generating") return;

    setGenStatus("generating");
    setGenError("");
    setPreviewJSON(null);
    setIsEditingPreview(false);
    setEditedPreviewText("");

    try {
      const payload = await generateResume(jobPost, answers, gapQuestions);
      setPreviewJSON(payload);
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
      setIsEditingPreview(false);
    } catch {
      alert("Invalid JSON. Please fix formatting.");
    }
  }

  return (
    <div className="rg-form">
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
          placeholder="Paste the full job description here."
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
        {gapStatus === "error" && (
          <p className="error">{gapError || "Something went wrong. Try again."}</p>
        )}

        {gapStatus === "ready" && (
          <>
            {gapQuestions.length === 0 ? (
              <p className="muted">Looking great! No meaningful gaps found.</p>
            ) : (
              <>
                <p>Answer the questions below so we can tailor your resume.</p>

                <ol className="qa-list">
                  {gapQuestions.map((q, i) => {
                    const qTitle   = typeof q === "string" ? q : q?.question ?? "";
                    const tags     = Array.isArray(q?.skill_tags) ? q.skill_tags : [];
                    const priority = typeof q === "object" ? q?.priority : null;
                    const jdGap    = typeof q === "object" ? q?.jd_gap : "";
                    const gapReason= typeof q === "object" ? q?.gap_reason : "";
                    const coverage = typeof q === "object" ? q?.coverage_status : null;

                    const anchor =
                      typeof q === "object" && typeof q?.target_anchor === "string"
                        ? q.target_anchor
                        : "";
                    const matchedOpt = experienceOptions.find(
                      (opt) => anchor && opt.toLowerCase().includes(anchor.toLowerCase())
                    );
                    const defaultOpt = matchedOpt || experienceOptions[0] || "";

                    const rows = toRows(answers[i] || [newRow()]);

                    return (
                      <li key={i} className="qa-item">
                        <div className="q">{qTitle}</div>

                        {(jdGap || gapReason || coverage) && (
                          <div className="gap-context">
                            {coverage && (
                              <span className={`coverage-badge ${coverage}`}>
                                {coverage === "missing" ? "Missing" : "Weak"}
                              </span>
                            )}
                            {jdGap && <blockquote className="jd-gap">“{jdGap}”</blockquote>}
                            {gapReason && <div className="gap-reason">{gapReason}</div>}
                          </div>
                        )}

                        {(priority || tags.length > 0) && (
                          <div className="mini-meta">
                            {priority && (
                              <span className={`mini-priority ${priority || ""}`}>
                                Priority: {priority}
                              </span>
                            )}
                            {tags.length > 0 && (
                              <div className="mini-tags">
                                {tags.map((t) => (
                                  <span key={t} className="tag">
                                    {t}
                                  </span>
                                ))}
                              </div>
                            )}
                          </div>
                        )}

                        {rows.map((row, rIdx) => (
                          <div key={rIdx} className="qa-row">
                            <span className="answer-label">Answer {rIdx + 1}</span>

                            <textarea
                              aria-label={`Answer ${i + 1} - response ${rIdx + 1}`}
                              value={row.text || ""}
                              onChange={(e) =>
                                handleRowChange(i, rIdx, "text", e.target.value)
                              }
                              rows={4}
                              placeholder="Start with a verb; include tools, scale, metric, outcome."
                            />

                            <div className="qa-controls">
                              <label
                                className="select-wrap"
                                aria-label="Link to experience or education"
                              >
                                <span className="mini-label">Link to:</span>
                                <select
                                  value={row.experience || defaultOpt}
                                  onChange={(e) =>
                                    handleRowChange(i, rIdx, "experience", e.target.value)
                                  }
                                >
                                  {experienceOptions.map((opt) => (
                                    <option key={opt} value={opt}>
                                      {opt}
                                    </option>
                                  ))}
                                </select>
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

                          <button type="button" onClick={() => addAnswerRow(i)}>
                            Add answer
                          </button>
                        </div>
                      </li>
                    );
                  })}
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
                    alert("Session saved in memory (will reset on leave).");
                  }}
                >
                  Save (session)
                </button>
              )}
            </div>
          </>
        )}
      </section>
    </div>
  );
}
