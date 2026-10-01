import { apiRequest } from './api.js';

export const fetchTransactions = () => apiRequest('/transactions');

export const updateTransaction = (id, data) =>
    apiRequest(`/update_transactions/${encodeURIComponent(id)}`, { method: 'PATCH', data });

export const associateTransactions = (transactionIds, updatedData) =>
    apiRequest('/transactions/associate', {
        method: 'POST',
        data: {
            transaction_ids: transactionIds,
            updated_data: { ...updatedData, value: parseFloat(updatedData.value) },
        },
    });

