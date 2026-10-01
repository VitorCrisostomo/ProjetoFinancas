import { getTransactionDateParts } from './transactionPeriod.js';

const formatDate = (dateString) => {
  const date = getTransactionDateParts(dateString);
  if (!date) return '—';
  return `${String(date.day).padStart(2, '0')}/${String(date.month).padStart(2, '0')}/${String(date.year).padStart(4, '0')}`;
};

export default formatDate;
