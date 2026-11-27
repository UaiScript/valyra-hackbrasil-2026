import { useEffect, useState } from 'react';

// Hash routing: a build usa base './' e é servida como arquivos estáticos, sem
// reescrita de rotas no servidor. Âncoras da landing (#capacidades) não começam com #/.
export type AppRoute = 'overview' | 'summary' | 'projection' | 'transactions' | 'alerts' | 'import';

export const ROUTES: Record<AppRoute, string> = {
  overview: '#/app',
  summary: '#/app/resumo',
  projection: '#/app/projecao',
  alerts: '#/app/alertas',
  transactions: '#/app/transacoes',
  import: '#/app/importar',
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
