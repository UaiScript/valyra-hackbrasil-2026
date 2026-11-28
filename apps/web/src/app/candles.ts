import type { ProjectionOut } from '../lib/api/schema';

/*
 * Agrupamento da projeção diária em velas, separado do desenho para ser testado sem React.
 * Só reorganiza centavos inteiros vindos da API: nenhum valor novo é calculado aqui.
 */

export type Candle = { start: string; end: string; open: number; close: number; high: number; low: number };

/** Período de cada vela: um dia, uma semana (blocos de 7 dias) ou um mês do calendário. */
export type CandlePeriod = 'day' | 'week' | 'month';

export const CANDLE_PERIODS: Record<CandlePeriod, { label: string; title: string; days: number; up: string; down: string }> = {
  // Horizonte pedido à API por período: duas semanas de velas diárias, cinco semanas de velas
  // semanais e, no mês, o máximo da API (90 dias), que cobre três ou quatro meses do calendário.
  day: { label: 'Dia', title: 'Projeção diária', days: 14, up: 'dia em alta', down: 'dia em queda' },
  week: { label: 'Semana', title: 'Projeção semanal', days: 35, up: 'semana em alta', down: 'semana em queda' },
  month: { label: 'Mês', title: 'Projeção mensal', days: 90, up: 'mês em alta', down: 'mês em queda' },
};

/** Chave do grupo de cada dia da projeção, conforme o período escolhido. */
function groupKey(period: CandlePeriod, date: string, index: number): string {
  if (period === 'day') return date;
  if (period === 'month') return date.slice(0, 7);
  return String(Math.floor(index / 7));
}

/** Agrupa a projeção diária em velas (abertura, fechamento, máxima, mínima) por período. */
export function projectionCandles(p: ProjectionOut, period: CandlePeriod = 'week'): Candle[] {
  const groups: ProjectionOut['items'][] = [];
  let last = '';
  p.items.forEach((d, i) => {
    const key = groupKey(period, d.date, i);
    if (key !== last || groups.length === 0) groups.push([]);
    groups[groups.length - 1].push(d);
    last = key;
  });
  const out: Candle[] = [];
  let open = p.start_balance_cents;
  for (const group of groups) {
    const balances = group.map((d) => d.balance_cents);
    const close = balances[balances.length - 1];
    out.push({ start: group[0].date, end: group[group.length - 1].date, open, close, high: Math.max(open, ...balances), low: Math.min(open, ...balances) });
    open = close;
  }
  return out;
}
