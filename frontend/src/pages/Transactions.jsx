import useTransactionControls from '../hooks/useTransactionControls.js';
import TransactionToolbar from '../components/transactions/TransactionToolbar.jsx';
import TransactionFilters from '../components/transactions/TransactionFilters.jsx';
import TransactionTable from '../components/transactions/TransactionTable.jsx';
import TransactionModal from '../components/common/TransactionModal.jsx';
import SyncTransactionsModal from '../components/transactions/SyncTransactionsModal.jsx';
import formatCurrency from '../utils/currency.jsx';

export default function TransactionsPage(props) {
  const controls = useTransactionControls(props);

  return (
    <div className="page-content">
      <TransactionToolbar
        selectedIds={controls.selectedIds}
        handleExecuteAssociation={controls.handleExecuteAssociation}
        isSyncing={controls.isSyncing}
        isAssociating={controls.isAssociating}
        openSyncModal={controls.openSyncModal}
      />
      <TransactionFilters
        period={controls.period}
        clearSelection={controls.clearSelection}
        categories={controls.categories}
        filterCategory={controls.filterCategory}
        setFilterCategory={controls.setFilterCategory}
        filterType={controls.filterType}
        setFilterType={controls.setFilterType}
      />
      <div className="highlight-section">
        <div className="highlight-card">
          <span className="highlight-label">
            {controls.openingBalance !== null ? 'Saldo com as movimentações filtradas' : 'Saldo total das transações filtradas'}
          </span>
          <span className={`highlight-value ${controls.totalBalance >= 0 ? 'positive' : 'negative'}`}>
            {formatCurrency(controls.totalBalance)}
          </span>
          {controls.openingBalance !== null ? <>
            <p className="transactions-balance-description">
              Saldo anterior: {formatCurrency(controls.openingBalance)}
              {' · '}Movimentações filtradas: {formatCurrency(controls.filteredBalance)}
            </p>
            <p className="transactions-balance-description">
              O saldo anterior inclui todo o histórico antes do início do período selecionado.
            </p>
          </> : <p className="transactions-balance-description">
            Receitas menos despesas de todas as transações que correspondem aos filtros.
            {controls.period.month !== 'all' && ' Selecione também o ano para incluir o saldo anterior.'}
          </p>}
        </div>
      </div>
      <TransactionTable
        displayedTransactions={controls.displayedTransactions}
        filteredTransactions={controls.filteredTransactions}
        selectedIds={controls.selectedIds}
        handleSelectTransaction={controls.handleSelectTransaction}
        handleUpdateCategory={controls.handleUpdateCategory}
        handleOpenEditModal={controls.handleOpenEditModal}
      />
      {controls.syncModalOpen && <SyncTransactionsModal
        period={controls.period}
        isSyncing={controls.isSyncing}
        error={controls.syncError}
        onClose={controls.closeSyncModal}
        onSync={controls.handleSyncTransactions}
      />}
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
