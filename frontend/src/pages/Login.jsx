import { useState } from "react";
import Button from "../components/common/Button";

const LoginPage = ({ onLogin, onRegister, onVerify }) => {
  const [isRegistering, setIsRegistering] = useState(false);
  const [isVerifying, setIsVerifying] = useState(false); // NOVO ESTADO!
  
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [code, setCode] = useState(''); // Guarda o código de 6 dígitos
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (isVerifying) {
      // 🟢 MODO 3: VERIFICAÇÃO DO CÓDIGO
      if (code) {
        const success = await onVerify({ email, code });
        if (success) {
          // Se deu certo, voltamos para a tela de Login e limpamos tudo
          setIsVerifying(false);
          setIsRegistering(false);
          setPassword('');
          setCode('');
        }
      } else {
        setError('Por favor, digite o código de 6 dígitos.');
      }

    } else if (isRegistering) {
      // 🟢 MODO 2: CADASTRO
      if (name && email && password) {
        // Espera a resposta do App.jsx
        const success = await onRegister({ name, email, password });
        if (success) {
          setIsVerifying(true); // Sucesso! Muda para a tela de digitar o código!
        }
      } else {
        setError('Por favor, preencha todos os campos.');
      }

    } else {
      // 🟢 MODO 1: LOGIN
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
          
          {/* O texto muda dependendo da tela atual */}
          <p>
            {isVerifying ? 'Verifique seu e-mail' 
             : isRegistering ? 'Crie sua conta para começar' 
             : 'Entre com sua conta para acessar o painel'}
          </p>
        </div>

        {error && <div className="login-error">{error}</div>}

        <form onSubmit={handleSubmit} className="login-form">
          
          {/* --- TELA DE VERIFICAÇÃO DE CÓDIGO --- */}
          {isVerifying ? (
            <div className="form-group">
              <label>Código de Verificação</label>
              <p style={{ fontSize: '0.85rem', color: '#666', marginBottom: '10px' }}>
                Enviamos um código de 6 dígitos para <strong>{email}</strong>
              </p>
              <input
                type="text"
                maxLength="6"
                value={code}
                onChange={(e) => setCode(e.target.value)}
                placeholder="Ex: 123456"
                style={{ textAlign: 'center', letterSpacing: '4px', fontSize: '1.2rem' }}
                required
              />
            </div>
          ) : (
            /* --- TELA DE LOGIN / CADASTRO --- */
            <>
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
            </>
          )}

          {/* BOTÕES */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginTop: '20px' }}>
            <Button variant="primary" size="lg" type="submit" className="login-btn">
              {isVerifying ? 'Verificar Código' : isRegistering ? 'Cadastrar' : 'Entrar'}
            </Button>

            {/* O Botão Secundário só aparece se NÃO estivermos verificando o código */}
            {!isVerifying && (
              <Button 
                variant="secondary" 
                size="lg" 
                type="button" 
                onClick={() => {
                  setIsRegistering(!isRegistering);
                  setError('');
                }}
              >
                {isRegistering ? 'Já tenho uma conta' : 'Criar nova conta'}
              </Button>
            )}
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