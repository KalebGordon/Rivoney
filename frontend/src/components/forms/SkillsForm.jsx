import React, { useEffect } from "react";
import AddRemoveButton from "../ui/AddRemoveButton";
import DescriptionList from "./DescriptionList";
import { useFormHandlers } from "../hooks/useFormHandlers";
import { initialSkill } from "../utils/defaultTemplates";

/**
 * JSON Resume shape expected:
 * skills: [{ name: string, level?: string, keywords: string[] }]
 */
const SkillsForm = ({ skills, setSkills }) => {
  const { handleChange, handleAdd } = useFormHandlers();

  // Ensure at least one row exists
  useEffect(() => {
    if (!skills || skills.length === 0) {
      setSkills([initialSkill]);
    }
  }, [skills, setSkills]);

  return (
    <>
      {(skills || []).map((skill, i) => (
        <div key={i} style={{ marginBottom: "1.5rem" }}>
          <h3>Skill</h3>

          <input
            type="text"
            className="form-input"
            placeholder="Skill name (e.g., Web Development)"
            value={skill.name || ""}
            onChange={handleChange(setSkills, i, "name")}
          />

          <input
            type="text"
            className="form-input"
            placeholder="Level (e.g., Beginner, Intermediate, Expert)"
            value={skill.level || ""}
            onChange={handleChange(setSkills, i, "level")}
          />

          {/* Add only on last row to reduce clutter */}
          {skills.length - 1 === i && (
            <AddRemoveButton label="Skill" onAdd={handleAdd(setSkills, initialSkill)} />
          )}
        </div>
      ))}
    </>
  );
};

export default SkillsForm;