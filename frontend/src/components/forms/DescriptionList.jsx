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
            type="text"
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
            onClick={() => onRemove(j)}
            disabled={disabledRemove && description.length === 1}
            style={{
              padding: 0,
              width: '2rem',
              height: '2rem',
              minWidth: '2rem',
              minHeight: '2rem',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '1.25rem',
              backgroundColor: '#1976d2',
              color: '#fff',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              flexShrink: 0,
            }}
          >
            ✖
          </button>
        </div>
      ))}
      <button type="button" onClick={onAdd}>+ Add Description</button>
      <hr style={{ marginTop: '1rem', marginBottom: '1rem', border: 'none', borderTop: '1px solid #ccc' }} />
    </div>
  );
};

export default DescriptionList;
