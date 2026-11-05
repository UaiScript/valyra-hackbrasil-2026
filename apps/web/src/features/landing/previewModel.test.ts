import { describe, expect, it } from 'vitest';
import personal from '../../data/demo/personal.json';
import business from '../../data/demo/business.json';
import { foodIllustration, previewModel } from './previewModel';

describe('dados apresentados na landing', () => {
  it('mantém os mesmos saldos e compromissos dos dois perfis da demonstração', () => {
    const own = previewModel(personal);
    const company = previewModel(business);
    expect(own.totals.balanceCents).toBe(555770);
    expect(own.committedCents).toBe(88490);
    expect(own.remainingCents).toBe(467280);
    expect(company.totals.balanceCents).toBe(1955000);
    expect(company.committedCents).toBe(745000);
    expect(company.remainingCents).toBe(1210000);
  });

  it('explica a hipótese de preços com centavos e sem aplicá-la ao saldo', () => {
    const model = previewModel(personal);
    const before = structuredClone(model);
    expect(foodIllustration(model)).toEqual({
      referenceCents: 48590,
      differenceCents: 2430,
      hypotheticalCents: 51020,
    });
    expect(model).toEqual(before);
    expect(model.remainingCents).toBe(467280);
  });

  it('ordena o recorte financeiro sem reordenar os dados da aplicação', () => {
    const records = structuredClone(personal);
    const before = structuredClone(records);
    const model = previewModel(records);
    expect(model.recent[0].date).toBe('2026-11-05');
    expect(model.recent).toHaveLength(3);
    expect(records).toEqual(before);
  });
});
