import { useState } from 'react';
import Button from '../components/common/Button.jsx';

export default function LoginPage({ onLogin, sessionError = '' }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (isSubmitting) return;
    setError('');
    setIsSubmitting(true);
    try {
      await onLogin({ email, password });
    } catch (failure) {
      setError(failure.message || 'Não foi possível conectar ao servidor.');
    } finally {
      setIsSubmitting(false);
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
        {(error || sessionError) && (
          <div className="login-error" role="alert">{error || sessionError}</div>
        )}
        <form onSubmit={handleSubmit} className="login-form">
          <div className="form-group">
            <label htmlFor="login-email">E-mail</label>
            <input
              id="login-email"
              type="email"
              autoComplete="username"
              maxLength={120}
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="seu@email.com"
              required
            />
          </div>
          <div className="form-group">
            <label htmlFor="login-password">Senha</label>
            <input
              id="login-password"
              type="password"
              autoComplete="current-password"
              maxLength={128}
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="••••••••"
              required
            />
          </div>
          <Button
            variant="primary" size="lg" type="submit"
            className="login-btn" disabled={isSubmitting}
          >
            {isSubmitting ? 'Entrando...' : 'Entrar'}
          </Button>
        </form>
        <div className="login-footer">
          <p>Para criar um acesso ou recuperar sua senha, fale com o administrador do servidor.</p>
        </div>
      </div>
    </div>
  );
}
