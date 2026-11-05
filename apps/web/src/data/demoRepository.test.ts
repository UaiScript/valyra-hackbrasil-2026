import { describe, expect, it } from 'vitest';
import { demoRepository } from './demoRepository';
import { summarize } from '../features/finance/calculations';

describe('contrato local e separação de perfis', () => {
  it('entrega registros, categorias e exposições próprios de cada perfil', async () => {
    const [personal, business] = await Promise.all([
      demoRepository.getWorkspace('personal'),
      demoRepository.getWorkspace('business'),
    ]);
    expect(personal.transactions.every((item) => item.id.startsWith('p-'))).toBe(true);
    expect(business.transactions.every((item) => item.id.startsWith('b-'))).toBe(true);
    expect(personal.interests).toContain('Custo de vida');
    expect(business.interests).toContain('Insumos');
    expect(business.interests).not.toContain('Custo de vida');
  });

  it('isola mutações entre leituras, inclusive em listas aninhadas', async () => {
    const personal = await demoRepository.getWorkspace('personal');
    personal.transactions[0].amountCents = 1;
    personal.interests.pop();
    const fresh = await demoRepository.getWorkspace('personal');
    expect(fresh.transactions[0].amountCents).toBe(620000);
    expect(fresh.interests).toHaveLength(3);
    expect((await demoRepository.getWorkspace('business')).transactions[0].amountCents).toBe(
      1850000,
    );
  });

  it('não aplica uma hipótese externa ao financeiro', async () => {
    const data = await demoRepository.getWorkspace('personal');
    const before = summarize(data.transactions, data.openingBalanceCents);
    data.radar[0].premise = 'Hipótese alterada para o teste';
    expect(summarize(data.transactions, data.openingBalanceCents)).toEqual(before);
  });
});
