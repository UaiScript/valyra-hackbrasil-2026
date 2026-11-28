import { test } from 'node:test';
import assert from 'node:assert/strict';
import { projectionCandles } from '../src/app/candles.ts';

// Projeção sintética: começa em R$ 1.000,00 e cada dia muda o saldo pelo delta indicado.
function projection(start: string, deltas: number[], startBalance = 100000) {
  const items = [];
  let balance = startBalance;
  const d = new Date(`${start}T00:00:00Z`);
  for (const delta of deltas) {
    balance += delta;
    items.push({ date: d.toISOString().slice(0, 10), recurrences: [], recurring_cents: 0, variable_cents: delta, balance_cents: balance });
    d.setUTCDate(d.getUTCDate() + 1);
  }
  return {
    account_id: 'a', today: '2026-11-27', start_balance_cents: startBalance, variable_daily_cents: 0, days: deltas.length,
    min_balance_cents: Math.min(...items.map((i) => i.balance_cents)), min_balance_date: items[0]?.date ?? start, items,
  };
}

test('vela diária abre no fechamento do dia anterior', () => {
  const candles = projectionCandles(projection('2026-11-28', [-500, 2000, -100]), 'day');
  assert.equal(candles.length, 3);
  assert.deepEqual(candles[0], { start: '2026-11-28', end: '2026-11-28', open: 100000, close: 99500, high: 100000, low: 99500 });
  assert.equal(candles[1].open, 99500);
  assert.equal(candles[1].close, 101500);
  assert.equal(candles[2].open, 101500);
});

test('semana agrupa blocos de 7 dias e a última pode ser parcial', () => {
  const candles = projectionCandles(projection('2026-11-28', Array.from({ length: 10 }, () => -100)), 'week');
  assert.equal(candles.length, 2);
  assert.equal(candles[0].end, '2026-12-04');
  assert.equal(candles[0].close, 99300);
  assert.equal(candles[1].start, '2026-12-05');
  assert.equal(candles[1].close, 99000);
});

test('mês segue o calendário, com o primeiro mês parcial', () => {
  const candles = projectionCandles(projection('2026-11-28', Array.from({ length: 40 }, () => 0).map((_, i) => (i === 5 ? -3000 : 0))), 'month');
  assert.deepEqual(candles.map((c) => c.start), ['2026-11-28', '2026-12-01', '2027-01-01']);
  assert.equal(candles[0].end, '2026-11-30');
  // A queda de 03/12 aparece na vela de dezembro, com máxima e mínima corretas.
  assert.equal(candles[1].high, 100000);
  assert.equal(candles[1].low, 97000);
  assert.equal(candles[2].open, 97000);
});

test('máxima e mínima incluem a abertura', () => {
  const [c] = projectionCandles(projection('2026-11-28', [500, 500]), 'week');
  assert.equal(c.low, 100000);
  assert.equal(c.high, 101000);
});

test('projeção vazia não gera velas', () => {
  assert.deepEqual(projectionCandles(projection('2026-11-28', []), 'month'), []);
});
