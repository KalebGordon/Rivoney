import React from 'react';

const BasicsForm = ({ basics, setBasics }) => {
  const handleChange = (field) => (e) => {
    setBasics((prev) => ({ ...prev, [field]: e.target.value }));
  };

  const handleLocationChange = (field) => (e) => {
    setBasics((prev) => ({
      ...prev,
      location: { ...prev.location, [field]: e.target.value }
    }));
  };

  return (
    <div style={{ marginBottom: '2rem' }}>
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
    </div>
  );
};

export default BasicsForm;
