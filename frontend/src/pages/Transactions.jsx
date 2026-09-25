import { useState } from "react";
import { categoryIcons } from "../utils/category.jsx";
import formatCurrency from "../utils/currency.jsx";
import formatDate from "../utils/date.jsx";
import Button from "../components/common/Button.jsx";
import TransactionModal from "../components/common/TransactionModal.jsx";
import EditableCategory from "../components/common/EditableCategory.jsx";

const TransactionsPage = ({ transactions, onAddTransaction, onDeleteTransaction, onUpdateTransaction }) => {
  const [modalOpen, setModalOpen] = useState(false);
  const [transactionToEdit, setTransactionToEdit] = useState(null);
  const [filterCategory, setFilterCategory] = useState('all');
  const [filterType, setFilterType] = useState('all');
  const [isUploading, setIsUploading] = useState(false); 

  const categories = ['all', ...new Set(transactions.map((t) => t.category))];
  const types = ['all', 'income', 'expense'];
  
  const allAvailableCategories = Object.keys(categoryIcons);

  const filteredTransactions = transactions.filter((t) => {
    const categoryMatch = filterCategory === 'all' || t.category === filterCategory;
    const typeMatch = filterType === 'all' || t.type === filterType;
    return categoryMatch && typeMatch;
  });

  const handleSave = (data, id) => {
    if (id) {
      onUpdateTransaction(id, data);
    } else {
      onAddTransaction(data);
    }
    setModalOpen(false);
    setTransactionToEdit(null); // Limpa após salvar
  };

  const handleOpenNewModal = () => {
    setTransactionToEdit(null); // Garante que abre vazio
    setModalOpen(true);
  };

  const handleOpenEditModal = (transaction) => {
    setTransactionToEdit(transaction); // Garante que abre preenchido
    setModalOpen(true);
  };

  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;
    
    if (!file.name.endsWith('.csv')) {
      alert("Por favor, selecione apenas arquivos .csv");
      return;
    }

    setIsUploading(true);
    const formData = new FormData();
    formData.append("file", file);

    try {
      const token = localStorage.getItem('token');
      const response = await fetch('http://localhost:5000/transactions/import', {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
        body: formData
      });

      if (response.ok) {
        const result = await response.json();
        alert(`Sucesso! ${result.imported_count} transações foram importadas.`);
        window.location.reload();
      } else {
        const errorData = await response.json();
        alert(`Erro na importação: ${errorData.message}`);
      }
    } catch (error) {
      console.error("Erro ao enviar arquivo:", error);
      alert("Erro ao tentar conectar com o servidor.");
    } finally {
      setIsUploading(false);
      event.target.value = null; 
    }
  };

  return (
    <div className="page-content">
      <div className="page-header">
        <h1>Transações</h1>
        
        <div style={{ display: 'flex', gap: '10px' }}>
          <input
            type="file"
            accept=".csv"
            id="csv-upload"
            style={{ display: 'none' }}
            onChange={handleFileUpload}
          />
          
          <Button 
            variant="secondary" 
            size="lg" 
            onClick={() => document.getElementById('csv-upload').click()}
            disabled={isUploading}
          >
            {isUploading ? '⏳ Importando...' : '📄 Importar CSV'}
          </Button>

          <Button variant="primary" size="lg" onClick={handleOpenNewModal}>
            ➕ Nova Transação
          </Button>
        </div>
      </div>

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
                    
                    <td className="category-cell">
                      <EditableCategory
                        currentCategory={t.category}
                        categories={allAvailableCategories}
                        categoryIcons={categoryIcons}
                        onUpdate={(newCategory) => onUpdateTransaction(t.id, { category: newCategory })}
                      />
                    </td>

                    <td className="type-cell">
                      <span className={`badge badge-${t.type}`}>
                        {t.type === 'income' ? '📈 Receita' : '📉 Despesa'}
                      </span>
                    </td>
                    <td className={`value-cell ${t.type}`}>
                      {t.type === 'income' ? '+' : '-'} {formatCurrency(t.value)}
                    </td>

                    <td className="actions-cell">
                      <button
                        className="action-btn edit-btn"
                        onClick={() => handleOpenEditModal(t)}
                        title="Editar transação completa"
                        style={{ marginRight: '8px' }}
                      >
                        ✏️
                      </button>

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

      <TransactionModal
        isOpen={modalOpen}
        onClose={() => { setModalOpen(false); setTransactionToEdit(null); }}
        onSave={handleSave}
        transactionToEdit={transactionToEdit}
      />
    </div>
  );
};

export default TransactionsPage;