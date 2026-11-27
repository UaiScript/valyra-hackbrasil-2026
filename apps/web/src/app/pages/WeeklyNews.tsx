import { useState } from 'react';
import type { FC } from 'react';
import {
  Activity, CloudRain, CreditCard, ExternalLink, Fuel, House, Landmark, LineChart, Loader2, Newspaper, ShoppingBasket, Sparkles, Sprout,
  TrendingUp, Wallet, Zap,
} from 'lucide-react';
import { ApiError, api, describeError } from '../api/client';
import { AI_MESSAGES, askHref, explain } from '../api/ai';
import type { ExplainResponse } from '../api/ai';
import type { BudgetReportOut, NewsItemOut, NewsThemeOut, RadarOut, SummaryOut, WeeklyNewsOut } from '../../lib/api/schema';
import { ROUTES } from '../router';
import { Answer } from './AskValyra';
import { BUDGET_STATUS_LABEL, usedPercent } from '../Budget';
import { compareDecimal, formatCents, formatDecimal, formatInstant } from '../money';
import { Async, Empty } from '../ui';
import { useApi } from '../useApi';
import { useProfile } from '../useProfile';
import { byPriority } from '../profiles';
import './news.css';

/*
 * Relatório semanal de notícias do Alternative Alpha (proposta da ADR-0013). A ligação
 * notícia → tema → categoria vem de uma regra versionada na API (news_theme_v3): é um
 * "pode mexer em", nunca causa ou previsão. Os valores do orçamento são os mesmos cálculos
 * Finance das outras telas, em centavos; esta tela não faz conta de dinheiro.
 */

const THEME_ICON: Record<string, typeof Fuel> = {
  acoes: LineChart,
  agro: Sprout,
  combustiveis: Fuel,
  contas: Zap,
  alimentos: ShoppingBasket,
  moradia: House,
  credito: CreditCard,
  renda: Wallet,
  juros: Landmark,
  inflacao: TrendingUp,
};

const SUMMARY_QUESTION =
  'Resuma as notícias desta semana e diga quais podem pesar no meu orçamento, citando a fonte e a data de cada uma.';

/** Data curta no horário de Brasília, ex.: "20/11". */
function shortDay(iso: string): string {
  return new Intl.DateTimeFormat('pt-BR', { timeZone: 'America/Sao_Paulo', day: '2-digit', month: '2-digit' }).format(new Date(iso));
}

type CategoryStatus = { slug: string; name: string; income: boolean; spent: number; limit?: number; status?: 'ok' | 'warning' | 'over' };

/** Junta orçamento (com limite) e resumo do mês (sem limite) por slug de categoria. */
function categoryIndex(budgets?: BudgetReportOut, summary?: SummaryOut): Map<string, CategoryStatus> {
  const index = new Map<string, CategoryStatus>();
  for (const c of summary?.categories ?? []) {
    // Resumo traz saídas negativas; o chip mostra o valor em módulo.
    const income = c.category.kind === 'income';
    index.set(c.category.slug, { slug: c.category.slug, name: c.category.name, income, spent: Math.abs(c.total_cents) });
  }
  for (const b of budgets?.items ?? []) {
    index.set(b.category.slug, { slug: b.category.slug, name: b.category.name, income: false, spent: b.spent_cents, limit: b.limit_cents, status: b.status });
  }
  return index;
}

const CategoryChip: FC<{ c: CategoryStatus }> = ({ c }) => (
  <li className={`nx-chip${c.status ? ` nx-chip--${c.status}` : ''}`}>
    <b>{c.name}</b>
    {c.limit !== undefined && c.status ? (
      <span>
        {formatCents(c.spent)} de {formatCents(c.limit)} · {usedPercent(c.spent, c.limit)}% <em>{BUDGET_STATUS_LABEL[c.status]}</em>
      </span>
    ) : (
      <span>{c.income ? `${formatCents(c.spent)} recebidos no mês` : `${formatCents(c.spent)} no mês, sem limite definido`}</span>
    )}
  </li>
);

