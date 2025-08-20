import React, { useEffect } from 'react';
import AddRemoveButton from '../ui/AddRemoveButton';
import { useFormHandlers } from '../hooks/useFormHandlers';
import { initialCertificate } from '../utils/defaultTemplates';

const CertificationsForm = ({ certifications, setCertifications }) => {
  const { handleChange, handleAdd } = useFormHandlers();

  // Ensure at least one row exists
  useEffect(() => {
    if (!certifications || certifications.length === 0) {
      setCertifications([initialCertificate]);
    }
  }, [certifications, setCertifications]);

  return (
    <>

      {certifications.map((cert, i) => (
        <div key={i} style={{ marginBottom: '1.5rem' }}>
          <h3>Certification</h3>
          <input
            type="text"
            className="form-input"
            placeholder="Certificate Name"
            value={cert.name || ''}
            onChange={handleChange(setCertifications, i, 'name')}
          />

          <label>Date</label>
          <input
            type="month"
            className="form-input"
            value={cert.date || ''}
            onChange={handleChange(setCertifications, i, 'date')}
          />

          <input
            type="text"
            className="form-input"
            placeholder="Issuer"
            value={cert.issuer || ''}
            onChange={handleChange(setCertifications, i, 'issuer')}
          />

          <input
            type="url"
            className="form-input"
            placeholder="Certificate URL"
            value={cert.url || ''}
            onChange={handleChange(setCertifications, i, 'url')}
          />

          {certifications.length - 1 === i && (
            <AddRemoveButton
              label="Certification"
              onAdd={handleAdd(setCertifications, initialCertificate)}
            />
          )}
        </div>
      ))}

      <hr />
    </>
  );
};

export default CertificationsForm;
