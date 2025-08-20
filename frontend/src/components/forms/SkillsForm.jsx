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
      <h3>Skill</h3>
      {(skills || []).map((skill, i) => (
        <div key={i} style={{ marginBottom: "1.5rem" }}>

          <input
            type="text"
            className="form-input"
            placeholder="Skill (e.g., Web Development)"
            value={skill || ""}
            onChange={(e) => {
              const newSkills = [...skills];
              newSkills[i] = e.target.value;
              setSkills(newSkills);
            }}
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