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
