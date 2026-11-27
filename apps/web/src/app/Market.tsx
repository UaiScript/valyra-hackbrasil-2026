import { useMemo } from 'react';
import type { FC } from 'react';
import type { ProjectionOut } from '../lib/api/schema';
import { formatCents, formatShortDate } from './money';

/*
 * Peças visuais de "mercado" da Central: candles e sparkline (a faixa do topo fica em
 * TickerBar.tsx). Todos os valores exibidos chegam prontos da API em centavos; a conversão
 * para pixels usa ponto flutuante só para desenhar, nunca para um número mostrado.
 */

type Candle = { start: string; end: string; open: number; close: number; high: number; low: number };

/** Agrupa a projeção diária em velas semanais (abertura, fechamento, máxima, mínima). */
export function weeklyCandles(p: ProjectionOut): Candle[] {
  const out: Candle[] = [];
  let open = p.start_balance_cents;
  for (let i = 0; i < p.items.length; i += 7) {
    const week = p.items.slice(i, i + 7);
    const balances = week.map((d) => d.balance_cents);
    const close = balances[balances.length - 1];
    out.push({ start: week[0].date, end: week[week.length - 1].date, open, close, high: Math.max(open, ...balances), low: Math.min(open, ...balances) });
    open = close;
  }
  return out;
}

export const CandleChart: FC<{ projection: ProjectionOut; height?: number }> = ({ projection, height = 220 }) => {
  const candles = useMemo(() => weeklyCandles(projection), [projection]);
  const W = 640;
  const pad = { top: 16, right: 12, bottom: 30, left: 12 };
  const lo = Math.min(0, ...candles.map((c) => c.low));
  const hi = Math.max(...candles.map((c) => c.high));
  const span = Math.max(hi - lo, 100);
  const innerW = W - pad.left - pad.right;
  const innerH = height - pad.top - pad.bottom;
  const y = (v: number) => pad.top + innerH * (1 - (v - lo) / span);
  const slot = innerW / Math.max(candles.length, 1);
  const body = Math.min(46, slot * 0.42);
  return (
    <figure className="cx-candles">
      <svg viewBox={`0 0 ${W} ${height}`} role="img" aria-label={`Projeção em velas semanais: ${candles.map((c) => `${formatShortDate(c.start)} a ${formatShortDate(c.end)}, de ${formatCents(c.open)} para ${formatCents(c.close)}`).join('; ')}`}>
        {lo < 0 && <line className="cx-candles__zero" x1={pad.left} x2={W - pad.right} y1={y(0)} y2={y(0)} />}
        {candles.map((c, i) => {
          const cx = pad.left + slot * (i + 0.5);
          const up = c.close >= c.open;
          const top = y(Math.max(c.open, c.close));
          const h = Math.max(2, Math.abs(y(c.open) - y(c.close)));
          return (
            <g key={c.start} className={up ? 'cx-candle cx-candle--up' : 'cx-candle cx-candle--down'} style={{ animationDelay: `${i * 90}ms` }}>
              <line x1={cx} x2={cx} y1={y(c.high)} y2={y(c.low)} />
              <rect x={cx - body / 2} y={top} width={body} height={h} rx={Math.min(8, body / 4)} />
              <text x={cx} y={height - 8} textAnchor="middle">{formatShortDate(c.start)}</text>
            </g>
          );
        })}
      </svg>
      <figcaption className="cx-candles__legend">
        <span className="cx-candles__key cx-candles__key--up">semana em alta</span>
        <span className="cx-candles__key cx-candles__key--down">semana em queda</span>
        <span>Saldo previsto, agrupado por semana</span>
      </figcaption>
    </figure>
  );
};

