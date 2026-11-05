import type { Commitment } from '../../shared/types/domain';

export interface BalancePoint extends Commitment {
  balanceCents: number;
}

// Dias civis em UTC impedem que fuso/horário de verão distorçam a distância entre vencimentos.
const day = (iso: string) => Date.parse(`${iso}T00:00:00Z`) / 86_400_000;

/** Só organiza a apresentação: os saldos já vêm calculados por projectCommitments. */
export function balanceChartGeometry(
  initialCents: number,
  points: BalancePoint[],
  referenceDate: string,
) {
  const balances = [initialCents, ...points.map((item) => item.balanceCents)];
  const minimum = Math.min(0, ...balances);
  const maximum = Math.max(0, ...balances);
  const rawStep = Math.max((maximum - minimum) / 3, 1);
  const magnitude = 10 ** Math.floor(Math.log10(rawStep));
  const step = [1, 2, 5, 10].map((value) => value * magnitude).find((value) => value >= rawStep)!;
  const lower = Math.floor(minimum / step) * step;
  const upper = Math.max(lower + step, Math.ceil(maximum / step) * step);
  const duration = Math.max(1, day(points.at(-1)?.date ?? referenceDate) - day(referenceDate));
  const y = (cents: number) => ((upper - cents) / (upper - lower)) * 100;
  const coordinates = [
    { x: 0, y: y(initialCents) },
    ...points.map((item) => ({
      x: ((day(item.date) - day(referenceDate)) / duration) * 100,
      y: y(item.balanceCents),
    })),
  ];
  // H mantém o saldo até o vencimento e V aplica a saída naquele dia: não há interpolação/previsão.
  const path = coordinates
    .map((point, index) => (index === 0 ? `M ${point.x} ${point.y}` : `H ${point.x} V ${point.y}`))
    .join(' ');
  const ticks = Array.from(
    { length: Math.round((upper - lower) / step) + 1 },
    (_, index) => upper - index * step,
  );
  return { coordinates, path, ticks: ticks.map((value) => ({ value, y: y(value) })) };
}
