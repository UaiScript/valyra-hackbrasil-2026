import { useState } from 'react';
import type { FC, FormEvent } from 'react';
import { ArrowUpRight, BellRing, Pencil, Radar, Repeat, Sparkles, TrendingUp } from 'lucide-react';
import { api, describeError } from '../api/client';
import type { AccountOut, AccountUpdate } from '../../lib/api/schema';
import { centsToInput, formatCents, formatIsoDate, formatShortDate, parseReaisToCents, shiftMonth } from '../money';
import { BudgetList, BudgetMeter, usedPercent } from '../Budget';
import { CandleChart, HeroArt, Sparkline, Ticker } from '../Market';
import { ROUTES } from '../router';
import { TransactionSummary } from '../TransactionRow';
import { Async, Card, Empty, NoticeBar } from '../ui';
import type { Notice } from '../ui';
import { useApi } from '../useApi';

/**
 * Destaque da Central: saldo realizado em evidência, a arte com a trajetória prevista e,
 * embaixo, a faixa de indicadores. Realizado e previsto ficam sempre rotulados à parte;
 * todos os números vêm prontos da API (resumo, projeção, orçamento e alertas).
 */
const Hero: FC<{ account: AccountOut; reloadKey: number }> = ({ account, reloadKey }) => {
  const summary = useApi((s) => api.getSummary({ account_id: account.id }, s), [account.id, reloadKey]);
  const projection = useApi((s) => api.getProjection(account.id, 30, s), [account.id, reloadKey]);
  const budgets = useApi((s) => api.getBudgets({}, s), [reloadKey]);
  const alerts = useApi((s) => api.listAlerts(s), []);
  const anomalies = useApi((s) => api.listTransactions({ is_anomaly: true, limit: 1 }, s), []);
  const s = summary.state.data;
  const p = projection.state.data;
  const b = budgets.state.data;
  const fresh = alerts.state.data?.items.filter((a) => a.status === 'new').length ?? 0;
  const signals = fresh + (anomalies.state.data?.total ?? 0);
  const budgetPct = b && b.total_limit_cents > 0 ? usedPercent(b.total_spent_cents, b.total_limit_cents) : null;
  const dash = (st: { status: string }) => (st.status === 'error' ? 'Indisponível' : '—');
  return (
    <section className="cx-hero cx-span-8" aria-label="Saldo de hoje e indicadores">
      <div className="cx-hero__body">
        <span className="cx-eyebrow">Saldo realizado · {s ? formatIsoDate(s.today) : 'hoje'}</span>
        <strong className="cx-hero__figure">{s ? (s.realized_balance_cents === null ? 'Indisponível' : formatCents(s.realized_balance_cents)) : dash(summary.state)}</strong>
        <p className="cx-hero__lede">{account.name}. Saldo de referência mais tudo o que entrou e saiu até hoje.</p>
        <div className="cx-hero__actions">
          <a className="cx-pill cx-pill--light" href={ROUTES.ai}><Sparkles size={16} aria-hidden="true" />Pergunte ao Valyra</a>
          <a className="cx-pill cx-pill--ghost" href={ROUTES.projection}>Ver projeção<ArrowUpRight size={16} aria-hidden="true" /></a>
        </div>
      </div>
      <HeroArt projection={p} />
      <dl className="cx-hero__kpis">
        <a href={ROUTES.summary} className="cx-kpi cx-kpi--amber">
          <dt>Resultado do mês</dt>
          <dd className={s && s.net_cents < 0 ? 'cx-neg' : undefined}>{s ? formatCents(s.net_cents) : dash(summary.state)}</dd>
          <span className="cx-kpi__bar" aria-hidden="true" />
        </a>
        <a href={ROUTES.projection} className="cx-kpi cx-kpi--coral">
          <dt>Menor saldo · 30 dias</dt>
          <dd className={p && p.min_balance_cents < 0 ? 'cx-neg' : undefined}>{p ? formatCents(p.min_balance_cents) : dash(projection.state)}</dd>
          <span className="cx-kpi__hint">{p ? `previsto para ${formatShortDate(p.min_balance_date)}` : 'previsão'}</span>
          <span className="cx-kpi__bar" aria-hidden="true" />
        </a>
        <a href={ROUTES.budgets} className="cx-kpi cx-kpi--lime">
          <dt>Orçamento usado</dt>
          <dd className={budgetPct !== null && budgetPct > 100 ? 'cx-neg' : undefined}>{budgetPct === null ? (b ? 'Sem tetos' : dash(budgets.state)) : `${budgetPct}%`}</dd>
          <span className="cx-kpi__bar" aria-hidden="true" />
        </a>
        <a href={ROUTES.alerts} className="cx-kpi cx-kpi--sky">
          <dt>Sinais ativos</dt>
          <dd>{alerts.state.data && anomalies.state.data ? signals : '—'}</dd>
          <span className="cx-kpi__bar" aria-hidden="true" />
        </a>
      </dl>
    </section>
  );
};

