import { describe, expect, it } from 'vitest';
import { demoHref, parseHashRoute } from './routes';
import type { ProfileId, ScreenId } from '../shared/types/domain';

describe('contrato das rotas por hash', () => {
  it.each(['', '#', '#/'])('abre a landing em %j', (hash) => {
    expect(parseHashRoute(hash)).toEqual({ kind: 'landing' });
  });

  it.each(['overview', 'finance', 'planning', 'radar'] as ScreenId[])(
    'preserva %s e o perfil no endereço gerado',
    (screen) => {
      for (const profile of ['personal', 'business'] as ProfileId[]) {
        const hash = demoHref(screen, profile);
        expect(hash).toBe(`#/demo/${screen}?profile=${profile}`);
        expect(parseHashRoute(hash)).toEqual({ kind: 'demo', screen, profile });
      }
    },
  );

  it.each([
    '#/demo/finance',
    '#/demo/finance?profile=',
    '#/demo/finance?profile=unknown',
    '#/demo/finance?profile=Business',
  ])('mantém Pessoal como fallback em %s', (hash) => {
    expect(parseHashRoute(hash)).toEqual({ kind: 'demo', screen: 'finance', profile: 'personal' });
  });

  it.each([
    '#/demo',
    '#/demo/unknown',
    '#/demo/Overview',
    '#/demo/finance/',
    '#/demo/finance/extra',
    '#como-funciona',
  ])('continua recusando o caminho não suportado %s', (hash) => {
    expect(parseHashRoute(hash)).toEqual({ kind: 'missing' });
  });

  it('mantém Empresa quando há outro parâmetro de consulta', () => {
    expect(parseHashRoute('#/demo/radar?theme=Juros&profile=business')).toEqual({
      kind: 'demo',
      screen: 'radar',
      profile: 'business',
    });
  });
});
