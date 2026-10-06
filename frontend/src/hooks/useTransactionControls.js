import { useRef, useState } from 'react';
import formatCurrency from '../utils/currency.jsx';
import useTransactionPeriod from './useTransactionPeriod.js';
import { getOpeningBalance, getTransactionSummary } from '../utils/transactionSummary.js';
import { getAssociationData } from '../utils/transactionAssociation.js';
import { sortTransactionsByDate } from '../utils/transactionList.js';
import { getCategoryCatalog } from '../utils/categoryCatalog.js';
import useFinancialVisibility from './useFinancialVisibility.js';

export default function useTransactionControls({ 
  transactions, 
  categoryCatalog = [],
  onUpdateTransaction,
  onAssociateTransactions,
  onSyncTransactions,
}) {
  const [modalOpen, setModalOpen] = useState(false);
  const [transactionToEdit, setTransactionToEdit] = useState(null);
  const [filterCategory, setFilterCategory] = useState('');
  const [filterType, setFilterType] = useState('all');
  const [selectedIds, setSelectedIds] = useState([]);
  const [isAssociating, setIsAssociating] = useState(false);
  const associating = useRef(false);
  const [isSyncing, setIsSyncing] = useState(false);
  const [syncModalOpen, setSyncModalOpen] = useState(false);
  const [syncError, setSyncError] = useState('');
  const period = useTransactionPeriod(transactions);
  const { valuesHidden } = useFinancialVisibility();

  const categories = ['', ...new Set(transactions.map((t) => t.category).filter(Boolean))];
  const availableCategories = getCategoryCatalog(categoryCatalog, transactions);

  // Filtragem
  const filteredTransactions = sortTransactionsByDate(period.transactions.filter((t) => {
    const categoryMatch = filterCategory === '' || t.category === filterCategory;
    const typeMatch = filterType === 'all' || t.type === filterType;
    return categoryMatch && typeMatch;
  }));

  const displayedTransactions = period.month !== 'all'
    ? filteredTransactions
    : filteredTransactions.slice(0, 50);
  const { balance: filteredBalance } = getTransactionSummary(filteredTransactions);
  const openingBalance = getOpeningBalance(transactions, period.month, period.year);
  const totalBalance = (openingBalance ?? 0) + filteredBalance;

  const handleSelectTransaction = (id) => {
    if (associating.current || transactions.find((transaction) => transaction.id === id)?.is_opening_balance) return;
    setSelectedIds((previous) => previous.includes(id)
      ? previous.filter((item) => item !== id) : [...previous, id]);
  };

  const handleExecuteAssociation = async () => {
    if (selectedIds.length < 2 || associating.current || isSyncing) return;
    const selected = selectedIds.map((id) => transactions.find((transaction) => transaction.id === id));
    if (selected.some((transaction) => !transaction || transaction.is_opening_balance)) return;
    const updatedData = getAssociationData(selected);
    const displayAmount = (value) => valuesHidden ? 'valor oculto' : formatCurrency(value);
    const details = selected.map((transaction) => (
      `- "${transaction.name}" (${transaction.type === 'income' ? '+' : '-'}${displayAmount(transaction.value)})`
    )).join('\n');
    const confirmMessage = `Deseja associar ${selected.length} transações:\n${details}\n\nResultado final: ${updatedData.type === 'income' ? 'Receita' : 'Despesa'} de ${displayAmount(updatedData.value)}?\nA data e a categoria serão as da primeira transação selecionada.`;

    if (window.confirm(confirmMessage)) {
      associating.current = true;
      setIsAssociating(true);
      try {
        const result = await onAssociateTransactions(selectedIds, updatedData);
        if (!result) return;
        setSelectedIds([]);
        alert('Transações associadas com sucesso!');
      } catch (error) {
        alert(`Erro ao associar: ${error.message}`);
      } finally {
        associating.current = false;
        setIsAssociating(false);
      }
    }
  };

  const handleSave = async (data, id) => {
    try {
      const result = await onUpdateTransaction(id, data);
      if (!result) return;
      setModalOpen(false);
      setTransactionToEdit(null);
    } catch (error) {
      alert(`Erro ao salvar transação: ${error.message}`);
    }
  };

  const handleUpdateCategory = async (id, data) => {
    try {
      await onUpdateTransaction(id, data);
    } catch (error) {
      alert(`Erro ao editar: ${error.message}`);
    }
  };

  const handleOpenEditModal = (transaction) => {
    setTransactionToEdit(transaction);
    setModalOpen(true);
  };

  const openSyncModal = () => {
    setSyncError('');
    setSyncModalOpen(true);
  };

  const closeSyncModal = () => {
    if (!isSyncing) setSyncModalOpen(false);
  };

  const handleSyncTransactions = async (options) => {
    if (isSyncing) return;
    setIsSyncing(true);
    setSyncError('');
    try {
      const result = await onSyncTransactions(options);
      if (result) {
        setSyncModalOpen(false);
        alert(result.message);
      }
    } catch (error) {
      setSyncError(error.message);
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
    filterType, setFilterType, isSyncing, isAssociating, selectedIds, period,
    clearSelection: () => setSelectedIds([]),
    categories, filteredTransactions, displayedTransactions, filteredBalance,
    availableCategories,
    openingBalance, totalBalance,
    handleSelectTransaction, handleExecuteAssociation, handleSave,
    handleUpdateCategory,
    handleOpenEditModal, handleSyncTransactions, closeModal,
    syncModalOpen, syncError, openSyncModal, closeSyncModal,
  };
}
