import type { FC } from 'react';
import type { BudgetOut } from '../lib/api/schema';
import { formatCents } from './money';

export const BUDGET_STATUS_LABEL: Record<BudgetOut['status'], string> = {
  ok: 'Dentro do limite',
  warning: 'Atenção',
  over: 'Estourado',
};

/**
 * Percentual inteiro de consumo, só para largura da barra e rótulo. Usa divisão inteira
 * sobre centavos: o status oficial (ok/warning/over) vem calculado da API.
 */
export function usedPercent(spent: number, limit: number): number {
  if (limit <= 0) return 0;
  return Math.floor((spent * 100) / limit);
}

/** Barra de consumo do limite; acima de 100% a faixa excedente aparece em vermelho. */
export const BudgetMeter: FC<{ spent: number; limit: number; status: BudgetOut['status'] }> = ({ spent, limit, status }) => {
  const pct = usedPercent(spent, limit);
  return (
    <div className={`cx-meter cx-meter--${status}`} role="meter" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.min(pct, 100)} aria-label={`${pct}% do limite usado`}>
      <span style={{ width: `${Math.min(Math.max(pct, 1), 100)}%` }} />
      <i className="cx-meter__tick" style={{ left: '80%' }} aria-hidden="true" />
    </div>
  );
};

/** Lista compacta para a central e o resumo do mês. */
export const BudgetList: FC<{ items: BudgetOut[]; max?: number }> = ({ items, max }) => {
  // Mais consumidos primeiro: o que pede atenção aparece no topo.
  const sorted = [...items].sort((a, b) => usedPercent(b.spent_cents, b.limit_cents) - usedPercent(a.spent_cents, a.limit_cents));
  return (
    <ul className="cx-budgets">
      {sorted.slice(0, max ?? sorted.length).map((b) => (
        <li key={b.category.id}>
          <div className="cx-budgets__row">
            <span className="cx-budgets__name">{b.category.name}</span>
            <span className={`cx-status cx-status--${b.status}`}>{BUDGET_STATUS_LABEL[b.status]}</span>
            <span className="cx-budgets__value"><b>{formatCents(b.spent_cents)}</b> / {formatCents(b.limit_cents)}</span>
          </div>
          <BudgetMeter spent={b.spent_cents} limit={b.limit_cents} status={b.status} />
        </li>
      ))}
    </ul>
  );
};
