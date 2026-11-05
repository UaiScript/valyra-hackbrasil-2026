import type { ProfileId, ScreenId } from '../shared/types/domain';

// App, sidebar e prévias usam este catálogo para não divergir em destinos e rótulos.
export const demoNavigation = [
  { id: 'overview', label: 'Visão geral', title: 'Visão geral', icon: 'overview' },
  { id: 'finance', label: 'Financeiro', title: 'Financeiro', icon: 'finance' },
  { id: 'planning', label: 'Planejamento', title: 'Planejamento', icon: 'planning' },
  { id: 'radar', label: 'Radar', title: 'Radar econômico', icon: 'radar' },
] as const;

type Route =
  | { kind: 'landing' }
  | { kind: 'demo'; screen: ScreenId; profile: ProfileId }
  | { kind: 'missing' };

/** Interpreta apenas o contrato atual do hash; perfil ausente/desconhecido continua em Pessoal. */
export function parseHashRoute(hash: string): Route {
  const path = hash || '#/';
  if (path === '#/' || path === '#') return { kind: 'landing' };
  const [pathname, query] = path.split('?');
  const parts = pathname.split('/');
  const screen = demoNavigation.find((item) => item.id === parts[2])?.id;
  const profile =
    new URLSearchParams(query).get('profile') === 'business' ? 'business' : 'personal';
  if (pathname.startsWith('#/demo/') && screen && parts.length === 3) {
    return { kind: 'demo', screen, profile };
  }
  return { kind: 'missing' };
}

/** Exigir o perfil evita que um atalho de Empresa retorne silenciosamente ao orçamento Pessoal. */
export function demoHref(screen: ScreenId, profile: ProfileId) {
  return `#/demo/${screen}?profile=${profile}`;
}
