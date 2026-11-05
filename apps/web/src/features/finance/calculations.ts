import type { Commitment, FinanceFilter, Transaction } from '../../shared/types/domain';

/** Centavos inteiros; despesas em módulo. Resultado exclui saldo inicial, enquanto saldo o inclui. */
export function summarize(transactions: Transaction[], openingBalanceCents = 0) {
  const incomeCents = transactions.reduce((sum, item) => sum + Math.max(item.amountCents, 0), 0);
  const expenseCents = transactions.reduce(
    (sum, item) => sum + Math.abs(Math.min(item.amountCents, 0)),
    0,
  );
  return {
    incomeCents,
    expenseCents,
    netCents: incomeCents - expenseCents,
    balanceCents: openingBalanceCents + incomeCents - expenseCents,
  };
}

/** Combina todos os filtros. A busca ignora maiúsculas e espaços externos, mas preserva acentos. */
export function filterTransactions(transactions: Transaction[], filter: FinanceFilter) {
  const query = filter.search.trim().toLocaleLowerCase('pt-BR');
  return transactions.filter(
    (item) =>
      (filter.direction === 'all' ||
        (filter.direction === 'income' ? item.amountCents > 0 : item.amountCents < 0)) &&
      (filter.category === 'all' || item.category === filter.category) &&
      `${item.description} ${item.category}`.toLocaleLowerCase('pt-BR').includes(query),
  );
}

export function expenseCategories(transactions: Transaction[]) {
  const totals = new Map<string, number>();
  for (const item of transactions) {
    if (item.amountCents < 0)
      totals.set(item.category, (totals.get(item.category) ?? 0) - item.amountCents);
  }
  return [...totals]
    .map(([label, amountCents]) => ({ label, amountCents }))
    .sort((a, b) => b.amountCents - a.amountCents);
}

/** Compromissos são saídas positivas ainda não realizadas; a projeção não os lança no Financeiro. */
export function projectCommitments(balanceCents: number, commitments: Commitment[]) {
  let remainingCents = balanceCents;
  // Apenas subtrai compromissos sintéticos; não infere renda, juros ou efeitos de eventos externos.
  return [...commitments]
    .sort((a, b) => a.date.localeCompare(b.date))
    .map((item) => {
      remainingCents -= item.amountCents;
      return { ...item, balanceCents: remainingCents };
    });
}
