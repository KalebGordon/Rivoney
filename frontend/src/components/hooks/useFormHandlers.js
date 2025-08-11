// File: hooks/useFormHandlers.js
export const useFormHandlers = () => {
  const handleChange = (setter, index, field) => (e) => {
    const { value, type, checked } = e.target;
    const val = type === 'checkbox' ? checked : value;

    setter((prev) =>
      prev.map((item, i) =>
        i === index
          ? {
              ...item,
              [field]: val,
              ...(field === 'isCurrent' && checked ? { endDate: 'Current' } : {}),
            }
          : item
      )
    );
  };

  const handleListChange = (setter, index) => (e) => {
    const { value } = e.target;
    setter((prev) =>
      prev.map((item, i) => (i === index ? value : item))
    );
  };

  const handleAdd = (setter, stateTemplate) => () =>
    setter((prev) => [...prev, stateTemplate]);

  return { handleChange, handleListChange, handleAdd };
};
