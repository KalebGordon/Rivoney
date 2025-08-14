import React, { useEffect } from 'react';
import AddRemoveButton from '../ui/AddRemoveButton';
import DescriptionList from './DescriptionList';
import { useFormHandlers } from '../hooks/useFormHandlers';
import { initialProject } from '../utils/defaultTemplates';

const ProjectsForm = ({ projects, setProjects }) => {
  const { handleChange, handleAdd } = useFormHandlers();

  // Ensure at least one project row exists on mount/when projects is empty
  useEffect(() => {
    if (!projects || projects.length === 0) {
      setProjects([initialProject]);
    }
  }, [projects, setProjects]);

  return (
    <>

      {projects.map((proj, i) => (
        <div key={i} style={{ marginBottom: '1.5rem' }}>
          <h3>Project</h3>
          <input
            type="text"
            className="form-input"
            placeholder="Project Name"
            value={proj.name || ''}
            onChange={handleChange(setProjects, i, 'name')}
          />

          <label>Start Date</label>
          <input
            type="date"
            className="form-input"
            value={proj.startDate || ''}
            onChange={handleChange(setProjects, i, 'startDate')}
          />

          <label>End Date</label>
          <input
            type="date"
            className="form-input"
            value={proj.endDate || ''}
            onChange={handleChange(setProjects, i, 'endDate')}
          />

          <input
            type="url"
            className="form-input"
            placeholder="Project URL (https://...)"
            value={proj.url || ''}
            onChange={handleChange(setProjects, i, 'url')}
          />

          <div style={{ marginTop: '1rem' }}>
            <DescriptionList
              description={proj.highlights || []}
              onChange={(j, value) =>
                setProjects(prev =>
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
                setProjects(prev =>
                  prev.map((item, idx) =>
                    idx === i
                      ? {
                          ...item,
                          highlights: (item.highlights || []).filter((_, dj) => dj !== j),
                        }
                      : item
                  )
                )
              }
              onAdd={() =>
                setProjects(prev =>
                  prev.map((item, idx) =>
                    idx === i
                      ? { ...item, highlights: [...(item.highlights || []), ''] }
                      : item
                  )
                )
              }
              disabledRemove={true}
            />
          </div>

          {projects.length - 1 === i && (
            <AddRemoveButton
              label="Project"
              onAdd={handleAdd(setProjects, initialProject)}
            />
          )}
          <hr />
        </div>
      ))}
    </>
  );
};

export default ProjectsForm;
