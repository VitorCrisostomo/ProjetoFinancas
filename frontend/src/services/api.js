export const API_URL = (
    import.meta.env.VITE_API_URL || "http://localhost:5000"
).replace(/\/+$/, "");

// Retorna Response para preservar o tratamento de sucesso e erro das telas.
export const apiRequest = (path, { method = 'GET', data, body, authenticated = true } = {}) => {
    const headers = {};

    if (authenticated) {
        headers.Authorization = `Bearer ${localStorage.getItem('token')}`;
    }

    if (data !== undefined) {
        headers['Content-Type'] = 'application/json';
        body = JSON.stringify(data);
    }

    return fetch(`${API_URL}${path}`, { method, headers, body });
};

export const readResponse = async (response) => {
    const text = await response.text();
    let data;
    try {
        data = text ? JSON.parse(text) : null;
    } catch {
        data = null;
    }
    if (!response.ok) {
        throw new Error(data?.message || data?.error || `Falha na requisição (${response.status}).`);
    }
    return data;
};