/*
 * "O que os dados dizem": o dado observado do radar Alpha ao lado da manchete. Para ações,
 * a variação do dia dos tickers citados; para os outros temas, os sinais por regra do radar
 * e, sem sinal, o último valor de cada série. Nenhuma conta nem previsão é feita aqui.
 */
type Reading = { key: string; label: string; value?: string; tone?: 'up' | 'down' | 'flat' };

function radarReadings(t: NewsThemeOut, radar?: RadarOut): Reading[] {
  if (!radar || !t.radar_theme) return [];
  if (t.radar_theme === 'acoes') {
    const tickers = [...new Set(t.items.flatMap((n) => n.tickers))];
    return tickers.flatMap((ticker) => {
      const i = radar.indicators.find((ind) => ind.key === `brapi:${ticker}:change_pct`);
      if (!i) return [];
      const v = i.latest.value;
      const tone = compareDecimal(v, '0') > 0 ? 'up' : compareDecimal(v, '0') < 0 ? 'down' : 'flat';
      return [{ key: i.key, label: `${ticker} no dia`, value: `${formatDecimal(v)}%`, tone }];
    });
  }
  const signals = radar.signals.filter((sg) => sg.theme === t.radar_theme).slice(0, 2);
  if (signals.length) return signals.map((sg) => ({ key: sg.key, label: sg.title }));
  return radar.indicators
    .filter((i) => i.theme === t.radar_theme)
    .slice(0, 2)
    .map((i) => ({ key: i.key, label: i.title, value: `${formatDecimal(i.latest.value)} ${i.unit_label}` }));
}

const RadarContext: FC<{ readings: Reading[]; theme: string }> = ({ readings, theme }) => (
  <div className="nx-radar">
    <span className="nx-label">
      {theme === 'clima' ? <CloudRain size={12} aria-hidden="true" /> : <Activity size={12} aria-hidden="true" />}
      O que os dados dizem
    </span>
    <ul>
      {readings.map((r) => (
        <li key={r.key}>
          <span>{r.label}</span>
          {r.value && <b className={r.tone ? `nx-tone--${r.tone}` : undefined}>{r.value}</b>}
        </li>
      ))}
    </ul>
    <a className="nx-radar__link" href={ROUTES.alpha}>Ver no radar econômico</a>
  </div>
);

/**
 * Foto da manchete principal, servida pela própria fonte (a API só aceita https do domínio
 * dela). Carrega sob demanda, sem enviar de onde veio o clique; sem foto, ou se ela falhar,
 * entra um visual do tema feito só com CSS, sem arquivo extra para baixar.
 */
const NewsMedia: FC<{ n: NewsItemOut; themeKey: string; Icon: typeof Fuel }> = ({ n, themeKey, Icon }) => {
  const [failed, setFailed] = useState(false);
  const photo = n.image_url && !failed ? n.image_url : null;
  return (
    <a className={`nx-media nx-media--${themeKey}`} href={n.url} target="_blank" rel="noreferrer" tabIndex={-1} aria-hidden="true">
      {photo ? (
        <>
          <img src={photo} alt="" loading="lazy" decoding="async" referrerPolicy="no-referrer" width={640} height={360} onError={() => setFailed(true)} />
          <small className="nx-media__credit">Foto: {n.image_credit ?? n.source.name}</small>
        </>
      ) : (
        <span className="nx-media__art"><Icon size={40} strokeWidth={1.4} /></span>
      )}
    </a>
  );
};

