import assert from 'node:assert/strict';
import test from 'node:test';
import { filterTransactionsByPeriod, getTransactionDateParts, getTransactionYears, normalizeTransactionPeriod } from '../src/utils/transactionPeriod.js';
import { getTransactionSummary } from '../src/utils/transactionSummary.js';

const transactions = [
  { id: 1, date: '2025-10-01T00:00:00', type: 'income', value: 50 },
  { id: 2, date: '2026-04-14T00:00:00', type: 'income', value: 100 },
  { id: 3, date: '2026-10-01T03:00:00Z', type: 'income', value: 200 },
  { id: 4, date: '2026-10-31T23:59:59-03:00', type: 'expense', value: 30, category: 'Extra' },
  { id: 5, date: '2026-11-01', type: 'expense', value: 10, category: 'Extra' },
];
const ids = (items) => items.map((item) => item.id);

test('filtra por mês e ano, mês com ano atual automático, só por ano e todo o histórico', () => {
  assert.deepEqual(ids(filterTransactionsByPeriod(transactions, '10', '2026')), [3, 4]);
  assert.deepEqual(ids(filterTransactionsByPeriod(transactions, '10', 'all', new Date('2026-10-01T12:00:00Z'))), [3, 4]);
  assert.deepEqual(ids(filterTransactionsByPeriod(transactions, 'all', '2026')), [2, 3, 4, 5]);
  assert.deepEqual(ids(filterTransactionsByPeriod(transactions)), [1, 2, 3, 4, 5]);
});

test('mês exige um ano, preserva o ano escolhido e usa o ano de São Paulo nas fronteiras', () => {
  const now = new Date('2026-01-01T01:00:00Z');
  assert.deepEqual(normalizeTransactionPeriod('9', 'all', now), { month: '9', year: '2025' });
  assert.deepEqual(normalizeTransactionPeriod('9', '2024', now), { month: '9', year: '2024' });
  assert.deepEqual(normalizeTransactionPeriod('all', '2024', now), { month: 'all', year: '2024' });
  assert.deepEqual(normalizeTransactionPeriod('all', 'all', now), { month: 'all', year: 'all' });
});

test('Overview calcula receitas, despesas, saldo e categorias somente do período', () => {
  const summary = getTransactionSummary(filterTransactionsByPeriod(transactions, '10', '2026'));
  assert.equal(summary.totalIncome, 200);
  assert.equal(summary.totalExpense, 30);
  assert.equal(summary.balance, 170);
  assert.deepEqual(summary.expensesByCategory, { Extra: 30 });
  assert.equal(getTransactionSummary(transactions).balance, 310);
});

test('período vazio retorna indicadores zerados e anos vêm do histórico completo', () => {
  assert.deepEqual(getTransactionYears(transactions), [2026, 2025]);
  assert.deepEqual(getTransactionYears([]), []);
  const filtered = filterTransactionsByPeriod(transactions, '1', '2026');
  assert.deepEqual(filtered, []);
  assert.equal(getTransactionSummary(filtered).balance, 0);
});

test('datas preservam mês e dia do lançamento nas fronteiras de fuso e ano', () => {
  assert.deepEqual(getTransactionDateParts('2026-10-01'), { year: 2026, month: 10, day: 1 });
  assert.deepEqual(getTransactionDateParts('2026-12-31T23:59:59-03:00'), { year: 2026, month: 12, day: 31 });
  assert.deepEqual(getTransactionDateParts('2026-01-01 00:00:00.000000'), { year: 2026, month: 1, day: 1 });
  assert.deepEqual(getTransactionDateParts('2024-02-29'), { year: 2024, month: 2, day: 29 });
});

test('datas inválidas não entram em períodos específicos nem nos anos disponíveis', () => {
  const invalid = [null, '', 'invalid', '2026-13-01', '2026-02-29', '2026-04-31'];
  invalid.forEach((date) => assert.equal(getTransactionDateParts(date), null));
  const records = invalid.map((date) => ({ date }));
  assert.deepEqual(filterTransactionsByPeriod(records, 'all', '2026'), []);
  assert.deepEqual(getTransactionYears(records), []);
});

test('resumo do período inclui registros além do limite visual de 50 linhas', () => {
  const records = Array.from({ length: 60 }, (_, id) => ({ id, date: '2026-10-01', type: 'income', value: 1 }));
  assert.equal(getTransactionSummary(filterTransactionsByPeriod(records, '10', '2026')).totalIncome, 60);
});
