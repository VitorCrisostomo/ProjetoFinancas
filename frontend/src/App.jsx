import LoginPage from './pages/Login.jsx';
import AuthenticatedDashboard from './app/AuthenticatedDashboard.jsx';
import useAuth from './hooks/useAuth.js';
import './styles/App.css';

export default function App() {
  const { user, isAuthenticated, isLoading, sessionError, login, logout } = useAuth();

  if (isLoading) return <div className="app-container" role="status">Verificando sessão...</div>;

  if (!isAuthenticated) {
    return (
      <div className="app-container">
        <LoginPage onLogin={login} sessionError={sessionError} />
      </div>
    );
  }

  return <AuthenticatedDashboard key={user.id} user={user} onLogout={logout} />;
}
