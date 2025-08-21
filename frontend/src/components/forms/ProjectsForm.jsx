import React, { useEffect } from "react";
import AddRemoveButton from "../ui/AddRemoveButton";
import DescriptionList from "./DescriptionList";
import { useFormHandlers } from "../hooks/useFormHandlers";
import { initialProject } from "../utils/defaultTemplates";

const ProjectsForm = ({ projects, setProjects }) => {
  const { handleChange, handleAdd } = useFormHandlers();

  // Ensure at least one project row exists
  useEffect(() => {
    if (!projects || projects.length === 0) {
      setProjects([initialProject]);
    }
  }, [projects, setProjects]);

  return (
    <section className="section-card">
      <h3>Projects</h3>

      {(projects || []).map((proj, i) => (
        <div key={i} style={{ marginBottom: "1.5rem" }}>
          <input
            type="text"
            className="form-input"
            placeholder="Project Name"
            value={proj.name || ""}
            onChange={handleChange(setProjects, i, "name")}
          />

          <input
            type="url"
            className="form-input"
            placeholder="Project URL"
            value={proj.url || ""}
            onChange={handleChange(setProjects, i, "url")}
          />

          <div style={{ marginTop: "1rem" }}>
            <DescriptionList
              description={proj.highlights || []}
              onChange={(j, value) =>
                setProjects((prev) =>
                  prev.map((item, idx) =>
                    idx === i
                      ? {
                          ...item,
                          highlights: (item.highlights || []).map((d, dj) =>
                            dj === j ? value : d
                          ),
                        }
                      : item
                  )
                )
              }
              onRemove={(j) =>
                setProjects((prev) =>
                  prev.map((item, idx) =>
                    idx === i
                      ? {
                          ...item,
                          highlights: (item.highlights || []).filter(
                            (_, dj) => dj !== j
                          ),
                        }
                      : item
                  )
                )
              }
              onAdd={() =>
                setProjects((prev) =>
                  prev.map((item, idx) =>
                    idx === i
                      ? {
                          ...item,
                          highlights: [...(item.highlights || []), ""],
                        }
                      : item
                  )
                )
              }
              disabledRemove={true}
            />
          </div>

          {/* Divider between rows (not after the last) */}
          {i < (projects?.length ?? 0) - 1 && <hr />}
        </div>
      ))}

      {/* Single add button adds another project row within the same section */}
      <AddRemoveButton
        label="Project"
        onAdd={handleAdd(setProjects, initialProject)}
      />
    </section>
  );
};

export default ProjectsForm;
