import { useState } from 'react';
import type { FC, FormEvent } from 'react';
import { ArrowUpRight, BellRing, Pencil } from 'lucide-react';
import { api, describeError } from '../api/client';
import type { AccountOut, AccountUpdate } from '../../lib/api/schema';
import { centsToInput, formatCents, formatIsoDate, formatMonth, formatShortDate, parseReaisToCents } from '../money';
import { ProjectionChart } from '../ProjectionChart';
import { ROUTES } from '../router';
import { TransactionSummary } from '../TransactionRow';
import { Async, Card, Empty, NoticeBar } from '../ui';
import type { Notice } from '../ui';
import { useApi } from '../useApi';

// Painel do topo: o realizado (resumo) ao lado do previsto (projeção), sempre rotulados
// separadamente para não confundir saldo de hoje com saldo estimado.
// Realizado e previsto usam a mesma conta, para que os dois números tenham o mesmo escopo.
const OverviewHero: FC<{ account: AccountOut; showName: boolean; reloadKey: number }> = ({ account, showName, reloadKey }) => {
  const summary = useApi((s) => api.getSummary({ account_id: account.id }, s), [account.id, reloadKey]);
  const projection = useApi((s) => api.getProjection(account.id, 30, s), [account.id, reloadKey]);
  const s = summary.state.data;
  const p = projection.state.data;
  const quiet = s && s.income_cents === 0 && s.expenses_cents === 0;
  return (
    <section className="vx-hero vx-hero--overview" aria-label="Saldo de hoje e próximos 30 dias">
      <div className="vx-hero__lead">
        <span className="vx-hero__label">Saldo realizado hoje{s ? `, ${formatIsoDate(s.today)}` : ''}{showName ? ` · ${account.name}` : ''}</span>
        {summary.state.status === 'error' && !s ? <span className="app-muted">Resumo indisponível.</span> : (
          <strong className={`vx-figure${s?.realized_balance_cents === null ? ' vx-figure--muted' : ''}`}>
            {s ? (s.realized_balance_cents === null ? 'Indisponível' : formatCents(s.realized_balance_cents)) : '—'}
          </strong>
        )}
        {s && (
          <a className="vx-hero__month" href={ROUTES.summary}>
            {quiet
              ? <>Sem movimentações em {formatMonth(s.month)} até agora</>
              : <>Resultado de {formatMonth(s.month)}: <b className={s.net_cents < 0 ? 'vx-totals__neg' : 'vx-totals__in'}>{formatCents(s.net_cents)}</b></>}
            <ArrowUpRight size={14} aria-hidden="true" />
          </a>
        )}
      </div>
      <a className="vx-hero__forecast" href={ROUTES.projection} aria-label="Abrir projeção de caixa">
        <span className="vx-hero__label">Próximos 30 dias, previsto</span>
        {p ? (
          <>
            <ProjectionChart projection={p} height={120} compact />
            <span className="vx-hero__caption">
              Menor saldo <b className={p.min_balance_cents < 0 ? 'vx-totals__neg' : undefined}>{formatCents(p.min_balance_cents)}</b> em {formatShortDate(p.min_balance_date)}
            </span>
          </>
        ) : <span className="app-muted vx-hero__placeholder">{projection.state.status === 'error' ? 'Projeção indisponível.' : 'Calculando projeção…'}</span>}
      </a>
    </section>
  );
};

const NewAlertsBanner: FC = () => {
  const alerts = useApi((s) => api.listAlerts(s), []);
  const fresh = alerts.state.data?.items.filter((a) => a.status === 'new') ?? [];
  if (fresh.length === 0) return null;
  return (
    <a className="app-inline-alert" href={ROUTES.alerts}>
      <BellRing size={18} aria-hidden="true" />
      <span><strong>{fresh[0].title}</strong>{fresh.length > 1 ? ` e mais ${fresh.length - 1}` : ''}. Ver alertas</span>
    </a>
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

  return (
    <div className="app-grid">
      <NewAlertsBanner />
      {accounts.state.data?.items[0] && (
        <OverviewHero account={accounts.state.data.items[0]} showName={accounts.state.data.items.length > 1} reloadKey={heroKey} />
      )}
      <NoticeBar notice={notice} onClose={() => setNotice(null)} />
      <div className="app-stack app-stack--loose">
      <Card title="Contas">
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

      <Card title="Importações recentes" action={<a className="app-link" href={ROUTES.import}>Importar</a>}>
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
      </div>
      <Card title="Últimas transações" action={<a className="app-link" href={ROUTES.transactions}>Ver todas</a>}>
        <Async state={recent.state} onRetry={recent.reload}>
          {(page) => page.items.length === 0
            ? <Empty>Sem transações ainda. <a className="app-link" href={ROUTES.import}>Importe um CSV</a>.</Empty>
            : <ul className="app-tx-list">{page.items.map((t) => <TransactionSummary key={t.id} t={t} />)}</ul>}
        </Async>
      </Card>

    </div>
  );
};
