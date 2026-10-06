import { getOpeningBalance, getTransactionSummary } from '../utils/transactionSummary.js';
import useTransactionPeriod from '../hooks/useTransactionPeriod.js';
import TransactionPeriodFilter from '../components/common/TransactionPeriodFilter.jsx';
import { sortTransactionsByDate } from '../utils/transactionList.js';
import formatCurrency from "../utils/currency";
import Card from "../components/common/Card";
import { categoryIcons } from "../utils/category";
import FinancialValue from '../components/common/FinancialValue.jsx';

const HomePage = ({ transactions }) => {
  const period = useTransactionPeriod(transactions);
  const { totalIncome, totalExpense, balance: periodBalance } = getTransactionSummary(period.transactions);
  const openingBalance = getOpeningBalance(transactions, period.month, period.year);
  const balance = (openingBalance ?? 0) + periodBalance;
  const recentTransactions = sortTransactionsByDate(period.transactions).slice(0, 5);

  return (
    <div className="page-content">
      <div className="page-header">
        <h1>Olá, Usuário! 👋</h1>
        <p>Bem-vindo ao seu gerenciador financeiro pessoal</p>
      </div>

      <div className="filters-section"><TransactionPeriodFilter period={period} /></div>

      {/* Saldo em Destaque */}
      <div className="highlight-section">
        <div className="highlight-card">
          <span className="highlight-label">Saldo acumulado</span>
          <span className={`highlight-value ${balance >= 0 ? 'positive' : 'negative'}`}>
            <FinancialValue>{formatCurrency(balance)}</FinancialValue>
          </span>
          {openingBalance !== null && <p className="transactions-balance-description">
            Saldo anterior: <FinancialValue>{formatCurrency(openingBalance)}</FinancialValue> · Movimentações do período: <FinancialValue>{formatCurrency(periodBalance)}</FinancialValue>
          </p>}
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
                  <span className="transaction-category">{t.category}{t.subcategory && ` › ${t.subcategory}`}</span>
                </div>
              </div>
              <span className={`transaction-value ${t.type}`}>
                <FinancialValue>{t.type === 'income' ? '+' : '-'} {formatCurrency(t.value)}</FinancialValue>
              </span>
            </div>
          ))}
        </div>
        {recentTransactions.length === 0 && <p className="empty-state">Nenhuma transação neste período.</p>}
      </div>

      {/* Atalhos de Ação */}
      <div className="section">
        <h2>Ações Rápidas</h2>
        <div className="shortcuts">
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
