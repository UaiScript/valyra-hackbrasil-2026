import { useMemo, useState } from 'react';
import type { FC } from 'react';
import { CalendarClock, Repeat } from 'lucide-react';
import { api } from '../api/client';
import type { ProjectionOut } from '../../lib/api/schema';
import { formatCents, formatIsoDate, formatShortDate } from '../money';
import { ProjectionChart } from '../ProjectionChart';
import { Amount } from '../TransactionRow';
import { Async, Card, Empty, ErrorState } from '../ui';
import { useApi } from '../useApi';

const HORIZONS = [30, 60, 90] as const;

const Figures: FC<{ p: ProjectionOut }> = ({ p }) => {
  const end = p.items[p.items.length - 1];
  return (
    <div className="vx-hero vx-hero--projection">
      <div className="vx-hero__lead">
        <span className="vx-hero__label">Saldo previsto em {formatShortDate(end.date)}</span>
        <strong className={`vx-figure${end.balance_cents < 0 ? ' vx-figure--negative' : ''}`}>{formatCents(end.balance_cents)}</strong>
        <span className="app-muted">Partindo de {formatCents(p.start_balance_cents)}, o saldo realizado de hoje ({formatIsoDate(p.today)}).</span>
      </div>
      <dl className="vx-facts">
        <div className={p.min_balance_cents < 0 ? 'vx-facts__item--danger' : undefined}>
          <dt>Menor saldo no período</dt>
          <dd>{formatCents(p.min_balance_cents)}</dd>
          <span>em {formatIsoDate(p.min_balance_date)}</span>
        </div>
        <div>
          <dt>Gasto variável estimado</dt>
          <dd>{formatCents(-p.variable_daily_cents)}</dd>
          <span>por dia</span>
        </div>
      </dl>
    </div>
  );
};

const Upcoming: FC<{ p: ProjectionOut }> = ({ p }) => {
  const rows = p.items.flatMap((d) => d.recurrences.map((r) => ({ ...r, date: d.date })));
  if (rows.length === 0) return <Empty>Nenhuma recorrência prevista neste horizonte.</Empty>;
  return (
    <ul className="vx-timeline">
      {rows.map((r) => (
        <li key={`${r.date}-${r.description}`}>
          <time dateTime={r.date}>{formatShortDate(r.date)}</time>
          <span className="vx-timeline__desc"><Repeat size={14} aria-hidden="true" /><span className="vx-timeline__text">{r.description}</span></span>
          <Amount cents={r.amount_cents} />
        </li>
      ))}
    </ul>
  );
};

export const Projection: FC = () => {
  const accounts = useApi((s) => api.listAccounts(s), []);
  const [accountId, setAccountId] = useState('');
  const [days, setDays] = useState<number>(30);
  const list = accounts.state.data?.items ?? [];
  const selected = accountId || list[0]?.id || '';
  const projection = useApi((s) => (selected ? api.getProjection(selected, days, s) : new Promise<never>(() => {})), [selected, days]);
  const accountName = useMemo(() => list.find((a) => a.id === selected)?.name, [list, selected]);

  return (
    <div className="app-stack app-stack--loose">
      <div className="vx-toolbar">
        <p className="vx-lede">
          Quanto deve sobrar na conta{accountName ? <> <strong>{accountName}</strong></> : null} nos próximos dias, somando as contas recorrentes e o ritmo de gastos dos últimos 90 dias.
        </p>
        <div className="vx-toolbar__controls">
          {list.length > 1 && (
            <label className="vx-select">Conta
              <select value={selected} onChange={(e) => setAccountId(e.target.value)}>
                {list.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
              </select>
            </label>
          )}
          <div className="vx-segmented" role="radiogroup" aria-label="Horizonte da projeção">
            {HORIZONS.map((h) => (
              <button key={h} type="button" role="radio" aria-checked={days === h} onClick={() => setDays(h)}>{h} dias</button>
            ))}
          </div>
        </div>
      </div>

      {accounts.state.status === 'error' ? <ErrorState error={accounts.state.error} onRetry={accounts.reload} />
        : accounts.state.status === 'success' && list.length === 0 ? <Empty>Nenhuma conta cadastrada. Rode o seed da API.</Empty> : (
        <Async state={projection.state} onRetry={projection.reload}>
          {(p) => (
            <>
              <Figures p={p} />
              <section className="vx-panel" aria-labelledby="proj-chart-title">
                <header className="vx-panel__header">
                  <h2 id="proj-chart-title">Saldo dia a dia</h2>
                  <span className="vx-legend">
                    <span className="vx-legend__item vx-legend__item--line">Saldo previsto</span>
                    <span className="vx-legend__item vx-legend__item--event">Recorrência</span>
                  </span>
                </header>
                <ProjectionChart projection={p} />
              </section>
              <div className="app-grid app-grid--even">
                <Card title="Recorrências previstas" action={<CalendarClock size={18} className="app-muted" aria-hidden="true" />}>
                  <Upcoming p={p} />
                </Card>
                <Card title="Como a projeção é feita">
                  <ul className="vx-method">
                    <li>Começa no saldo realizado de hoje, a partir do saldo de referência da conta.</li>
                    <li>Cada conta recorrente (pelo menos 3 meses, intervalo de 25 a 35 dias, valor estável) é prevista pelo intervalo e pelo valor medianos.</li>
                    <li>Os demais gastos entram como uma média diária das saídas não recorrentes dos últimos 90 dias, arredondada para cima.</li>
                    <li>Entradas avulsas ficam de fora. São valores previstos, não realizados.</li>
                  </ul>
                </Card>
              </div>
            </>
          )}
        </Async>
      )}
    </div>
  );
};
