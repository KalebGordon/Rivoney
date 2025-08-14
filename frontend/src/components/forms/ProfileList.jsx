import React from 'react';

const toProfileObj = (p) =>
  typeof p === 'string' ? { network: '', url: p } : (p || { network: '', url: '' });

const ProfileList = ({ profiles = [], onChange, onRemove, onAdd, disabledRemove }) => {
  const handleField = (index, field) => (e) => {
    const curr = toProfileObj(profiles[index]);
    const updated = { ...curr, [field]: e.target.value };
    // Keep the same onChange signature (index, value), but now value is an object
    onChange(index, updated);
  };

  return (
    <div style={{ marginBottom: '1rem' }}>
      {profiles.map((link, j) => {
        const profile = toProfileObj(link);

        return (
          <div
            key={j}
            style={{
              display: 'grid',
              gridTemplateColumns: '1fr 2fr auto',
              gap: '0.5rem',
              alignItems: 'center',
              marginBottom: '0.5rem',
            }}
          >
            {/* Network */}
            <input
              type="text"
              className="form-input"
              placeholder="Network (e.g., Twitter)"
              value={profile.network}
              onChange={handleField(j, 'network')}
              list="social-networks"
            />

            {/* URL */}
            <input
              type="url"
              className="form-input"
              placeholder="https://twitter.com/handle"
              value={profile.url}
              onChange={handleField(j, 'url')}
            />

            {/* Remove */}
            <button
              type="button"
              className="remove-btn"
              onClick={() => onRemove(j)}
              disabled={disabledRemove && profiles.length === 1}
              aria-label={`Remove profile ${j + 1}`}
              title="Remove"
            >
              <span>✖</span>
            </button>
          </div>
        );
      })}

      {/* Add */}
      <button
        type="button"
        onClick={() => onAdd({ network: '', url: '' }) /* pass a sensible default if parent accepts it */}
      >
        + Add Social
      </button>

      <hr
        style={{
          marginTop: '1rem',
          marginBottom: '1rem',
          border: 'none',
          borderTop: '1px solid #ccc',
        }}
      />
    </div>
  );
};

export default ProfileList;
