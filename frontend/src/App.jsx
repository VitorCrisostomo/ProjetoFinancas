import LoginPage from './pages/Login.jsx';
import AuthenticatedDashboard from './app/AuthenticatedDashboard.jsx';
import useAuth from './hooks/useAuth.js';
import './styles/App.css';

export default function App() {
  const { user, isAuthenticated, login, register, verifyEmail, logout } = useAuth();

  if (!isAuthenticated) {
    return (
      <div className="app-container">
        <LoginPage onLogin={login} onRegister={register} onVerify={verifyEmail} />
      </div>
    );
  }

  return <AuthenticatedDashboard key={user.id} user={user} onLogout={logout} />;
}
