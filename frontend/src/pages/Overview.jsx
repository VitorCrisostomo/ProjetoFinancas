import Card from "../components/common/Card";
import formatCurrency from "../utils/currency";
import { categoryIcons, categoryColors } from "../utils/category";

const OverviewPage = ({ transactions }) => {
  const totalIncome = transactions
    .filter((t) => t.type === 'income')
    .reduce((sum, t) => sum + t.value, 0); // Modificado para t.value

  const totalExpense = transactions
    .filter((t) => t.type === 'expense')
    .reduce((sum, t) => sum + t.value, 0); // Modificado para t.value

  const balance = totalIncome - totalExpense;

  // Distribuição por categoria
  const expensesByCategory = {};
  transactions
    .filter((t) => t.type === 'expense')
    .forEach((t) => {
      // Modificado para t.value
      expensesByCategory[t.category] = (expensesByCategory[t.category] || 0) + t.value; 
    });

  const maxExpense = Math.max(...Object.values(expensesByCategory), 1);

  return (
    <div className="page-content">
      <div className="page-header">
        <h1>Visão Geral Financeira</h1>
        <p>Análise detalhada do seu desempenho financeiro</p>
      </div>

      {/* Indicadores Principais */}
      <div className="cards-grid large">
        <Card
          title="Saldo Total"
          value={formatCurrency(balance)}
          icon="💰"
          color={balance >= 0 ? '#10b981' : '#ef4444'}
        />
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
                {formatCurrency(totalIncome)}
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
                {formatCurrency(totalExpense)}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Distribuição de Despesas por Categoria */}
      <div className="section">
        <h2>Distribuição de Despesas por Categoria</h2>
        <div className="category-breakdown">
          {Object.entries(expensesByCategory)
            .sort((a, b) => b[1] - a[1])
            .map(([category, value]) => (
              <div key={category} className="category-item">
                <div className="category-info">
                  <span className="category-icon">{categoryIcons[category] || '💸'}</span>
                  <span className="category-name">{category}</span>
                </div>
                <div className="category-bar-container">
                  <div
                    className="category-bar"
                    style={{
                      width: `${(value / maxExpense) * 100}%`,
                      backgroundColor: categoryColors[category] || '#6b7280',
                    }}
                  />
                </div>
                <span className="category-value">{formatCurrency(value)}</span>
              </div>
            ))}
        </div>
      </div>
    </div>
  );
};

export default OverviewPage;