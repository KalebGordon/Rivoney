import React, { useEffect } from "react";
import DescriptionList from "./DescriptionList";
import AddRemoveButton from "../ui/AddRemoveButton";
import { initialExperience } from "../utils/defaultTemplates";
import { useFormHandlers } from "../hooks/useFormHandlers";

const ExperienceForm = ({ experience, setExperience }) => {
  const { handleChange, handleAdd } = useFormHandlers();

  // Ensure at least one row exists
  useEffect(() => {
    if (!experience || experience.length === 0) {
      setExperience([initialExperience]);
    }
  }, [experience, setExperience]);

  return (
    <section className="section-card">
      <h3>Experience</h3>

      {(experience || []).map((exp, i) => (
        <div key={i} style={{ marginBottom: "1.5rem" }}>
          <input
            type="text"
            className="resume-form"
            placeholder="Company"
            value={exp.company || ""}
            onChange={handleChange(setExperience, i, "company")}
          />

          <input
            type="text"
            className="resume-form"
            placeholder="Title"
            value={exp.title || ""}
            onChange={handleChange(setExperience, i, "title")}
          />

          <label>Start Date</label>
          <input
            type="month"
            value={exp.startDate || ""}
            onChange={handleChange(setExperience, i, "startDate")}
          />

          <label>End Date</label>
          <input
            type="month"
            value={exp.isCurrent ? "" : (exp.endDate || "")}
            onChange={handleChange(setExperience, i, "endDate")}
            disabled={!!exp.isCurrent}
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
              htmlFor={`currentExp-${i}`}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "0.25rem",
                whiteSpace: "nowrap",
              }}
            >
              <input
                id={`currentExp-${i}`}
                type="checkbox"
                className="checkbox"         
                checked={!!exp.isCurrent}
                onChange={handleChange(setExperience, i, "isCurrent")}
                style={{ margin: "0.1rem" }}
              />
              <span>Currently Working Here</span>
            </label>
          </div>

          <input
            type="text"
            className="resume-form"
            placeholder="Setting (e.g., Remote)"
            value={exp.setting || ""}
            onChange={handleChange(setExperience, i, "setting")}
          />

          <DescriptionList
            description={exp.description || []}
            onChange={(j, value) =>
              setExperience((prev) =>
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
              setExperience((prev) =>
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
              setExperience((prev) =>
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

      {/* Single add button adds another experience row within the same section */}
      <AddRemoveButton
        label="Experience"
        onAdd={handleAdd(setExperience, initialExperience)}
      />
    </section>
  );
};

export default ExperienceForm;
