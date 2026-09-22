import React, { useState } from 'react';
import LoginPage from "./pages/Login.jsx";
import HomePage from "./pages/Home.jsx";
import OverviewPage from "./pages/Overview.jsx";
import TransactionsPage from "./pages/Transactions.jsx";
import Sidebar from "./components/Sidebar";
import Header from "./components/Header";
import "./styles/App.css"

// ============================================================================
// DATA & UTILS
// ============================================================================

// Dados fictícios estruturados para fácil substituição por API
export const initialTransactions = [
  { id: 1, date: '2024-01-15', name: 'Salário', category: 'Salário', amount: 5000, type: 'income' },
  { id: 2, date: '2024-01-18', name: 'Supermercado', category: 'Alimentação', amount: 350, type: 'expense' },
  { id: 3, date: '2024-01-19', name: 'Aluguel', category: 'Moradia', amount: 1500, type: 'expense' },
  { id: 4, date: '2024-01-20', name: 'Freelance', category: 'Extra', amount: 800, type: 'income' },
  { id: 5, date: '2024-01-21', name: 'Netflix', category: 'Entretenimento', amount: 35, type: 'expense' },
  { id: 6, date: '2024-01-22', name: 'Restaurante', category: 'Alimentação', amount: 120, type: 'expense' },
  { id: 7, date: '2024-01-23', name: 'Gasolina', category: 'Transporte', amount: 200, type: 'expense' },
  { id: 8, date: '2024-01-24', name: 'Bônus', category: 'Salário', amount: 1000, type: 'income' },
];

// Função utilitária para formatação de moeda

// Função para formatar data

// ============================================================================
// COMPONENTES REUTILIZÁVEIS
// ============================================================================

// Card - Componente base para exibição de informações

// Button - Componente de botão reutilizável

// Modal - Componente para formulário de nova transação

// ============================================================================
// PÁGINAS (INCLUINDO LOGIN)
// ============================================================================

// Página de Login

// Página Home - Dashboard Inicial

// Página Overview - Análise Financeira

// Página Transactions - Gerenciamento de Transações

// ============================================================================
// COMPONENTES DE LAYOUT
// ============================================================================

// Sidebar - Navegação lateral

// Header - Cabeçalho da página

// ============================================================================
// APLICAÇÃO PRINCIPAL
// ============================================================================

export default function FinancialDashboard() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [currentPage, setCurrentPage] = useState('home');
  const [transactions, setTransactions] = useState(initialTransactions);

  const handleLogin = (userData) => {
    setIsAuthenticated(true);
  };

  const handleLogout = () => {
    setIsAuthenticated(false);
    setCurrentPage('home');
  };

  const handleAddTransaction = (newTransaction) => {
    const transaction = {
      ...newTransaction,
      id: Math.max(...transactions.map((t) => t.id), 0) + 1,
    };
    setTransactions([...transactions, transaction]);
  };

  const handleDeleteTransaction = (id) => {
    if (window.confirm('Tem certeza que deseja deletar esta transação?')) {
      setTransactions(transactions.filter((t) => t.id !== id));
    }
  };

  const handleEditTransaction = (id, data) => {
    setTransactions(
      transactions.map((t) => (t.id === id ? { ...t, ...data } : t))
    );
  };

  const renderPage = () => {
    switch (currentPage) {
      case 'home':
        return <HomePage transactions={transactions} />;
      case 'overview':
        return <OverviewPage transactions={transactions} />;
      case 'transactions':
        return (
          <TransactionsPage
            transactions={transactions}
            onAddTransaction={handleAddTransaction}
            onDeleteTransaction={handleDeleteTransaction}
            onEditTransaction={handleEditTransaction}
          />
        );
      default:
        return <HomePage transactions={transactions} />;
    }
  };

  if (!isAuthenticated) {
    return (
      <div className="app-container">
        <LoginPage onLogin={handleLogin} />
      </div>
    );
  }

  return (
    <div className="app-container">
      <Sidebar currentPage={currentPage} onPageChange={setCurrentPage} onLogout={handleLogout} />
      <div className="main-content">
        <Header />
        <div className="content-area">{renderPage()}</div>
      </div>
    </div>
  );
}

// ============================================================================
// ESTILOS CSS
// ============================================================================