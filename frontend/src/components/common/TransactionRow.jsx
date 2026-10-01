import formatCurrency from "../../utils/currency.jsx";
import formatDate from "../../utils/date.jsx";
import EditableCategory from "./EditableCategory.jsx";

const TransactionRow = ({
  transaction,
  isSelected,
  onSelect,
  onUpdateTransaction,
  onOpenEditModal,
  onDeleteTransaction,
  allAvailableCategories,
  categoryIcons
}) => {
  return (
    <tr className="transaction-row">
      <td className="col-checkbox">
        <input
          type="checkbox"
          checked={isSelected}
          onChange={() => onSelect(transaction.id)}
        />
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
        <EditableCategory
          currentCategory={transaction.category}
          categories={allAvailableCategories}
          categoryIcons={categoryIcons}
          onUpdate={(newCategory) => onUpdateTransaction(transaction.id, { category: newCategory })}
        />
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
        <button
          className="action-btn edit-btn"
          onClick={() => onOpenEditModal(transaction)}
          title="Editar transação completa"
        >
          ✏️
        </button>
        <button
          className="action-btn delete-btn"
          onClick={() => onDeleteTransaction(transaction.id)}
          title="Deletar"
        >
          🗑️
        </button>
      </td>
    </tr>
  );
};

export default TransactionRow;