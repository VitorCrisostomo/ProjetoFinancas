import { API_URL } from './api';

// Busca todos os usuários[cite: 3]
export const fetchUsers = async () => {
    const response = await fetch(`${API_URL}/users`);
    if (!response.ok) {
        throw new Error("Erro ao buscar usuários");
    }
    return await response.json();
};

// Cria um novo usuário[cite: 6]
export const createUser = async (data) => {
    const response = await fetch(`${API_URL}/create_users`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(data)
    });
    return response;
};

// Atualiza um usuário existente[cite: 6]
export const updateUser = async (id, data) => {
    const response = await fetch(`${API_URL}/update_users/${id}`, {
        method: "PATCH",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(data)
    });
    return response;
};

// Deleta um usuário[cite: 1]
export const deleteUser = async (id) => {
    const response = await fetch(`${API_URL}/delete_users/${id}`, {
        method: "DELETE"
    });
    return response;
};