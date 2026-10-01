import assert from 'node:assert/strict';
import test from 'node:test';
import { groupTransactionsByDate, sortTransactionsByDate } from '../src/utils/transactionList.js';

const records = [
  { id: 1, date: '2025-09-13' },
  { id: 2, date: '2026-09-13T23:59:59-03:00' },
  { id: 3, date: '2026-09-14T00:00:00Z' },
  { id: 4, date: '2026-09-13T00:00:00Z' },
  { id: 5, date: '2026-10-01' },
];

test('ordena da data mais recente à mais antiga sem alterar os dados originais', () => {
  assert.deepEqual(sortTransactionsByDate(records).map((record) => record.id), [5, 3, 4, 2, 1]);
  assert.deepEqual(records.map((record) => record.id), [1, 2, 3, 4, 5]);
});

test('agrupa por dia de calendário e distingue anos sem converter o fuso', () => {
  const groups = groupTransactionsByDate(records);
  assert.deepEqual(groups.map((group) => group.label), [
    '1 de outubro de 2026', '14 de setembro de 2026', '13 de setembro de 2026', '13 de setembro de 2025',
  ]);
  assert.deepEqual(groups[2].transactions.map((record) => record.id), [4, 2]);
});

test('o limite aplicado após ordenar mantém as 50 transações mais recentes', () => {
  const history = Array.from({ length: 60 }, (_, index) => ({
    id: index + 1, date: `2026-${index < 30 ? '09' : '10'}-${String(index % 30 + 1).padStart(2, '0')}`,
  }));
  const displayed = sortTransactionsByDate(history).slice(0, 50);
  assert.equal(displayed[0].date, '2026-10-30');
  assert.equal(displayed.at(-1).date, '2026-09-11');
});

test('datas ausentes ou inválidas ficam no último grupo e listas vazias são suportadas', () => {
  const groups = groupTransactionsByDate([{ id: 1, date: null }, { id: 2, date: 'invalid' }, ...records]);
  assert.equal(groups.at(-1).label, 'Data não informada');
  assert.equal(groups.at(-1).transactions.length, 2);
  assert.deepEqual(groupTransactionsByDate([]), []);
});
