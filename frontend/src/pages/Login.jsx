import React, { useState } from "react";
import Button from "../components/common/Button" 
import Card from "../components/common/Card";

const LoginPage = ({ onLogin }) => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    // Simulação básica de validação de login
    if (email && password) {
      onLogin({ name: 'João Silva', email });
    } else {
      setError('Por favor, preencha todos os campos.');
    }
  };

  return (
    <div className="login-container">
      <div className="login-card">
        <div className="login-header">
          <div className="sidebar-logo">💰</div>
          <h1>FinanceHub</h1>
          <p>Entre com sua conta para acessar o painel</p>
        </div>

        {error && <div className="login-error">{error}</div>}

        <form onSubmit={handleSubmit} className="login-form">
          <div className="form-group">
            <label>E-mail</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="seu@email.com"
              required
            />
          </div>

          <div className="form-group">
            <label>Senha</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              required
            />
          </div>

          <Button variant="primary" size="lg" type="submit" className="login-btn">
            Entrar
          </Button>
        </form>

        <div className="login-footer">
          <p>Dica: Digite qualquer e-mail e senha para testar.</p>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
