import { useState } from 'react';
import type { FC, FormEvent } from 'react';
import { ChevronLeft, ChevronRight, Pencil, Plus, Sparkles, Trash2 } from 'lucide-react';
import { askHref } from '../api/ai';
import { api, describeError } from '../api/client';
import type { BudgetOut, BudgetReportOut, CategoryOut } from '../../lib/api/schema';
import { BUDGET_STATUS_LABEL, BudgetMeter, usedPercent } from '../Budget';
import { centsToInput, formatCents, formatIsoDate, formatMonth, parseReaisToCents, shiftMonth } from '../money';
import { Async, NoticeBar } from '../ui';
import type { Notice } from '../ui';
import { useApi } from '../useApi';

const LimitEditor: FC<{ initial?: number; onSave: (cents: number) => Promise<void>; onCancel: () => void }> = ({ initial, onSave, onCancel }) => {
  const [text, setText] = useState(initial ? centsToInput(initial) : '');
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    const cents = parseReaisToCents(text);
    if (cents === null || cents <= 0) { setError('Informe um valor positivo, ex.: 600,00'); return; }
    setSaving(true);
    setError(null);
    try { await onSave(cents); } catch (err) { setError(describeError(err)); setSaving(false); }
  }

  return (
    <form className="cx-limit-form" onSubmit={submit}>
      <label>
        <span className="sr-only">Limite mensal em reais</span>
        <span className="cx-limit-form__prefix" aria-hidden="true">R$</span>
        <input autoFocus value={text} onChange={(e) => setText(e.target.value)} inputMode="decimal" placeholder="600,00" />
      </label>
      <button type="submit" className="button button--primary button--sm" disabled={saving}>{saving ? 'Salvando…' : 'Salvar'}</button>
      <button type="button" className="button button--ghost button--sm" onClick={onCancel}>Cancelar</button>
      {error && <p className="app-field-error" role="alert">{error}</p>}
    </form>
  );
};

type Row = { category: CategoryOut; spent: number; budget?: BudgetOut };

