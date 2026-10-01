import useTransactionControls from '../hooks/useTransactionControls.js';
import TransactionToolbar from '../components/transactions/TransactionToolbar.jsx';
import TransactionFilters from '../components/transactions/TransactionFilters.jsx';
import TransactionTable from '../components/transactions/TransactionTable.jsx';
import TransactionModal from '../components/common/TransactionModal.jsx';

export default function TransactionsPage(props) {
  const controls = useTransactionControls(props);

  return (
    <div className="page-content">
      <TransactionToolbar
        selectedIds={controls.selectedIds}
        handleExecuteAssociation={controls.handleExecuteAssociation}
        handleFileUpload={controls.handleFileUpload}
        isUploading={controls.isUploading}
        isSyncing={controls.isSyncing}
        handleSyncTransactions={controls.handleSyncTransactions}
        handleOpenNewModal={controls.handleOpenNewModal}
      />
      <TransactionFilters
        categories={controls.categories}
        filterCategory={controls.filterCategory}
        setFilterCategory={controls.setFilterCategory}
        filterType={controls.filterType}
        setFilterType={controls.setFilterType}
      />
      <TransactionTable
        displayedTransactions={controls.displayedTransactions}
        filteredTransactions={controls.filteredTransactions}
        selectedIds={controls.selectedIds}
        handleSelectTransaction={controls.handleSelectTransaction}
        handleUpdateCategory={controls.handleUpdateCategory}
        handleOpenEditModal={controls.handleOpenEditModal}
        handleDeleteTransaction={controls.handleDeleteTransaction}
      />
      {controls.modalOpen && <TransactionModal
        key={controls.transactionToEdit?.id ?? "new"}
        isOpen={controls.modalOpen}
        onClose={controls.closeModal}
        onSave={controls.handleSave}
        transactionToEdit={controls.transactionToEdit}
      />}
    </div>
  );
}
