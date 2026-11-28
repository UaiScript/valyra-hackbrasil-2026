import type { FC } from 'react';
import { CircleHelp, ShieldCheck } from 'lucide-react';
import { formatEvidenceValue } from './api/ai';
import type { EvidenceItem, ExplainResponse } from './api/ai';
import type { AlphaSignalSource, CalculationSource, FinanceRecordSource } from '../lib/api/schema';
import { formatIsoDate } from './money';

/* Resposta da Valyra AI com evidências e limitações; usada na barra de chat e na tela cheia. */

const BASIS_LABEL: Record<EvidenceItem['basis'], string> = {
  observed: 'Observado',
  projected: 'Previsto',
  reference: 'Referência',
};

function formatPeriod(p: EvidenceItem['period']): string {
  return p.start === p.end ? formatIsoDate(p.start) : `${formatIsoDate(p.start)} a ${formatIsoDate(p.end)}`;
}

/** Instante UTC da API para data e hora locais de São Paulo, só para leitura. */
function formatInstant(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString('pt-BR', { timeZone: 'America/Sao_Paulo', dateStyle: 'short', timeStyle: 'short' });
}

const EvidenceOrigin: FC<{ evidence: EvidenceItem }> = ({ evidence }) => {
  // O gerador mantém esta união como unknown; reconhecemos somente as origens do contrato.
  const source = evidence.source as Partial<AlphaSignalSource & CalculationSource & FinanceRecordSource> | null;
  if (!source || typeof source !== 'object') return null;
  if (source.kind === 'alpha_signal') {
    let url: URL | undefined;
    try {
      const candidate = new URL(source.source_url ?? '');
      if (candidate.protocol === 'https:' || candidate.protocol === 'http:') url = candidate;
    } catch { /* Uma origem sem URL válida continua mostrando a data, sem link. */ }
    return <small className="cx-evidence__source">
      {url && <a className="app-link" href={url.href} target="_blank" rel="noopener noreferrer">Consultar fonte original · {url.hostname}</a>}
      {source.published_at && <span>{source.published_at_estimated ? 'Publicação estimada em ' : 'Publicado em '}<time dateTime={source.published_at}>{formatInstant(source.published_at)}</time></span>}
    </small>;
  }
  if (source.kind === 'calculation' && source.computed_at) {
    return <small className="cx-evidence__source">Calculado pelo {source.module === 'finance' ? 'Finance' : 'Alpha'} em <time dateTime={source.computed_at}>{formatInstant(source.computed_at)}</time></small>;
  }
  if (source.kind === 'finance_record' && source.recorded_at) {
    return <small className="cx-evidence__source">Registro {source.record_type === 'account' ? 'da conta' : 'da movimentação'} em <time dateTime={source.recorded_at}>{formatInstant(source.recorded_at)}</time></small>;
  }
  return null;
};

export const Answer: FC<{ r: ExplainResponse }> = ({ r }) => (
  <div className="cx-answer">
    <div className="cx-answer__meta">
      <span className={`cx-uncertainty cx-uncertainty--${r.uncertainty === 'média' ? 'media' : r.uncertainty}`}>Incerteza {r.uncertainty}</span>
      <span>Dados até {formatInstant(r.as_of)}</span>
    </div>
    <p className="cx-answer__text">{r.answer}</p>
    {r.evidences.length > 0 && (
      <section className="cx-evidences" aria-label="Evidências citadas">
        <h3><ShieldCheck size={14} aria-hidden="true" />Evidências citadas ({r.evidences.length})</h3>
        <ul>
          {r.evidences.map((e) => (
            <li key={e.evidence_id}>
              <span className={`cx-basis cx-basis--${e.basis}`}>{BASIS_LABEL[e.basis]}</span>
              <span className="cx-evidence__label">{e.label}<small>{formatPeriod(e.period)}</small><EvidenceOrigin evidence={e} /></span>
              <strong className="cx-evidence__value">{formatEvidenceValue(e.value)}</strong>
            </li>
          ))}
        </ul>
      </section>
    )}
    {r.limitations.length > 0 && (
      <section className="cx-limits">
        <h3><CircleHelp size={14} aria-hidden="true" />Limitações</h3>
        <ul>{r.limitations.map((l) => <li key={l}>{l}</li>)}</ul>
      </section>
    )}
  </div>
);
