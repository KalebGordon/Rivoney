import React from 'react';
import AddRemoveButton from '../ui/AddRemoveButton';

const SkillsForm = ({ skills, setSkills }) => {
  const handleChange = (index) => (e) => {
    const value = e.target.value;
    setSkills((prev) => prev.map((item, i) => (i === index ? value : item)));
  };

  const handleAdd = () => setSkills((prev) => [...prev, '']);

  return (
    <>
      <h3>Skills</h3>
      {skills.map((skill, i) => (
        <input
          key={i}
          type="text" className="form-input"
          placeholder="Skill"
          value={skill}
          onChange={handleChange(i)}
        />
      ))}
      <AddRemoveButton label="Skill" onAdd={handleAdd} />
      <hr />
    </>
  );
};

export default SkillsForm;
