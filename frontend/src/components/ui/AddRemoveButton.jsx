import React from 'react';

const AddRemoveButton = ({ label, onAdd }) => (
  <button type="button" onClick={onAdd}>
    + Add {label}
  </button>
);

export default AddRemoveButton;
