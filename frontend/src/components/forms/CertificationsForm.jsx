import React, { useEffect } from "react";
import AddRemoveButton from "../ui/AddRemoveButton";
import { useFormHandlers } from "../hooks/useFormHandlers";
import { initialCertificate } from "../utils/defaultTemplates";

const CertificationsForm = ({ certifications, setCertifications }) => {
  const { handleChange, handleAdd } = useFormHandlers();

  // Ensure at least one row exists
  useEffect(() => {
    if (!certifications || certifications.length === 0) {
      setCertifications([initialCertificate]);
    }
  }, [certifications, setCertifications]);

  return (
    <section className="section-card">
      <h3>Certifications</h3>

      {(certifications || []).map((cert, i) => (
        <div key={i} style={{ marginBottom: "1.5rem" }}>
          <input
            type="text"
            className="form-input"
            placeholder="Certificate Name"
            value={cert.name || ""}
            onChange={handleChange(setCertifications, i, "name")}
          />

          <label>Date</label>
          <input
            type="month"
            className="form-input"
            value={cert.date || ""}
            onChange={handleChange(setCertifications, i, "date")}
          />

          <input
            type="text"
            className="form-input"
            placeholder="Issuer"
            value={cert.issuer || ""}
            onChange={handleChange(setCertifications, i, "issuer")}
          />

          <input
            type="url"
            className="form-input"
            placeholder="Certificate URL"
            value={cert.url || ""}
            onChange={handleChange(setCertifications, i, "url")}
          />

          {/* Divider between rows (not after the last) */}
          {i < (certifications?.length ?? 0) - 1 && <hr />}
        </div>
      ))}

      {/* Single add button adds another certification row within the same section */}
      <AddRemoveButton
        label="Certification"
        onAdd={handleAdd(setCertifications, initialCertificate)}
      />
    </section>
  );
};

export default CertificationsForm;
