import { useId, useState } from 'react';
import type { FC } from 'react';
import {
  Calculator, CircleAlert, CircleCheck, CircleDot, Database, FlaskConical, History, Info, Sparkles, Target, TrendingUp,
} from 'lucide-react';
import { api } from '../api/client';
import { askHref } from '../api/ai';
import type { ForecastOut, ForecastsOut, InputSeriesOut } from '../../lib/api/schema';
import { fanGeometry } from '../fanChart';
import { formatIsoDate, formatInstant, formatMonth, roundDecimal } from '../money';
import { localToIso } from './Alpha';
import { Async } from '../ui';
import { useApi } from '../useApi';
import { useProfile } from '../useProfile';
import './forecasts.css';

/*
 * Previsões da Valyra (ADR-0016). A calculadora e o narrador: a API calcula tudo em código
 * (modelo, 1.000 cenários, chance, teste com o passado) e esta tela só mostra. A "visão da
 * Valyra" vem de uma regra fixa sobre esses números e fica separada dos dados, para a pessoa
 * tirar as próprias conclusões. A Valyra AI, se chamada, só explica o resultado pronto.
 */

type Stance = ForecastOut['view']['stance'];
const STANCE: Record<Stance, { label: string; Icon: typeof CircleAlert }> = {
  atencao: { label: 'Atenção', Icon: CircleAlert },
  neutra: { label: 'Neutra', Icon: CircleDot },
  favoravel: { label: 'Favorável', Icon: CircleCheck },
};

const PROFILE_IDS = new Set(['orcamento-apertado', 'comecando-a-investir', 'investidor']);

function signed(value: string, places = 1): string {
  const text = roundDecimal(value, places);
  return text.startsWith('-') || /^0(,0+)?$/.test(text) ? text : `+${text}`;
}

function places(f: ForecastOut): number {
  return f.key === 'selic_6m' ? 2 : 1;
}

function headlineText(f: ForecastOut, v: string): string {
  return f.key === 'acoes_1m' || f.key === 'dolar_1m' || f.key === 'agro_6m' ? `${signed(v)}%` : `${roundDecimal(v, places(f))}%`;
}

function dayLabel(f: ForecastOut, iso: string): string {
  return f.method === 'holt_damped' ? formatMonth(iso.slice(0, 7)) : formatIsoDate(iso);
}

/* ---------- Gráfico em leque ---------- */

const FanChart: FC<{ f: ForecastOut }> = ({ f }) => {
  const g = fanGeometry(f, 640, 230);
  const titleId = useId();
  const first = f.history[0];
  const last = f.fan[f.fan.length - 1];
  return (
    <figure className="fx-chart">
      <svg viewBox={`0 0 ${g.width} ${g.height}`} role="img" aria-labelledby={titleId} preserveAspectRatio="none">
        <title id={titleId}>
          {`${f.title}: histórico até ${dayLabel(f, f.history[f.history.length - 1]?.day ?? '')} e leque de cenários até ${last ? dayLabel(f, last.day) : ''}, em ${f.chart_unit}.`}
        </title>
        {g.ticks.map((t) => (
          <g key={t.label} className="fx-chart__grid">
            <line x1={40} x2={g.width - 12} y1={t.y} y2={t.y} />
            <text x={34} y={t.y + 3.5} textAnchor="end">{t.label}</text>
          </g>
        ))}
        <rect className="fx-chart__future" x={g.nowX} y={8} width={g.width - 12 - g.nowX} height={g.height - 26} rx={8} />
        <path className="fx-chart__band95" d={g.band95} />
        <path className="fx-chart__band80" d={g.band80} />
        <path className="fx-chart__history" d={g.history} />
        <path className="fx-chart__median" d={g.median} />
        <line className="fx-chart__now" x1={g.nowX} x2={g.nowX} y1={8} y2={g.height - 18} />
        <text className="fx-chart__label" x={g.nowX - 6} y={20} textAnchor="end">hoje</text>
        <text className="fx-chart__label" x={g.nowX + 6} y={20}>cenários</text>
      </svg>
      <figcaption>
        <span>{first ? dayLabel(f, first.day) : ''}</span>
        <span className="fx-chart__unit">{f.chart_unit}</span>
        <span>{last ? dayLabel(f, last.day) : ''}</span>
      </figcaption>
    </figure>
  );
};

