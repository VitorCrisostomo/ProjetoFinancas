import { apiRequest } from './api.js';

export const fetchTransactions = () => apiRequest('/transactions');

export const createTransaction = (data) =>
    apiRequest('/create_transactions', { method: 'POST', data });

export const updateTransaction = (id, data) =>
    apiRequest(`/update_transactions/${encodeURIComponent(id)}`, { method: 'PATCH', data });

export const deleteTransaction = (id) =>
    apiRequest(`/transactions/${encodeURIComponent(id)}`, { method: 'DELETE' });

export const associateTransactions = (keepId, removeId, updatedData) =>
    apiRequest('/transactions/associate', {
        method: 'POST',
        data: {
            keep_id: keepId,
            remove_id: removeId,
            updated_data: { ...updatedData, value: parseFloat(updatedData.value) },
        },
    });

export const importTransactions = (file) => {
    const body = new FormData();
    body.append('file', file);
    return apiRequest('/transactions/import', { method: 'POST', body });
};
