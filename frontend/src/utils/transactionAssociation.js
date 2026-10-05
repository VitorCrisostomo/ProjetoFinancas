export const getAssociationData = (transactions) => {
  const first = transactions[0];
  const cents = transactions.reduce((total, transaction) => (
    total + Math.round(Number(transaction.value) * 100) * (transaction.type === 'income' ? 1 : -1)
  ), 0);
  return {
    name: transactions.map((transaction) => transaction.name).join(' / ').slice(0, 120),
    value: Math.abs(cents) / 100,
    type: cents >= 0 ? 'income' : 'expense',
    category: first.category,
    subcategory: first.subcategory || null,
    date: typeof first.date === 'string' ? first.date.split('T')[0] : first.date,
  };
};
