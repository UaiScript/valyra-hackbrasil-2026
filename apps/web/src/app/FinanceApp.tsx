import { Suspense, lazy, useCallback, useEffect, useState } from 'react';
import type { FC } from 'react';
import { ArrowLeft, Bell, Calculator, ChartPie, ChartSpline, Command, Compass, LayoutDashboard, ListOrdered, Menu, Newspaper, PanelLeftClose, PanelLeftOpen, Sparkles, Target, Upload, X } from 'lucide-react';
import { api } from './api/client';
import { ROUTES, routeFromHash, useHash } from './router';
import type { AppRoute } from './router';
import { useApi } from './useApi';
import { Overview } from './pages/Overview';
import { ALERTS_CHANGED } from './alertsEvents';
import { LogoMark } from '../components/LogoMark';
import { MODULES, ModuleBadge } from './modules';
import type { ModuleId } from './modules';
import { ProfileMenu } from './ProfileUI';
import { ProfileProvider, useProfile } from './useProfile';
import { ChatPanel, ValyraChatProvider, questionFromHref, useValyraChat } from './ValyraChat';
import { AlertsPopover } from './AlertsPopover';
import './cockpit.css';
import './app.css';

/*
 * A Central vem no pacote inicial; as outras telas viram pedaços separados, carregados
 * na primeira visita. Logo depois que a Central aparece, o navegador baixa esses pedaços
 * no tempo ocioso: a primeira tela abre mais rápido e a navegação continua instantânea.
 */
const PAGE_LOADERS = {
  transactions: () => import('./pages/Transactions').then((m) => ({ default: m.Transactions })),
  summary: () => import('./pages/Summary').then((m) => ({ default: m.Summary })),
  budgets: () => import('./pages/Budgets').then((m) => ({ default: m.Budgets })),
  projection: () => import('./pages/Projection').then((m) => ({ default: m.Projection })),
  alerts: () => import('./pages/Alerts').then((m) => ({ default: m.Alerts })),
  ai: () => import('./pages/AskValyra').then((m) => ({ default: m.AskValyra })),
  alpha: () => import('./pages/Alpha').then((m) => ({ default: m.Alpha })),
  news: () => import('./pages/WeeklyNews').then((m) => ({ default: m.WeeklyNews })),
  forecasts: () => import('./pages/Forecasts').then((m) => ({ default: m.Forecasts })),
  import: () => import('./pages/ImportCsv').then((m) => ({ default: m.ImportCsv })),
} as const;
const PAGES = Object.fromEntries(Object.entries(PAGE_LOADERS).map(([k, load]) => [k, lazy(load)])) as Record<keyof typeof PAGE_LOADERS, ReturnType<typeof lazy>>;

function usePrefetchPages() {
  useEffect(() => {
    const run = () => { for (const load of Object.values(PAGE_LOADERS)) void load().catch(() => undefined); };
    const w = window as Window & { requestIdleCallback?: (cb: () => void, opts?: { timeout: number }) => number; cancelIdleCallback?: (id: number) => void };
    if (w.requestIdleCallback) {
      const id = w.requestIdleCallback(run, { timeout: 4000 });
      return () => w.cancelIdleCallback?.(id);
    }
    const id = window.setTimeout(run, 1500);
    return () => window.clearTimeout(id);
  }, []);
}

type NavItem = { route: AppRoute; label: string; icon: typeof LayoutDashboard };

// Agrupado pelos módulos da landing, com os mesmos nomes: a navegação mostra que as telas
// são partes de três produtos (Valyra Finance, Alternative Alpha e Valyra AI), não telas soltas.
const NAV_GROUPS: { module: ModuleId; items: NavItem[] }[] = [
  {
    module: 'finance',
    items: [
      { route: 'overview', label: 'Central', icon: LayoutDashboard },
      { route: 'summary', label: 'Resumo do mês', icon: ChartPie },
      { route: 'budgets', label: 'Orçamento', icon: Target },
      { route: 'projection', label: 'Projeção de caixa', icon: ChartSpline },
      { route: 'transactions', label: 'Transações', icon: ListOrdered },
      { route: 'alerts', label: 'Alertas', icon: Bell },
      { route: 'import', label: 'Importar CSV', icon: Upload },
    ],
  },
  {
    module: 'alpha',
    items: [
      { route: 'alpha', label: 'Radar econômico', icon: Compass },
      { route: 'forecasts', label: 'Previsões', icon: Calculator },
      { route: 'news', label: 'Relatório da semana', icon: Newspaper },
    ],
  },
  {
    module: 'ai',
    items: [{ route: 'ai', label: 'Pergunte ao Valyra', icon: Sparkles }],
  },
];
const NAV: (NavItem & { module: ModuleId })[] = NAV_GROUPS.flatMap((g) => g.items.map((i) => ({ ...i, module: g.module })));

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
  return <ProfileProvider><ProfileShell /></ProfileProvider>;
}

