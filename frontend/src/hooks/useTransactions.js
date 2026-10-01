import useCollection from './useCollection.js';
import * as transactionService from '../services/transactionService.js';
import { syncPluggyTransactions } from '../services/pluggyService.js';
import { readResponse } from '../services/api.js';

const loadTransactions = async () => readResponse(await transactionService.fetchTransactions());

export default function useTransactions() {
  const { items: transactions, execute, ...state } = useCollection(loadTransactions);
  const reloadTransactions = () => execute(loadTransactions, (_previous, loaded) => loaded);

  const updateTransaction = (id, data) => execute(
    async () => readResponse(await transactionService.updateTransaction(id, data)),
    (previous, saved) => previous.map((item) => item.id === id ? saved : item),
  );

  const associateTransactions = (transactionIds, data) => execute(
    async () => readResponse(await transactionService.associateTransactions(transactionIds, data)),
    (previous, saved) => previous.filter((item) => !transactionIds.slice(1).includes(item.id))
      .map((item) => item.id === saved.id ? saved : item),
  );

  const syncTransactions = (options) => execute(async () => {
    const result = await readResponse(await syncPluggyTransactions(options));
    // Recarrega o histórico completo, incluindo associações e ajustes de saldo anterior.
    return { result, transactions: await loadTransactions() };
  }, (_previous, data) => data.transactions).then((data) => data?.result);

  return { transactions, ...state, updateTransaction,
    associateTransactions, syncTransactions, reloadTransactions };
}
