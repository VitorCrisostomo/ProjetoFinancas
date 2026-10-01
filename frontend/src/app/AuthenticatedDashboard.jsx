import { useState } from 'react';
import AppLayout from '../components/layout/AppLayout.jsx';
import useAccounts from '../hooks/useAccounts.js';
import useTransactions from '../hooks/useTransactions.js';
import { DEFAULT_PAGE, getPage } from './navigation.js';

// Os hooks de dados vivem somente durante a sessão autenticada.
export default function AuthenticatedDashboard({ user, onLogout }) {
  const [currentPage, setCurrentPage] = useState(DEFAULT_PAGE);
  const accountData = useAccounts();
  const transactionData = useTransactions();
  const { accounts } = accountData;
  const { transactions } = transactionData;

  const syncAccounts = async (itemId) => {
    const result = await accountData.syncAccounts(itemId);
    if (result) await transactionData.reloadTransactions();
    return result;
  };

  const syncTransactions = async (options) => {
    const result = await transactionData.syncTransactions(options);
    if (result) await accountData.reloadAccounts();
    return result;
  };

  const pageProps = {
    home: { transactions },
    overview: { transactions },
    transactions: {
      transactions,
      onAddTransaction: transactionData.addTransaction,
      onDeleteTransaction: transactionData.deleteTransaction,
      onUpdateTransaction: transactionData.updateTransaction,
      onAssociateTransactions: transactionData.associateTransactions,
      onImportTransactions: transactionData.importTransactions,
      onSyncTransactions: syncTransactions,
    },
    accounts: {
      accounts,
      onGetConnectToken: accountData.getConnectToken,
      onSyncAccounts: syncAccounts,
      onDeleteAccount: accountData.deleteAccount,
    },
  };
  const page = getPage(currentPage);
  const Page = page.component;

  const isLoading = accountData.isLoading || transactionData.isLoading;
  const errors = [...new Set([accountData.error, transactionData.error].filter(Boolean))];

  return (
    <AppLayout user={user} currentPage={currentPage} onPageChange={setCurrentPage} onLogout={onLogout}>
      {errors.map((message) => <p role="alert" key={message}>{message}</p>)}
      {isLoading ? <p role="status">Carregando dados...</p> : <Page {...pageProps[page.id]} />}
    </AppLayout>
  );
}
