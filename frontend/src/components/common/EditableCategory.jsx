const EditableCategory = ({ currentCategory, categories, categoryIcons, onUpdate, label = 'Alterar categoria' }) => {
  const handleChange = (e) => {
    const newCategory = e.target.value;
    if (newCategory !== currentCategory) {
      onUpdate(newCategory);
    }
  };

  return (
    <span className="editable-category">
      <select
        value={currentCategory}
        onChange={handleChange}
        aria-label={label}
        title="Clique para alterar a categoria"
        className="editable-category-select"
      >
        {!categories.includes(currentCategory) && (
          <option value={currentCategory}>{currentCategory}</option>
        )}
        {categories.map((cat) => (
          <option key={cat} value={cat}>
            {categoryIcons[cat]} {cat}
          </option>
        ))}
      </select>
    </span>
  );
};

export default EditableCategory;
