import { useState } from "react";
import { categoryIcons } from "../utils/category.jsx";
import formatCurrency from "../utils/currency.jsx";
import formatDate from "../utils/date.jsx"
import Button from "../components/common/Button.jsx";
import TransactionModal from "../components/common/TransactionModal.jsx"

const TransactionsPage = ({ transactions, onAddTransaction, onDeleteTransaction }) => {
  const [modalOpen, setModalOpen] = useState(false);
  const [filterCategory, setFilterCategory] = useState('all');
  const [filterType, setFilterType] = useState('all');
  
  // NOVO: Estado para mostrar se está carregando o arquivo
  const [isUploading, setIsUploading] = useState(false); 

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

  // NOVO: Função que captura o arquivo escolhido
  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    // Verifica se é realmente um CSV
    if (!file.name.endsWith('.csv')) {
      alert("Por favor, selecione apenas arquivos .csv");
      return;
    }

    setIsUploading(true);

    // Cria o "pacote" de formulário para enviar o arquivo
    const formData = new FormData();
    formData.append("file", file);

    try {
      const token = localStorage.getItem('token');
      // Vamos criar essa rota no Python no próximo passo!
      const response = await fetch('http://localhost:5000/transactions/import', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
          // NOTA: Ao enviar FormData (arquivos), NÃO colocamos o 'Content-Type'. 
          // O próprio navegador cuida de colocar como 'multipart/form-data'.
        },
        body: formData
      });

      if (response.ok) {
        const result = await response.json();
        alert(`Sucesso! ${result.imported_count} transações foram importadas.`);
        window.location.reload(); // Recarrega a página para puxar os dados novos
      } else {
        const errorData = await response.json();
        alert(`Erro na importação: ${errorData.message}`);
      }
    } catch (error) {
      console.error("Erro ao enviar arquivo:", error);
      alert("Erro ao tentar conectar com o servidor.");
    } finally {
      setIsUploading(false);
      // Limpa o input para permitir enviar o mesmo arquivo de novo, se precisar
      event.target.value = null; 
    }
  };

  return (
    <div className="page-content">
      <div className="page-header">
<h1>Transações</h1>
        
        {/* NOVO: Container para os botões ficarem lado a lado */}
        <div style={{ display: 'flex', gap: '10px' }}>
          
          {/* Input de arquivo invisível */}
          <input
            type="file"
            accept=".csv"
            id="csv-upload"
            style={{ display: 'none' }}
            onChange={handleFileUpload}
          />
          
          {/* Botão que "clica" no input invisível */}
          <Button 
            variant="secondary" 
            size="lg" 
            onClick={() => document.getElementById('csv-upload').click()}
            disabled={isUploading}
          >
            {isUploading ? '⏳ Importando...' : '📄 Importar CSV'}
          </Button>

          <Button variant="primary" size="lg" onClick={() => setModalOpen(true)}>
            ➕ Nova Transação
          </Button>
        </div>
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
                    <td className={`value-cell ${t.type}`}>
                      {t.type === 'income' ? '+' : '-'} {formatCurrency(t.value)}
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