const Headline: FC<{ n: NewsItemOut; theme: string; themeKey: string; Icon: typeof Fuel; lead?: boolean }> = ({ n, theme, themeKey, Icon, lead }) => (
  <li className={`nx-headline${lead ? ' nx-headline--lead' : ''}`}>
    {lead && <NewsMedia n={n} themeKey={themeKey} Icon={Icon} />}
    {n.tickers.length > 0 && (
      <span className="nx-tickers">{n.tickers.map((tk) => <i key={tk}>{tk}</i>)}</span>
    )}
    <a className="nx-headline__title" href={n.url} target="_blank" rel="noreferrer">
      {n.title}<ExternalLink size={12} aria-hidden="true" />
    </a>
    {n.summary && <p>{n.summary}</p>}
    <div className="nx-headline__meta">
      <span>{n.source.name}</span>
      <span aria-hidden="true">·</span>
      <time dateTime={n.published_at}>publicado em {formatInstant(n.published_at)}</time>
    </div>
    <div className="nx-headline__actions">
      <a className="nx-source-btn" href={n.url} target="_blank" rel="noreferrer" aria-label={`Ler na fonte: ${n.title} (abre em nova aba)`}>
        Ler na fonte<ExternalLink size={12} aria-hidden="true" />
      </a>
      <a className="cx-why" href={askHref(`A notícia "${n.title}" (${n.source.name}) pode afetar meu orçamento em ${theme.toLowerCase()}?`)}>
        <Sparkles size={11} aria-hidden="true" />Por quê?
      </a>
    </div>
  </li>
);

const ThemeCard: FC<{ t: NewsThemeOut; categories: Map<string, CategoryStatus>; radar?: RadarOut }> = ({ t, categories, radar }) => {
  const Icon = THEME_ICON[t.key] ?? Newspaper;
  const readings = radarReadings(t, radar);
  const linked = t.category_slugs.map((slug) => categories.get(slug)).filter((c): c is CategoryStatus => Boolean(c));
  return (
    <article className={`nx-theme nx-theme--${t.key}`} aria-label={t.title}>
      <header className="nx-theme__head">
        <span className="nx-theme__icon" aria-hidden="true"><Icon size={18} /></span>
        <div>
          <h3>{t.title}</h3>
          <small>{t.items.length === 1 ? '1 manchete' : `${t.items.length} manchetes`}</small>
        </div>
      </header>
      <p className="nx-theme__why"><b>Por que olhar:</b> {t.why}</p>
      {linked.length > 0 && (
        <div className="nx-theme__budget">
          <span className="nx-label">No seu orçamento deste mês</span>
          <ul className="nx-chips">{linked.map((c) => <CategoryChip key={c.slug} c={c} />)}</ul>
        </div>
      )}
      {readings.length > 0 && t.radar_theme && <RadarContext readings={readings} theme={t.radar_theme} />}
      <ul className="nx-headlines">
        {t.items.map((n, i) => <Headline key={n.signal_key} n={n} theme={t.title} themeKey={t.key} Icon={Icon} lead={i === 0} />)}
      </ul>
    </article>
  );
};

type Digest = { status: 'idle' } | { status: 'loading' } | { status: 'done'; response: ExplainResponse } | { status: 'error'; message: string };

/** Resumo da semana pela Valyra AI direto na tela, com as evidências citadas. */
const AiDigest: FC<{ accountId?: string }> = ({ accountId }) => {
  const [state, setState] = useState<Digest>({ status: 'idle' });
  async function run() {
    if (!accountId) return;
    setState({ status: 'loading' });
    try {
      setState({ status: 'done', response: await explain(accountId, SUMMARY_QUESTION) });
    } catch (err) {
      const message = err instanceof ApiError ? AI_MESSAGES[err.code] ?? describeError(err) : describeError(err);
      setState({ status: 'error', message });
    }
  }
  return (
    <section className="nx-digest" aria-label="Resumo da semana pela Valyra AI">
      <header>
        <span className="nx-digest__orb" aria-hidden="true"><Sparkles size={18} /></span>
        <div>
          <h3>Resumo da semana pela Valyra AI</h3>
          <p className="app-muted">Lê as manchetes e o seu orçamento como evidências e explica o que pode pesar. Cada citação aparece com fonte e data.</p>
        </div>
        {state.status !== 'done' && (
          <button type="button" className="button button--primary" onClick={run} disabled={!accountId || state.status === 'loading'}>
            {state.status === 'loading' ? <><Loader2 size={15} className="nx-spin" aria-hidden="true" />Lendo a semana…</> : <><Sparkles size={15} aria-hidden="true" />Gerar resumo</>}
          </button>
        )}
      </header>
      {state.status === 'error' && <p className="nx-digest__error" role="alert">{state.message}</p>}
      {state.status === 'done' && <Answer r={state.response} />}
    </section>
  );
};

