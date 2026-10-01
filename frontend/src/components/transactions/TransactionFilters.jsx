import { categoryIcons } from '../../utils/category.jsx';
import TransactionPeriodFilter from '../common/TransactionPeriodFilter.jsx';

const types = ['all', 'income', 'expense'];

export default function TransactionFilters({ categories, filterCategory, setFilterCategory,
  filterType, setFilterType, period, clearSelection }) {
  return (
    <div className="filters-section">
      <div className="filter-group">
        <label>Categoria</label>
        <select
          value={filterCategory}
          onChange={(e) => { setFilterCategory(e.target.value); clearSelection(); }}
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
          onChange={(e) => { setFilterType(e.target.value); clearSelection(); }}
          className="filter-select"
        >
          {types.map((type) => (
            <option key={type} value={type}>
              {type === 'all' ? 'Todos os tipos' : type === 'income' ? 'Receitas' : 'Despesas'}
            </option>
          ))}
        </select>
      </div>
      <TransactionPeriodFilter period={period} onChange={clearSelection} />
    </div>
  );
}