/* ---------- Dados e estatística ---------- */

const Stats: FC<{ f: ForecastOut }> = ({ f }) => {
  const p = places(f);
  const h = f.headline;
  return (
    <dl className="fx-stats">
      <div className="fx-stat fx-stat--main">
        <dt>Cenário central · {f.horizon_label}</dt>
        <dd>{headlineText(f, h.p50)}</dd>
        <span>{f.unit_label}</span>
      </div>
      <div className="fx-stat">
        <dt>Faixa provável (80%)</dt>
        <dd>{headlineText(f, h.p10)} a {headlineText(f, h.p90)}</dd>
        <span>8 de cada 10 cenários · 95%: {headlineText(f, h.p2_5)} a {headlineText(f, h.p97_5)}</span>
      </div>
      {f.chance && (
        <div className="fx-stat fx-stat--chance">
          <dt>Chance de {f.chance.event_label}</dt>
          <dd>{f.chance.pct}%</dd>
          <span className="fx-meter" aria-hidden="true"><i style={{ width: `${Math.min(100, Number(f.chance.pct))}%` }} /></span>
        </div>
      )}
      <div className="fx-stat">
        <dt>Hoje</dt>
        <dd>{f.key === 'acoes_1m' || f.key === 'dolar_1m' || f.key === 'agro_6m' ? `${signed(f.current)}%` : `${roundDecimal(f.current, p)}%`}</dd>
        <span>{f.current_label}</span>
      </div>
    </dl>
  );
};

const BacktestNote: FC<{ f: ForecastOut }> = ({ f }) => {
  const b = f.backtest;
  if (!b) return null;
  const share = Math.round((b.hits / b.trials) * 100);
  return (
    <div className="fx-backtest">
      <FlaskConical size={15} aria-hidden="true" />
      <p>
        <b>Teste com o passado:</b> refazendo a previsão {b.trials} vezes em datas antigas ({b.horizon_label}), a faixa de 80% acertou{' '}
        <b>{b.hits} de {b.trials}</b> ({share}%).
        {b.model_mae && b.naive_mae && (
          <> Erro médio do cenário central: {roundDecimal(b.model_mae, 2)} contra {roundDecimal(b.naive_mae, 2)} de só repetir o último valor.</>
        )}
      </p>
    </div>
  );
};

const OriginBadge: FC<{ origin: ForecastOut['data_origin'] }> = ({ origin }) =>
  origin === 'coleta'
    ? <span className="fx-origin fx-origin--real"><Database size={12} aria-hidden="true" />Dados públicos coletados</span>
    : <span className="fx-origin fx-origin--reserve"><Info size={12} aria-hidden="true" />{origin === 'misto' ? 'Parte em dados de reserva' : 'Dados de reserva sintéticos'}</span>;

const InputRow: FC<{ i: InputSeriesOut }> = ({ i }) => (
  <li>
    <b>{i.title}</b>
    <span>
      {i.observations} pontos, de {formatIsoDate(i.first_day)} a {formatIsoDate(i.last_day)} ·{' '}
      {i.origin === 'coleta' ? <a href={i.source.url} target="_blank" rel="noreferrer">{i.source.name}</a> : i.source.name}
    </span>
    {i.origin === 'coleta' && (
      <small>
        {i.last_published_at && <>Publicado até {formatInstant(i.last_published_at)}</>}
        {i.last_ingested_at && <> · coletado em {formatInstant(i.last_ingested_at)}</>}
        {i.published_at_estimated && <> · parte com publicação estimada</>}
      </small>
    )}
  </li>
);

const PARAM_LABEL: Record<string, string> = {
  alpha: 'α (peso do nível)', beta: 'β (peso da tendência)', phi: 'φ (amortecimento)', sigma: 'σ (erro típico de 1 passo)',
  daily_vol_pct: 'volatilidade diária (%)',
};

