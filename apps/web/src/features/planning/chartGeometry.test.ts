import { describe, expect, it } from 'vitest';
import { balanceChartGeometry } from './chartGeometry';
import { projectCommitments } from '../finance/calculations';
import business from '../../data/demo/business.json';

describe('representação dos compromissos no gráfico', () => {
  it('representa intervalos reais e muda o saldo apenas nos vencimentos', () => {
    const points = projectCommitments(1955000, business.commitments);
    const graph = balanceChartGeometry(1955000, points, '2026-11-05');
    expect(graph.coordinates[0].x).toBe(0);
    expect(graph.coordinates[1].x).toBeCloseTo(25);
    expect(graph.coordinates[2].x).toBeCloseTo(55);
    expect(graph.coordinates[3].x).toBe(100);
    expect(graph.path).not.toMatch(/[LCQS]/);
    expect(graph.path.match(/H /g)).toHaveLength(3);
    expect(graph.path.match(/V /g)).toHaveLength(3);
    expect(graph.ticks.some((tick) => tick.value === 0)).toBe(true);
  });

  it('mantém zero e saldo negativo dentro da escala', () => {
    const graph = balanceChartGeometry(
      10000,
      [
        {
          id: 'test',
          date: '2026-11-10',
          description: 'Teste',
          amountCents: 30000,
          balanceCents: -20000,
        },
      ],
      '2026-11-05',
    );
    expect(graph.coordinates.every((point) => point.y >= 0 && point.y <= 100)).toBe(true);
    expect(graph.ticks.some((tick) => tick.value === 0)).toBe(true);
    expect(Math.min(...graph.ticks.map((tick) => tick.value))).toBeLessThanOrEqual(-20000);
  });

  it('suporta saldo zero e ausência de compromissos sem divisão por zero', () => {
    const graph = balanceChartGeometry(0, [], '2026-11-05');
    expect(graph.coordinates).toHaveLength(1);
    expect(Number.isFinite(graph.coordinates[0].y)).toBe(true);
    expect(graph.path).not.toMatch(/NaN|Infinity/);
  });
});
