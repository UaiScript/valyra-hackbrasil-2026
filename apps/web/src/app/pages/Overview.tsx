import { useState } from 'react';
import type { FC, FormEvent } from 'react';
import { Activity, ArrowUpRight, BellRing, ChartSpline, Pencil, Radar, Repeat, Sparkles, Target, TrendingUp, Wallet } from 'lucide-react';
import { api, describeError } from '../api/client';
import type { AccountOut, AccountUpdate } from '../../lib/api/schema';
import { centsToInput, formatCents, formatIsoDate, formatMonth, formatShortDate, parseReaisToCents } from '../money';
import { BudgetList, usedPercent } from '../Budget';
import { ProjectionChart } from '../ProjectionChart';
import { ROUTES } from '../router';
import { TransactionSummary } from '../TransactionRow';
import { Async, Card, Empty, NoticeBar } from '../ui';
import type { Notice } from '../ui';
import { useApi } from '../useApi';

/**
 * Linha de indicadores da central. Realizado e previsto ficam em blocos separados e
 * rotulados, para não confundir saldo de hoje com saldo estimado; todos os números vêm
 * prontos da API (resumo, projeção e orçamento), sem cálculo financeiro no navegador.
 */
const CommandKpis: FC<{ account: AccountOut; reloadKey: number }> = ({ account, reloadKey }) => {
  const summary = useApi((s) => api.getSummary({ account_id: account.id }, s), [account.id, reloadKey]);
  const projection = useApi((s) => api.getProjection(account.id, 30, s), [account.id, reloadKey]);
  const budgets = useApi((s) => api.getBudgets({}, s), [reloadKey]);
  const s = summary.state.data;
  const p = projection.state.data;
  const b = budgets.state.data;
  const pending = (st: { status: string }) => (st.status === 'error' ? 'Indisponível' : '—');
  const budgetPct = b && b.total_limit_cents > 0 ? usedPercent(b.total_spent_cents, b.total_limit_cents) : null;
  const overCount = b?.items.filter((i) => i.status === 'over').length ?? 0;
  return (
    <section className="cx-kpis cx-span" aria-label="Indicadores principais">
      <a className="cx-kpi cx-kpi--lead" href={ROUTES.summary}>
        <span className="cx-kpi__label"><Wallet size={13} aria-hidden="true" />Saldo realizado · {s ? formatIsoDate(s.today) : 'hoje'}</span>
        <strong className="cx-kpi__value">{s ? (s.realized_balance_cents === null ? 'Indisponível' : formatCents(s.realized_balance_cents)) : pending(summary.state)}</strong>
        <span className="cx-kpi__hint">{account.name}</span>
      </a>
      <a className={`cx-kpi${s && s.net_cents < 0 ? ' cx-kpi--danger' : ''}`} href={ROUTES.summary}>
        <span className="cx-kpi__label"><Activity size={13} aria-hidden="true" />Resultado do mês</span>
        <strong className="cx-kpi__value">{s ? formatCents(s.net_cents) : pending(summary.state)}</strong>
        <span className="cx-kpi__hint">{s ? `${formatMonth(s.month)}, realizado` : 'entradas menos saídas'}</span>
      </a>
      <a className={`cx-kpi${p && p.min_balance_cents < 0 ? ' cx-kpi--danger' : ''}`} href={ROUTES.projection}>
        <span className="cx-kpi__label"><ChartSpline size={13} aria-hidden="true" />Menor saldo · 30 dias</span>
        <strong className="cx-kpi__value">{p ? formatCents(p.min_balance_cents) : pending(projection.state)}</strong>
        <span className="cx-kpi__hint">{p ? `em ${formatShortDate(p.min_balance_date)} · previsão` : 'projeção de caixa'}</span>
      </a>
      <a className={`cx-kpi${overCount ? ' cx-kpi--danger' : budgetPct !== null && budgetPct >= 80 ? ' cx-kpi--warning' : ''}`} href={ROUTES.budgets}>
        <span className="cx-kpi__label"><Target size={13} aria-hidden="true" />Orçamento do mês</span>
        <strong className="cx-kpi__value">{budgetPct === null ? (b ? 'Sem limites' : pending(budgets.state)) : `${budgetPct}%`}</strong>
        <span className="cx-kpi__hint">{b && budgetPct !== null ? `${formatCents(b.total_spent_cents)} de ${formatCents(b.total_limit_cents)}${overCount ? ` · ${overCount} estourado${overCount > 1 ? 's' : ''}` : ''}` : 'defina tetos por categoria'}</span>
      </a>
    </section>
  );
};

const ForecastPanel: FC<{ account: AccountOut; reloadKey: number }> = ({ account, reloadKey }) => {
  const projection = useApi((s) => api.getProjection(account.id, 30, s), [account.id, reloadKey]);
  const p = projection.state.data;
  return (
    <section className="app-card cx-panel cx-panel--chart">
      <header className="app-card__header">
        <h2>Fluxo de caixa previsto · 30 dias</h2>
        <a className="app-link" href={ROUTES.projection}>Detalhar<ArrowUpRight size={14} aria-hidden="true" /></a>
      </header>
      {p ? (
        <>
          <ProjectionChart projection={p} height={250} />
          <p className="cx-caption">Previsão a partir do saldo realizado de hoje ({formatCents(p.start_balance_cents)}), das recorrências detectadas e da média de gastos variáveis ({formatCents(p.variable_daily_cents)}/dia).</p>
        </>
      ) : <span className="app-muted vx-hero__placeholder">{projection.state.status === 'error' ? 'Projeção indisponível.' : 'Calculando projeção…'}</span>}
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
    <section className="app-card cx-panel cx-radar">
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
      {account && <CommandKpis account={account} reloadKey={heroKey} />}
      {account && <ForecastPanel account={account} reloadKey={heroKey} />}
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
