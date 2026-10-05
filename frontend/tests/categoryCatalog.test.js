import assert from 'node:assert/strict';
import test from 'node:test';
import { getCategoryCatalog, getExpenseBreakdown } from '../src/utils/categoryCatalog.js';
import { filterTransactionsByPeriod } from '../src/utils/transactionPeriod.js';

const transactions = [
  { category: 'Viagens', subcategory: 'Hospedagem', type: 'expense', value: 100, date: '2026-10-01' },
  { category: 'Viagens', subcategory: 'Hospedagem', type: 'expense', value: 50, date: '2026-10-02' },
  { category: 'Viagens', subcategory: 'Passagens', type: 'expense', value: 60, date: '2026-10-03' },
  { category: 'Viagens', type: 'expense', value: 10, date: '2026-10-04' },
  { category: 'Viagens', type: 'income', value: 500, date: '2026-10-04' },
  { category: 'Alimentação', type: 'expense', value: 30, date: '2026-10-04' },
  { category: 'Viagens', subcategory: 'Hospedagem', type: 'expense', value: 999, date: '2026-09-01' },
  { category: 'Saldo anterior', type: 'expense', value: 9999, date: '2026-10-01', is_opening_balance: true },
];

test('gráfico mantém categorias ou detalha apenas subcategorias da categoria e do período escolhidos', () => {
  const period = filterTransactionsByPeriod(transactions, '10', '2026');
  assert.deepEqual(getExpenseBreakdown(period), [{ name: 'Viagens', value: 220 }, { name: 'Alimentação', value: 30 }]);
  assert.deepEqual(getExpenseBreakdown(period, 'Viagens'), [
    { name: 'Hospedagem', value: 150 }, { name: 'Passagens', value: 60 }, { name: 'Sem subcategoria', value: 10 },
  ]);
  assert.deepEqual(getExpenseBreakdown(period, 'Sem lançamentos'), []);
});

test('catálogo inclui categorias novas e históricas, preservando a origem e sem duplicar subcategorias', () => {
  const categories = [{ id: 1, name: 'Viagens', subcategories: [{ id: 1, name: 'Hospedagem' }] }];
  const catalog = getCategoryCatalog(categories, transactions);
  assert.deepEqual(catalog.map((category) => category.name), ['Alimentação', 'Viagens']);
  assert.deepEqual(catalog[1].subcategories.map((sub) => sub.name), ['Hospedagem', 'Passagens']);
  assert.equal(categories[0].subcategories.length, 1);
});

test('gráfico usa centavos e aceita nomes que também são chaves de objetos', () => {
  const period = ['__proto__', 'all'].flatMap((category) => [
    { category, type: 'expense', value: 0.1 }, { category, type: 'expense', value: 0.2 },
  ]);
  assert.equal(getExpenseBreakdown(period, 'all')[0].value, 0.3);
  assert.equal(getExpenseBreakdown(period).length, 2);
});
