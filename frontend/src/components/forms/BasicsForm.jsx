import React from 'react';
import ProfileList from './ProfileList';

const BasicsForm = ({ basics, setBasics }) => {
  const handleChange = (field) => (e) => {
    setBasics((prev) => ({ ...prev, [field]: e.target.value }));
  };

  const handleLocationChange = (field) => (e) => {
    setBasics((prev) => ({
      ...prev,
      location: { ...prev.location, [field]: e.target.value },
    }));
  };

  return (
    <div style={{ marginBottom: '2rem' }}>
      <section className="section-card">
        <h2>Resume Builder</h2>
        <h3>Basic Information</h3>
        <input type="text" placeholder="Full Name" value={basics.name} onChange={handleChange('name')} />
        <input type="text" placeholder="Professional Title" value={basics.label} onChange={handleChange('label')} />
        <input type="email" placeholder="Email" value={basics.email} onChange={handleChange('email')} />
        <input type="tel" placeholder="Phone" value={basics.phone} onChange={handleChange('phone')} />
        <input type="url" placeholder="Website" value={basics.url} onChange={handleChange('url')} />
        <textarea placeholder="Professional Summary" value={basics.summary} onChange={handleChange('summary')} />

        <h4>Location</h4>
        <input type="text" placeholder="Address" value={basics.location.address} onChange={handleLocationChange('address')} />
        <input type="text" placeholder="City" value={basics.location.city} onChange={handleLocationChange('city')} />
        <input type="text" placeholder="Region/State" value={basics.location.region} onChange={handleLocationChange('region')} />
        <input type="text" placeholder="Postal Code" value={basics.location.postalCode} onChange={handleLocationChange('postalCode')} />
        <input type="text" placeholder="Country" value={basics.location.countryCode} onChange={handleLocationChange('countryCode')} />

        <h4>Social Profiles</h4>
        <ProfileList
          profiles={
            Array.isArray(basics.profiles) && basics.profiles.length > 0
              ? basics.profiles
              : [''] // fallback to one empty
          }
          onChange={(j, value) =>
            setBasics((prev) => ({
              ...prev,
              profiles: (prev.profiles ?? []).map((link, idx) =>
                idx === j ? value : link
              ),
            }))
          }
          onRemove={(j) =>
            setBasics((prev) => ({
              ...prev,
              profiles: (prev.profiles ?? []).filter((_, idx) => idx !== j),
            }))
          }
          onAdd={() =>
            setBasics((prev) => ({
              ...prev,
              profiles: [...(prev.profiles ?? []), ''],
            }))
          }
          disabledRemove={true}
        />
      </section>
    </div>
  );
};

export default BasicsForm;
