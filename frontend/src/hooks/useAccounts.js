import useCollection from './useCollection.js';
import { fetchAccounts, deleteAccount as deleteAccountRequest } from '../services/accountService.js';
import { fetchConnectToken, syncPluggyAccounts } from '../services/pluggyService.js';
import { readResponse } from '../services/api.js';

const loadAccounts = async () => readResponse(await fetchAccounts());

export default function useAccounts() {
  const { items: accounts, execute, ...state } = useCollection(loadAccounts);

  const getConnectToken = () => execute(async () => {
    const data = await readResponse(await fetchConnectToken());
    return data.connectToken;
  });

  const syncAccounts = (itemId) => execute(
    async () => readResponse(await syncPluggyAccounts(itemId)),
    (previous, result) => {
      const merged = new Map(previous.map((account) => [account.id, account]));
      result.accounts.forEach((account) => merged.set(account.id, account));
      return [...merged.values()];
    },
  );

  const deleteAccount = (id) => execute(
    async () => readResponse(await deleteAccountRequest(id)),
    (previous) => previous.filter((account) => account.id !== id),
  );

  return { accounts, ...state, getConnectToken, syncAccounts, deleteAccount };
}
