// components/forms/EducationForm.jsx
import React, { useEffect } from "react";
import DescriptionList from "./DescriptionList";
import AddRemoveButton from "../ui/AddRemoveButton";
import { initialEducation } from "../utils/defaultTemplates";
import { useFormHandlers } from "../hooks/useFormHandlers";

const EducationForm = ({ education, setEducation }) => {
  const { handleChange, handleAdd } = useFormHandlers();

  // Ensure at least one row exists
  useEffect(() => {
    if (!education || education.length === 0) {
      setEducation([initialEducation]);
    }
  }, [education, setEducation]);

  return (
    <section className="section-card">
      <h3>Education</h3>

      {(education || []).map((edu, i) => (
        <div key={i} style={{ marginBottom: "1.5rem" }}>
          <input
            type="text"
            className="form-input"
            placeholder="Institution"
            value={edu.institution || ""}
            onChange={handleChange(setEducation, i, "institution")}
          />

          <input
            type="text"
            className="form-input"
            placeholder="Degree"
            value={edu.studyType || ""}
            onChange={handleChange(setEducation, i, "studyType")}
          />

          <input
            type="text"
            className="form-input"
            placeholder="Area of Study"
            value={edu.area || ""}
            onChange={handleChange(setEducation, i, "area")}
          />

          <input
            type="text"
            className="form-input"
            placeholder="GPA"
            value={edu.score || ""}
            onChange={handleChange(setEducation, i, "score")}
          />

          <label>Start Date</label>
          <input
            type="month"
            value={edu.startDate || ""}
            onChange={handleChange(setEducation, i, "startDate")}
          />

          <label>End Date</label>
          <input
            type="month"
            value={edu.isCurrent ? "" : (edu.endDate || "")}
            onChange={handleChange(setEducation, i, "endDate")}
            disabled={!!edu.isCurrent}
          />

          <div
            style={{
              marginTop: "-1rem",
              marginBottom: "1rem",
              display: "flex",
              justifyContent: "flex-start",
            }}
          >
            <label
              htmlFor={`currentEdu-${i}`}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "0.25rem",
                whiteSpace: "nowrap",
              }}
            >
              <input
                id={`currentEdu-${i}`}
                type="checkbox"
                checked={!!edu.isCurrent}
                onChange={handleChange(setEducation, i, "isCurrent")}
                style={{ margin: "0.1rem" }}
              />
              <span>Currently Attending</span>
            </label>
          </div>

          {/* Description bullets */}
          <DescriptionList
            description={edu.description || []}
            onChange={(j, value) =>
              setEducation((prev) =>
                prev.map((item, idx) =>
                  idx === i
                    ? {
                        ...item,
                        description: (item.description || []).map((d, dj) =>
                          dj === j ? value : d
                        ),
                      }
                    : item
                )
              )
            }
            onRemove={(j) =>
              setEducation((prev) =>
                prev.map((item, idx) =>
                  idx === i
                    ? {
                        ...item,
                        description: (item.description || []).filter(
                          (_, dj) => dj !== j
                        ),
                      }
                    : item
                )
              )
            }
            onAdd={() =>
              setEducation((prev) =>
                prev.map((item, idx) =>
                  idx === i
                    ? {
                        ...item,
                        description: [...(item.description || []), ""],
                      }
                    : item
                )
              )
            }
            disabledRemove={true}
          />

          <hr />
        </div>
      ))}

      {/* Single add button adds another education row within the same section */}
      <AddRemoveButton
        label="Education"
        onAdd={handleAdd(setEducation, initialEducation)}
      />
    </section>
  );
};

export default EducationForm;
