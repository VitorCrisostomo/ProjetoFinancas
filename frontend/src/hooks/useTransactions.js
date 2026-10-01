import useCollection from './useCollection.js';
import * as transactionService from '../services/transactionService.js';
import { syncPluggyTransactions } from '../services/pluggyService.js';
import { readResponse } from '../services/api.js';

const loadTransactions = async () => readResponse(await transactionService.fetchTransactions());

export default function useTransactions() {
  const { items: transactions, execute, ...state } = useCollection(loadTransactions);
  const reloadTransactions = () => execute(loadTransactions, (_previous, loaded) => loaded);

  const addTransaction = (data) => execute(
    async () => readResponse(await transactionService.createTransaction(data)),
    (previous, saved) => [...previous, saved],
  );

  const updateTransaction = (id, data) => execute(
    async () => readResponse(await transactionService.updateTransaction(id, data)),
    (previous, saved) => previous.map((item) => item.id === id ? saved : item),
  );

  const deleteTransaction = (id) => execute(
    async () => readResponse(await transactionService.deleteTransaction(id)),
    (previous) => previous.filter((item) => item.id !== id),
  );

  const associateTransactions = (keepId, removeId, data) => execute(
    async () => readResponse(await transactionService.associateTransactions(keepId, removeId, data)),
    (previous, saved) => previous.filter((item) => item.id !== removeId)
      .map((item) => item.id === keepId ? saved : item),
  );

  const importTransactions = (file) => execute(async () => {
    const result = await readResponse(await transactionService.importTransactions(file));
    return { result, transactions: await loadTransactions() };
  }, (_previous, data) => data.transactions).then((data) => data?.result);

  const syncTransactions = (options) => execute(async () => {
    const result = await readResponse(await syncPluggyTransactions(options));
    // A resposta da Pluggy inclui apenas transações bancárias; recarrega também as manuais.
    return { result, transactions: await loadTransactions() };
  }, (_previous, data) => data.transactions).then((data) => data?.result);

  return { transactions, ...state, addTransaction, updateTransaction, deleteTransaction,
    associateTransactions, importTransactions, syncTransactions, reloadTransactions };
}
