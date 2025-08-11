import React from 'react';
import AddRemoveButton from '../ui/AddRemoveButton';

const ProjectsForm = ({ projects, setProjects }) => {
  const handleChange = (index) => (e) => {
    const value = e.target.value;
    setProjects((prev) => prev.map((item, i) => (i === index ? value : item)));
  };

  const handleAdd = () => setProjects((prev) => [...prev, '']);

  return (
    <>
      <h3>Projects</h3>
      {projects.map((proj, i) => (
        <input
          key={i}
          type="text"
          placeholder="Project Description"
          value={proj}
          onChange={handleChange(i)}
        />
      ))}
      <AddRemoveButton label="Project" onAdd={handleAdd} />
      <hr />
    </>
  );
};

export default ProjectsForm;
