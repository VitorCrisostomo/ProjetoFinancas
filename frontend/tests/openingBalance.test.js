import assert from 'node:assert/strict';
import test from 'node:test';
import { getOpeningBalance, getTransactionSummary } from '../src/utils/transactionSummary.js';
import { filterTransactionsByPeriod } from '../src/utils/transactionPeriod.js';

const transactions = [
  { date: '2025-12-31', type: 'income', value: 1000, category: 'Extra' },
  { date: '2026-01-01', type: 'expense', value: 200, category: 'Casa' },
  { date: '2026-03-31T23:59:59-03:00', type: 'expense', value: 100, category: 'Casa' },
  { date: '2026-04-01', type: 'income', value: 300, category: 'Extra' },
  { date: '2026-04-30', type: 'expense', value: 50, category: 'Casa' },
  { date: '2026-05-01', type: 'income', value: 900, category: 'Extra' },
];

test('saldo anterior acumula todo o histórico e exclui o mês selecionado e meses futuros', () => {
  const opening = getOpeningBalance(transactions, '4', '2026');
  assert.equal(opening, 700);
  const movements = getTransactionSummary(filterTransactionsByPeriod(transactions, '4', '2026')).balance;
  assert.equal(opening + movements, 950);
  const expenses = filterTransactionsByPeriod(transactions, '4', '2026')
    .filter((transaction) => transaction.category === 'Casa' && transaction.type === 'expense');
  assert.equal(opening + getTransactionSummary(expenses).balance, 650);
});

test('janeiro e filtro anual carregam o saldo do ano anterior', () => {
  assert.equal(getOpeningBalance(transactions, '1', '2026'), 1000);
  assert.equal(getOpeningBalance(transactions, 'all', '2026'), 1000);
});

test('sem ano não há saldo anterior único; histórico vazio e negativo são preservados', () => {
  assert.equal(getOpeningBalance(transactions, '4', 'all'), null);
  assert.equal(getOpeningBalance(transactions), null);
  assert.equal(getOpeningBalance([], '4', '2026'), 0);
  assert.equal(getOpeningBalance([
    { date: '2026-03-01', type: 'expense', value: 50 },
    { date: 'inválida', type: 'income', value: 100 },
  ], '4', '2026'), -50);
});