const Method: FC<{ f: ForecastOut }> = ({ f }) => (
  <details className="fx-method">
    <summary><Calculator size={14} aria-hidden="true" />Método, dados de entrada e limites</summary>
    <div className="fx-method__body">
      <p><b>{f.method_label}.</b> {f.paths.toLocaleString('pt-BR')} cenários simulados com os erros do próprio passado (versão {f.method_version}).</p>
      {Object.keys(f.params).length > 0 && (
        <ul className="fx-params">
          {Object.entries(f.params).map(([k, v]) => {
            const base = k.replace(/^(cdi|ipca)_/, '');
            const prefix = k.startsWith('cdi_') ? 'CDI · ' : k.startsWith('ipca_') ? 'IPCA · ' : '';
            return <li key={k}><span>{prefix}{PARAM_LABEL[base] ?? base}</span><b>{roundDecimal(String(v), 3)}</b></li>;
          })}
        </ul>
      )}
      <p className="fx-label">Dados de entrada</p>
      <ul className="fx-inputs">{f.inputs.map((i) => <InputRow key={i.key} i={i} />)}</ul>
      <p className="fx-label">Limites desta leitura</p>
      <ul className="fx-limits">{f.limitations.map((l) => <li key={l}>{l}</li>)}</ul>
    </div>
  </details>
);

