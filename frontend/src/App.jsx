import React, { useState, useEffect } from 'react';
import LoginPage from "./pages/Login.jsx";
import HomePage from "./pages/Home.jsx";
import OverviewPage from "./pages/Overview.jsx";
import TransactionsPage from "./pages/Transactions.jsx";
import Sidebar from "./components/Sidebar";
import Header from "./components/Header";
import "./styles/App.css";

// Defina a URL base do seu backend (ajuste a porta, Flask costuma ser 5000, FastAPI 8000)
const API_URL = "http://localhost:5000"; 

export default function FinancialDashboard() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [currentPage, setCurrentPage] = useState('home');
  // Agora começa vazio! Os dados virão do banco.
  const [transactions, setTransactions] = useState([]); 

  // --- 1. BUSCAR DADOS (GET) ---
  // Esse useEffect roda automaticamente toda vez que 'isAuthenticated' muda para true
  useEffect(() => {
    if (isAuthenticated) {
      const fetchTransactions = async () => {
        try {
          const response = await fetch(`${API_URL}/transactions`);
          if (response.ok) {
            const data = await response.json();
            setTransactions(data);
          } else {
            console.error("Falha ao carregar transações");
          }
        } catch (error) {
          console.error("Erro de conexão com a API:", error);
        }
      };
      
      fetchTransactions();
    }
  }, [isAuthenticated]);

  // --- 2. LOGIN (POST) ---
  const handleLogin = async (userData) => {
    try {
      // Envia nome e senha para a rota de login no backend
      const response = await fetch(`${API_URL}/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(userData)
      });

      if (response.ok) {
        setIsAuthenticated(true);
      } else {
        alert("Nome ou senha incorretos!");
      }
    } catch (error) {
      console.error("Erro ao fazer login:", error);
      alert("Não foi possível conectar ao servidor.");
    }
  };

  const handleLogout = () => {
    setIsAuthenticated(false);
    setCurrentPage('home');
    setTransactions([]); // Limpa as transações ao deslogar
  };

  // --- 3. ADICIONAR (POST) ---
  const handleAddTransaction = async (newTransaction) => {
    try {
      const response = await fetch(`${API_URL}/transactions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newTransaction)
      });

      if (response.ok) {
        const savedTransaction = await response.json();
        // Adiciona a transação que voltou do banco (agora com um ID real do banco)
        setTransactions([...transactions, savedTransaction]);
      }
    } catch (error) {
      console.error("Erro ao adicionar:", error);
    }
  };

  // --- 4. DELETAR (DELETE) ---
  const handleDeleteTransaction = async (id) => {
    if (window.confirm('Tem certeza que deseja deletar esta transação?')) {
      try {
        const response = await fetch(`${API_URL}/transactions/${id}`, {
          method: 'DELETE',
        });

        if (response.ok) {
          // Só remove da tela se o backend confirmar que deletou
          setTransactions(transactions.filter((t) => t.id !== id));
        }
      } catch (error) {
        console.error("Erro ao deletar:", error);
      }
    }
  };

  // --- 5. EDITAR (PUT / PATCH) ---
  const handleEditTransaction = async (id, data) => {
    try {
      const response = await fetch(`${API_URL}/transactions/${id}`, {
        method: 'PUT', // ou 'PATCH', dependendo de como você criar no backend
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      });

      if (response.ok) {
        const updatedTransaction = await response.json();
        setTransactions(
          transactions.map((t) => (t.id === id ? updatedTransaction : t))
        );
      }
    } catch (error) {
      console.error("Erro ao editar:", error);
    }
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