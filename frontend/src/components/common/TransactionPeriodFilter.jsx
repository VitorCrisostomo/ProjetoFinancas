import { useId } from 'react';
import { months } from '../../utils/transactionPeriod.js';
import Button from './Button.jsx';

export default function TransactionPeriodFilter({ period, onChange }) {
  const id = useId();
  return (
    <>
      <div className="filter-group">
        <label htmlFor={`${id}-month`}>Mês</label>
        <select id={`${id}-month`} className="filter-select" value={period.month}
          onChange={(event) => { period.setMonth(event.target.value); onChange?.(); }}>
          <option value="all">Todos os meses</option>
          {months.map((month, index) => <option key={month} value={index + 1}>{month}</option>)}
        </select>
      </div>
      <div className="filter-group">
        <label htmlFor={`${id}-year`}>Ano</label>
        <select id={`${id}-year`} className="filter-select" value={period.year}
          onChange={(event) => { period.setYear(event.target.value); onChange?.(); }}>
          {period.month === 'all' && <option value="all">Todos os anos</option>}
          {period.years.map((year) => <option key={year} value={year}>{year}</option>)}
        </select>
      </div>
      <div className="period-reset">
        <Button variant="secondary" disabled={!period.isFiltered}
          onClick={() => { period.resetPeriod(); onChange?.(); }}>Limpar período</Button>
      </div>
    </>
  );
}
