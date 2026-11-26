import type { FC } from 'react';
import type { TransactionOut } from '../lib/api/schema';
import { formatCents, formatIsoDate } from './money';

export const SOURCE_LABEL: Record<TransactionOut['category_source'], string> = {
  rule: 'Regra',
  model: 'Modelo',
  user: 'Você',
};

export const Amount: FC<{ cents: number }> = ({ cents }) => (
  <span className={`app-amount ${cents < 0 ? 'app-amount--out' : 'app-amount--in'}`}>{formatCents(cents)}</span>
);

export const TransactionSummary: FC<{ t: TransactionOut }> = ({ t }) => (
  <li className="app-tx">
    <div>
      <strong>{t.description}</strong>
      <span className="app-muted">{formatIsoDate(t.date)} · {t.category.name}</span>
    </div>
    <Amount cents={t.amount_cents} />
  </li>
);
