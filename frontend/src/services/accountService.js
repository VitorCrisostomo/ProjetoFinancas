import { apiRequest } from './api.js';

export const fetchAccounts = () => apiRequest('/accounts');

export const deleteAccount = (id) =>
    apiRequest(`/accounts/${encodeURIComponent(id)}`, { method: 'DELETE' });
