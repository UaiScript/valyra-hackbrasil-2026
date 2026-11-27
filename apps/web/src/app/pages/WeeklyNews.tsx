import type { FC } from 'react';
import {
  CreditCard, ExternalLink, Fuel, House, Landmark, Newspaper, ShoppingBasket, Sparkles, TrendingUp, Wallet, Zap,
} from 'lucide-react';
import { api } from '../api/client';
import { askHref } from '../api/ai';
import type { BudgetReportOut, NewsItemOut, NewsThemeOut, SummaryOut, WeeklyNewsOut } from '../../lib/api/schema';
import { BUDGET_STATUS_LABEL, usedPercent } from '../Budget';
import { formatCents, formatInstant } from '../money';
import { Async, Empty } from '../ui';
import { useApi } from '../useApi';
import './news.css';

/*
 * Relatório semanal de notícias do Alternative Alpha (proposta da ADR-0013). A ligação
 * notícia → tema → categoria vem de uma regra versionada na API (news_theme_v1): é um
 * "pode mexer em", nunca causa ou previsão. Os valores do orçamento são os mesmos cálculos
 * Finance das outras telas, em centavos; esta tela não faz conta de dinheiro.
 */

const THEME_ICON: Record<string, typeof Fuel> = {
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

const Headline: FC<{ n: NewsItemOut; theme: string }> = ({ n, theme }) => (
  <li className="nx-headline">
    <a className="nx-headline__title" href={n.url} target="_blank" rel="noreferrer">
      {n.title}<ExternalLink size={12} aria-hidden="true" />
    </a>
    {n.summary && <p>{n.summary}</p>}
    <div className="nx-headline__meta">
      <span>{n.source.name}</span>
      <span aria-hidden="true">·</span>
      <time dateTime={n.published_at}>publicado em {formatInstant(n.published_at)}</time>
      <a className="cx-why" href={askHref(`A notícia "${n.title}" (${n.source.name}) pode afetar meu orçamento em ${theme.toLowerCase()}?`)}>
        <Sparkles size={11} aria-hidden="true" />Por quê?
      </a>
    </div>
  </li>
);

const ThemeCard: FC<{ t: NewsThemeOut; categories: Map<string, CategoryStatus> }> = ({ t, categories }) => {
  const Icon = THEME_ICON[t.key] ?? Newspaper;
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
      <ul className="nx-headlines">{t.items.map((n) => <Headline key={n.signal_key} n={n} theme={t.title} />)}</ul>
    </article>
  );
};

const Report: FC<{ r: WeeklyNewsOut; categories: Map<string, CategoryStatus> }> = ({ r, categories }) => {
  const linked = r.total_items - r.unmatched_items;
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
          <a className="button button--primary nx-hero__cta" href={askHref(SUMMARY_QUESTION)}>
            <Sparkles size={15} aria-hidden="true" />Resumir com a Valyra AI
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
        <div className="nx-grid">{r.themes.map((t) => <ThemeCard key={t.key} t={t} categories={categories} />)}</div>
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
  // Orçamento é complemento: se falhar, o relatório aparece sem os chips de categoria.
  const categories = categoryIndex(budgets.state.data, summary.state.data);

  return (
    <div className="app-stack app-stack--loose nx">
      <Async state={report.state} onRetry={report.reload}>
        {(r) => <Report r={r} categories={categories} />}
      </Async>
    </div>
  );
};
