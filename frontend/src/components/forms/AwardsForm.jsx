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

  useEffect(() => {
    if (!awards || awards.length === 0) {
      setAwards([initialAward]);
    }
  }, [awards, setAwards]);

  return (
    <>
      {(awards || []).map((award, i) => (
        <div key={i} style={{ marginBottom: "1.5rem" }}>
          <h3>Award</h3>

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
            type="date"
            className="form-input"
            placeholder="YYYY-MM-DD"
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

          {awards.length - 1 === i && (
            <AddRemoveButton label="Award" onAdd={handleAdd(setAwards, initialAward)} />
          )}
        </div>
      ))}
    </>
  );
};

export default AwardsForm;