import { useEffect, useMemo, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import type { FC } from 'react';
import { CloudRain, ExternalLink, History, Landmark, LineChart, Percent, Radar as RadarIcon, Sparkles, X } from 'lucide-react';
import { api } from '../api/client';
import { askHref } from '../api/ai';
import type { DerivedSignalOut, IndicatorOut, PointOut, RadarOut, SourceStatusOut } from '../../lib/api/schema';
import { Sparkline } from '../Market';
import { compareDecimal, formatDecimal, formatIsoDate, formatInstant, formatMonth } from '../money';
import { Async, Card, Empty } from '../ui';
import { useApi } from '../useApi';

/*
 * Radar do Alternative Alpha (ADR-0012). Cada número mostra a fonte, a data de referência,
 * quando foi publicado e quando a Valyra coletou: são instantes diferentes, e o corte "ver como
 * estava em" só enxerga o que já tinha sido publicado naquele momento (sem data leakage).
 * Valores chegam como texto decimal e são exibidos como texto; Number() só desenha gráficos.
 */

// Brasília não tem horário de verão desde 2019: o deslocamento fixo converte o campo local.
const SAO_PAULO_OFFSET = '-03:00';

/** Valor de `datetime-local` (horário de Brasília) para ISO com fuso, aceito pela API. */
export function localToIso(local: string): string | undefined {
  return /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/.test(local) ? `${local}:00${SAO_PAULO_OFFSET}` : undefined;
}

type Theme = IndicatorOut['theme'];
type Filter = Theme | 'todos';

const THEMES: { id: Filter; label: string; Icon: typeof Landmark }[] = [
  { id: 'todos', label: 'Tudo', Icon: RadarIcon },
  { id: 'juros', label: 'Juros', Icon: Landmark },
  { id: 'inflacao', label: 'Inflação', Icon: Percent },
  { id: 'acoes', label: 'Ações', Icon: LineChart },
  { id: 'clima', label: 'Clima', Icon: CloudRain },
];
const THEME_LABEL: Record<Theme, string> = { juros: 'Juros', inflacao: 'Inflação', acoes: 'Ações', clima: 'Clima' };

const SELIC = 'bcb:sgs:432';
const CDI = 'bcb:sgs:12';
const IPCA = 'bcb:sgs:433';
// Sem coleta há mais de 3 dias, a fonte aparece como desatualizada (cobre fim de semana).
const STALE_HOURS = 72;

function referenceLabel(i: IndicatorOut, p: { observation_date: string }): string {
  return i.periodicity === 'monthly' ? formatMonth(p.observation_date.slice(0, 7)) : formatIsoDate(p.observation_date);
}

/** Tom só pela comparação de texto decimal com o ponto anterior, sem float. */
function tone(i: IndicatorOut): 'up' | 'down' | 'flat' {
  if (!i.previous || compareDecimal(i.latest.value, i.previous.value) === 0) return 'flat';
  return compareDecimal(i.latest.value, i.previous.value) > 0 ? 'up' : 'down';
}

/** Tom pelo próprio sinal do valor (variação do dia, anomalia de chuva). */
function signTone(value: string): 'up' | 'down' | 'flat' {
  const c = compareDecimal(value, '0');
  return c > 0 ? 'up' : c < 0 ? 'down' : 'flat';
}

const arrow = (t: 'up' | 'down' | 'flat') => (t === 'up' ? '▲' : t === 'down' ? '▼' : '■');

function hoursSince(asOf: string, instant: string): number {
  return Math.max(0, Math.floor((Date.parse(asOf) - Date.parse(instant)) / 3_600_000));
}

function ago(hours: number): string {
  if (hours < 1) return 'há menos de 1 h';
  if (hours < 48) return `há ${hours} h`;
  return `há ${Math.floor(hours / 24)} dias`;
}

/** Valores normalizados 0–100 só para o traço do gráfico. */
function shape(values: string[]): number[] {
  const nums = values.map(Number);
  const lo = Math.min(...nums);
  const span = Math.max(...nums) - lo || 1;
  return nums.map((v) => ((v - lo) * 100) / span);
}

const Stamp: FC<{ p: PointOut }> = ({ p }) => (
  <p className="ax-stamp">
    Publicado {formatInstant(p.published_at)} · coletado {formatInstant(p.ingested_at)}
    {p.published_at_estimated && <span className="ax-flag" title="Publicação estimada de forma conservadora na carga histórica">reconstituição ilustrativa</span>}
  </p>
);

const DetailsButton: FC<{ i: IndicatorOut; onOpen: (key: string) => void }> = ({ i, onOpen }) => (
  <button type="button" className="ax-more" onClick={() => onOpen(i.key)} aria-label={`Detalhes de ${i.title}`}>Detalhes</button>
);

/* ---------- Pulso: o resumo de uma linha ---------- */

const Pulse: FC<{ r: RadarOut }> = ({ r }) => {
  const find = (key: string) => r.indicators.find((i) => i.key === key);
  const selic = find(SELIC);
  const ipca = find(IPCA);
  const cdi = find(CDI);
  const climate = r.signals.filter((s) => s.theme === 'clima').length;
  const regions = new Set(r.indicators.filter((i) => i.theme === 'clima').map((i) => i.region?.slug)).size;
  const tile = (label: string, value: string, hint: string, t: 'up' | 'down' | 'flat' = 'flat') => (
    <div className={`ax-pulse__tile ax-pulse__tile--${t}`}>
      <dt>{label}</dt>
      <dd>{value}</dd>
      <span>{hint}</span>
    </div>
  );
  return (
    <dl className="ax-pulse" aria-label="Pulso econômico">
      {tile('Selic meta', selic ? `${formatDecimal(selic.latest.value)}%` : '—', selic ? `ao ano · ${referenceLabel(selic, selic.latest)}` : 'sem coleta', selic ? tone(selic) : 'flat')}
      {tile('IPCA do mês', ipca ? `${formatDecimal(ipca.latest.value)}%` : '—', ipca ? referenceLabel(ipca, ipca.latest) : 'sem coleta', ipca ? tone(ipca) : 'flat')}
      {tile('CDI', cdi ? `${formatDecimal(cdi.latest.value)}%` : '—', cdi ? `ao dia · ${referenceLabel(cdi, cdi.latest)}` : 'sem coleta')}
      {tile('Clima fora do padrão', regions ? `${climate} de ${regions}` : '—', regions ? 'regiões produtoras' : 'sem coleta', climate ? 'down' : 'flat')}
      {tile('Sinais', String(r.signals.length), 'por regras versionadas')}
    </dl>
  );
};

/* ---------- Seções por tema ---------- */

const MacroCard: FC<{ i: IndicatorOut; onOpen: (key: string) => void }> = ({ i, onOpen }) => {
  const t = tone(i);
  return (
    <article className={`ax-card ax-card--${t}`} aria-label={i.title}>
      <header className="ax-card__head">
        <h3>{i.title}</h3>
        {i.previous && <span className={`ax-delta ax-delta--${t}`}>{arrow(t)} antes {formatDecimal(i.previous.value)}</span>}
      </header>
      <p className="ax-card__value"><strong>{formatDecimal(i.latest.value)}</strong><small>{i.unit_label}</small></p>
      <Sparkline values={shape(i.history.map((h) => h.value))} width={240} height={44} className="ax-spark" />
      <footer className="ax-card__foot">
        <span>Referência: <b>{referenceLabel(i, i.latest)}</b></span>
        <DetailsButton i={i} onOpen={onOpen} />
      </footer>
      <Stamp p={i.latest} />
    </article>
  );
};

const StockRows: FC<{ items: IndicatorOut[]; onOpen: (key: string) => void }> = ({ items, onOpen }) => (
  <ul className="ax-stocks">
    {items.map((i) => {
      const t = signTone(i.latest.value);
      const ticker = i.title.split(':')[0];
      return (
        <li key={i.key} className={`ax-stock ax-stock--${t}`} aria-label={i.title}>
          <span className="ax-stock__ticker">{ticker}</span>
          <Sparkline values={shape(i.history.map((h) => h.value))} width={120} height={28} className="ax-spark ax-spark--mini" />
          <span className="ax-stock__value">{arrow(t)} {formatDecimal(i.latest.value)}%</span>
          <span className="ax-stock__date">{formatIsoDate(i.latest.observation_date)}</span>
          <DetailsButton i={i} onOpen={onOpen} />
        </li>
      );
    })}
  </ul>
);

/** Barra de -100% a +100%: onde a chuva recente está em relação à média de 10 anos. */
const AnomalyBar: FC<{ value: string }> = ({ value }) => {
  const n = Math.max(-100, Math.min(100, Number(value)));
  const left = n < 0 ? 50 + n / 2 : 50;
  const width = Math.abs(n) / 2;
  return (
    <div className="ax-anomaly" aria-hidden="true">
      <span className="ax-anomaly__zone" />
      <span className={`ax-anomaly__fill ax-anomaly__fill--${n < 0 ? 'dry' : 'wet'}`} style={{ left: `${left}%`, width: `${width}%` }} />
      <span className="ax-anomaly__mid" />
    </div>
  );
};

const RegionCard: FC<{ rain: IndicatorOut; anomaly?: IndicatorOut; onOpen: (key: string) => void }> = ({ rain, anomaly, onOpen }) => {
  const region = rain.region!;
  const value = anomaly?.latest.value;
  const t = value ? signTone(value) : 'flat';
  return (
    <article className="ax-card ax-region" aria-label={`Clima em ${region.name}`}>
      <header className="ax-card__head">
        <h3>{region.name}</h3>
        <span className="ax-chip">{region.production}</span>
      </header>
      <p className="ax-card__value"><strong>{formatDecimal(rain.latest.value)}</strong><small>mm em 30 dias</small></p>
      {value !== undefined ? (
        <>
          <AnomalyBar value={value} />
          <p className={`ax-region__vs ax-region__vs--${t === 'down' ? 'dry' : t === 'up' ? 'wet' : 'flat'}`}>
            {arrow(t)} {formatDecimal(value.replace('-', ''))}% {t === 'down' ? 'abaixo' : t === 'up' ? 'acima' : 'igual'} da média de 10 anos
          </p>
        </>
      ) : (
        <p className="ax-region__vs">Sem média comparável para esta janela.</p>
      )}
      <footer className="ax-card__foot">
        <span>Até <b>{formatIsoDate(rain.latest.observation_date)}</b></span>
        <DetailsButton i={anomaly ?? rain} onOpen={onOpen} />
      </footer>
    </article>
  );
};

/* ---------- Sinais e fontes ---------- */

function evidenceLabel(key: string, indicators: IndicatorOut[]): string | null {
  const ind = indicators.find((i) => key.startsWith(`${i.key}:`));
  if (!ind) return null;
  const date = key.slice(ind.key.length + 1);
  const point = ind.history.find((h) => h.observation_date === date);
  if (!point) return null;
  return `${ind.title} · ${referenceLabel(ind, point)}: ${formatDecimal(point.value)} ${ind.unit_label}`;
}

const SignalItem: FC<{ s: DerivedSignalOut; indicators: IndicatorOut[] }> = ({ s, indicators }) => {
  const evidence = s.evidence_keys.map((k) => evidenceLabel(k, indicators)).filter((x): x is string => x !== null);
  return (
    <li className={`ax-signal ax-signal--${s.theme}`}>
      <div className="ax-signal__top">
        <span className="ax-chip">{THEME_LABEL[s.theme]}</span>
        <small className="app-muted">{formatIsoDate(s.observation_date)}</small>
      </div>
      <p className="ax-signal__kind">Leitura da regra</p>
      <strong>{s.title}</strong>
      <p>{s.summary}</p>
      {evidence.length > 0 && (
        <>
          <p className="ax-signal__kind">Dados observados</p>
          <ul className="ax-evidence">{evidence.map((e) => <li key={e}>{e}</li>)}</ul>
        </>
      )}
      {s.limitations.length > 0 && (
        <ul className="ax-limits" aria-label="Limitações">{s.limitations.map((l) => <li key={l}>{l}</li>)}</ul>
      )}
      <div className="ax-signal__foot">
        <small className="app-muted">Regra {s.rule} · publicado {formatInstant(s.published_at)}</small>
        <a className="cx-why" href={askHref(`O que o sinal "${s.title}" mostra e quais dados sustentam isso?`)}>
          <Sparkles size={11} aria-hidden="true" />Por quê?
        </a>
      </div>
    </li>
  );
};

const SourceList: FC<{ items: SourceStatusOut[]; asOf: string }> = ({ items, asOf }) =>
  items.length ? (
    <ul className="ax-sources">
      {items.map(({ source, last_ingested_at, series_count }) => {
        const hours = last_ingested_at ? hoursSince(asOf, last_ingested_at) : null;
        const stale = hours === null || hours > STALE_HOURS;
        return (
          <li key={source.slug}>
            <div>
              <a className="app-link" href={source.url} target="_blank" rel="noreferrer">{source.name}<ExternalLink size={11} aria-hidden="true" /></a>
              <small>{source.license}</small>
            </div>
            <span className={`ax-health ax-health--${stale ? 'stale' : 'ok'}`}>
              {stale ? 'desatualizada' : 'em dia'}
              <small>{hours === null ? 'sem coleta' : ago(hours)} · {series_count === 1 ? '1 série' : `${series_count} séries`}</small>
            </span>
          </li>
        );
      })}
    </ul>
  ) : <Empty>Nenhuma fonte coletada até este corte.</Empty>;

/* ---------- Detalhe do indicador ---------- */

const DetailChart: FC<{ i: IndicatorOut }> = ({ i }) => {
  const W = 560;
  const H = 180;
  const values = i.history.map((h) => h.value);
  const ys = shape(values);
  const pts = ys.map((y, idx) => [16 + ((W - 32) * idx) / Math.max(ys.length - 1, 1), H - 16 - ((H - 32) * y) / 100] as const);
  const path = pts.map(([x, y], idx) => `${idx ? 'L' : 'M'}${x.toFixed(1)},${y.toFixed(1)}`).join(' ');
  const max = values.reduce((a, b) => (compareDecimal(a, b) >= 0 ? a : b));
  const min = values.reduce((a, b) => (compareDecimal(a, b) <= 0 ? a : b));
  const first = i.history[0];
  const last = i.history[i.history.length - 1];
  return (
    <figure className="ax-chart">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`Histórico de ${i.title}: de ${formatDecimal(first.value)} a ${formatDecimal(last.value)} ${i.unit_label}`}>
        <line x1="16" x2={W - 16} y1="16" y2="16" className="ax-chart__grid" />
        <line x1="16" x2={W - 16} y1={H - 16} y2={H - 16} className="ax-chart__grid" />
        {pts.length > 1 && <path d={path} className="ax-chart__line" />}
        {pts.map(([x, y], idx) => <circle key={idx} cx={x} cy={y} r={idx === pts.length - 1 ? 4 : 2} className="ax-chart__dot" />)}
      </svg>
      <figcaption>
        <span>Máx. {formatDecimal(max)} · mín. {formatDecimal(min)} {i.unit_label}</span>
        <span>{referenceLabel(i, first)} → {referenceLabel(i, last)} · {i.history.length} pontos</span>
      </figcaption>
    </figure>
  );
};

