import type { FC } from 'react';
import { Repeat, Sparkles, TrendingUp } from 'lucide-react';
import { askHref } from './api/ai';
import type { TransactionOut } from '../lib/api/schema';
import { formatCents, formatIsoDate, formatScore } from './money';

export const SOURCE_LABEL: Record<TransactionOut['category_source'], string> = {
  rule: 'Regra',
  model: 'Modelo',
  user: 'Você',
};

export const Amount: FC<{ cents: number }> = ({ cents }) => (
  <span className={`app-amount ${cents < 0 ? 'app-amount--out' : 'app-amount--in'}`}>{formatCents(cents)}</span>
);

/**
 * Selos calculados pelo backend (ADR-0010). O score de atípico é um indicador
 * heurístico (corte 0,80), não probabilidade nem causa: o texto evita sugerir motivo.
 */
export const TransactionFlags: FC<{ t: TransactionOut }> = ({ t }) => (
  <>
    {t.is_recurring && (
      <span className="vx-flag vx-flag--recurring" title="Repete todo mês com valor parecido">
        <Repeat size={12} aria-hidden="true" />Recorrente
      </span>
    )}
    {t.is_anomaly && (
      <span className="vx-flag vx-flag--anomaly" title="Acima do padrão da categoria; o selo aparece a partir do indicador 0,80.">
        <TrendingUp size={12} aria-hidden="true" />Atípico{t.anomaly_score && <span className="vx-flag__score">{formatScore(t.anomaly_score)}</span>}
      </span>
    )}
    {t.is_anomaly && (
      // Pergunta pronta para a IA explicar o selo com as evidências da conta.
      <a className="cx-why" href={askHref(`Por que a transação "${t.description}" de ${formatCents(t.amount_cents)} em ${formatIsoDate(t.date)} foi marcada como atípica?`)}>
        <Sparkles size={11} aria-hidden="true" />Por quê?
      </a>
    )}
  </>
);

export const TransactionSummary: FC<{ t: TransactionOut }> = ({ t }) => (
  <li className="app-tx">
    <div>
      <span className="app-tx__title"><strong>{t.description}</strong><TransactionFlags t={t} /></span>
      <span className="app-muted">{formatIsoDate(t.date)} · {t.category.name}</span>
    </div>
    <Amount cents={t.amount_cents} />
  </li>
);
