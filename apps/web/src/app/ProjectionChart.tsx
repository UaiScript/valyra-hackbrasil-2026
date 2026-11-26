import { useEffect, useId, useMemo, useRef, useState } from 'react';
import type { FC, PointerEvent } from 'react';
import type { ProjectionOut } from '../lib/api/schema';
import { formatCents, formatShortDate } from './money';

// Os valores chegam em centavos inteiros. Converter para pixels usa ponto flutuante,
// mas só para desenhar: nenhum número exibido sai dessa conta (rótulos usam formatCents).
// O SVG usa a largura real do contêiner (e não um viewBox esticado) para que textos
// e traços mantenham o mesmo tamanho em qualquer tela.
function useWidth<T extends HTMLElement>(fallback: number) {
  const ref = useRef<T>(null);
  const [width, setWidth] = useState(fallback);
  useEffect(() => {
    const el = ref.current;
    if (!el || typeof ResizeObserver === 'undefined') return;
    const observer = new ResizeObserver(([entry]) => setWidth(Math.max(240, Math.round(entry.contentRect.width))));
    observer.observe(el);
    return () => observer.disconnect();
  }, []);
  return [ref, width] as const;
}
const PAD = { top: 20, right: 16, bottom: 28, left: 76 };

/** Passo "redondo" em centavos para as linhas de grade: 1, 2 ou 5 × 10^n reais. */
function niceStep(rangeCents: number, maxTicks: number): number {
  for (let magnitude = 100; ; magnitude *= 10) {
    for (const m of [1, 2, 5]) {
      const step = m * magnitude;
      if (rangeCents / step <= maxTicks) return step;
    }
  }
}

/** Rótulo de eixo sem centavos: ticks são múltiplos de R$ 1, então ",00" é exato. */
const axisLabel = (cents: number) => formatCents(cents).replace(/,00$/, '');

type Point = { date: string; balance: number; variable: number; recurrences: ProjectionOut['items'][number]['recurrences'] };

