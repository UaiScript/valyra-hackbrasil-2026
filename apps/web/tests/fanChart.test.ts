import { test } from 'node:test';
import assert from 'node:assert/strict';
import { fanGeometry } from '../src/app/fanChart.ts';

const band = (lo: string, mid: string, hi: string) => ({ p2_5: lo, p10: lo, p50: mid, p90: hi, p97_5: hi });

test('leque começa no último ponto observado e cobre toda a faixa no eixo', () => {
  const g = fanGeometry({
    history: [{ day: '2026-09-01', value: '4' }, { day: '2026-10-01', value: '4.5' }],
    fan: [{ day: '2026-11-01', band: band('3', '4.6', '6') }, { day: '2026-12-01', band: band('2.5', '4.7', '7') }],
  });
  assert.ok(g.min <= 2.5 && g.max >= 7);
  // A mediana e a faixa partem do mesmo ponto que encerra o histórico.
  const end = g.history.split('L').pop();
  assert.ok(g.median.startsWith(`M${end}`));
  assert.ok(g.band80.endsWith('Z') && g.ticks.length >= 3);
});

test('série constante não divide por zero', () => {
  const g = fanGeometry({ history: [{ day: '2026-10-01', value: '15' }], fan: [{ day: '2026-11-01', band: band('15', '15', '15') }] });
  assert.ok(Number.isFinite(g.nowX) && !g.history.includes('NaN') && !g.band95.includes('NaN'));
});
