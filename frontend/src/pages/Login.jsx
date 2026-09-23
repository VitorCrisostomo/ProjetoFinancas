import { useState } from "react";
import Button from "../components/common/Button" 

const LoginPage = ({ onLogin }) => {
  const [name, setName] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (name && password) {
      // O SEGREDO ESTÁ AQUI: Você precisa enviar name E password
      onLogin({ name: name, password: password }); 
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
            <label>Nome</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Seu nome"
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
          <p>Caso esqueça a senha, entrar em contato com Vítor.</p>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;