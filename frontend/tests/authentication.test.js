import assert from 'node:assert/strict';
import test from 'node:test';
import { apiRequest, readResponse, setCsrfToken } from '../src/services/api.js';
import { login, fetchSession, logout } from '../src/services/authService.js';

test('sessão usa cookie, envia CSRF nas escritas e não envia token no cabeçalho', async () => {
    const originalFetch = globalThis.fetch;
    const calls = [];
    globalThis.fetch = async (url, options) => {
        calls.push({ url, options });
        return new Response('{}', { status: 200 });
    };
    try {
        setCsrfToken('session-csrf');
        await apiRequest('/accounts');
        await apiRequest('/categories', { method: 'POST', data: { name: 'Extra' } });
        assert.equal(calls[0].options.credentials, 'include');
        assert.equal(calls[0].options.headers.Authorization, undefined);
        assert.equal(calls[0].options.headers['X-CSRF-TOKEN'], undefined);
        assert.equal(calls[1].options.headers['X-CSRF-TOKEN'], 'session-csrf');
        assert.equal(calls[1].options.headers['Content-Type'], 'application/json');
        assert.equal(calls[1].options.body, '{"name":"Extra"}');
    } finally {
        globalThis.fetch = originalFetch;
        setCsrfToken(null);
    }
});

test('login, restauração e logout usam os contratos da sessão', async () => {
    const originalFetch = globalThis.fetch;
    const calls = [];
    globalThis.fetch = async (url, options) => {
        calls.push({ url, options });
        return new Response('{}', { status: 200 });
    };
    try {
        setCsrfToken('session-csrf');
        await login({ email: 'user@example.com', password: 'password' });
        await fetchSession();
        await logout();
        assert.equal(calls[0].url, '/api/login');
        assert.equal(calls[0].options.headers['X-CSRF-TOKEN'], undefined);
        assert.equal(calls[1].url, '/api/auth/session');
        assert.equal(calls[2].url, '/api/logout');
        assert.equal(calls[2].options.method, 'POST');
        assert.equal(calls[2].options.headers['X-CSRF-TOKEN'], 'session-csrf');
    } finally {
        globalThis.fetch = originalFetch;
        setCsrfToken(null);
    }
});

test('sessão expirada limpa a autenticação; senha incorreta no login não dispara expiração', async () => {
    const originalFetch = globalThis.fetch;
    const originalWindow = globalThis.window;
    globalThis.window = new EventTarget();
    globalThis.fetch = async () => new Response('{"message":"Entre novamente."}', { status: 401 });
    let expired = 0;
    window.addEventListener('auth:expired', () => { expired += 1; });
    try {
        setCsrfToken('old-csrf');
        await login({ email: 'user@example.com', password: 'wrong' });
        assert.equal(expired, 0);
        const response = await apiRequest('/accounts');
        assert.equal(expired, 1);
        await assert.rejects(readResponse(response), /Entre novamente/);
    } finally {
        globalThis.fetch = originalFetch;
        globalThis.window = originalWindow;
        setCsrfToken(null);
    }
});

test('resposta expirada de uma requisição antiga preserva a sessão recém-criada', async () => {
    const originalFetch = globalThis.fetch;
    const originalWindow = globalThis.window;
    globalThis.window = new EventTarget();
    let resolveFetch;
    globalThis.fetch = () => new Promise((resolve) => { resolveFetch = resolve; });
    let expired = 0;
    window.addEventListener('auth:expired', () => { expired += 1; });
    try {
        setCsrfToken('old-session');
        const pending = apiRequest('/accounts');
        setCsrfToken('new-session');
        resolveFetch(new Response('{}', { status: 401 }));
        await pending;
        assert.equal(expired, 0);
    } finally {
        globalThis.fetch = originalFetch;
        globalThis.window = originalWindow;
        setCsrfToken(null);
    }
});
