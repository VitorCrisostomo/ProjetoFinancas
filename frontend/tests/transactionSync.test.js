import assert from 'node:assert/strict';
import test from 'node:test';
import { getDefaultSyncMonth, getSyncOptions } from '../src/utils/transactionSync.js';

test('sincronização exige um mês e ano explícitos', () => {
  assert.throws(() => getSyncOptions(), /válidos/);
  assert.throws(() => getSyncOptions('all'), /válidos/);
});

test('mês específico envia mês e ano como números', () => {
  assert.deepEqual(getSyncOptions('2024-02'), { mode: 'month', year: 2024, month: 2 });
  for (const value of ['', '2026-00', '2026-13', '1899-12', '2026-1']) {
    assert.throws(() => getSyncOptions(value), /válidos/);
  }
});

test('preenche o mês com o filtro ou com a data atual de São Paulo', () => {
  const boundary = new Date('2026-11-01T01:00:00Z');
  assert.equal(getDefaultSyncMonth({ month: 'all', year: 'all' }, boundary), '2026-10');
  assert.equal(getDefaultSyncMonth({ month: '2', year: '2024' }, boundary), '2024-02');
});
