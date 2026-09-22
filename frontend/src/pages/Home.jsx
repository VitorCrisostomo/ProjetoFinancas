import React, { useState } from "react";
import { initialTransactions } from "../App";
import formatCurrency from "../utils/currency";
import Card from "../components/common/Card";
import { categoryIcons } from "../utils/category"

const HomePage = ({ transactions }) => {
  const totalIncome = transactions
    .filter((t) => t.type === 'income')
    .reduce((sum, t) => sum + t.amount, 0);

  const totalExpense = transactions
    .filter((t) => t.type === 'expense')
    .reduce((sum, t) => sum + t.amount, 0);

  const balance = totalIncome - totalExpense;
  const recentTransactions = transactions.slice(-5).reverse();

  return (
    <div className="page-content">
      <div className="page-header">
        <h1>Olá, Usuário! 👋</h1>
        <p>Bem-vindo ao seu gerenciador financeiro pessoal</p>
      </div>

      {/* Saldo em Destaque */}
      <div className="highlight-section">
        <div className="highlight-card">
          <span className="highlight-label">Saldo Disponível</span>
          <span className={`highlight-value ${balance >= 0 ? 'positive' : 'negative'}`}>
            {formatCurrency(balance)}
          </span>
        </div>
      </div>

      {/* Cards de Resumo */}
      <div className="cards-grid">
        <Card
          title="Saldo Atual"
          value={formatCurrency(balance)}
          icon="💳"
          color={balance >= 0 ? '#10b981' : '#ef4444'}
        />
        <Card
          title="Receitas"
          value={formatCurrency(totalIncome)}
          icon="📈"
          color="#10b981"
        />
        <Card
          title="Despesas"
          value={formatCurrency(totalExpense)}
          icon="📉"
          color="#ef4444"
        />
      </div>

      {/* Últimas Transações */}
      <div className="section">
        <h2>Últimas Transações</h2>
        <div className="transaction-quick-list">
          {recentTransactions.map((t) => (
            <div key={t.id} className="transaction-item">
              <div className="transaction-info">
                <span className="transaction-icon">
                  {categoryIcons[t.category] || '💸'}
                </span>
                <div className="transaction-details">
                  <span className="transaction-name">{t.name}</span>
                  <span className="transaction-category">{t.category}</span>
                </div>
              </div>
              <span className={`transaction-amount ${t.type}`}>
                {t.type === 'income' ? '+' : '-'} {formatCurrency(t.amount)}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Atalhos de Ação */}
      <div className="section">
        <h2>Ações Rápidas</h2>
        <div className="shortcuts">
          <div className="shortcut-card">
            <span className="shortcut-icon">➕</span>
            <span>Adicionar Transação</span>
          </div>
          <div className="shortcut-card">
            <span className="shortcut-icon">📊</span>
            <span>Ver Relatório</span>
          </div>
          <div className="shortcut-card">
            <span className="shortcut-icon">🎯</span>
            <span>Metas Financeiras</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default HomePage;
