import { apiRequest } from './api.js';

// Mantém o contrato dos serviços de usuários existentes.
export const fetchUsers = async () => {
    const response = await apiRequest('/users', { authenticated: false });
    if (!response.ok) {
        throw new Error("Erro ao buscar usuários");
    }
    return await response.json();
};

export const createUser = async (data) => {
    const response = await apiRequest('/create_users', { method: 'POST', data, authenticated: false });
    return response;
};

export const updateUser = async (id, data) => {
    const response = await apiRequest(`/update_users/${encodeURIComponent(id)}`, { method: 'PATCH', data, authenticated: false });
    return response;
};

export const deleteUser = async (id) => {
    const response = await apiRequest(`/delete_users/${encodeURIComponent(id)}`, { method: 'DELETE', authenticated: false });
    return response;
};
