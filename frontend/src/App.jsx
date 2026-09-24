import React, { useState, useEffect } from 'react';
import LoginPage from "./pages/Login.jsx";
import HomePage from "./pages/Home.jsx";
import OverviewPage from "./pages/Overview.jsx";
import TransactionsPage from "./pages/Transactions.jsx";
import Sidebar from "./components/Sidebar";
import Header from "./components/Header";
import "./styles/App.css";

const API_URL = "http://localhost:5000"; 

export default function FinancialDashboard() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [currentPage, setCurrentPage] = useState('home');
  // Agora começa vazio! Os dados virão do banco.
  const [transactions, setTransactions] = useState([]); 

  useEffect(() => {
    if (isAuthenticated) {
      const fetchTransactions = async () => {
        try {
          // 1. Pega o token salvo
          const token = localStorage.getItem('token');

          // Se não tiver token, nem tenta buscar (o usuário não tá logado ainda)
          if (!token) return;
        
          const response = await fetch(`${API_URL}/transactions`, {
            method: 'GET', // Opcional colocar o GET, mas é bom para clareza
            headers: {
              'Content-Type': 'application/json',
              // 2. Mostra o crachá para o servidor!
              'Authorization': `Bearer ${token}` 
            }
          });
        
          if (response.ok) {
            const data = await response.json();
            setTransactions(data); // Salva as transações do usuário logado!
          } else {
            console.error("Falha ao carregar transações");
          }
        } catch (error) {
          console.error("Erro:", error);
        }
  };
      
      fetchTransactions();
    }
  }, [isAuthenticated]);

  const handleLogin = async (userData) => {
    try {
      // Envia os dados (que já estão vindo como objeto do seu form) para a rota de login
      const response = await fetch(`${API_URL}/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(userData) 
      });

      if (response.ok) {
        // 1. Extrai a resposta JSON que veio do Python
        const data = await response.json();
        
        // 2. Salva o token mágico no navegador!
        localStorage.setItem('token', data.access_token); 
        
        // 3. Atualiza o estado (ISSO AQUI é o que te leva para a Home!)
        setIsAuthenticated(true); 
      } else {
        const errorData = await response.json();
        alert(`Erro: ${errorData.message || errorData.error || "Nome ou senha incorretos!"}`);
      }
    } catch (error) {
      console.error("Erro ao fazer login:", error);
      alert("Não foi possível conectar ao servidor.");
    }
  };

const handleLogout = () => {
    // 1. Remove o token JWT do navegador (Destrói o "crachá")
    localStorage.removeItem('token'); 

    // 2. Limpa os estados do React
    setIsAuthenticated(false);
    setCurrentPage('home');
    setTransactions([]); // Limpa as transações ao deslogar
  };

  // --- 3. ADICIONAR (POST) ---
const handleAddTransaction = async (newTransaction) => {
    // 1. Pegue o token onde você o salvou no momento do login (geralmente localStorage)
    // O nome da chave ('token', 'access_token') depende de como você salvou no login
    const token = localStorage.getItem('token'); 

    try {
      const response = await fetch(`${API_URL}/create_transactions`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          // 2. Adicione o token com a palavra "Bearer " antes dele
          'Authorization': `Bearer ${token}` 
        },
        body: JSON.stringify(newTransaction)
      });

      if (response.ok) {
        const savedTransaction = await response.json();
        setTransactions([...transactions, savedTransaction]);
      } else {
        const errorData = await response.text(); 
        console.error("Erro do servidor:", errorData);
      }
    } catch (error) {
      console.error("Erro ao adicionar:", error);
    }
  };

  // --- 4. DELETAR (DELETE) ---
const handleDeleteTransaction = async (id) => {
    if (window.confirm('Tem certeza que deseja deletar esta transação?')) {
      try {
        const token = localStorage.getItem('token');

        const response = await fetch(`${API_URL}/transactions/${id}`, {
          method: 'DELETE',
          headers: { 
            'Authorization': `Bearer ${token}` 
          }
        });

        if (response.ok) {
          setTransactions(transactions.filter((t) => t.id !== id));
        } else {
          const errorData = await response.text();
          console.error("Erro do servidor ao deletar:", errorData);
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