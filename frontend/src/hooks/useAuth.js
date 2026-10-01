import { useState } from 'react';
import {
  login as loginRequest,
  register as registerRequest,
  verifyEmail as verifyEmailRequest,
} from '../services/authService.js';

export default function useAuth() {
  const [user, setUser] = useState(null);

  const login = async ({ email, password }) => { 
    try {
      const response = await loginRequest({ email, password });

      if (response.ok) {
        const data = await response.json();
        
        localStorage.setItem('token', data.access_token); 
        localStorage.setItem('userName', data.user.name);
        
        setUser(data.user); 
      } else {
        const errorData = await response.json();
        alert(`Erro: ${errorData.message || errorData.error || "Nome ou senha incorretos!"}`);
      }
    } catch (error) {
      console.error("Erro ao fazer login:", error);
      alert("Não foi possível conectar ao servidor.");
    }
  };

  const register = async ({ name, email, password }) => {
    try {
      const response = await registerRequest({ name, email, password });

      if (response.ok) {
        return true; 
      } else {
        const errorData = await response.json();
        alert(`Erro: ${errorData.message}`);
        return false;
      }
    } catch (error) {
      console.error("Erro ao criar conta:", error);
      return false;
    }
  };

  const verifyEmail = async ({ email, code }) => {
    try {
      const response = await verifyEmailRequest({ email, code });

      if (response.ok) {
        alert('E-mail verificado com sucesso! Agora você pode fazer login.');
        return true; // Retorna true para a tela saber que deu certo
      } else {
        const errorData = await response.json();
        alert(`Erro: ${errorData.message}`);
        return false;
      }
    } catch (error) {
      console.error("Erro ao verificar conta:", error);
      return false;
    }
  };

  const logout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('userName');
    setUser(null);
  };

  return {
    user,
    isAuthenticated: user !== null,
    login,
    register,
    verifyEmail,
    logout,
  };
}