/** Saldo previsto em linha fina, com a mesma série do gráfico detalhado. */
const ForecastCard: FC<{ account: AccountOut; reloadKey: number }> = ({ account, reloadKey }) => {
  const projection = useApi((s) => api.getProjection(account.id, 30, s), [account.id, reloadKey]);
  const p = projection.state.data;
  const end = p?.items[p.items.length - 1];
  return (
    <a className="cx-card cx-forecast cx-span-4" href={ROUTES.projection}>
      <span className="cx-card__title">Saldo previsto · 30 dias</span>
      {p && end ? (
        <>
          <strong className={`cx-card__figure${end.balance_cents < 0 ? ' cx-neg' : ''}`}>{formatCents(end.balance_cents)}</strong>
          <span className="cx-card__hint">em {formatShortDate(end.date)} · previsão</span>
          <Sparkline values={[p.start_balance_cents, ...p.items.map((d) => d.balance_cents)]} width={320} height={92} className="cx-spark--amber" />
        </>
      ) : <span className="cx-card__hint">{projection.state.status === 'error' ? 'Projeção indisponível.' : 'Calculando…'}</span>}
    </a>
  );
};

const BudgetCard: FC<{ reloadKey: number }> = ({ reloadKey }) => {
  const budgets = useApi((s) => api.getBudgets({}, s), [reloadKey]);
  const b = budgets.state.data;
  const available = b ? b.total_limit_cents - b.total_spent_cents : 0;
  const over = b?.items.filter((i) => i.status === 'over').length ?? 0;
  return (
    <a className="cx-card cx-budget-card cx-span-4" href={ROUTES.budgets}>
      <span className="cx-card__title">Orçamento do mês</span>
      {b && b.items.length > 0 ? (
        <>
          <strong className={`cx-card__figure cx-card__figure--lime${available < 0 ? ' cx-neg' : ''}`}>{formatCents(Math.abs(available))}</strong>
          <span className="cx-card__hint">{available < 0 ? 'acima do limite' : 'disponível'} · {formatCents(b.total_spent_cents)} de {formatCents(b.total_limit_cents)}{over ? ` · ${over} estourado${over > 1 ? 's' : ''}` : ''}</span>
          <BudgetMeter spent={b.total_spent_cents} limit={b.total_limit_cents} status={over ? 'over' : usedPercent(b.total_spent_cents, b.total_limit_cents) >= 80 ? 'warning' : 'ok'} />
        </>
      ) : <span className="cx-card__hint">{b ? 'Defina tetos por categoria para acompanhar aqui.' : 'Carregando…'}</span>}
    </a>
  );
};

const CandlesCard: FC<{ account: AccountOut; reloadKey: number }> = ({ account, reloadKey }) => {
  const projection = useApi((s) => api.getProjection(account.id, 35, s), [account.id, reloadKey]);
  const p = projection.state.data;
  return (
    <section className="app-card cx-panel cx-span-8">
      <header className="app-card__header">
        <h2>Projeção semanal</h2>
        <a className="app-link" href={ROUTES.projection}>Detalhar<ArrowUpRight size={14} aria-hidden="true" /></a>
      </header>
      {p ? <CandleChart projection={p} /> : <span className="app-muted">{projection.state.status === 'error' ? 'Projeção indisponível.' : 'Calculando projeção…'}</span>}
      {p && <p className="cx-caption">Cada vela é uma semana prevista: abre no saldo da semana anterior e fecha no último dia. Base: saldo realizado de hoje, recorrências detectadas e média de gastos variáveis ({formatCents(p.variable_daily_cents)}/dia).</p>}
    </section>
  );
};

