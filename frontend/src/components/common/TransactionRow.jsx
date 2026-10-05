import formatCurrency from "../../utils/currency.jsx";
import formatDate from "../../utils/date.jsx";
import EditableCategory from "./EditableCategory.jsx";

const TransactionRow = ({
  transaction,
  isSelected,
  onSelect,
  onUpdateTransaction,
  onOpenEditModal,
  allAvailableCategories,
  categoryIcons
}) => {
  return (
    <tr className={`transaction-row${isSelected ? ' is-selected' : ''}`}>
      <td className="col-checkbox">
        <label
          className="transaction-selection"
          title={transaction.is_opening_balance ? 'Saldo anterior automático não pode ser associado' : 'Selecionar para associação'}
        >
          <input
            className="transaction-checkbox"
            type="checkbox"
            aria-label={`Selecionar ${transaction.name} para associação`}
            checked={isSelected}
            disabled={transaction.is_opening_balance}
            onChange={() => onSelect(transaction.id)}
          />
        </label>
      </td>

      <td className="col-date">
        {formatDate(transaction.date)}
      </td>

      <td className="col-name">
        <span className="category-icon-inline">
          {categoryIcons[transaction.category] || '💸'}
        </span>
        <span className="name-text" title={transaction.name}>
          {transaction.name}
        </span>
      </td>

      <td className="col-category">
        {transaction.is_opening_balance ? <span>Saldo anterior</span> : <EditableCategory
          currentCategory={transaction.category}
          currentSubcategory={transaction.subcategory}
          label={`Alterar categoria de ${transaction.name}`}
          categories={allAvailableCategories}
          onUpdate={(classification) => onUpdateTransaction(transaction.id, classification)}
        />}
      </td>

      <td className="col-type">
        <span className={`badge badge-${transaction.type}`}>
          {transaction.type === 'income' ? '📈 Receita' : '📉 Despesa'}
        </span>
      </td>

      <td className={`col-value ${transaction.type}`}>
        {transaction.type === 'income' ? '+' : '-'} {formatCurrency(transaction.value)}
      </td>

      <td className="col-actions">
        {transaction.is_opening_balance ? <span title={transaction.description}>Automático</span> : <>
          <button
            className="action-btn edit-btn"
            onClick={() => onOpenEditModal(transaction)}
            title="Editar nome, data e categoria"
          >
            ✏️
          </button>
        </>}
      </td>
    </tr>
  );
};

export default TransactionRow;
