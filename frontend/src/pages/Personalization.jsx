import { useId, useRef, useState } from 'react';
import Button from '../components/common/Button.jsx';
import { categoryIcons } from '../utils/category.jsx';

function CategoryNameForm({ label, placeholder, submitLabel, onSave }) {
  const id = useId();
  const [name, setName] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState('');
  const saving = useRef(false);

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!name.trim() || saving.current) return;
    saving.current = true;
    setIsSaving(true);
    setError('');
    try {
      if (await onSave(name.trim())) setName('');
    } catch (cause) {
      setError(cause.message);
    } finally {
      saving.current = false;
      setIsSaving(false);
    }
  };

  return (
    <form className="category-create-form" onSubmit={handleSubmit}>
      <div className="form-group">
        <label htmlFor={id}>{label}</label>
        <input id={id} value={name} maxLength={50} placeholder={placeholder} required
          disabled={isSaving} onChange={(event) => setName(event.target.value)} />
      </div>
      <Button type="submit" variant="secondary" disabled={isSaving || !name.trim()}>
        {isSaving ? 'Salvando...' : submitLabel}
      </Button>
      {error && <p className="category-form-error" role="alert">{error}</p>}
    </form>
  );
}

export default function PersonalizationPage({ categories, onCreateCategory, onCreateSubcategory }) {
  const [search, setSearch] = useState('');
  const id = useId();
  const query = search.trim().toLocaleLowerCase('pt-BR');
  const visibleCategories = categories.filter((category) => (
    [category.name, ...category.subcategories.map((sub) => sub.name)]
      .some((name) => name.toLocaleLowerCase('pt-BR').includes(query))
  ));
  const childCount = categories.reduce((count, category) => count + category.subcategories.length, 0);

  return (
    <div className="page-content">
      <div className="page-header">
        <h1>Personalização</h1>
        <p>Organize suas categorias e detalhe as transações com subcategorias opcionais.</p>
      </div>
      <div className="section">
        <h2>Nova categoria</h2>
        <CategoryNameForm label="Nome da categoria" placeholder="Ex.: Viagens"
          submitLabel="＋ Criar categoria" onSave={onCreateCategory} />
      </div>
      <div className="category-catalog-header">
        <div>
          <h2>Suas categorias</h2>
          <p>{categories.length} categorias · {childCount} subcategorias</p>
        </div>
        <div className="filter-group">
          <label htmlFor={id}>Buscar categoria ou subcategoria</label>
          <input id={id} className="filter-select" type="search" value={search}
            placeholder="Buscar pelo nome" onChange={(event) => setSearch(event.target.value)} />
        </div>
      </div>
      <div className="category-catalog-grid">
        {visibleCategories.map((category) => (
          <article className="card category-catalog-card" key={category.id}>
            <div className="category-catalog-title">
              <span aria-hidden="true">{categoryIcons[category.name] || '🏷️'}</span>
              <h3>{category.name}</h3>
              <span className="category-child-count">{category.subcategories.length}</span>
            </div>
            {category.subcategories.length ? (
              <ul className="subcategory-list">
                {category.subcategories.map((sub) => <li key={sub.id}>{sub.name}</li>)}
              </ul>
            ) : <p className="category-no-children">Sem subcategorias. Você pode usar apenas a categoria.</p>}
            <CategoryNameForm label={`Nova subcategoria de ${category.name}`} placeholder="Ex.: Hospedagem"
              submitLabel="＋ Adicionar" onSave={(name) => onCreateSubcategory(category.id, name)} />
          </article>
        ))}
      </div>
      {visibleCategories.length === 0 && <p className="empty-state">Nenhuma categoria encontrada.</p>}
    </div>
  );
}
