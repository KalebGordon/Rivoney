import React, { useEffect } from "react";
import AddRemoveButton from "../ui/AddRemoveButton";
import { useFormHandlers } from "../hooks/useFormHandlers";
import { initialPublication } from "../utils/defaultTemplates";

/**
 * JSON Resume shape expected:
 * publications: [{ name, publisher, releaseDate, url, summary }]
 */
export const PublicationsForm = ({ publications, setPublications }) => {
  const { handleChange, handleAdd } = useFormHandlers();

  useEffect(() => {
    if (!publications || publications.length === 0) {
      setPublications([initialPublication]);
    }
  }, [publications, setPublications]);

  return (
    <>
      {(publications || []).map((pub, i) => (
        <div key={i} style={{ marginBottom: "1.5rem" }}>
          <h3>Article/Publication</h3>

          <input
            type="text"
            className="form-input"
            placeholder="Title"
            value={pub.name || ""}
            onChange={handleChange(setPublications, i, "name")}
          />

          <input
            type="text"
            className="form-input"
            placeholder="Publisher"
            value={pub.publisher || ""}
            onChange={handleChange(setPublications, i, "publisher")}
          />

          <input
            type="date"
            className="form-input"
            placeholder="Release date"
            value={pub.releaseDate || ""}
            onChange={handleChange(setPublications, i, "releaseDate")}
          />

          <input
            type="url"
            className="form-input"
            placeholder="https://example.com"
            value={pub.url || ""}
            onChange={handleChange(setPublications, i, "url")}
          />

          <textarea
            className="form-textarea mt-2"
            rows={3}
            placeholder="Summary"
            value={pub.summary || ""}
            onChange={handleChange(setPublications, i, "summary")}
          />

          {publications.length - 1 === i && (
            <AddRemoveButton
              label="Publication"
              onAdd={handleAdd(setPublications, initialPublication)}
            />
          )}
        </div>
      ))}
    </>
  );
};

export default PublicationsForm;