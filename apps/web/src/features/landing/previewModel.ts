import { landingExample } from '../../data/demoRepository';
import type { DemoDataset } from '../../shared/types/domain';
import { expenseCategories, projectCommitments, summarize } from '../finance/calculations';

export function previewModel(data: DemoDataset) {
  const totals = summarize(data.transactions, data.openingBalanceCents);
  const commitments = projectCommitments(totals.balanceCents, data.commitments);
  return {
    data,
    totals,
    categories: expenseCategories(data.transactions),
    commitments,
    committedCents: data.commitments.reduce((sum, item) => sum + item.amountCents, 0),
    remainingCents: commitments.at(-1)?.balanceCents ?? totals.balanceCents,
    recent: [...data.transactions].sort((a, b) => b.date.localeCompare(a.date)).slice(0, 3),
  };
}

// O exemplo comercial lê a mesma base da demonstração; não mantém indicadores paralelos.
export const personalPreview = previewModel(landingExample);
export type PreviewModel = ReturnType<typeof previewModel>;

export function foodIllustration(model: PreviewModel) {
  const referenceCents =
    model.categories.find((item) => item.label === 'Alimentação')?.amountCents ?? 0;
  // Hipótese editorial desta página. Arredonda uma vez em centavos e não altera o planejamento.
  const differenceCents = Math.round((referenceCents * 5) / 100);
  return { referenceCents, differenceCents, hypotheticalCents: referenceCents + differenceCents };
}
