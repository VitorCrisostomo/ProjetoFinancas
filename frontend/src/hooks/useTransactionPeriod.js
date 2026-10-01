import { useState } from 'react';
import { filterTransactionsByPeriod, getCurrentYear, getTransactionYears, normalizeTransactionPeriod } from '../utils/transactionPeriod.js';

export default function useTransactionPeriod(transactions) {
  const [{ month, year }, setPeriod] = useState({ month: 'all', year: 'all' });
  const setMonth = (nextMonth) => setPeriod((previous) => normalizeTransactionPeriod(nextMonth, previous.year));
  const setYear = (nextYear) => setPeriod((previous) => normalizeTransactionPeriod(previous.month, nextYear));
  const resetPeriod = () => {
    setPeriod({ month: 'all', year: 'all' });
  };

  return {
    month, year, setMonth, setYear, resetPeriod,
    years: [...new Set([
      ...getTransactionYears(transactions), Number(getCurrentYear()),
      ...(year === 'all' ? [] : [Number(year)]),
    ])].sort((a, b) => b - a),
    isFiltered: month !== 'all' || year !== 'all',
    transactions: filterTransactionsByPeriod(transactions, month, year),
  };
}