/**
 * Trocar de perfil é trocar de cliente: remontar descarta estado e dados do anterior,
 * inclusive a conversa com a Valyra AI, que fica dentro da mesma chave.
 */
function ProfileShell() {
  const { profile } = useProfile();
  return <ValyraChatProvider key={profile.id}><Shell /></ValyraChatProvider>;
}

// Menu lateral largo (ícones + nomes) ou só ícones: preferência de visualização guardada
// no navegador; sem armazenamento, volta ao padrão só ícones.
const NAV_WIDE_KEY = 'valyra:nav-wide';
function readNavWide(): boolean {
  try { return window.localStorage.getItem(NAV_WIDE_KEY) === '1'; } catch { return false; }
}
function writeNavWide(wide: boolean) {
  try { window.localStorage.setItem(NAV_WIDE_KEY, wide ? '1' : '0'); } catch { /* vale só nesta visita */ }
}

function Shell() {
  const route = routeFromHash(useHash());
  const { profile, chosen } = useProfile();
  // O menu segue a ordem de módulos do perfil: o foco do cliente aparece primeiro.
  const groups = profile.modules.map((m) => NAV_GROUPS.find((g) => g.module === m)!);
  const [menuOpen, setMenuOpen] = useState(false);
  const [navWide, setNavWide] = useState(readNavWide);
  const [alertsOpen, setAlertsOpen] = useState(false);
  const { openPanel } = useValyraChat();
  const closeAlerts = useCallback(() => setAlertsOpen(false), []);
  const current = NAV.find((n) => n.route === route)!;
  const newAlerts = useNewAlertCount(route);
  usePrefetchPages();
  const Page = route === 'overview' ? null : PAGES[route];

  useEffect(() => {
    document.documentElement.lang = 'pt-BR';
    document.title = `${current.label} · Valyra`;
    setMenuOpen(false);
    setAlertsOpen(false);
  }, [current.label]);

  /*
   * Links para a Valyra AI e para Alertas abrem a barra de chat e a janela de alertas em
   * vez de trocar de tela. A interceptação é central para valer em todo atalho do app
   * ("Por quê?", radar, sugestões do perfil) sem mexer em cada link. Links marcados com
   * data-full (tela cheia, "ver todos") e cliques com Ctrl/⌘/Shift seguem para a página.
   */
  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
      const link = (e.target as Element | null)?.closest?.('a[href]');
      if (!link || link.hasAttribute('data-full')) return;
      const href = link.getAttribute('href') ?? '';
      if (href === ROUTES.ai || href.startsWith(`${ROUTES.ai}?`)) {
        if (route === 'ai') return;
        e.preventDefault();
        setMenuOpen(false);
        setAlertsOpen(false);
        openPanel(questionFromHref(href));
      } else if (href === ROUTES.alerts) {
        if (route === 'alerts') return;
        e.preventDefault();
        setMenuOpen(false);
        setAlertsOpen(true);
      }
    };
    document.addEventListener('click', onClick);
    return () => document.removeEventListener('click', onClick);
  }, [route, openPanel]);

  // Atalho de teclado da barra de comando: Ctrl/⌘+K abre a pergunta à IA.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        if (route === 'ai') document.getElementById('cx-question')?.focus();
        else { setAlertsOpen(false); openPanel(); }
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [route, openPanel]);

  return (
    <div className={`app-shell cx${navWide ? ' cx--nav-wide' : ''}`}>
      <aside className={`app-sidebar${menuOpen ? ' app-sidebar--open' : ''}`} aria-label="Módulos">
        <a href={ROUTES.overview} className="cx-brand" aria-label="Valyra — central">
          <span className="cx-brand__mark" aria-hidden="true"><LogoMark size={30} /></span>
          <span className="cx-brand__text"><b>Valyra</b><small>Inteligência financeira</small></span>
        </a>
        <nav className="cx-nav">
          {groups.map((group, index) => (
            <div key={group.module} className={`cx-nav__group cx-nav__group--${group.module}`}>
              <span className="cx-nav__title"><ModuleBadge id={group.module} compact />{chosen && index === 0 && <span className="cx-nav__focus" title={`Foco do perfil ${profile.name}`}>Foco</span>}</span>
              {group.items.map(({ route: r, label, icon: Icon }) => (
                <a key={r} href={ROUTES[r]} aria-current={r === route ? 'page' : undefined} data-tip={`${MODULES[group.module].title} · ${label}`}>
                  <Icon size={19} aria-hidden="true" /><span className="cx-nav__label">{label}</span>
                  {r === 'alerts' && newAlerts > 0 && <span className="app-nav__count" aria-label={`${newAlerts} novos`}>{newAlerts}</span>}
                </a>
              ))}
            </div>
          ))}
        </nav>
        <div className="cx-sidebar__foot">
          <button type="button" className="app-nav__back cx-nav-toggle" aria-pressed={navWide} data-tip={navWide ? 'Recolher menu' : 'Expandir menu'}
            onClick={() => setNavWide((w) => { writeNavWide(!w); return !w; })}>
            {navWide ? <PanelLeftClose size={18} aria-hidden="true" /> : <PanelLeftOpen size={18} aria-hidden="true" />}
            <span className="cx-nav__label">{navWide ? 'Recolher menu' : 'Expandir menu'}</span>
          </button>
          <a className="app-nav__back" href="#top" data-tip="Voltar à landing"><ArrowLeft size={18} aria-hidden="true" /><span className="cx-nav__label">Voltar à landing</span></a>
        </div>
      </aside>
      <div className="app-main">
        <header className="app-header cx-header">
          <button type="button" className="app-menu-toggle button button--ghost button--sm" aria-expanded={menuOpen} aria-label={menuOpen ? 'Fechar menu' : 'Abrir menu'} onClick={() => setMenuOpen((o) => !o)}>
            {menuOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
          <div className="cx-header__title">
            <span className="cx-crumb"><ModuleBadge id={current.module} /></span>
            <h1>{current.label}</h1>
          </div>
          <a className="cx-command" href={ROUTES.ai} aria-label="Pergunte ao Valyra (Ctrl+K)">
            <Sparkles size={15} aria-hidden="true" />
            <span>Pergunte sobre seu dinheiro…</span>
            <kbd><Command size={11} aria-hidden="true" />K</kbd>
          </a>
          <ApiStatus route={route} />
          <div className="cx-alerts-anchor">
            <button type="button" className="cx-icon-link" data-alerts-trigger aria-expanded={alertsOpen} aria-haspopup="dialog"
              aria-label={newAlerts ? `Alertas, ${newAlerts} novos` : 'Alertas'} onClick={() => setAlertsOpen((o) => !o)}>
              <Bell size={18} aria-hidden="true" />{newAlerts > 0 && <span className="cx-icon-link__dot" aria-hidden="true" />}
            </button>
            <AlertsPopover open={alertsOpen} onClose={closeAlerts} />
          </div>
          <ProfileMenu />
        </header>
        <main className="app-content" id="main">
          {Page ? (
            <Suspense fallback={<div className="cx-page-loading" role="status" aria-label="Carregando tela" />}>
              <Page />
            </Suspense>
          ) : <Overview />}
          <p className="cx-footnote" role="note">
            {route === 'alpha'
              ? 'Dados públicos do Banco Central, da brapi.dev e da Open-Meteo, com fonte e instante de coleta. Contexto econômico, não recomendação de investimento.'
              : route === 'forecasts'
              ? 'Previsões calculadas em código sobre dados públicos do Banco Central e da brapi.dev, com 1.000 cenários e teste com o passado. Leitura estatística, não recomendação de investimento.'
              : route === 'news'
              ? 'Manchetes da Agência Brasil, do Banco Central e do IBGE, com fonte e data e link para a matéria original. Contexto, não recomendação de investimento.'
              : chosen
                ? `Ambiente de demonstração: cliente fictício do perfil ${profile.name}, com extrato sintético, sem login. Todo número vem de um cálculo auditável da API.`
                : 'Ambiente de demonstração: usuário demo e dados sintéticos, sem login. Todo número vem de um cálculo auditável da API.'}
          </p>
        </main>
      </div>
      <ChatPanel />
    </div>
  );
}
