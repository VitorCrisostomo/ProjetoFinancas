import { useState } from "react";

const EditableCategory = ({ currentCategory, categories, categoryIcons, onUpdate }) => {
  const [isEditing, setIsEditing] = useState(false);

  const handleChange = (e) => {
    const newCategory = e.target.value;
    if (newCategory !== currentCategory) {
      onUpdate(newCategory); // Só chama a API se realmente mudou
    }
    setIsEditing(false); // Fecha o select após a escolha
  };

  if (isEditing) {
    return (
      <select
        autoFocus
        defaultValue={currentCategory}
        onChange={handleChange}
        onBlur={() => setIsEditing(false)} // Fecha se o usuário clicar fora
        className="filter-select"
        style={{ padding: '4px 8px', fontSize: '0.9em', width: '100%', minWidth: '130px' }}
      >
        {categories.map((cat) => (
          <option key={cat} value={cat}>
            {categoryIcons[cat]} {cat}
          </option>
        ))}
      </select>
    );
  }

  return (
    <div 
      onClick={() => setIsEditing(true)}
      style={{ 
        cursor: 'pointer', 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'space-between',
        padding: '4px 8px',
        borderRadius: '6px',
        transition: 'background-color 0.2s',
        minWidth: '130px'
      }}
      title="Clique para alterar a categoria"
      onMouseEnter={(e) => e.currentTarget.style.backgroundColor = 'rgba(0,0,0,0.05)'}
      onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
    >
      <span>{currentCategory}</span>
      <span style={{ fontSize: '0.85em', opacity: 0.4 }}>✏️</span>
    </div>
  );
};

export default EditableCategory;