/** Radar: o que os cálculos sinalizaram, com atalho para pedir explicação à IA. */
const SignalRadar: FC = () => {
  const alerts = useApi((s) => api.listAlerts(s), []);
  const anomalies = useApi((s) => api.listTransactions({ is_anomaly: true, limit: 3 }, s), []);
  const recurring = useApi((s) => api.listTransactions({ is_recurring: true, limit: 1 }, s), []);
  const fresh = alerts.state.data?.items.filter((a) => a.status === 'new') ?? [];
  const atypical = anomalies.state.data;
  return (
    <section className="app-card cx-panel cx-radar cx-span-4">
      <header className="app-card__header"><h2><Radar size={14} aria-hidden="true" />Radar de sinais</h2></header>
      <ul className="cx-signals">
        <li className={fresh.length ? 'cx-signal cx-signal--warning' : 'cx-signal'}>
          <BellRing size={16} aria-hidden="true" />
          <a href={ROUTES.alerts}><span><b>{fresh.length}</b> {fresh.length === 1 ? 'alerta novo' : 'alertas novos'}</span>{fresh[0] ? <small>{fresh[0].title}</small> : <small>Nenhuma pressão de caixa</small>}</a>
        </li>
        <li className={atypical?.total ? 'cx-signal cx-signal--warning' : 'cx-signal'}>
          <TrendingUp size={16} aria-hidden="true" />
          <a href={ROUTES.transactions}><span><b>{atypical?.total ?? '—'}</b> {atypical?.total === 1 ? 'gasto atípico' : 'gastos atípicos'}</span>{atypical?.items[0] ? <small>{atypical.items[0].description} · {formatCents(atypical.items[0].amount_cents)}</small> : <small>Acima do padrão da categoria</small>}</a>
        </li>
        <li className="cx-signal cx-signal--info">
          <Repeat size={16} aria-hidden="true" />
          <a href={ROUTES.transactions}><span><b>{recurring.state.data?.total ?? '—'}</b> lançamentos recorrentes</span><small>Base das previsões de caixa</small></a>
        </li>
      </ul>
      <a className="cx-ask" href={ROUTES.ai}>
        <Sparkles size={16} aria-hidden="true" />
        <span><b>Pergunte ao Valyra</b><small>Explicações em linguagem simples, com evidências citadas</small></span>
        <ArrowUpRight size={16} aria-hidden="true" />
      </a>
    </section>
  );
};

const MarketTicker: FC<{ reloadKey: number }> = ({ reloadKey }) => {
  const current = useApi((s) => api.getSummary({}, s), [reloadKey]);
  const month = current.state.data?.month;
  const previous = useApi((s) => (month ? api.getSummary({ month: shiftMonth(month, -1) }, s) : Promise.resolve(undefined)), [month, reloadKey]);
  return <Ticker current={current.state.data} previous={previous.state.data} />;
};

const BudgetPanel: FC<{ reloadKey: number }> = ({ reloadKey }) => {
  const budgets = useApi((s) => api.getBudgets({}, s), [reloadKey]);
  return (
    <section className="app-card cx-panel">
      <header className="app-card__header"><h2>Orçamento do mês</h2><a className="app-link" href={ROUTES.budgets}>Gerenciar</a></header>
      <Async state={budgets.state} onRetry={budgets.reload}>
        {(b) => b.items.length === 0
          ? <Empty>Nenhum limite definido. <a className="app-link" href={ROUTES.budgets}>Definir tetos por categoria</a>.</Empty>
          : <BudgetList items={b.items} max={5} />}
      </Async>
    </section>
  );
};

const STATUS_LABEL = { processing: 'Processando', completed: 'Concluído', failed: 'Falhou' } as const;

const AccountEditor: FC<{ account: AccountOut; onSaved: (a: AccountOut) => void; onCancel: () => void }> = ({ account, onSaved, onCancel }) => {
  const [name, setName] = useState(account.name);
  const [balance, setBalance] = useState(centsToInput(account.balance_cents));
  const [asOf, setAsOf] = useState(account.balance_as_of);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    const cents = parseReaisToCents(balance);
    if (cents === null) { setError('Use o formato 1.234,56 para o saldo.'); return; }
    if (!name.trim()) { setError('Informe um nome para a conta.'); return; }
    // Só envia o que mudou: os campos do AccountUpdate são omissíveis.
    const body: AccountUpdate = {};
    if (name.trim() !== account.name) body.name = name.trim();
    if (cents !== account.balance_cents) body.balance_cents = cents;
    if (asOf !== account.balance_as_of) body.balance_as_of = asOf;
    if (Object.keys(body).length === 0) { onCancel(); return; }
    setSaving(true);
    setError(null);
    try {
      onSaved(await api.updateAccount(account.id, body));
    } catch (err) {
      setError(describeError(err));
    } finally {
      setSaving(false);
    }
  }

  return (
    <form className="app-form" onSubmit={submit}>
      <label>Nome<input value={name} onChange={(e) => setName(e.target.value)} required /></label>
      <label>Saldo de referência (R$)<input value={balance} onChange={(e) => setBalance(e.target.value)} inputMode="decimal" placeholder="1.234,56" required /></label>
      <label>Saldo em<input type="date" value={asOf} onChange={(e) => setAsOf(e.target.value)} required /></label>
      {error && <p className="app-field-error" role="alert">{error}</p>}
      <div className="app-form__actions">
        <button type="button" className="button button--ghost button--sm" onClick={onCancel}>Cancelar</button>
        <button type="submit" className="button button--primary button--sm" disabled={saving}>{saving ? 'Salvando…' : 'Salvar'}</button>
      </div>
    </form>
  );
};