const Drawer: FC<{ i: IndicatorOut; onClose: () => void }> = ({ i, onClose }) => {
  const close = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    close.current?.focus();
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);
  const recent = [...i.history].reverse().slice(0, 8);
  const question = i.region
    ? `O que a chuva recente em ${i.region.name} mostra e com quais limites?`
    : `O que o indicador ${i.title} mostra hoje e com quais limites?`;
  // Portal na raiz do app (.cx): fica acima do cabeçalho e mantém os tokens do tema.
  const root = document.querySelector('.app-shell') ?? document.body;
  return createPortal(
    <div className="ax-drawer" role="presentation" onClick={onClose}>
      <aside className="ax-drawer__panel" role="dialog" aria-modal="true" aria-labelledby="ax-drawer-title" onClick={(e) => e.stopPropagation()}>
        <header className="ax-drawer__head">
          <div>
            <span className="ax-chip">{THEME_LABEL[i.theme]}</span>
            <h2 id="ax-drawer-title">{i.title}</h2>
            <p className="ax-card__value"><strong>{formatDecimal(i.latest.value)}</strong><small>{i.unit_label}</small></p>
          </div>
          <button ref={close} type="button" className="vx-icon-btn" onClick={onClose} aria-label="Fechar detalhes"><X size={18} /></button>
        </header>
        <DetailChart i={i} />
        <h3 className="ax-drawer__sub">Últimas observações</h3>
        <table className="ax-table">
          <thead><tr><th scope="col">Referência</th><th scope="col">Valor</th></tr></thead>
          <tbody>{recent.map((h) => <tr key={h.observation_date}><td>{referenceLabel(i, h)}</td><td>{formatDecimal(h.value)}</td></tr>)}</tbody>
        </table>
        <h3 className="ax-drawer__sub">Procedência do último valor</h3>
        <dl className="ax-prov">
          <div><dt>Referência</dt><dd>{referenceLabel(i, i.latest)}</dd></div>
          <div><dt>Revisão</dt><dd>{i.latest.revision_id}</dd></div>
          <div><dt>Publicado</dt><dd>{formatInstant(i.latest.published_at)}</dd></div>
          <div><dt>Coletado</dt><dd>{formatInstant(i.latest.ingested_at)}</dd></div>
          {i.latest.published_at_estimated && (
            <p className="ax-prov__flag"><span className="ax-flag">reconstituição ilustrativa</span> publicação estimada de forma conservadora na carga histórica</p>
          )}
          <div className="ax-prov__source">
            <dt>Fonte</dt>
            <dd>
              <a className="app-link" href={i.latest.source_url} target="_blank" rel="noreferrer">{i.source.name}<ExternalLink size={11} aria-hidden="true" /></a>
              <small>{i.source.license}</small>
            </dd>
          </div>
        </dl>
        <a className="button button--primary button--sm ax-drawer__ask" href={askHref(question)}><Sparkles size={14} aria-hidden="true" />Perguntar à Valyra</a>
      </aside>
    </div>,
    root,
  );
};

