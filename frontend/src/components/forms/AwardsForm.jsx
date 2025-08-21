import React, { useEffect } from "react";
import AddRemoveButton from "../ui/AddRemoveButton";
import { useFormHandlers } from "../hooks/useFormHandlers";
import { initialAward } from "../utils/defaultTemplates";

/**
 * JSON Resume shape expected:
 * awards: [{ title, date, awarder, summary }]
 */
export const AwardsForm = ({ awards, setAwards }) => {
  const { handleChange, handleAdd } = useFormHandlers();

  // Ensure at least one row exists
  useEffect(() => {
    if (!awards || awards.length === 0) {
      setAwards([initialAward]);
    }
  }, [awards, setAwards]);

  return (
    <section className="section-card">
      <h3>Awards</h3>

      {(awards || []).map((award, i) => (
        <div key={i} style={{ marginBottom: "1.5rem" }}>
          <input
            type="text"
            className="form-input"
            placeholder="Award Title"
            value={award.title || ""}
            onChange={handleChange(setAwards, i, "title")}
          />

          <input
            type="text"
            className="form-input"
            placeholder="Awarding Organization"
            value={award.awarder || ""}
            onChange={handleChange(setAwards, i, "awarder")}
          />

          <input
            type="month"
            className="form-input"
            value={award.date || ""}
            onChange={handleChange(setAwards, i, "date")}
          />

          <textarea
            className="form-textarea mt-2"
            rows={3}
            placeholder="Summary"
            value={award.summary || ""}
            onChange={handleChange(setAwards, i, "summary")}
          />

          {/* Divider between rows (not after the last) */}
          {i < (awards?.length ?? 0) - 1 && <hr />}
        </div>
      ))}

      {/* Single add button adds another award row within the same section */}
      <AddRemoveButton
        label="Award"
        onAdd={handleAdd(setAwards, initialAward)}
      />
    </section>
  );
};

export default AwardsForm;