export const ProjectionChart: FC<{ projection: ProjectionOut; height?: number; compact?: boolean }> = ({ projection, height = 280, compact = false }) => {
  const gradientId = useId();
  const [figureRef, W] = useWidth<HTMLElement>(720);
  const [hover, setHover] = useState<number | null>(null);

  const points: Point[] = useMemo(() => [
    { date: projection.today, balance: projection.start_balance_cents, variable: 0, recurrences: [] },
    ...projection.items.map((d) => ({ date: d.date, balance: d.balance_cents, variable: d.variable_cents, recurrences: d.recurrences })),
  ], [projection]);

  const pad = compact ? { top: 10, right: 6, bottom: 10, left: 6 } : PAD;
  const balances = points.map((p) => p.balance);
  const rawMin = Math.min(0, ...balances);
  const rawMax = Math.max(...balances);
  const step = niceStep(Math.max(rawMax - rawMin, 100), compact ? 3 : 4);
  const lo = Math.floor(rawMin / step) * step;
  const hi = Math.ceil(rawMax / step) * step + (rawMax % step === 0 ? step : 0);

  const innerW = W - pad.left - pad.right;
  const innerH = height - pad.top - pad.bottom;
  const x = (i: number) => pad.left + (innerW * i) / Math.max(points.length - 1, 1);
  const y = (cents: number) => pad.top + innerH * (1 - (cents - lo) / (hi - lo));

  const line = points.map((p, i) => `${i === 0 ? 'M' : 'L'}${x(i).toFixed(1)},${y(p.balance).toFixed(1)}`).join('');
  const zeroY = y(0);
  const area = `${line}L${x(points.length - 1).toFixed(1)},${zeroY.toFixed(1)}L${x(0).toFixed(1)},${zeroY.toFixed(1)}Z`;
  const ticks: number[] = [];
  for (let t = lo; t <= hi; t += step) ticks.push(t);

  const minIndex = points.findIndex((p, i) => i > 0 && p.date === projection.min_balance_date);
  const goesNegative = projection.min_balance_cents < 0;

  function onPointer(event: PointerEvent<SVGSVGElement>) {
    const rect = event.currentTarget.getBoundingClientRect();
    const px = ((event.clientX - rect.left) / rect.width) * W;
    const i = Math.round(((px - pad.left) / innerW) * (points.length - 1));
    setHover(Math.min(points.length - 1, Math.max(0, i)));
  }

  const active = hover !== null ? points[hover] : null;
  const summary = `Projeção de ${projection.days} dias: começa em ${formatCents(projection.start_balance_cents)} hoje e chega ao menor saldo, ${formatCents(projection.min_balance_cents)}, em ${formatShortDate(projection.min_balance_date)}.`;

  return (
    <figure ref={figureRef} className={`vx-chart${compact ? ' vx-chart--compact' : ''}${goesNegative ? ' vx-chart--negative' : ''}`}>
      <svg
        viewBox={`0 0 ${W} ${height}`}
        role="img"
        aria-label={summary}
        onPointerMove={compact ? undefined : onPointer}
        onPointerLeave={() => setHover(null)}
      >
        <defs>
          <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" className="vx-chart__fill-top" />
            <stop offset="100%" className="vx-chart__fill-bottom" />
          </linearGradient>
        </defs>

        {!compact && ticks.map((t) => (
          <g key={t} className={t === 0 ? 'vx-chart__zero' : 'vx-chart__grid'}>
            <line x1={pad.left} x2={W - pad.right} y1={y(t)} y2={y(t)} />
            <text x={pad.left - 10} y={y(t)} dy="0.32em" textAnchor="end">{axisLabel(t)}</text>
          </g>
        ))}
        {compact && lo < 0 && <line className="vx-chart__zero" x1={pad.left} x2={W - pad.right} y1={zeroY} y2={zeroY} />}

        <path d={area} fill={`url(#${gradientId})`} />
        <path d={line} className="vx-chart__line" />

        {!compact && points.map((p, i) => p.recurrences.length > 0 && (
          <g key={p.date} className={`vx-chart__event${p.recurrences.some((r) => r.amount_cents > 0) ? ' vx-chart__event--in' : ''}`}>
            <line x1={x(i)} x2={x(i)} y1={y(p.balance) + 6} y2={height - pad.bottom} />
            <circle cx={x(i)} cy={y(p.balance)} r={4} />
          </g>
        ))}

        <circle className="vx-chart__today" cx={x(0)} cy={y(points[0].balance)} r={5} />
        {minIndex > 0 && (
          <g className="vx-chart__min">
            <circle cx={x(minIndex)} cy={y(points[minIndex].balance)} r={compact ? 4 : 6} />
            {!compact && (
              <text x={x(minIndex)} y={y(points[minIndex].balance)} dy={y(points[minIndex].balance) > height - pad.bottom - 24 ? -14 : 22} textAnchor={minIndex > points.length * 0.8 ? 'end' : 'middle'}>
                Menor saldo: {formatCents(points[minIndex].balance)}
              </text>
            )}
          </g>
        )}

        {!compact && (
          <g className="vx-chart__axis">
            <text x={x(0)} y={height - 8}>Hoje</text>
            <text x={W - pad.right} y={height - 8} textAnchor="end">{formatShortDate(points[points.length - 1].date)}</text>
          </g>
        )}

        {active && hover !== null && (
          <g className="vx-chart__cursor" pointerEvents="none">
            <line x1={x(hover)} x2={x(hover)} y1={pad.top} y2={height - pad.bottom} />
            <circle cx={x(hover)} cy={y(active.balance)} r={5} />
          </g>
        )}
      </svg>

      {active && hover !== null && (
        <div className="vx-chart__tip" style={{ left: `${(x(hover) / W) * 100}%` }} role="status">
          <strong>{hover === 0 ? 'Hoje' : formatShortDate(active.date)}</strong>
          <span className="vx-chart__tip-balance">{formatCents(active.balance)}</span>
          {active.recurrences.map((r) => (
            <span key={r.description} className="vx-chart__tip-row">{r.description}<em>{formatCents(r.amount_cents)}</em></span>
          ))}
          {hover > 0 && <span className="vx-chart__tip-row vx-chart__tip-row--muted">Gasto variável<em>{formatCents(active.variable)}</em></span>}
        </div>
      )}
    </figure>
  );
};