export const Budgets: FC = () => {
  const [month, setMonth] = useState<string | undefined>(undefined);
  const categories = useApi((s) => api.listCategories(s), []);
  const report = useApi((s) => api.getBudgets({ month }, s), [month]);
  // Gasto das categorias ainda sem limite vem do mesmo resumo mensal usado pela API.
  const summary = useApi((s) => api.getSummary({ month }, s), [month]);
  const [editing, setEditing] = useState<string | null>(null);
  const [notice, setNotice] = useState<Notice>(null);

  const r = report.state.data;
  const current = r?.month;
  const todayMonth = r?.today.slice(0, 7);
  const canNext = current !== undefined && todayMonth !== undefined && current < todayMonth;

  function applyReport(next: BudgetReportOut) {
    // PUT devolve o mês corrente; se a tela mostra outro mês, recarrega o que está aberto.
    if (next.month === current) report.setState({ status: 'success', data: next });
    else report.reload();
  }

  async function save(category: CategoryOut, cents: number) {
    applyReport(await api.setBudget(category.id, cents));
    setEditing(null);
    setNotice({ kind: 'success', text: `Limite de ${category.name} definido em ${formatCents(cents)} por mês.` });
  }

  async function remove(category: CategoryOut) {
    try {
      await api.deleteBudget(category.id);
      report.reload();
      setNotice({ kind: 'success', text: `Limite de ${category.name} removido.` });
    } catch (err) {
      setNotice({ kind: 'error', text: describeError(err) });
    }
  }

  return (
    <div className="app-stack app-stack--loose">
      <div className="vx-toolbar">
        <div className="vx-month" aria-live="polite">
          <button type="button" className="vx-icon-btn" aria-label="Mês anterior" disabled={!current} onClick={() => current && setMonth(shiftMonth(current, -1))}><ChevronLeft size={18} /></button>
          <h2 className="vx-month__name">{current ? formatMonth(current) : 'Carregando…'}</h2>
          <button type="button" className="vx-icon-btn" aria-label="Próximo mês" disabled={!canNext} onClick={() => current && setMonth(shiftMonth(current, 1))}><ChevronRight size={18} /></button>
        </div>
        <p className="vx-lede">Defina um teto mensal por categoria. O consumo soma as saídas <strong>já realizadas</strong> no mês, em todas as contas; nada aqui é previsão.</p>
      </div>

      <NoticeBar notice={notice} onClose={() => setNotice(null)} />

      <Async state={report.state} onRetry={report.reload}>
        {(rep) => {
          const expenseCats = (categories.state.data?.items ?? []).filter((c) => c.kind === 'expense');
          const totals = new Map((summary.state.data?.categories ?? []).map((c) => [c.category.id, c.total_cents]));
          const budgets = new Map(rep.items.map((b) => [b.category.id, b]));
          const rows: Row[] = expenseCats.map((c) => ({
            category: c,
            budget: budgets.get(c.id),
            spent: budgets.get(c.id)?.spent_cents ?? Math.max(0, -(totals.get(c.id) ?? 0)),
          }));
          // Com limite primeiro (mais consumido no topo); depois as demais por gasto.
          rows.sort((a, b) => {
            if (!!a.budget !== !!b.budget) return a.budget ? -1 : 1;
            if (a.budget && b.budget) return usedPercent(b.spent, b.budget.limit_cents) - usedPercent(a.spent, a.budget.limit_cents);
            return b.spent - a.spent;
          });
          const over = rep.items.filter((b) => b.status === 'over').length;
          const warn = rep.items.filter((b) => b.status === 'warning').length;
          const available = rep.total_limit_cents - rep.total_spent_cents;
          return (
            <>
              <section className="cx-kpis" aria-label="Totais do orçamento">
                <div className="cx-kpi"><span className="cx-kpi__label">Limite do mês</span><strong className="cx-kpi__value">{formatCents(rep.total_limit_cents)}</strong><span className="cx-kpi__hint">{rep.items.length} {rep.items.length === 1 ? 'categoria' : 'categorias'} com teto</span></div>
                <div className="cx-kpi"><span className="cx-kpi__label">Gasto até {formatIsoDate(rep.today)}</span><strong className="cx-kpi__value">{formatCents(rep.total_spent_cents)}</strong><span className="cx-kpi__hint">só categorias com teto</span></div>
                <div className={`cx-kpi${available < 0 ? ' cx-kpi--danger' : ''}`}><span className="cx-kpi__label">{available < 0 ? 'Acima do limite' : 'Disponível'}</span><strong className="cx-kpi__value">{formatCents(Math.abs(available))}</strong><span className="cx-kpi__hint">{rep.daily_allowance_cents !== null ? `${formatCents(rep.daily_allowance_cents)} por dia nos ${rep.days_left} ${rep.days_left === 1 ? 'dia restante' : 'dias restantes'}` : 'limite menos gasto'}</span></div>
                <div className={`cx-kpi${over ? ' cx-kpi--danger' : warn ? ' cx-kpi--warning' : ''}`}><span className="cx-kpi__label">Sinais</span><strong className="cx-kpi__value">{over} <small>estourado{over === 1 ? '' : 's'}</small></strong><span className="cx-kpi__hint">{warn} em atenção (≥ 80%)</span></div>
              </section>

              <section className="app-card cx-panel">
                <header className="app-card__header"><h2>Categorias de saída</h2><span className="app-muted">{formatMonth(rep.month)}</span></header>
                <ul className="cx-budget-table">
                  {rows.map(({ category, spent, budget }) => (
                    <li key={category.id} className={budget ? `cx-budget-row cx-budget-row--${budget.status}` : 'cx-budget-row cx-budget-row--none'}>
                      <div className="cx-budget-row__head">
                        <span className="cx-budgets__name">{category.name}</span>
                        {budget && <span className={`cx-status cx-status--${budget.status}`}>{BUDGET_STATUS_LABEL[budget.status]} · {usedPercent(spent, budget.limit_cents)}%</span>}
                        <span className="cx-budgets__value">
                          <b>{formatCents(spent)}</b>{budget ? <> / {formatCents(budget.limit_cents)}</> : <> gastos</>}
                        </span>
                        {editing !== category.id && (
                          <span className="cx-budget-row__actions">
                            {budget ? (
                              <>
                                <button type="button" className="vx-icon-btn" aria-label={`Editar limite de ${category.name}`} onClick={() => setEditing(category.id)}><Pencil size={14} /></button>
                                <button type="button" className="vx-icon-btn" aria-label={`Remover limite de ${category.name}`} onClick={() => remove(category)}><Trash2 size={14} /></button>
                              </>
                            ) : (
                              <button type="button" className="button button--outline button--sm" onClick={() => setEditing(category.id)}><Plus size={14} aria-hidden="true" />Definir limite</button>
                            )}
                          </span>
                        )}
                      </div>
                      {budget && <BudgetMeter spent={spent} limit={budget.limit_cents} status={budget.status} />}
                      {budget && budget.remaining_cents < 0 && <span className="cx-budget-row__note">Passou {formatCents(-budget.remaining_cents)} do limite.</span>}
                      {budget && budget.status !== 'ok' && (
                        // A IA recebe o orçamento como evidência calculada; a pergunta só aponta a categoria.
                        <a className="cx-why" href={askHref(`Por que o orçamento de ${category.name} está ${budget.status === 'over' ? 'acima do limite' : 'perto do limite'} neste mês?`)}>
                          <Sparkles size={11} aria-hidden="true" />Por quê?
                        </a>
                      )}
                      {editing === category.id && (
                        <LimitEditor initial={budget?.limit_cents} onCancel={() => setEditing(null)} onSave={(cents) => save(category, cents)} />
                      )}
                    </li>
                  ))}
                </ul>
              </section>
            </>
          );
        }}
      </Async>
    </div>
  );
};
