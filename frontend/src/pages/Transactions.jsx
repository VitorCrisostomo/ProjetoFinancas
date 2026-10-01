import { useState } from "react";
import { categoryIcons } from "../utils/category.jsx";
import Button from "../components/common/Button.jsx";
import TransactionModal from "../components/common/TransactionModal.jsx";
import TransactionRow from "../components/common/TransactionRow.jsx";
import formatCurrency from "../utils/currency.jsx";

const TransactionsPage = ({ 
  transactions, 
  onAddTransaction, 
  onDeleteTransaction, 
  onUpdateTransaction,
  onAssociateTransactions 
}) => {
  const [modalOpen, setModalOpen] = useState(false);
  const [transactionToEdit, setTransactionToEdit] = useState(null);
  const [filterCategory, setFilterCategory] = useState('all');
  const [filterType, setFilterType] = useState('all');
  const [isUploading, setIsUploading] = useState(false); 
  const [selectedIds, setSelectedIds] = useState([]);
  const [isSyncing, setIsSyncing] = useState(false);

  const categories = ['all', ...new Set(transactions.map((t) => t.category))];
  const types = ['all', 'income', 'expense'];
  const allAvailableCategories = Object.keys(categoryIcons);

  // Filtragem
  const filteredTransactions = transactions.filter((t) => {
    const categoryMatch = filterCategory === 'all' || t.category === filterCategory;
    const typeMatch = filterType === 'all' || t.type === filterType;
    return categoryMatch && typeMatch;
  });

  const displayedTransactions = filteredTransactions.slice(0, 50);

  const handleSelectTransaction = (id) => {
    if (selectedIds.includes(id)) {
      setSelectedIds(selectedIds.filter((item) => item !== id));
    } else {
      if (selectedIds.length >= 2) {
        alert("Você só pode selecionar até 2 transações para associar de cada vez.");
        return;
      }
      setSelectedIds([...selectedIds, id]);
    }
  };

  const handleExecuteAssociation = () => {
    if (selectedIds.length !== 2) return;

    const t1 = transactions.find((t) => t.id === selectedIds[0]);
    const t2 = transactions.find((t) => t.id === selectedIds[1]);

    if (!t1 || !t2) return;

    const val1 = t1.type === 'income' ? t1.value : -t1.value;
    const val2 = t2.type === 'income' ? t2.value : -t2.value;
    const resultValue = val1 + val2;

    const newType = resultValue >= 0 ? 'income' : 'expense';
    const finalValue = Math.abs(resultValue);

    const formattedDate = typeof t1.date === 'string' ? t1.date.split('T')[0] : t1.date;

    const confirmMessage = `Deseja associar as transações:\n- "${t1.name}" (${formatCurrency(t1.value)})\n- "${t2.name}" (${formatCurrency(t2.value)})\n\nResultado final: ${newType === 'income' ? 'Receita' : 'Despesa'} de ${formatCurrency(finalValue)}?`;

    if (window.confirm(confirmMessage)) {
      const updatedData = {
        name: `${t1.name} / ${t2.name}`,
        value: parseFloat(finalValue),
        type: newType,
        category: t1.category,
        date: formattedDate
      };

      if (onAssociateTransactions) {
        onAssociateTransactions(t1.id, t2.id, updatedData);
      } else {
        onUpdateTransaction(t1.id, updatedData);
        onDeleteTransaction(t2.id);
      }
      setSelectedIds([]);
    }
  };

  const handleSave = (data, id) => {
    if (id) {
      onUpdateTransaction(id, data);
    } else {
      onAddTransaction(data);
    }
    setModalOpen(false);
    setTransactionToEdit(null);
  };

  const handleOpenNewModal = () => {
    setTransactionToEdit(null);
    setModalOpen(true);
  };

  const handleOpenEditModal = (transaction) => {
    setTransactionToEdit(transaction);
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

  const handleSyncTransactions = async () => {
  setIsSyncing(true);
  try {
    const token = localStorage.getItem('token');
    const response = await fetch('http://localhost:5000/pluggy/transactions/sync', {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}` 
      }
    });

    if (response.ok) {
      const result = await response.json();
      alert(result.message);
      
      // Opção A: Se você tiver uma função para buscar as transações da API novamente
      if (typeof fetchTransactions === 'function') {
        fetchTransactions();
      }
      
      // Opção B: Ou se preferir atualizar o estado local diretamente com o retorno:
      // if (typeof setTransactions === 'function') {
      //   setTransactions(result.transactions);
      // }

    } else {
      const errorData = await response.json();
      alert(`Erro ao sincronizar transações: ${errorData.message}`);
    }
  } catch (error) {
    console.error("Erro na requisição de sincronização:", error);
    alert("Falha de conexão com o servidor.");
  } finally {
    setIsSyncing(false);
  }
};

  return (
    <div className="page-content">
      <div className="page-header">
        <div>
          <h1>Transações</h1>
          <p>Gerencie e filtre suas receitas e despesas</p>
        </div>
        
        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
          {selectedIds.length === 2 && (
            <Button variant="secondary" size="lg" onClick={handleExecuteAssociation}>
              🔗 Associar (2)
            </Button>
          )}

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

          <Button variant="primary" size="lg" onClick={() => { setTransactionToEdit(null); setModalOpen(true); }}>
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
          Exibindo {displayedTransactions.length} de {filteredTransactions.length} transações encontradas
          {filteredTransactions.length > 50 && ' (limite de 50 exibido)'}
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
            <tbody>
              {displayedTransactions.length === 0 ? (
                <tr>
                  <td colSpan="7" className="empty-state">
                    Nenhuma transação encontrada
                  </td>
                </tr>
              ) : (
                displayedTransactions.map((t) => (
                  <TransactionRow
                    key={t.id}
                    transaction={t}
                    isSelected={selectedIds.includes(t.id)}
                    onSelect={handleSelectTransaction}
                    onUpdateTransaction={onUpdateTransaction}
                    onOpenEditModal={(tx) => { setTransactionToEdit(tx); setModalOpen(true); }}
                    onDeleteTransaction={onDeleteTransaction}
                    allAvailableCategories={allAvailableCategories}
                    categoryIcons={categoryIcons}
                  />
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