import { describe, expect, it } from 'vitest';
import {
  summarize,
  filterTransactions,
  expenseCategories,
  projectCommitments,
} from './calculations';
import personal from '../../data/demo/personal.json';
import business from '../../data/demo/business.json';

describe('regras financeiras em centavos', () => {
  it('concilia o período pessoal e o saldo inicial com valores conferidos', () => {
    expect(summarize(personal.transactions, personal.openingBalanceCents)).toEqual({
      incomeCents: 705000,
      expenseCents: 274230,
      netCents: 430770,
      balanceCents: 555770,
    });
  });

  it('concilia o caixa da empresa independentemente do orçamento pessoal', () => {
    expect(summarize(business.transactions, business.openingBalanceCents)).toEqual({
      incomeCents: 2570000,
      expenseCents: 1455000,
      netCents: 1115000,
      balanceCents: 1955000,
    });
  });

  it('preserva centavos e permite resultado negativo ou lista vazia', () => {
    const items = [
      { id: '1', date: '2026-11-01', description: 'A', category: 'Teste', amountCents: 10 },
      { id: '2', date: '2026-11-01', description: 'B', category: 'Teste', amountCents: -29 },
    ];
    expect(summarize(items).balanceCents).toBe(-19);
    expect(summarize([], 123).balanceCents).toBe(123);
  });

  it('combina direção, categoria e busca sem diferenciar maiúsculas', () => {
    const filtered = filterTransactions(personal.transactions, {
      direction: 'expense',
      category: 'Moradia',
      search: '  ENERGIA  ',
    });
    expect(filtered.map((item) => item.id)).toEqual(['p-06']);
    expect(summarize(filtered).netCents).toBe(-21840);
    expect(
      filterTransactions(business.transactions, {
        direction: 'all',
        category: 'Moradia',
        search: '',
      }),
    ).toEqual([]);
  });

  it('reconcilia categorias apenas com saídas, sem alterar os registros', () => {
    const before = structuredClone(personal.transactions);
    const categories = expenseCategories(personal.transactions);
    expect(categories[0]).toEqual({ label: 'Moradia', amountCents: 201840 });
    expect(categories.reduce((sum, item) => sum + item.amountCents, 0)).toBe(274230);
    expect(personal.transactions).toEqual(before);
  });

  it('ordena compromissos e calcula saldos sem prever novas receitas', () => {
    const reversed = [...personal.commitments].reverse();
    const projected = projectCommitments(555770, reversed);
    expect(projected.map((item) => item.balanceCents)).toEqual([543780, 509780, 467280]);
    expect(reversed[0].id).toBe('p-c3');
    expect(
      projectCommitments(100, [
        { id: 'x', date: '2026-11-10', description: 'Teste', amountCents: 200 },
      ])[0].balanceCents,
    ).toBe(-100);
    expect(projectCommitments(100, [])).toEqual([]);
  });
});
