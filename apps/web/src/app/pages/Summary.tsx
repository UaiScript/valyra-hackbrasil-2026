import { useState } from 'react';
import type { FC } from 'react';
import { ChevronLeft, ChevronRight, Inbox } from 'lucide-react';
import { api } from '../api/client';
import type { CategoryTotalOut, SummaryOut } from '../../lib/api/schema';
import { formatCents, formatIsoDate, formatMonth, shiftMonth } from '../money';
import { ROUTES } from '../router';
import { Async, Card, Empty } from '../ui';
import { useApi } from '../useApi';

/** Participação inteira (0–100) de uma categoria no total; só para a barra e o rótulo. */
const share = (part: number, total: number) => (total === 0 ? 0 : Math.round((Math.abs(part) * 100) / Math.abs(total)));

export const CategoryBars: FC<{ items: CategoryTotalOut[]; total: number; tone: 'out' | 'in' }> = ({ items, total, tone }) => (
  <ul className={`vx-bars vx-bars--${tone}`}>
    {items.map((c) => {
      const pct = share(c.total_cents, total);
      return (
        <li key={c.category.id}>
          <div className="vx-bars__row">
            <span className="vx-bars__name">{c.category.name}</span>
            <span className="vx-bars__count">{c.count === 1 ? '1 lançamento' : `${c.count} lançamentos`}</span>
            <strong className="vx-bars__value">{formatCents(c.total_cents)}</strong>
          </div>
          <div className="vx-bars__track" aria-hidden="true"><span style={{ width: `${Math.max(pct, 1)}%` }} /></div>
          <span className="vx-bars__pct">{pct}% do total</span>
        </li>
      );
    })}
  </ul>
);

export const MonthTotals: FC<{ s: SummaryOut }> = ({ s }) => (
  <dl className="vx-totals">
    <div><dt>Entradas</dt><dd className={s.income_cents > 0 ? 'vx-totals__in' : undefined}>{formatCents(s.income_cents)}</dd></div>
    <div><dt>Saídas</dt><dd>{formatCents(s.expenses_cents)}</dd></div>
    <div className="vx-totals__net"><dt>Resultado do mês</dt><dd className={s.net_cents < 0 ? 'vx-totals__neg' : s.net_cents > 0 ? 'vx-totals__in' : undefined}>{formatCents(s.net_cents)}</dd></div>
  </dl>
);

export const Summary: FC = () => {
  const accounts = useApi((s) => api.listAccounts(s), []);
  const [accountId, setAccountId] = useState('');
  const [month, setMonth] = useState<string | undefined>(undefined);
  const summary = useApi((s) => api.getSummary({ account_id: accountId || undefined, month }, s), [accountId, month]);

  const shown = summary.state.data;
  const current = shown?.month;
  const todayMonth = shown?.today.slice(0, 7);
  // Meses futuros não têm movimentação realizada; o botão para no mês de hoje.
  const canNext = current !== undefined && todayMonth !== undefined && current < todayMonth;

  return (
    <div className="app-stack app-stack--loose">
      <div className="vx-toolbar">
        <div className="vx-month" aria-live="polite">
          <button type="button" className="vx-icon-btn" aria-label="Mês anterior" disabled={!current} onClick={() => current && setMonth(shiftMonth(current, -1))}><ChevronLeft size={18} /></button>
          <h2 className="vx-month__name">{current ? formatMonth(current) : 'Carregando…'}</h2>
          <button type="button" className="vx-icon-btn" aria-label="Próximo mês" disabled={!canNext} onClick={() => current && setMonth(shiftMonth(current, 1))}><ChevronRight size={18} /></button>
        </div>
        <label className="vx-select">Conta
          <select value={accountId} onChange={(e) => setAccountId(e.target.value)}>
            <option value="">Todas as contas</option>
            {accounts.state.data?.items.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
          </select>
        </label>
      </div>

      <Async state={summary.state} onRetry={summary.reload}>
        {(s) => {
          const expenses = s.categories.filter((c) => c.category.kind === 'expense').sort((a, b) => a.total_cents - b.total_cents);
          const income = s.categories.filter((c) => c.category.kind === 'income').sort((a, b) => b.total_cents - a.total_cents);
          const empty = s.categories.length === 0;
          return (
            <>
              <div className="vx-hero">
                <div className="vx-hero__lead">
                  <span className="vx-hero__label">Saldo realizado hoje, {formatIsoDate(s.today)}</span>
                  {s.realized_balance_cents === null
                    ? <strong className="vx-figure vx-figure--muted">Indisponível</strong>
                    : <strong className="vx-figure">{formatCents(s.realized_balance_cents)}</strong>}
                  <span className="app-muted">
                    {s.realized_balance_cents === null
                      ? 'O saldo de referência de alguma conta é posterior a hoje.'
                      : 'Saldo de referência mais o que entrou e saiu depois dele, até hoje.'}
                  </span>
                </div>
                <MonthTotals s={s} />
              </div>

              {empty ? (
                <div className="vx-empty">
                  <Inbox size={28} aria-hidden="true" />
                  <h2>Sem movimentações em {formatMonth(s.month)}</h2>
                  <p>Os lançamentos aparecem aqui conforme são importados.</p>
                  <div className="vx-empty__actions">
                    <button type="button" className="button button--primary button--sm" onClick={() => setMonth(shiftMonth(s.month, -1))}>Ver {formatMonth(shiftMonth(s.month, -1))}</button>
                    <a className="button button--ghost button--sm" href={ROUTES.import}>Importar CSV</a>
                  </div>
                </div>              ) : (
                <div className="app-grid app-grid--wide-left">
                  <Card title="Para onde foi o dinheiro">
                    {expenses.length ? <CategoryBars items={expenses} total={s.expenses_cents} tone="out" /> : <Empty>Nenhuma saída no mês.</Empty>}
                  </Card>
                  <Card title="De onde veio">
                    {income.length ? <CategoryBars items={income} total={s.income_cents} tone="in" /> : <Empty>Nenhuma entrada no mês.</Empty>}
                  </Card>
                </div>
              )}
            </>
          );
        }}
      </Async>
    </div>
  );
};
