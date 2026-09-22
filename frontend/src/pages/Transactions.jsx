import React, { useState } from "react";
import HomePage from "./Home.jsx";
import Button from "../components/common/Button.jsx";
import { categoryIcons } from "../utils/category.jsx";
import TransactionModal from "../components/common/TransactionModal.jsx"
import formatDate from "../utils/date.jsx"
import formatCurrency from "../utils/currency.jsx";

const TransactionsPage = ({ transactions, onAddTransaction, onDeleteTransaction }) => {
  const [modalOpen, setModalOpen] = useState(false);
  const [filterCategory, setFilterCategory] = useState('all');
  const [filterType, setFilterType] = useState('all');

  const categories = ['all', ...new Set(transactions.map((t) => t.category))];
  const types = ['all', 'income', 'expense'];

  const filteredTransactions = transactions.filter((t) => {
    const categoryMatch = filterCategory === 'all' || t.category === filterCategory;
    const typeMatch = filterType === 'all' || t.type === filterType;
    return categoryMatch && typeMatch;
  });

  const handleSave = (data) => {
    onAddTransaction(data);
    setModalOpen(false);
  };

  return (
    <div className="page-content">
      <div className="page-header">
        <h1>Transações</h1>
        <Button variant="primary" size="lg" onClick={() => setModalOpen(true)}>
          ➕ Nova Transação
        </Button>
      </div>

      {/* Filtros */}
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

      {/* Lista de Transações */}
      <div className="section">
        <div className="transactions-count">
          {filteredTransactions.length} transação(ões) encontrada(s)
        </div>

        <div className="transactions-table-container">
          <table className="transactions-table">
            <thead>
              <tr>
                <th>Data</th>
                <th>Descrição</th>
                <th>Categoria</th>
                <th>Tipo</th>
                <th>Valor</th>
                <th>Ações</th>
              </tr>
            </thead>
            <tbody>
              {filteredTransactions.length === 0 ? (
                <tr>
                  <td colSpan="6" className="empty-state">
                    Nenhuma transação encontrada
                  </td>
                </tr>
              ) : (
                filteredTransactions.map((t) => (
                  <tr key={t.id} className="transaction-row">
                    <td className="date-cell">{formatDate(t.date)}</td>
                    <td className="name-cell">
                      <span className="category-icon-inline">{categoryIcons[t.category]}</span>
                      {t.name}
                    </td>
                    <td className="category-cell">{t.category}</td>
                    <td className="type-cell">
                      <span className={`badge badge-${t.type}`}>
                        {t.type === 'income' ? '📈 Receita' : '📉 Despesa'}
                      </span>
                    </td>
                    <td className={`amount-cell ${t.type}`}>
                      {t.type === 'income' ? '+' : '-'} {formatCurrency(t.amount)}
                    </td>
                    <td className="actions-cell">
                      <button
                        className="action-btn delete-btn"
                        onClick={() => onDeleteTransaction(t.id)}
                        title="Deletar"
                      >
                        🗑️
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Modal */}
      <TransactionModal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        onSave={handleSave}
      />
    </div>
  );
};

export default TransactionsPage;