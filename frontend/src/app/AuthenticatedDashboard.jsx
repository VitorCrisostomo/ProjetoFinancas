import { useState } from 'react';
import AppLayout from '../components/layout/AppLayout.jsx';
import useAccounts from '../hooks/useAccounts.js';
import useTransactions from '../hooks/useTransactions.js';
import useCategories from '../hooks/useCategories.js';
import { DEFAULT_PAGE, getPage } from './navigation.js';
import FinancialVisibilityProvider from './FinancialVisibilityProvider.jsx';

// Os hooks de dados vivem somente durante a sessão autenticada.
export default function AuthenticatedDashboard({ user, onLogout }) {
  const [currentPage, setCurrentPage] = useState(DEFAULT_PAGE);
  const accountData = useAccounts();
  const transactionData = useTransactions();
  const categoryData = useCategories();
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
    overview: { transactions, categoryCatalog: categoryData.categories },
    transactions: {
      transactions,
      categoryCatalog: categoryData.categories,
      onUpdateTransaction: transactionData.updateTransaction,
      onAssociateTransactions: transactionData.associateTransactions,
      onSyncTransactions: syncTransactions,
    },
    accounts: {
      accounts,
      onGetConnectToken: accountData.getConnectToken,
      onSyncAccounts: syncAccounts,
      onDeleteAccount: accountData.deleteAccount,
    },
    personalization: {
      categories: categoryData.categories,
      onCreateCategory: categoryData.createCategory,
      onCreateSubcategory: categoryData.createSubcategory,
    },
  };
  const page = getPage(currentPage);
  const Page = page.component;

  const isLoading = accountData.isLoading || transactionData.isLoading || categoryData.isLoading;
  const errors = [...new Set([accountData.error, transactionData.error, categoryData.error].filter(Boolean))];

  return (
    <FinancialVisibilityProvider userId={user.id}>
      <AppLayout user={user} currentPage={currentPage} onPageChange={setCurrentPage} onLogout={onLogout}>
        {errors.map((message) => <p role="alert" key={message}>{message}</p>)}
        {isLoading ? <p role="status">Carregando dados...</p> : <Page {...pageProps[page.id]} />}
      </AppLayout>
    </FinancialVisibilityProvider>
  );
}