const Report: FC<{ r: WeeklyNewsOut; categories: Map<string, CategoryStatus>; radar?: RadarOut; accountId?: string }> = ({ r, categories, radar, accountId }) => {
  const linked = r.total_items - r.unmatched_items;
  // Os temas que mais importam ao perfil sobem; o conteúdo de cada tema não muda.
  const { profile } = useProfile();
  const themes = byPriority(r.themes, (t) => t.key, profile.newsThemes);
  return (
    <>
      <section className="nx-hero">
        <div className="nx-hero__copy">
          <span className="nx-eyebrow"><Newspaper size={14} aria-hidden="true" />Relatório da semana<i>bônus</i></span>
          <h2>Sua semana em notícias</h2>
          <p className="app-muted">
            De {shortDay(r.week_start)} a {shortDay(r.as_of)}: as manchetes de fontes públicas que tocam o seu orçamento,
            cada uma com a fonte e a data. É contexto para decidir com calma, não recomendação de investimento.
          </p>
          <a className="button button--ghost nx-hero__cta" href={askHref(SUMMARY_QUESTION)}>
            <Sparkles size={15} aria-hidden="true" />Conversar sobre a semana
          </a>
        </div>
        <dl className="nx-stats">
          <div><dt>Manchetes lidas</dt><dd>{r.total_items}</dd></div>
          <div><dt>Ligadas ao orçamento</dt><dd>{linked}</dd></div>
          <div><dt>Temas</dt><dd>{r.themes.length}</dd></div>
        </dl>
      </section>

      {r.themes.length === 0 ? (
        <Empty>
          {r.total_items === 0
            ? 'Ainda não há manchetes coletadas nesta semana. A coleta roda três vezes ao dia.'
            : 'Nenhuma manchete da semana tocou os temas do seu orçamento.'}
        </Empty>
      ) : (
        <>
          <AiDigest accountId={accountId} />
          <div className="nx-grid">{themes.map((t) => <ThemeCard key={t.key} t={t} categories={categories} radar={radar} />)}</div>
        </>
      )}

      <footer className="nx-foot">
        <p>
          <b>Como a Valyra liga notícia e orçamento:</b> palavras-chave fixas e versionadas (regra <code>{r.rule}</code>) levam cada
          manchete a um tema, e o tema aponta as categorias que ele pode mexer. A Valyra AI só explica essas ligações e cita as
          manchetes; ela não cria números nem diz que uma notícia causou um gasto.
        </p>
        {r.sources.length > 0 && (
          <ul className="nx-sources">
            {r.sources.map((s) => (
              <li key={s.slug}>
                <a className="app-link" href={s.url} target="_blank" rel="noreferrer">{s.name}<ExternalLink size={11} aria-hidden="true" /></a>
                <small>{s.license}</small>
              </li>
            ))}
          </ul>
        )}
        <p className="app-muted">
          {r.last_ingested_at ? <>Última coleta: {formatInstant(r.last_ingested_at)}.</> : 'Sem coletas até agora.'}
          {r.unmatched_items > 0 && <> {r.unmatched_items} manchete(s) da semana não tocam o orçamento e ficaram fora.</>}
        </p>
      </footer>
    </>
  );
};

export const WeeklyNews: FC = () => {
  const report = useApi((s) => api.getWeeklyNews(undefined, s), []);
  const budgets = useApi((s) => api.getBudgets({}, s), []);
  const summary = useApi((s) => api.getSummary({}, s), []);
  const radar = useApi((s) => api.getAlphaRadar(undefined, s), []);
  const accounts = useApi((s) => api.listAccounts(s), []);
  // Orçamento e radar são complementos: se falharem, o relatório aparece sem chips nem dados.
  const categories = categoryIndex(budgets.state.data, summary.state.data);

  return (
    <div className="app-stack app-stack--loose nx">
      <Async state={report.state} onRetry={report.reload}>
        {(r) => <Report r={r} categories={categories} radar={radar.state.data} accountId={accounts.state.data?.items[0]?.id} />}
      </Async>
    </div>
  );
};
