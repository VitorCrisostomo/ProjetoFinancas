import { getTransactionDateParts, months } from './transactionPeriod.js';

const dateKey = (transaction) => {
  const date = getTransactionDateParts(transaction.date);
  return date ? `${String(date.year).padStart(4, '0')}-${String(date.month).padStart(2, '0')}-${String(date.day).padStart(2, '0')}` : '';
};

export const sortTransactionsByDate = (transactions) => [...transactions].sort((a, b) => {
  const firstDate = dateKey(a);
  const secondDate = dateKey(b);
  if (!firstDate && secondDate) return 1;
  if (firstDate && !secondDate) return -1;
  return secondDate.localeCompare(firstDate) || Number(b.id) - Number(a.id);
});

export const groupTransactionsByDate = (transactions) => {
  const groups = new Map();
  for (const transaction of sortTransactionsByDate(transactions)) {
    const key = dateKey(transaction);
    if (!groups.has(key)) {
      const date = getTransactionDateParts(transaction.date);
      groups.set(key, {
        date: key,
        label: date ? `${date.day} de ${months[date.month - 1].toLowerCase()} de ${date.year}` : 'Data não informada',
        transactions: [],
      });
    }
    groups.get(key).transactions.push(transaction);
  }
  return [...groups.values()];
};
