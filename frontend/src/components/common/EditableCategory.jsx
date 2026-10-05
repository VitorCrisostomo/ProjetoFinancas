import { useRef, useState } from 'react';
import CategoryPicker from './CategoryPicker.jsx';

export default function EditableCategory({ currentCategory, currentSubcategory, categories,
  onUpdate, label = 'Alterar categoria' }) {
  const [isSaving, setIsSaving] = useState(false);
  const saving = useRef(false);
  const handleChange = async (data) => {
    if (saving.current) return;
    saving.current = true;
    setIsSaving(true);
    try { await onUpdate(data); }
    finally { saving.current = false; setIsSaving(false); }
  };
  return <CategoryPicker categories={categories} category={currentCategory} subcategory={currentSubcategory}
    label={label} disabled={isSaving} onChange={handleChange} />;
}