export const Overview: FC = () => {
  const accounts = useApi((s) => api.listAccounts(s), []);
  const recent = useApi((s) => api.listTransactions({ limit: 6 }, s), []);
  const batches = useApi((s) => api.listImportBatches({ limit: 5 }, s), []);
  const [editing, setEditing] = useState<string | null>(null);
  const [notice, setNotice] = useState<Notice>(null);
  // Editar o saldo de referência muda o realizado e a projeção: recarrega o painel.
  const [heroKey, setHeroKey] = useState(0);

  const account = accounts.state.data?.items[0];

  return (
    <div className="cx-grid">
      <MarketTicker reloadKey={heroKey} />
      {account && <Hero account={account} reloadKey={heroKey} />}
      {account && (
        <div className="cx-stack cx-span-4">
          <ForecastCard account={account} reloadKey={heroKey} />
          <BudgetCard reloadKey={heroKey} />
        </div>
      )}
      {account && <CandlesCard account={account} reloadKey={heroKey} />}
      <SignalRadar />
      <BudgetPanel reloadKey={heroKey} />
      <NoticeBar notice={notice} onClose={() => setNotice(null)} />
      <Card title="Contas" className="cx-order-accounts">
        <Async state={accounts.state} onRetry={accounts.reload}>
          {(page) => page.items.length === 0 ? <Empty>Nenhuma conta cadastrada. Rode o seed da API.</Empty> : (
            <ul className="app-accounts">
              {page.items.map((account) => (
                <li key={account.id} className="app-account">
                  {editing === account.id ? (
                    <AccountEditor
                      account={account}
                      onCancel={() => setEditing(null)}
                      onSaved={(updated) => {
                        setEditing(null);
                        setHeroKey((k) => k + 1);
                        accounts.setState({ status: 'success', data: { ...page, items: page.items.map((a) => (a.id === updated.id ? updated : a)) } });
                        setNotice({ kind: 'success', text: `Conta “${updated.name}” atualizada.` });
                      }}
                    />
                  ) : (
                    <>
                      <div>
                        <span className="app-muted">{account.name}</span>
                        <strong className="app-balance">{formatCents(account.balance_cents)}</strong>
                        <span className="app-muted">Saldo de referência em {formatIsoDate(account.balance_as_of)}</span>
                      </div>
                      <button type="button" className="button button--outline button--sm" onClick={() => setEditing(account.id)}>
                        <Pencil size={14} aria-hidden="true" />Editar
                      </button>
                    </>
                  )}
                </li>
              ))}
            </ul>
          )}
        </Async>
      </Card>

      <Card title="Importações recentes" className="cx-order-imports" action={<a className="app-link" href={ROUTES.import}>Importar</a>}>
        <Async state={batches.state} onRetry={batches.reload}>
          {(page) => page.items.length === 0 ? <Empty>Nenhuma importação feita.</Empty> : (
            <div className="app-table-wrap">
            <table className="app-table">
              <thead><tr><th>Status</th><th>Linhas</th><th>Importadas</th><th>Duplicadas</th><th>Rejeitadas</th></tr></thead>
              <tbody>
                {page.items.map((b) => (
                  <tr key={b.id}>
                    <td><span className={`app-badge app-badge--${b.status}`}>{STATUS_LABEL[b.status]}</span></td>
                    <td>{b.rows_total}</td><td>{b.rows_imported}</td><td>{b.rows_duplicated}</td><td>{b.rows_rejected}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            </div>
          )}
        </Async>
      </Card>
      <Card title="Últimas transações" className="cx-order-recent" action={<a className="app-link" href={ROUTES.transactions}>Ver todas</a>}>
        <Async state={recent.state} onRetry={recent.reload}>
          {(page) => page.items.length === 0
            ? <Empty>Sem transações ainda. <a className="app-link" href={ROUTES.import}>Importe um CSV</a>.</Empty>
            : <ul className="app-tx-list">{page.items.map((t) => <TransactionSummary key={t.id} t={t} />)}</ul>}
        </Async>
      </Card>

    </div>
  );
};
