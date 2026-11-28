import { useEffect, useState } from 'react';

// Hash routing: a build usa base './' e é servida como arquivos estáticos, sem
// reescrita de rotas no servidor. Âncoras da landing (#capacidades) não começam com #/.
export type AppRoute = 'overview' | 'summary' | 'budgets' | 'projection' | 'transactions' | 'alerts' | 'ai' | 'import' | 'alpha' | 'news' | 'forecasts';

export const ROUTES: Record<AppRoute, string> = {
  overview: '#/app',
  summary: '#/app/resumo',
  budgets: '#/app/orcamento',
  ai: '#/app/valyra-ai',
  projection: '#/app/projecao',
  alerts: '#/app/alertas',
  transactions: '#/app/transacoes',
  import: '#/app/importar',
  alpha: '#/app/alpha',
  news: '#/app/alpha/semana',
  forecasts: '#/app/alpha/previsoes',
};

export function isAppHash(hash: string): boolean {
  return hash === '#/app' || hash.startsWith('#/app/');
}

export function routeFromHash(hash: string): AppRoute {
  if (hash.startsWith('#/app/transacoes')) return 'transactions';
  if (hash.startsWith('#/app/importar')) return 'import';
  if (hash.startsWith('#/app/resumo')) return 'summary';
  if (hash.startsWith('#/app/projecao')) return 'projection';
  if (hash.startsWith('#/app/alertas')) return 'alerts';
  if (hash.startsWith('#/app/orcamento')) return 'budgets';
  if (hash.startsWith('#/app/valyra-ai')) return 'ai';
  // Antes de '#/app/alpha': relatório da semana e previsões são sub-rotas do Alpha.
  if (hash.startsWith('#/app/alpha/semana')) return 'news';
  if (hash.startsWith('#/app/alpha/previsoes')) return 'forecasts';
  if (hash.startsWith('#/app/alpha')) return 'alpha';
  return 'overview';
}

export function useHash(): string {
  const [hash, setHash] = useState(() => window.location.hash);
  useEffect(() => {
    const onChange = () => setHash(window.location.hash);
    window.addEventListener('hashchange', onChange);
    return () => window.removeEventListener('hashchange', onChange);
  }, []);
  return hash;
}
