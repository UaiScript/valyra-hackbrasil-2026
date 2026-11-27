import { useState } from 'react';
import type { FC } from 'react';
import { ExternalLink, History, Radar as RadarIcon, Sparkles } from 'lucide-react';
import { api } from '../api/client';
import { askHref } from '../api/ai';
import type { DerivedSignalOut, IndicatorOut, PointOut } from '../../lib/api/schema';
import { Sparkline } from '../Market';
import { compareDecimal, formatDecimal, formatIsoDate, formatInstant, formatMonth } from '../money';
import { Async, Card, Empty } from '../ui';
import { useApi } from '../useApi';

/*
 * Radar do Alternative Alpha (ADR-0012). Cada número mostra a fonte, a data de referência,
 * quando foi publicado e quando a Valyra coletou: são instantes diferentes, e o corte "ver como
 * estava em" só enxerga o que já tinha sido publicado naquele momento (sem data leakage).
 */

// Brasília não tem horário de verão desde 2019: o deslocamento fixo converte o campo local.
const SAO_PAULO_OFFSET = '-03:00';

/** Valor de `datetime-local` (horário de Brasília) para ISO com fuso, aceito pela API. */
export function localToIso(local: string): string | undefined {
  return /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/.test(local) ? `${local}:00${SAO_PAULO_OFFSET}` : undefined;
}

const isMonthly = (i: IndicatorOut) => i.key === 'bcb:sgs:433';

function referenceLabel(i: IndicatorOut, p: PointOut): string {
  return isMonthly(i) ? formatMonth(p.observation_date.slice(0, 7)) : formatIsoDate(p.observation_date);
}

/** Tom só pela comparação de texto decimal com o ponto anterior, sem float. */
function tone(i: IndicatorOut): 'up' | 'down' | 'flat' {
  if (!i.previous) return 'flat';
  const a = i.latest.value;
  const b = i.previous.value;
  if (a === b) return 'flat';
  return compareDecimal(a, b) > 0 ? 'up' : 'down';
}

const Provenance: FC<{ p: PointOut; label: string; source: IndicatorOut['source'] }> = ({ p, label, source }) => (
  <dl className="ax-prov">
    <div><dt>Referência</dt><dd>{label}</dd></div>
    <div>
      <dt>Publicado</dt>
      <dd>{formatInstant(p.published_at)}</dd>
    </div>
    {p.published_at_estimated && (
      <p className="ax-prov__flag"><span className="ax-flag">reconstituição ilustrativa</span> publicação estimada pelo calendário oficial, na carga histórica</p>
    )}
    <div><dt>Coletado</dt><dd>{formatInstant(p.ingested_at)}</dd></div>
    <div className="ax-prov__source">
      <dt>Fonte</dt>
      <dd>
        <a className="app-link" href={p.source_url} target="_blank" rel="noreferrer">{source.name}<ExternalLink size={11} aria-hidden="true" /></a>
        <small>{source.license}{p.revision_id > 1 ? ` · revisão ${p.revision_id}` : ''}</small>
      </dd>
    </div>
  </dl>
);

const IndicatorCard: FC<{ i: IndicatorOut }> = ({ i }) => {
  const t = tone(i);
  // Number() só desenha a linha; o valor exibido é sempre o texto decimal da fonte.
  const values = i.history.map((h) => Number(h.value));
  const lo = Math.min(...values);
  const span = Math.max(...values) - lo || 1;
  return (
    <article className={`ax-card ax-card--${t}`} aria-label={i.title}>
      <header className="ax-card__head">
        <h3>{i.title}</h3>
        {i.previous && (
          <span className={`ax-delta ax-delta--${t}`}>
            {t === 'up' ? '▲' : t === 'down' ? '▼' : '■'} antes {formatDecimal(i.previous.value)}
          </span>
        )}
      </header>
      <p className="ax-card__value">
        <strong>{formatDecimal(i.latest.value)}</strong>
        <small>{i.unit_label}</small>
      </p>
      <Sparkline values={values.map((v) => ((v - lo) * 100) / span)} width={240} height={44} className="ax-spark" />
      <Provenance p={i.latest} label={referenceLabel(i, i.latest)} source={i.source} />
    </article>
  );
};

const SignalItem: FC<{ s: DerivedSignalOut }> = ({ s }) => (
  <li className="ax-signal">
    <div>
      <strong>{s.title}</strong>
      <p>{s.summary}</p>
      <small className="app-muted">Regra {s.rule} · publicado em {formatInstant(s.published_at)}</small>
    </div>
    <a className="cx-why" href={askHref(`O que o sinal "${s.title}" mostra e quais dados sustentam isso?`)}>
      <Sparkles size={11} aria-hidden="true" />Por quê?
    </a>
  </li>
);

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
            Selic, CDI e IPCA do Banco Central e o movimento do dia de quatro ações da B3. É contexto para entender o cenário:
            não é recomendação de investimento e não explica, sozinho, os seus gastos.
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
        {(r) => {
          const macro = r.indicators.filter((i) => i.kind === 'macro_indicator');
          const stocks = r.indicators.filter((i) => i.kind !== 'macro_indicator');
          return (
            <>
              <p className="ax-status" role="status">
                {r.last_ingested_at
                  ? <>Última coleta até o corte: <b>{formatInstant(r.last_ingested_at)}</b>. Se uma fonte falhar, o radar fica desatualizado, nunca com dado inventado.</>
                  : 'Ainda não há coletas publicadas até este corte.'}
              </p>
              {r.indicators.length === 0 ? (
                <Empty>Nenhum indicador coletado até {formatInstant(r.as_of)}. A coleta roda de hora em hora no pregão.</Empty>
              ) : (
                <>
                  {macro.length > 0 && (
                    <Card title="Indicadores do Banco Central">
                      <div className="ax-grid">{macro.map((i) => <IndicatorCard key={i.key} i={i} />)}</div>
                    </Card>
                  )}
                  {stocks.length > 0 && (
                    <Card title="Ações: variação do dia">
                      <p className="app-muted ax-note">Cotação com cerca de 30 minutos de atraso na fonte gratuita.</p>
                      <div className="ax-grid ax-grid--stocks">{stocks.map((i) => <IndicatorCard key={i.key} i={i} />)}</div>
                    </Card>
                  )}
                </>
              )}
              <Card title="Sinais">
                {r.signals.length
                  ? <ul className="ax-signals">{r.signals.map((s) => <SignalItem key={s.key} s={s} />)}</ul>
                  : <Empty>Sem sinais com os dados publicados até este corte.</Empty>}
              </Card>
            </>
          );
        }}
      </Async>
    </div>
  );
};
