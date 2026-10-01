import { categoryIcons } from '../../utils/category.jsx';

const types = ['all', 'income', 'expense'];

export default function TransactionFilters({ categories, filterCategory, setFilterCategory,
  filterType, setFilterType }) {
  return (
    <div className="filters-section">
      <div className="filter-group">
        <label>Categoria</label>
        <select
          value={filterCategory}
          onChange={(e) => setFilterCategory(e.target.value)}
          className="filter-select"
        >
          {categories.map((cat) => (
            <option key={cat} value={cat}>
              {cat === 'all' ? 'Todas as categorias' : `${categoryIcons[cat]} ${cat}`}
            </option>
          ))}
        </select>
      </div>

      <div className="filter-group">
        <label>Tipo</label>
        <select
          value={filterType}
          onChange={(e) => setFilterType(e.target.value)}
          className="filter-select"
        >
          {types.map((type) => (
            <option key={type} value={type}>
              {type === 'all' ? 'Todos os tipos' : type === 'income' ? 'Receitas' : 'Despesas'}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}
