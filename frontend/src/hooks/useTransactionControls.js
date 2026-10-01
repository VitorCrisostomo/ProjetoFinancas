import { useState } from 'react';
import formatCurrency from '../utils/currency.jsx';

export default function useTransactionControls({ 
  transactions, 
  onAddTransaction, 
  onDeleteTransaction, 
  onUpdateTransaction,
  onAssociateTransactions,
  onImportTransactions,
  onSyncTransactions,
}) {
  const [modalOpen, setModalOpen] = useState(false);
  const [transactionToEdit, setTransactionToEdit] = useState(null);
  const [filterCategory, setFilterCategory] = useState('all');
  const [filterType, setFilterType] = useState('all');
  const [isUploading, setIsUploading] = useState(false); 
  const [selectedIds, setSelectedIds] = useState([]);
  const [isSyncing, setIsSyncing] = useState(false);

  const categories = ['all', ...new Set(transactions.map((t) => t.category))];

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

  const handleExecuteAssociation = async () => {
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

      try {
        const result = await onAssociateTransactions(t1.id, t2.id, updatedData);
        if (!result) return;
        setSelectedIds([]);
        alert('Transações associadas com sucesso!');
      } catch (error) {
        alert(`Erro ao associar: ${error.message}`);
      }
    }
  };

  const handleSave = async (data, id) => {
    try {
      const result = id ? await onUpdateTransaction(id, data) : await onAddTransaction(data);
      if (!result) return;
      setModalOpen(false);
      setTransactionToEdit(null);
    } catch (error) {
      alert(`Erro ao salvar transação: ${error.message}`);
    }
  };

  const handleDeleteTransaction = async (id) => {
    if (!window.confirm('Tem certeza que deseja deletar esta transação?')) return;
    try {
      await onDeleteTransaction(id);
    } catch (error) {
      alert(`Erro ao deletar: ${error.message}`);
    }
  };

  const handleUpdateCategory = async (id, data) => {
    try {
      await onUpdateTransaction(id, data);
    } catch (error) {
      alert(`Erro ao editar: ${error.message}`);
    }
  };

  const handleOpenNewModal = () => {
    setTransactionToEdit(null);
    setModalOpen(true);
  };

  const handleOpenEditModal = (transaction) => {
    setTransactionToEdit(transaction);
    setModalOpen(true);
  };

  const handleFileUpload = async (file) => {
    if (!file) return;
    
    if (!file.name.endsWith('.csv')) {
      alert("Por favor, selecione apenas arquivos .csv");
      return;
    }

    setIsUploading(true);
    try {
      const result = await onImportTransactions(file);
      if (result) alert(`Sucesso! ${result.imported_count} transações foram importadas.`);
    } catch (error) {
      alert(`Erro na importação: ${error.message}`);
    } finally {
      setIsUploading(false);
    }
  };

  const handleSyncTransactions = async () => {
    setIsSyncing(true);
    try {
      const result = await onSyncTransactions();
      if (result) alert(result.message);
    } catch (error) {
      alert(`Erro ao sincronizar transações: ${error.message}`);
    } finally {
      setIsSyncing(false);
    }
  };

  const closeModal = () => {
    setModalOpen(false);
    setTransactionToEdit(null);
  };

  return {
    modalOpen, transactionToEdit, filterCategory, setFilterCategory,
    filterType, setFilterType, isUploading, isSyncing, selectedIds,
    categories, filteredTransactions, displayedTransactions,
    handleSelectTransaction, handleExecuteAssociation, handleSave,
    handleDeleteTransaction, handleUpdateCategory, handleOpenNewModal,
    handleOpenEditModal, handleFileUpload, handleSyncTransactions, closeModal,
  };
}
