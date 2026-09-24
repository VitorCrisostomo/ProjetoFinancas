import { useState } from "react";
import Button from "../components/common/Button";

const LoginPage = ({ onLogin, onRegister }) => {
  // Estado para controlar se a tela é de Login ou Cadastro
  const [isRegistering, setIsRegistering] = useState(false);
  
  const [name, setName] = useState(''); // Só será usado no cadastro
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    setError(''); // Limpa mensagens de erro antigas

    if (isRegistering) {
      // MODO CADASTRO
      if (name && email && password) {
        onRegister({ name, email, password }); 
      } else {
        setError('Por favor, preencha todos os campos.');
      }
    } else {
      // MODO LOGIN
      if (email && password) {
        onLogin({ email, password }); 
      } else {
        setError('Por favor, preencha todos os campos.');
      }
    }
  };

  return (
    <div className="login-container">
      <div className="login-card">
        <div className="login-header">
          <div className="sidebar-logo">💰</div>
          <h1>FinanceHub</h1>
          {/* O texto muda dependendo da tela */}
          <p>{isRegistering ? 'Crie sua conta para começar' : 'Entre com sua conta para acessar o painel'}</p>
        </div>

        {error && <div className="login-error">{error}</div>}

        <form onSubmit={handleSubmit} className="login-form">
          
          {/* O campo Nome SÓ aparece se estivermos no modo "Criar Conta" */}
          {isRegistering && (
            <div className="form-group">
              <label>Nome</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Seu nome completo"
                required={isRegistering}
              />
            </div>
          )}

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

          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginTop: '20px' }}>
            <Button variant="primary" size="lg" type="submit" className="login-btn">
              {isRegistering ? 'Cadastrar' : 'Entrar'}
            </Button>

            {/* O Botão Secundário que alterna as telas */}
            <Button 
              variant="secondary" 
              size="lg" 
              type="button" 
              onClick={() => {
                setIsRegistering(!isRegistering); // Inverte a tela
                setError(''); // Limpa qualquer erro que estava na tela
              }}
            >
              {isRegistering ? 'Já tenho uma conta' : 'Criar nova conta'}
            </Button>
          </div>
        </form>

        <div className="login-footer">
          <p>Caso esqueça a senha, entrar em contato com Vítor.</p>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;