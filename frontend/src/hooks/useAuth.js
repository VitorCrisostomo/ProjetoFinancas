import { useEffect, useRef, useState } from 'react';
import {
  fetchSession,
  login as loginRequest,
  logout as logoutRequest,
} from '../services/authService.js';
import { readResponse, setCsrfToken } from '../services/api.js';

export default function useAuth() {
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [sessionError, setSessionError] = useState('');
  const channel = useRef(null);
  const generation = useRef(0);

  useEffect(() => {
    let active = true;
    // Remove credenciais antigas durante a transição para cookies.
    try {
      localStorage.removeItem('token');
      localStorage.removeItem('userName');
    } catch {
      // Cookies permitem autenticar mesmo se o armazenamento local estiver bloqueado.
    }
    const clearSession = () => {
      generation.current += 1;
      setCsrfToken(null);
      setUser(null);
      setIsLoading(false);
    };
    window.addEventListener('auth:expired', clearSession);
    const restoreSession = async () => {
      const requestGeneration = ++generation.current;
      try {
        const response = await fetchSession();
        if (response.status === 401) return;
        const data = await readResponse(response);
        if (active && requestGeneration === generation.current) {
          setCsrfToken(data.csrf_token);
          setUser(data.user);
        }
      } catch {
        if (active && requestGeneration === generation.current) {
          setSessionError('Não foi possível verificar sua sessão. Tente entrar novamente.');
        }
      } finally {
        if (active && requestGeneration === generation.current) setIsLoading(false);
      }
    };
    if (typeof BroadcastChannel !== 'undefined') {
      channel.current = new BroadcastChannel('financehub-session');
      channel.current.onmessage = () => {
        clearSession();
        setIsLoading(true);
        restoreSession();
      };
    }
    restoreSession();
    return () => {
      active = false;
      window.removeEventListener('auth:expired', clearSession);
      channel.current?.close();
      channel.current = null;
    };
  }, []);

  const login = async (credentials) => {
    const data = await readResponse(await loginRequest(credentials));
    generation.current += 1;
    setCsrfToken(data.csrf_token);
    setSessionError('');
    setUser(data.user);
    channel.current?.postMessage('changed');
  };

  const logout = async () => {
    try {
      await readResponse(await logoutRequest());
      generation.current += 1;
      setCsrfToken(null);
      setUser(null);
      channel.current?.postMessage('changed');
    } catch (error) {
      alert(error.message || 'Não foi possível encerrar a sessão. Tente novamente.');
    }
  };

  return { user, isLoading, sessionError, isAuthenticated: user !== null, login, logout };
}
