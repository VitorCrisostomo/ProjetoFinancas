import { apiRequest } from './api.js';

// A API retorna somente o perfil do usuário autenticado.
export const fetchUsers = async () => {
    const response = await apiRequest('/users');
    if (!response.ok) throw new Error('Erro ao buscar seu perfil');
    return response.json();
};

export const updateUser = (id, data) =>
    apiRequest(`/update_users/${encodeURIComponent(id)}`, { method: 'PATCH', data });

export const deleteUser = (id, currentPassword) =>
    apiRequest(`/delete_users/${encodeURIComponent(id)}`, {
        method: 'DELETE', data: { current_password: currentPassword },
    });
