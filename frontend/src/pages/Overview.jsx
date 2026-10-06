import { useId, useState } from 'react';
import { getOpeningBalance, getTransactionSummary } from '../utils/transactionSummary.js';
import useTransactionPeriod from '../hooks/useTransactionPeriod.js';
import TransactionPeriodFilter from '../components/common/TransactionPeriodFilter.jsx';
import Card from "../components/common/Card";
import formatCurrency from "../utils/currency";
import { categoryIcons, categoryColors } from "../utils/category";
import { getCategoryCatalog, getExpenseBreakdown } from '../utils/categoryCatalog.js';
import FinancialValue from '../components/common/FinancialValue.jsx';

const OverviewPage = ({ transactions, categoryCatalog = [] }) => {
  const period = useTransactionPeriod(transactions);
  const [selectedCategory, setSelectedCategory] = useState(null);
  const categoryFilterId = useId();
  const categories = getCategoryCatalog(categoryCatalog, transactions);
  const { totalIncome, totalExpense, balance } = getTransactionSummary(period.transactions);
  const openingBalance = getOpeningBalance(transactions, period.month, period.year);
  const totalBalance = (openingBalance ?? 0) + balance;
  const breakdown = getExpenseBreakdown(period.transactions, selectedCategory);
  const maxExpense = Math.max(...breakdown.map((item) => item.value), 1);

  return (
    <div className="page-content">
      <div className="page-header">
        <h1>Visão Geral Financeira</h1>
        <p>Análise detalhada do seu desempenho financeiro</p>
      </div>

      <div className="filters-section">
        <TransactionPeriodFilter period={period} />
        <div className="filter-group">
          <label htmlFor={categoryFilterId}>Categoria</label>
          <select id={categoryFilterId} className="filter-select" value={selectedCategory || ''}
            onChange={(event) => setSelectedCategory(event.target.value || null)}>
            <option value="">Todas as categorias</option>
            {categories.map((category) => <option key={category.name} value={category.name}>{category.name}</option>)}
          </select>
        </div>
      </div>
      {period.transactions.length === 0 && (
        <p role="status">Nenhuma transação encontrada no período selecionado.</p>
      )}

      {/* Indicadores Principais */}
      <div className="cards-grid large">
        <Card
          title={openingBalance !== null ? 'Saldo acumulado' : period.isFiltered ? 'Saldo do período' : 'Saldo Total'}
          value={formatCurrency(totalBalance)}
          icon="💰"
          color={totalBalance >= 0 ? '#10b981' : '#ef4444'}
        >
          {openingBalance !== null ? <>
            <p className="transactions-balance-description">
              Saldo anterior: <FinancialValue>{formatCurrency(openingBalance)}</FinancialValue>
            </p>
            <p className="transactions-balance-description">
              Movimentações do período: <FinancialValue>{formatCurrency(balance)}</FinancialValue>
            </p>
            <p className="transactions-balance-description">
              Inclui todo o histórico antes do início do período selecionado.
            </p>
          </> : period.month !== 'all' && <p className="transactions-balance-description">
            Selecione também o ano para incluir o saldo anterior.
          </p>}
        </Card>
        <Card
          title="Total de Receitas"
          value={formatCurrency(totalIncome)}
          icon="📈"
          color="#10b981"
        />
        <Card
          title="Total de Despesas"
          value={formatCurrency(totalExpense)}
          icon="📉"
          color="#ef4444"
        />
        <Card
          title="Taxa de Economia"
          value={`${totalIncome > 0 ? Math.round((balance / totalIncome) * 100) : 0}%`}
          icon="🎯"
          color="#3b82f6"
        />
      </div>

      {/* Gráfico de Receitas vs Despesas */}
      <div className="section">
        <h2>Receitas vs Despesas</h2>
        <div className="chart-container">
          <div className="chart-bar">
            <div className="chart-label">Receitas</div>
            <div className="chart-bar-bg">
              <div
                className="chart-bar-fill income"
                style={{ width: `${(totalIncome / (totalIncome + totalExpense + 100)) * 100}%` }}
              >
                <FinancialValue>{formatCurrency(totalIncome)}</FinancialValue>
              </div>
            </div>
          </div>
          <div className="chart-bar">
            <div className="chart-label">Despesas</div>
            <div className="chart-bar-bg">
              <div
                className="chart-bar-fill expense"
                style={{ width: `${(totalExpense / (totalIncome + totalExpense + 100)) * 100}%` }}
              >
                <FinancialValue>{formatCurrency(totalExpense)}</FinancialValue>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Distribuição de Despesas por Categoria */}
      <div className="section">
        <h2>{selectedCategory ? `Despesas de ${selectedCategory} por subcategoria` : 'Distribuição de Despesas por Categoria'}</h2>
        <p className="category-chart-description">
          O filtro de categoria detalha este gráfico. Os indicadores mostram todo o período.
        </p>
        {breakdown.length === 0 && <p className="empty-state">Nenhuma despesa encontrada para este filtro.</p>}
        <div className="category-breakdown">
          {breakdown.map(({ name: category, value }) => (
              <div key={category} className="category-item">
                <div className="category-info">
                  <span className="category-icon">{categoryIcons[selectedCategory || category] || '🏷️'}</span>
                  <span className="category-name">{category}</span>
                </div>
                <div className="category-bar-container">
                  <div
                    className="category-bar"
                    style={{
                      width: `${(value / maxExpense) * 100}%`,
                      backgroundColor: categoryColors[selectedCategory || category] || '#6b7280',
                    }}
                  />
                </div>
                <span className="category-value"><FinancialValue>{formatCurrency(value)}</FinancialValue></span>
              </div>
            ))}
        </div>
      </div>
    </div>
  );
};

export default OverviewPage;
