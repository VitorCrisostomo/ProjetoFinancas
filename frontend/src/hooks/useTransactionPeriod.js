import { useState } from 'react';
import { filterTransactionsByPeriod, getTransactionYears } from '../utils/transactionPeriod.js';

export default function useTransactionPeriod(transactions) {
  const [month, setMonth] = useState('all');
  const [year, setYear] = useState('all');
  const resetPeriod = () => {
    setMonth('all');
    setYear('all');
  };

  return {
    month, year, setMonth, setYear, resetPeriod,
    years: getTransactionYears(transactions),
    isFiltered: month !== 'all' || year !== 'all',
    transactions: filterTransactionsByPeriod(transactions, month, year),
  };
}
