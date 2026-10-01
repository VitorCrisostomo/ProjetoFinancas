import { apiRequest } from './api.js';

export const fetchAccounts = () => apiRequest('/accounts');

export const syncAccount = (data) =>
    apiRequest('/accounts/sync', { method: 'POST', data });

export const deleteAccount = (id) =>
    apiRequest(`/accounts/${encodeURIComponent(id)}`, { method: 'DELETE' });
