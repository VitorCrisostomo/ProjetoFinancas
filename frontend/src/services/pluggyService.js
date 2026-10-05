import { apiRequest } from './api.js';

export const fetchConnectToken = () => apiRequest('/pluggy/connect_token', { method: 'POST' });

export const syncPluggyAccounts = (itemId) =>
    apiRequest('/pluggy/accounts/sync', { method: 'POST', data: { itemId } });

export const syncPluggyTransactions = (options) =>
    apiRequest('/pluggy/transactions/sync', { method: 'POST', data: options });
