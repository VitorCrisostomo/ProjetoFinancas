import { apiRequest } from './api.js';

export const login = (credentials) =>
    apiRequest('/login', { method: 'POST', data: credentials, authenticated: false });

export const fetchSession = () => apiRequest('/auth/session');

export const logout = () => apiRequest('/logout', { method: 'POST' });
