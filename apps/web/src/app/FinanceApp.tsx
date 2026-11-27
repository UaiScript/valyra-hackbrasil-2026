import { useEffect, useState } from 'react';
import type { FC } from 'react';
import { ArrowLeft, Bell, ChartPie, ChartSpline, Command, FlaskConical, LayoutDashboard, ListOrdered, Menu, Sparkles, Target, Upload, X } from 'lucide-react';
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
import { Budgets } from './pages/Budgets';
import { AskValyra } from './pages/AskValyra';
import './cockpit.css';
import './app.css';

type NavItem = { route: AppRoute; label: string; icon: typeof LayoutDashboard };

// Agrupado por módulo: a navegação mostra que Finance e a camada de inteligência são
// partes de uma mesma ferramenta, não telas soltas.
const NAV_GROUPS: { title: string; items: NavItem[] }[] = [
  {
    title: 'Finance',
    items: [
      { route: 'overview', label: 'Central', icon: LayoutDashboard },
      { route: 'summary', label: 'Resumo do mês', icon: ChartPie },
      { route: 'budgets', label: 'Orçamento', icon: Target },
      { route: 'projection', label: 'Projeção de caixa', icon: ChartSpline },
      { route: 'transactions', label: 'Transações', icon: ListOrdered },
    ],
  },
  {
    title: 'Inteligência',
    items: [
      { route: 'ai', label: 'Pergunte ao Valyra', icon: Sparkles },
      { route: 'alerts', label: 'Alertas', icon: Bell },
    ],
  },
  {
    title: 'Dados',
    items: [{ route: 'import', label: 'Importar CSV', icon: Upload }],
  },
];
const NAV: (NavItem & { group: string })[] = NAV_GROUPS.flatMap((g) => g.items.map((i) => ({ ...i, group: g.title })));

// No plano gratuito (Render + Neon) a API e o banco dormem: a primeira checagem pode
// falhar ou voltar 503 enquanto acordam, e logo depois tudo responde. Por isso o
// indicador não fica preso no primeiro resultado e volta a checar na troca de tela, a cada
// 15 s enquanto estiver fora e a cada 60 s quando estiver ok.
const ApiStatus: FC<{ route: AppRoute }> = ({ route }) => {
  const [tick, setTick] = useState(0);
  const { state } = useApi((signal) => api.health(signal), [route, tick]);
  const ok = state.status === 'success' && state.data.status === 'ok';
  const settled = state.status !== 'loading';
  useEffect(() => {
    if (!settled) return;
    const id = window.setTimeout(() => setTick((t) => t + 1), ok ? 60_000 : 15_000);
    return () => window.clearTimeout(id);
  }, [settled, ok, tick]);
  // Durante a rechecagem mantemos o último resultado na tela, sem piscar.
  const known = state.status === 'loading' ? state.data : state.status === 'success' ? state.data : undefined;
  const shownOk = state.status === 'loading' ? known?.status === 'ok' : ok;
  const pending = state.status === 'loading' && known === undefined;
  const label = pending ? 'Verificando API…' : shownOk ? 'API conectada' : 'API indisponível, tentando de novo';
  return (
    <span className={`app-health app-health--${pending ? 'pending' : shownOk ? 'ok' : 'down'}`} role="status">
      <span className="app-health__dot" aria-hidden="true" /><span className="app-health__label">{label}</span>
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

  // Atalho de teclado da barra de comando: Ctrl/⌘+K abre a pergunta à IA.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        window.location.hash = ROUTES.ai;
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  return (
    <div className="app-shell cx">
      <aside className={`app-sidebar${menuOpen ? ' app-sidebar--open' : ''}`} aria-label="Módulos">
        <a href={ROUTES.overview} className="cx-brand" aria-label="Valyra — central">
          <span className="cx-brand__mark" aria-hidden="true">V</span>
          <span className="cx-brand__text"><b>Valyra</b><small>Inteligência financeira</small></span>
        </a>
        <nav className="cx-nav">
          {NAV_GROUPS.map((group) => (
            <div key={group.title} className="cx-nav__group">
              <span className="cx-nav__title">{group.title}</span>
              {group.items.map(({ route: r, label, icon: Icon }) => (
                <a key={r} href={ROUTES[r]} aria-current={r === route ? 'page' : undefined}>
                  <Icon size={17} aria-hidden="true" />{label}
                  {r === 'alerts' && newAlerts > 0 && <span className="app-nav__count" aria-label={`${newAlerts} novos`}>{newAlerts}</span>}
                </a>
              ))}
            </div>
          ))}
          <div className="cx-nav__group">
            <span className="cx-nav__title">Pesquisa</span>
            <span className="cx-nav__soon" title="Módulo em pesquisa; ainda sem dados conectados">
              <FlaskConical size={17} aria-hidden="true" />Alternative Alpha<em>em breve</em>
            </span>
          </div>
        </nav>
        <div className="cx-sidebar__foot">
          <span className="cx-session"><span className="cx-session__avatar" aria-hidden="true">D</span><span><b>Usuário demo</b><small>Dados sintéticos · sem login</small></span></span>
          <a className="app-nav__back" href="#top"><ArrowLeft size={15} aria-hidden="true" />Voltar à landing</a>
        </div>
      </aside>
      <div className="app-main">
        <header className="app-header cx-header">
          <button type="button" className="app-menu-toggle button button--ghost button--sm" aria-expanded={menuOpen} aria-label={menuOpen ? 'Fechar menu' : 'Abrir menu'} onClick={() => setMenuOpen((o) => !o)}>
            {menuOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
          <div className="cx-header__title">
            <span className="cx-crumb">{current.group}<span aria-hidden="true">/</span></span>
            <h1>{current.label}</h1>
          </div>
          <a className="cx-command" href={ROUTES.ai} aria-label="Pergunte ao Valyra (Ctrl+K)">
            <Sparkles size={15} aria-hidden="true" />
            <span>Pergunte sobre seu dinheiro…</span>
            <kbd><Command size={11} aria-hidden="true" />K</kbd>
          </a>
          <ApiStatus route={route} />
        </header>
        <main className="app-content" id="main">
          {route === 'overview' && <Overview />}
          {route === 'transactions' && <Transactions />}
          {route === 'summary' && <Summary />}
          {route === 'budgets' && <Budgets />}
          {route === 'projection' && <Projection />}
          {route === 'alerts' && <Alerts />}
          {route === 'ai' && <AskValyra />}
          {route === 'import' && <ImportCsv />}
          <p className="cx-footnote" role="note">Ambiente de demonstração: usuário demo e dados sintéticos, sem login. Todo número vem de um cálculo auditável da API.</p>
        </main>
      </div>
    </div>
  );
}
