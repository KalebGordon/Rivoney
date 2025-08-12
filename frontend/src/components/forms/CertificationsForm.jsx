import React from 'react';
import AddRemoveButton from '../ui/AddRemoveButton';

const CertificationsForm = ({ certifications, setCertifications }) => {
  const handleChange = (index) => (e) => {
    const value = e.target.value;
    setCertifications((prev) => prev.map((item, i) => (i === index ? value : item)));
  };

  const handleAdd = () => setCertifications((prev) => [...prev, '']);

  return (
    <>
      <h3>Certifications</h3>
      {certifications.map((cert, i) => (
        <input
          key={i}
          type="text" className="form-input"
          placeholder="Certification"
          value={cert}
          onChange={handleChange(i)}
        />
      ))}
      <AddRemoveButton label="Certification" onAdd={handleAdd} />
      <hr />
    </>
  );
};

export default CertificationsForm;
