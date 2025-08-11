import React from 'react';

const FormSection = ({ title, children }) => (
  <section style={{ marginBottom: '2rem' }}>
    <h3>{title}</h3>
    {children}
  </section>
);

export default FormSection;
