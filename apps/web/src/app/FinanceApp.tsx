import { useEffect, useState } from 'react';
import type { FC } from 'react';
import { ArrowLeft, Bell, ChartPie, ChartSpline, LayoutDashboard, ListOrdered, Menu, Upload, X } from 'lucide-react';
import { api } from './api/client';
import { ROUTES, routeFromHash, useHash } from './router';
import type { AppRoute } from './router';
import { useApi } from './useApi';
import { Overview } from './pages/Overview';
import { Transactions } from './pages/Transactions';
import { ImportCsv } from './pages/ImportCsv';
import { Summary } from './pages/Summary';
import { Projection } from './pages/Projection';
import { Alerts, ALERTS_CHANGED } from './pages/Alerts';
import './app.css';

const NAV: { route: AppRoute; label: string; icon: typeof LayoutDashboard }[] = [
  { route: 'overview', label: 'Visão geral', icon: LayoutDashboard },
  { route: 'summary', label: 'Resumo do mês', icon: ChartPie },
  { route: 'projection', label: 'Projeção de caixa', icon: ChartSpline },
  { route: 'transactions', label: 'Transações', icon: ListOrdered },
  { route: 'alerts', label: 'Alertas', icon: Bell },
  { route: 'import', label: 'Importar CSV', icon: Upload },
];

const ApiStatus: FC = () => {
  const { state } = useApi((signal) => api.health(signal), []);
  const ok = state.status === 'success' && state.data.status === 'ok';
  const label = state.status === 'loading' ? 'Verificando API…' : ok ? 'API conectada' : 'API indisponível';
  return (
    <span className={`app-health app-health--${state.status === 'loading' ? 'pending' : ok ? 'ok' : 'down'}`} role="status">
      <span className="app-health__dot" aria-hidden="true" />{label}
    </span>
  );
};

/** Quantidade de alertas novos para o selo do menu; recarrega quando um alerta muda. */
function useNewAlertCount(route: AppRoute): number {
  const { state, reload } = useApi((signal) => api.listAlerts(signal), [route]);
  useEffect(() => {
    window.addEventListener(ALERTS_CHANGED, reload);
    return () => window.removeEventListener(ALERTS_CHANGED, reload);
  }, [reload]);
  return state.data?.items.filter((a) => a.status === 'new').length ?? 0;
}

export default function FinanceApp() {
  const route = routeFromHash(useHash());
  const [menuOpen, setMenuOpen] = useState(false);
  const current = NAV.find((n) => n.route === route)!;
  const newAlerts = useNewAlertCount(route);

  useEffect(() => {
    document.documentElement.lang = 'pt-BR';
    document.title = `${current.label} · Valyra`;
    setMenuOpen(false);
  }, [current.label]);

  return (
    <div className="app-shell">
      <aside className={`app-sidebar${menuOpen ? ' app-sidebar--open' : ''}`} aria-label="Módulos">
        <a href={ROUTES.overview} className="brand app-brand" aria-label="Valyra — visão geral">
          <span className="brand__mark" aria-hidden="true">V</span>
          <span className="brand__word">valyra<span className="brand__period">.</span></span>
        </a>
        <nav className="app-nav">
          {NAV.map(({ route: r, label, icon: Icon }) => (
            <a key={r} href={ROUTES[r]} aria-current={r === route ? 'page' : undefined}>
              <Icon size={18} aria-hidden="true" />{label}
              {r === 'alerts' && newAlerts > 0 && <span className="app-nav__count" aria-label={`${newAlerts} novos`}>{newAlerts}</span>}
            </a>
          ))}
        </nav>
        <a className="app-nav__back" href="#top"><ArrowLeft size={16} aria-hidden="true" />Voltar à landing</a>
      </aside>
      <div className="app-main">
        <header className="app-header">
          <button type="button" className="app-menu-toggle button button--ghost button--sm" aria-expanded={menuOpen} aria-label={menuOpen ? 'Fechar menu' : 'Abrir menu'} onClick={() => setMenuOpen((o) => !o)}>
            {menuOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
          <h1>{current.label}</h1>
          <ApiStatus />
        </header>
        <main className="app-content" id="main">
          <p className="app-demo-note" role="note">Ambiente de demonstração: usuário demo e dados sintéticos, sem login.</p>
          {route === 'overview' && <Overview />}
          {route === 'transactions' && <Transactions />}
          {route === 'summary' && <Summary />}
          {route === 'projection' && <Projection />}
          {route === 'alerts' && <Alerts />}
          {route === 'import' && <ImportCsv />}
        </main>
      </div>
    </div>
  );
}
