// src/App.jsx

import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import UsersPage from './pages/UsersPage';
import './styles/App.css';

function App() {
  return (
    <Router>
      <nav style={{ padding: '10px', backgroundColor: '#f0f0f0', marginBottom: '20px' }}>
        <ul style={{ listStyle: 'none', display: 'flex', gap: '15px', margin: 0, padding: 0 }}>
          <li>
            <Link to="/">Início</Link>
          </li>
          <li>
            <Link to="/users">Usuários</Link>
          </li>
          {/* Futuramente, você adicionará o link para Transações aqui */}
          {/* <li><Link to="/transactions">Transações</Link></li> */}
        </ul>
      </nav>

      <main style={{ padding: '20px' }}>
        <Routes>
          <Route path="/" element={<h2>Bem-vindo ao Sistema</h2>} />
          <Route path="/users" element={<UsersPage />} />
          
          {/* Futuramente, você adicionará a rota para Transações aqui */}
          {/* <Route path="/transactions" element={<TransactionsPage />} /> */}
        </Routes>
      </main>
    </Router>
  );
}

export default App;