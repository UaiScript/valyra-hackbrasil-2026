import { useId, useState } from 'react';
import { money } from '../../shared/format';
import { balanceChartGeometry, type BalancePoint } from './chartGeometry';

const axisMoney = new Intl.NumberFormat('pt-BR', {
  style: 'currency',
  currency: 'BRL',
  minimumFractionDigits: 0,
  maximumFractionDigits: 2,
});
const chartDate = (date: string) =>
  new Intl.DateTimeFormat('pt-BR', { day: '2-digit', month: 'short' })
    .format(new Date(`${date}T12:00:00`))
    .replace(' de ', ' ')
    .replace('.', '');

export function BalanceChart({
  initialCents,
  points,
  referenceDate,
  tableId,
}: {
  initialCents: number;
  points: BalancePoint[];
  referenceDate: string;
  tableId: string;
}) {
  const [activeIndex, setActiveIndex] = useState(0);
  const readoutId = useId();
  const pickerId = useId();
  const geometry = balanceChartGeometry(initialCents, points, referenceDate);
  const entries = [
    {
      id: 'realized',
      date: referenceDate,
      description: 'Saldo realizado',
      amountCents: 0,
      balanceCents: initialCents,
    },
    ...points,
  ];
  const active = entries[activeIndex] ?? entries[0];

  return (
    <figure className="balance-chart" aria-label="Evolução do saldo por vencimento">
      <figcaption>Saldo em reais · selecione uma data para consultar o valor</figcaption>
      <div className="chart-grid">
        <div className="chart-axis" aria-hidden="true">
          {geometry.ticks.map((tick) => (
            <span key={tick.value} style={{ top: `${tick.y}%` }}>
              {axisMoney.format(tick.value / 100)}
            </span>
          ))}
        </div>
        <div
          className="chart-plot"
          role="group"
          aria-label="Datas e saldos da simulação"
          aria-details={tableId}
        >
          <svg viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
            {geometry.ticks.map((tick) => (
              <line
                key={tick.value}
                x1="0"
                x2="100"
                y1={tick.y}
                y2={tick.y}
                className={tick.value === 0 ? 'chart-zero' : 'chart-gridline'}
                vectorEffect="non-scaling-stroke"
              />
            ))}
            <path d={geometry.path} className="chart-step" vectorEffect="non-scaling-stroke" />
          </svg>
          {entries.map((entry, index) => (
            <button
              key={entry.id}
              type="button"
              className={`chart-point${index === 0 ? ' chart-point-realized' : ''}`}
              style={{
                left: `${geometry.coordinates[index].x}%`,
                top: `${geometry.coordinates[index].y}%`,
              }}
              aria-pressed={activeIndex === index}
              aria-label={`${chartDate(entry.date)}: ${entry.description}; saldo ${money(entry.balanceCents)}${index === 0 ? ', realizado' : ', simulado'}`}
              aria-controls={readoutId}
              onPointerEnter={() => setActiveIndex(index)}
              onFocus={() => setActiveIndex(index)}
              onClick={() => setActiveIndex(index)}
            >
              <span />
            </button>
          ))}
          <div className="chart-dates" aria-hidden="true">
            {entries.map((entry, index) => (
              <span key={entry.id} style={{ left: `${geometry.coordinates[index].x}%` }}>
                {entry.date.slice(8)}/{entry.date.slice(5, 7)}
              </span>
            ))}
          </div>
        </div>
      </div>
      <label className="chart-date-picker" htmlFor={pickerId}>
        Consultar uma data
        <select
          id={pickerId}
          value={activeIndex}
          onChange={(event) => setActiveIndex(Number(event.target.value))}
        >
          {entries.map((entry, index) => (
            <option value={index} key={entry.id}>
              {chartDate(entry.date)} · {entry.description}
            </option>
          ))}
        </select>
      </label>
      <div className="chart-readout" id={readoutId} aria-live="polite" aria-atomic="true">
        <div>
          <time dateTime={active.date}>{chartDate(active.date)}</time>
          <span>{active.description}</span>
          <small>
            {activeIndex === 0
              ? 'Realizado · ponto de partida'
              : `Simulado · compromisso de ${money(active.amountCents)}`}
          </small>
        </div>
        <strong>{money(active.balanceCents)}</strong>
      </div>
      <p className="chart-explanation">
        O saldo muda apenas nas datas dos compromissos. A{' '}
        <a
          href={`#${tableId}`}
          onClick={(event) => {
            event.preventDefault();
            const table = document.getElementById(tableId);
            const disclosure = table?.closest('details');
            if (disclosure) disclosure.open = true;
            table?.focus();
          }}
        >
          memória de cálculo
        </a>{' '}
        contém todos os valores.
      </p>
    </figure>
  );
}
