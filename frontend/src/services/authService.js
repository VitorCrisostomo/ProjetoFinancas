import { apiRequest } from './api.js';

export const login = (credentials) =>
    apiRequest('/login', { method: 'POST', data: credentials, authenticated: false });

export const register = (data) =>
    apiRequest('/create_users', { method: 'POST', data, authenticated: false });

export const verifyEmail = (data) =>
    apiRequest('/verify_email', { method: 'POST', data, authenticated: false });
