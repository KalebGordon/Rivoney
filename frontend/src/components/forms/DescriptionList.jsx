import React from 'react';

const DescriptionList = ({ description = [], onChange, onRemove, onAdd, disabledRemove }) => {
  return (
    <div style={{ marginBottom: '1rem' }}>
      <label>Description</label>
      {description.map((desc, j) => (
        <div
          key={j}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            marginBottom: '0.5rem',
          }}
        >
          <input
            type="text" className="form-input"
            placeholder={`Description ${j + 1}`}
            value={desc}
            onChange={(e) => onChange(j, e.target.value)}
            style={{
              flexGrow: 1,
              padding: '0.5rem',
              fontSize: '1rem',
              lineHeight: '1.5rem',
              height: '1.5rem',
            }}
          />
          <button
            type="button"
            className="remove-btn"
            onClick={() => onRemove(j)}
            disabled={disabledRemove && description.length === 1}
          >
            <span>✖</span>
          </button>
        </div>
      ))}
      <button type="button" onClick={onAdd}>+ Add Description</button>
      <hr style={{ marginTop: '1rem', marginBottom: '1rem', border: 'none', borderTop: '1px solid #ccc' }} />
    </div>
  );
};

export default DescriptionList;