/* ---------- Página ---------- */

const Board: FC<{ r: RadarOut }> = ({ r }) => {
  const [filter, setFilter] = useState<Filter>('todos');
  const [open, setOpen] = useState<string | null>(null);
  const counts = useMemo(() => {
    const c: Record<Filter, number> = { todos: r.indicators.length, juros: 0, inflacao: 0, acoes: 0, clima: 0 };
    for (const i of r.indicators) c[i.theme] += 1;
    return c;
  }, [r]);
  const show = (t: Theme) => filter === 'todos' || filter === t;
  const macro = r.indicators.filter((i) => (i.theme === 'juros' || i.theme === 'inflacao') && show(i.theme));
  const stocks = show('acoes') ? r.indicators.filter((i) => i.theme === 'acoes') : [];
  const rains = show('clima') ? r.indicators.filter((i) => i.theme === 'clima' && i.unit === 'mm') : [];
  const anomalyOf = (slug?: string) => r.indicators.find((i) => i.theme === 'clima' && i.unit === '%' && i.region?.slug === slug);
  const signals = r.signals.filter((s) => show(s.theme));
  const selected = r.indicators.find((i) => i.key === open);

  return (
    <>
      <Pulse r={r} />
      <div className="ax-toolbar">
        <div className="ax-tabs" role="group" aria-label="Filtrar por tema">
          {THEMES.map(({ id, label, Icon }) => (
            <button key={id} type="button" className="ax-tab" aria-pressed={filter === id} disabled={id !== 'todos' && counts[id] === 0} onClick={() => setFilter(id)}>
              <Icon size={14} aria-hidden="true" />{label}<span className="ax-tab__count">{counts[id]}</span>
            </button>
          ))}
        </div>
        <p className="ax-status" role="status">
          {r.last_ingested_at
            ? <>Última coleta até o corte: <b>{formatInstant(r.last_ingested_at)}</b></>
            : 'Ainda não há coletas publicadas até este corte.'}
        </p>
      </div>

      <div className="ax-layout">
        <div className="ax-main">
          {r.indicators.length === 0 && <Empty>Nenhum indicador coletado até {formatInstant(r.as_of)}. A coleta roda de hora em hora no pregão e o clima, uma vez por dia.</Empty>}
          {macro.length > 0 && (
            <Card title="Juros e inflação · Banco Central">
              <div className="ax-grid">{macro.map((i) => <MacroCard key={i.key} i={i} onOpen={setOpen} />)}</div>
            </Card>
          )}
          {rains.length > 0 && (
            <Card title="Clima nas regiões produtoras">
              <p className="app-muted ax-note">Chuva acumulada nos últimos 30 dias contra a mesma janela nos 10 anos anteriores. Dado alternativo: ajuda a acompanhar o campo antes de ele aparecer nos preços.</p>
              <div className="ax-grid">{rains.map((i) => <RegionCard key={i.key} rain={i} anomaly={anomalyOf(i.region?.slug)} onOpen={setOpen} />)}</div>
            </Card>
          )}
          {stocks.length > 0 && (
            <Card title="Ações · variação do dia">
              <p className="app-muted ax-note">Cotação com cerca de 30 minutos de atraso na fonte gratuita.</p>
              <StockRows items={stocks} onOpen={setOpen} />
            </Card>
          )}
        </div>
        <div className="ax-side">
          <Card title="Sinais">
            {signals.length
              ? <ul className="ax-signals">{signals.map((s) => <SignalItem key={s.key} s={s} indicators={r.indicators} />)}</ul>
              : <Empty>Sem sinais com os dados publicados até este corte.</Empty>}
          </Card>
          <Card title="Fontes">
            <SourceList items={r.sources} asOf={r.as_of} />
          </Card>
        </div>
      </div>
      {selected && <Drawer i={selected} onClose={() => setOpen(null)} />}
    </>
  );
};