const Tickers: FC<{ f: ForecastOut }> = ({ f }) =>
  f.tickers.length ? (
    <div className="fx-tickers">
      <p className="fx-label">Por ação, em 21 pregões</p>
      <table>
        <thead><tr><th scope="col">Ação</th><th scope="col">Faixa de 80%</th><th scope="col">Chance de alta</th><th scope="col">Oscilação diária</th></tr></thead>
        <tbody>
          {f.tickers.map((t) => (
            <tr key={t.ticker}>
              <th scope="row">{t.ticker}</th>
              <td>{signed(t.band.p10)}% a {signed(t.band.p90)}%</td>
              <td>{t.chance_up_pct}%</td>
              <td>{roundDecimal(t.daily_vol_pct, 1)}%</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  ) : null;

/* ---------- Visão da Valyra ---------- */

const ValyraView: FC<{ f: ForecastOut }> = ({ f }) => {
  const { label, Icon } = STANCE[f.view.stance];
  const question = `Explique a previsão "${f.title}" da Valyra: o que os números dizem e o que devo observar?`;
  return (
    <aside className={`fx-view fx-view--${f.view.stance}`} aria-label="Visão da Valyra">
      <span className="fx-view__eyebrow"><Sparkles size={13} aria-hidden="true" />Visão da Valyra</span>
      <span className="fx-view__stance"><Icon size={14} aria-hidden="true" />{label}</span>
      <h4>{f.view.headline}</h4>
      <p>{f.view.text}</p>
      <a className="fx-view__ask" href={askHref(question)}>
        <Sparkles size={14} aria-hidden="true" />Explicar com a Valyra AI
      </a>
      <small>Regra fixa ({f.view.rule}) sobre os números ao lado. Opinião da Valyra, não recomendação: a decisão é sua.</small>
    </aside>
  );
};

/* ---------- Composição ---------- */

const ForecastCard: FC<{ f: ForecastOut; index: number }> = ({ f, index }) => (
  <article className="fx-card" id={`previsao-${f.key}`} aria-labelledby={`fx-title-${f.key}`}>
    <header className="fx-card__head">
      <span className="fx-card__index">{String(index + 1).padStart(2, '0')}</span>
      <div>
        <p className="fx-card__question">{f.question}</p>
        <h3 id={`fx-title-${f.key}`}>{f.title}</h3>
      </div>
      <OriginBadge origin={f.data_origin} />
    </header>
    <div className="fx-card__body">
      <section className="fx-data" aria-label="Dados e estatística">
        <p className="fx-label"><TrendingUp size={13} aria-hidden="true" />Os dados e a estatística</p>
        <FanChart f={f} />
        <ul className="fx-legend" aria-hidden="true">
          <li><i className="fx-legend__history" />Observado</li>
          <li><i className="fx-legend__median" />Cenário central</li>
          <li><i className="fx-legend__band80" />80% dos cenários</li>
          <li><i className="fx-legend__band95" />95%</li>
        </ul>
        <Stats f={f} />
        <Tickers f={f} />
        <BacktestNote f={f} />
        <Method f={f} />
      </section>
      <ValyraView f={f} />
    </div>
  </article>
);

const Summary: FC<{ data: ForecastsOut }> = ({ data }) => (
  <nav className="fx-summary" aria-label="Resumo das previsões">
    {data.items.map((f) => {
      const { Icon } = STANCE[f.view.stance];
      return (
        <a key={f.key} href={`#previsao-${f.key}`} className={`fx-tile fx-tile--${f.view.stance}`}
          onClick={(e) => { e.preventDefault(); document.getElementById(`previsao-${f.key}`)?.scrollIntoView({ behavior: 'smooth', block: 'start' }); }}>
          <span className="fx-tile__title">{f.title}</span>
          {/* No passeio aleatório o centro é o próprio "hoje": a faixa é o que informa. */}
          <strong>{f.method === 'random_walk' ? `${headlineText(f, f.headline.p10)} a ${headlineText(f, f.headline.p90)}` : headlineText(f, f.headline.p50)}</strong>
          <span className="fx-tile__meta">
            {f.chance
              ? `${f.chance.pct}% de chance de ${f.chance.event_label}`
              : `faixa de 80%: ${headlineText(f, f.headline.p10)} a ${headlineText(f, f.headline.p90)}`}
          </span>
          <span className="fx-tile__view"><Icon size={13} aria-hidden="true" />{f.view.headline}</span>
        </a>
      );
    })}
  </nav>
);

const Board: FC<{ data: ForecastsOut }> = ({ data }) => {
  const reserve = data.items.some((f) => f.data_origin !== 'coleta');
  return (
    <>
      <Summary data={data} />
      {reserve && (
        <p className="fx-reserve-note" role="note">
          <Info size={15} aria-hidden="true" />
          Algumas previsões usam séries de reserva sintéticas porque a coleta ainda não tem histórico suficiente. Elas mostram o método
          funcionando, não o mercado real, e nunca vão para a Valyra AI como evidência.
        </p>
      )}
      <div className="fx-list">{data.items.map((f, i) => <ForecastCard key={f.key} f={f} index={i} />)}</div>
      <footer className="fx-notes">
        <p className="fx-label"><Target size={13} aria-hidden="true" />Como ler</p>
        <ul>{data.notes.map((n) => <li key={n}>{n}</li>)}</ul>
        <small className="app-muted">Calculado em {formatInstant(data.computed_at)} com o que estava publicado até {formatInstant(data.as_of)}.</small>
      </footer>
    </>
  );
};

export const Forecasts: FC = () => {
  const { profile } = useProfile();
  const profileId = PROFILE_IDS.has(profile.id) ? (profile.id as NonNullable<ForecastsOut['profile']>) : undefined;
  const [local, setLocal] = useState('');
  const asOf = localToIso(local);
  const forecasts = useApi((sig) => api.getForecasts(profileId, asOf, sig), [profileId, asOf]);

  return (
    <div className="app-stack app-stack--loose">
      <section className="fx-intro">
        <div>
          <span className="fx-intro__eyebrow"><Calculator size={14} aria-hidden="true" />Previsões da Valyra</span>
          <h2>{profileId ? `O que pode vir pela frente para o perfil ${profile.name.toLowerCase()}` : 'O que pode vir pela frente'}</h2>
          <p className="app-muted">
            Cada previsão é calculada em código a partir de dados públicos: um modelo estatístico simula 1.000 cenários e mostra o
            cenário central, a faixa provável e a chance de cada evento, com um teste contra o passado. Ao lado, separada dos dados,
            fica a visão da Valyra. Você vê os dois e decide.
          </p>
        </div>
        <label className="ax-replay">
          <span><History size={14} aria-hidden="true" />Ver como estava em</span>
          <input type="datetime-local" value={local} onChange={(e) => setLocal(e.target.value)} aria-describedby="fx-replay-hint" />
          <small id="fx-replay-hint" className="app-muted">Horário de Brasília. O modelo só usa o que já tinha sido publicado.</small>
          {local && <button type="button" className="button button--ghost button--sm" onClick={() => setLocal('')}>Voltar para agora</button>}
        </label>
      </section>

      <Async state={forecasts.state} onRetry={forecasts.reload}>
        {(data) => <Board data={data} />}
      </Async>
    </div>
  );
};
