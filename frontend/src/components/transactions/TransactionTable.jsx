import TransactionRow from '../common/TransactionRow.jsx';
import { categoryIcons } from '../../utils/category.jsx';
import { groupTransactionsByDate } from '../../utils/transactionList.js';

const allAvailableCategories = Object.keys(categoryIcons);

export default function TransactionTable({ displayedTransactions, filteredTransactions,
  selectedIds, handleSelectTransaction, handleUpdateCategory, handleOpenEditModal }) {
  return (
    <div className="section">
      <div className="transactions-count">
        Exibindo {displayedTransactions.length} de {filteredTransactions.length} transações encontradas
        {displayedTransactions.length < filteredTransactions.length && ' (limite de 50 exibido)'}
      </div>

      <div className="transactions-table-container">
        <table className="transactions-table">
          <thead>
            <tr>
              <th className="col-checkbox"></th>
              <th className="col-date">Data</th>
              <th className="col-name">Descrição</th>
              <th className="col-category">Categoria</th>
              <th className="col-type">Tipo</th>
              <th className="col-value">Valor</th>
              <th className="col-actions">Ações</th>
            </tr>
          </thead>
            {displayedTransactions.length === 0 ? <tbody>
              <tr>
                <td colSpan="7" className="empty-state">
                  Nenhuma transação encontrada
                </td>
              </tr>
            </tbody> : groupTransactionsByDate(displayedTransactions).map((group) => (
              <tbody key={group.date || 'undated'}>
                <tr className="transaction-date-group">
                  <th colSpan="7" scope="rowgroup">
                    <span className="transaction-date-separator">
                      {group.date ? <time dateTime={group.date}>{group.label}</time> : <span>{group.label}</span>}
                    </span>
                  </th>
                </tr>
                {group.transactions.map((t) => (
                <TransactionRow
                  key={t.id}
                  transaction={t}
                  isSelected={selectedIds.includes(t.id)}
                  onSelect={handleSelectTransaction}
                  onUpdateTransaction={handleUpdateCategory}
                  onOpenEditModal={handleOpenEditModal}
                  allAvailableCategories={allAvailableCategories}
                  categoryIcons={categoryIcons}
                />
                ))}
              </tbody>
            ))}
        </table>
      </div>
    </div>
  );
}