export const Alpha: FC = () => {
  const [local, setLocal] = useState('');
  const asOf = localToIso(local);
  const radar = useApi((sig) => api.getAlphaRadar(asOf, sig), [asOf]);

  return (
    <div className="app-stack app-stack--loose">
      <section className="ax-intro">
        <div>
          <span className="ax-intro__eyebrow"><RadarIcon size={14} aria-hidden="true" />Radar econômico</span>
          <h2>O contexto da economia, com origem e data</h2>
          <p className="app-muted">
            Juros e inflação do Banco Central, o movimento de quatro ações da B3 e a chuva em regiões produtoras de alimentos.
            É contexto para entender o cenário: não é recomendação de investimento e não explica, sozinho, os seus gastos.
          </p>
        </div>
        <label className="ax-replay">
          <span><History size={14} aria-hidden="true" />Ver como estava em</span>
          <input type="datetime-local" value={local} onChange={(e) => setLocal(e.target.value)} aria-describedby="ax-replay-hint" />
          <small id="ax-replay-hint" className="app-muted">Horário de Brasília. Só aparece o que já tinha sido publicado.</small>
          {local && <button type="button" className="button button--ghost button--sm" onClick={() => setLocal('')}>Voltar para agora</button>}
        </label>
      </section>

      <Async state={radar.state} onRetry={radar.reload}>
        {(r) => <Board r={r} />}
      </Async>
    </div>
  );
};
