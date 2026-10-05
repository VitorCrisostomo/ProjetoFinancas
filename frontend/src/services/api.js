export const API_URL = (
    import.meta.env?.VITE_API_URL || '/api'
).replace(/\/+$/, '');

let csrfToken = null;
let sessionGeneration = 0;

export const setCsrfToken = (token) => {
    csrfToken = token;
    sessionGeneration += 1;
};

// A sessão fica no cookie HttpOnly; apenas o valor de proteção CSRF fica em memória.
export const apiRequest = async (path, { method = 'GET', data, body, authenticated = true } = {}) => {
    const requestGeneration = sessionGeneration;
    const headers = {};
    if (authenticated && csrfToken && !['GET', 'HEAD', 'OPTIONS'].includes(method.toUpperCase())) {
        headers['X-CSRF-TOKEN'] = csrfToken;
    }
    if (data !== undefined) {
        headers['Content-Type'] = 'application/json';
        body = JSON.stringify(data);
    }
    const response = await fetch(`${API_URL}${path}`, {
        method, headers, body, credentials: 'include',
    });
    // Uma resposta atrasada da sessão anterior não deve derrubar um novo login.
    if (authenticated && response.status === 401 && requestGeneration === sessionGeneration) {
        setCsrfToken(null);
        window.dispatchEvent(new Event('auth:expired'));
    }
    return response;
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
