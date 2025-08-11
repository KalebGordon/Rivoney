import React from 'react';
import DescriptionList from './DescriptionList';
import AddRemoveButton from '../ui/AddRemoveButton';
import { initialEducation } from '../utils/defaultTemplates';
import { useFormHandlers } from '../hooks/useFormHandlers';

const EducationForm = ({ education, setEducation }) => {
  const { handleChange, handleAdd } = useFormHandlers();

  return (
    <>
      {education.map((edu, i) => (
        <div key={i} style={{ marginBottom: '2rem' }}>
          <h3>Education</h3>
          <input type="text" placeholder="School" value={edu.school} onChange={handleChange(setEducation, i, 'school')} />
          <input type="text" placeholder="Degree" value={edu.degree} onChange={handleChange(setEducation, i, 'degree')} />
          
          <label>Start Date</label>
          <input type="month" value={edu.startDate} onChange={handleChange(setEducation, i, 'startDate')} />

          <label>End Date</label>
          <input type="month" value={edu.isCurrent ? '' : edu.endDate} onChange={handleChange(setEducation, i, 'endDate')} disabled={edu.isCurrent} />

          <div style={{ marginTop: '0rem', marginBottom: '1rem', display: 'flex', justifyContent: 'flex-start' }}>
            <label htmlFor={`currentEdu-${i}`} style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', whiteSpace: 'nowrap' }}>
              <input
                id={`currentEdu-${i}`}
                type="checkbox"
                checked={edu.isCurrent}
                onChange={handleChange(setEducation, i, 'isCurrent')}
                style={{ margin: '0.1rem' }}
              />
              <span>Currently Attending</span>
            </label>
          </div>

          <input type="text" placeholder="Focus Areas" value={edu.focusAreas} onChange={handleChange(setEducation, i, 'focusAreas')} />
          <input type="text" placeholder="Honors (optional)" value={edu.honors} onChange={handleChange(setEducation, i, 'honors')} />

          <DescriptionList
            description={edu.description}
            onChange={(j, value) =>
              setEducation(prev =>
                prev.map((item, idx) =>
                  idx === i
                    ? {
                        ...item,
                        description: item.description.map((d, dj) =>
                          dj === j ? value : d
                        ),
                      }
                    : item
                )
              )
            }
            onRemove={(j) =>
              setEducation(prev =>
                prev.map((item, idx) =>
                  idx === i
                    ? {
                        ...item,
                        description: item.description.filter((_, dj) => dj !== j),
                      }
                    : item
                )
              )
            }
            onAdd={() =>
              setEducation(prev =>
                prev.map((item, idx) =>
                  idx === i
                    ? {
                        ...item,
                        description: [...item.description, ''],
                      }
                    : item
                )
              )
            }
            disabledRemove={true}
          />

          {education.length - 1 === i && (
            <AddRemoveButton
              label="Education"
              onAdd={handleAdd(setEducation, initialEducation)}
            />
          )}
          <hr />
        </div>
      ))}
    </>
  );
};

export default EducationForm;