/** Linha fina e suave (curva de Catmull-Rom convertida em Bézier). */
export function smoothPath(points: [number, number][]): string {
  if (points.length < 2) return '';
  let d = `M${points[0][0].toFixed(1)},${points[0][1].toFixed(1)}`;
  for (let i = 0; i < points.length - 1; i++) {
    const p0 = points[i - 1] ?? points[i];
    const p1 = points[i];
    const p2 = points[i + 1];
    const p3 = points[i + 2] ?? p2;
    const c1 = [p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6];
    const c2 = [p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6];
    d += ` C${c1[0].toFixed(1)},${c1[1].toFixed(1)} ${c2[0].toFixed(1)},${c2[1].toFixed(1)} ${p2[0].toFixed(1)},${p2[1].toFixed(1)}`;
  }
  return d;
}

export const Sparkline: FC<{ values: number[]; width?: number; height?: number; className?: string }> = ({ values, width = 120, height = 36, className }) => {
  if (values.length < 2) return null;
  const lo = Math.min(...values);
  const hi = Math.max(...values);
  const span = Math.max(hi - lo, 1);
  const pts = values.map((v, i) => [(width * i) / (values.length - 1), 3 + (height - 6) * (1 - (v - lo) / span)] as [number, number]);
  return (
    <svg className={`cx-spark${className ? ` ${className}` : ''}`} viewBox={`0 0 ${width} ${height}`} width={width} height={height} aria-hidden="true" preserveAspectRatio="none">
      <path d={smoothPath(pts)} />
    </svg>
  );
};

/**
 * Arte do destaque: um orbe com anéis finos, atravessado pela trajetória real do saldo
 * previsto. É decorativa (aria-hidden); o valor correspondente está no texto ao lado.
 */
export const HeroArt: FC<{ projection?: ProjectionOut }> = ({ projection }) => {
  const W = 420;
  const H = 360;
  const path = useMemo(() => {
    if (!projection) return '';
    const vals = [projection.start_balance_cents, ...projection.items.map((d) => d.balance_cents)];
    const lo = Math.min(...vals);
    const span = Math.max(Math.max(...vals) - lo, 1);
    return smoothPath(vals.map((v, i) => [20 + ((W - 40) * i) / (vals.length - 1), 250 - 150 * ((v - lo) / span)] as [number, number]));
  }, [projection]);
  return (
    <svg className="cx-hero-art" viewBox={`0 0 ${W} ${H}`} aria-hidden="true">
      <defs>
        <radialGradient id="cx-orb" cx="38%" cy="32%" r="70%">
          <stop offset="0%" stopColor="#d6f6ff" />
          <stop offset="30%" stopColor="#52d4ff" />
          <stop offset="62%" stopColor="#2f6dff" />
          <stop offset="100%" stopColor="#081a5c" />
        </radialGradient>
        <radialGradient id="cx-orb-glow" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#2f86ff" stopOpacity="0.55" />
          <stop offset="100%" stopColor="#2f86ff" stopOpacity="0" />
        </radialGradient>
        <linearGradient id="cx-trail" x1="0" x2="1">
          <stop offset="0%" stopColor="#52d4ff" stopOpacity="0" />
          <stop offset="35%" stopColor="#52d4ff" />
          <stop offset="100%" stopColor="#e8fbff" />
        </linearGradient>
      </defs>
      <circle cx="230" cy="180" r="170" fill="url(#cx-orb-glow)" />
      <g className="cx-hero-art__rings" fill="none" stroke="rgba(255,255,255,0.14)">
        <circle cx="230" cy="180" r="150" />
        <circle cx="230" cy="180" r="118" strokeDasharray="2 6" />
        <ellipse cx="230" cy="180" rx="190" ry="54" transform="rotate(-18 230 180)" />
      </g>
      <circle className="cx-hero-art__orb" cx="230" cy="180" r="86" fill="url(#cx-orb)" />
      <ellipse cx="205" cy="146" rx="30" ry="16" fill="rgba(255,255,255,0.35)" transform="rotate(-28 205 146)" />
      {path && <path className="cx-hero-art__trail" d={path} fill="none" stroke="url(#cx-trail)" strokeWidth="2.5" strokeLinecap="round" />}
    </svg>
  );
};
