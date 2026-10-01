import { getTransactionDateParts } from './transactionPeriod.js';

export const getTransactionSummary = (transactions) => {
  let totalIncome = 0;
  let totalExpense = 0;
  const expensesByCategory = {};

  for (const transaction of transactions) {
    if (transaction.type === 'income') totalIncome += transaction.value;
    if (transaction.type === 'expense') {
      totalExpense += transaction.value;
      expensesByCategory[transaction.category] =
        (expensesByCategory[transaction.category] || 0) + transaction.value;
    }
  }

  return { totalIncome, totalExpense, balance: totalIncome - totalExpense, expensesByCategory };
};

// Um saldo anterior exige um período contínuo; mês sem ano reúne períodos distintos.
export const getOpeningBalance = (transactions, month = 'all', year = 'all') => {
  if (year === 'all') return null;
  const start = Number(year) * 12 + (month === 'all' ? 1 : Number(month));
  const previousTransactions = transactions.filter((transaction) => {
    const date = getTransactionDateParts(transaction.date);
    return date !== null && date.year * 12 + date.month < start;
  });
  return getTransactionSummary(previousTransactions).balance;
};
