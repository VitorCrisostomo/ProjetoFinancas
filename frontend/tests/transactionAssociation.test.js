import assert from 'node:assert/strict';
import test from 'node:test';
import { getAssociationData } from '../src/utils/transactionAssociation.js';

const transaction = (name, value, type = 'income') => ({ name, value, type, category: 'Extra', date: '2026-10-01T00:00:00' });

test('associa várias transações com soma de receitas e despesas e metadados da primeira', () => {
  assert.deepEqual(getAssociationData([
    transaction('Primeira', 100), transaction('Segunda', 40, 'expense'),
    transaction('Terceira', 20, 'expense'), transaction('Quarta', 10),
  ]), { name: 'Primeira / Segunda / Terceira / Quarta', value: 50, type: 'income', category: 'Extra', date: '2026-10-01' });
});

test('associação aceita saldo zero em centavos e resultado negativo', () => {
  const zero = getAssociationData([transaction('A', 0.1), transaction('B', 0.2), transaction('C', 0.3, 'expense')]);
  assert.equal(zero.value, 0);
  assert.equal(zero.type, 'income');
  const negative = getAssociationData([transaction('A', 0), transaction('B', 5, 'expense'), transaction('C', 2)]);
  assert.equal(negative.value, 3);
  assert.equal(negative.type, 'expense');
});

test('nome combinado respeita o tamanho do campo ao associar muitos lançamentos', () => {
  const result = getAssociationData(Array.from({ length: 10 }, () => transaction('Descrição extensa', 1)));
  assert.equal(result.name.length, 120);
  assert.equal(result.value, 10);
});
