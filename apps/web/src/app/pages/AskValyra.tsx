import { useEffect, useRef, useState } from 'react';
import type { FC, FormEvent } from 'react';
import { ArrowUp, Bot, CircleHelp, Loader2, ShieldCheck, Sparkles, TriangleAlert, User } from 'lucide-react';
import { api, ApiError, describeError } from '../api/client';
import { AI_MESSAGES, explain, formatEvidenceValue } from '../api/ai';
import type { EvidenceItem, ExplainResponse } from '../api/ai';
import { formatIsoDate } from '../money';
import { useApi } from '../useApi';
import { useProfile } from '../useProfile';

const SUGGESTIONS = [
  'Por que meu saldo previsto fica negativo nos próximos dias?',
  'Onde estou gastando mais neste mês?',
  'Quais gastos fogem do meu padrão?',
  'Quais contas fixas vencem nas próximas semanas?',
  'O que mudou nos meus gastos em relação ao mês passado?',
  'Meu orçamento aguenta até o fim do mês?',
];

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

type Turn =
  | { id: number; question: string; status: 'loading' }
  | { id: number; question: string; status: 'done'; response: ExplainResponse }
  | { id: number; question: string; status: 'error'; message: string };

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
              <span className="cx-evidence__label">{e.label}<small>{formatPeriod(e.period)}</small></span>
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

function questionFromHash(): string {
  const i = window.location.hash.indexOf('?');
  if (i < 0) return '';
  return new URLSearchParams(window.location.hash.slice(i + 1)).get('q') ?? '';
}

export const AskValyra: FC = () => {
  const accounts = useApi((s) => api.listAccounts(s), []);
  const account = accounts.state.data?.items[0];
  const [text, setText] = useState('');
  const [turns, setTurns] = useState<Turn[]>([]);
  const nextId = useRef(1);
  const endRef = useRef<HTMLDivElement>(null);
  const busy = turns.some((t) => t.status === 'loading');
  // Perguntas do perfil primeiro, completadas pelas gerais, sem repetir: a grade fica com 6.
  const { profile } = useProfile();
  const suggestions = [...new Set([...profile.questions, ...SUGGESTIONS])].slice(0, SUGGESTIONS.length);

  async function ask(question: string) {
    const q = question.trim();
    if (!q || !account || busy) return;
    const id = nextId.current++;
    setText('');
    setTurns((ts) => [...ts, { id, question: q, status: 'loading' }]);
    try {
      const response = await explain(account.id, q);
      setTurns((ts) => ts.map((t) => (t.id === id ? { id, question: q, status: 'done', response } : t)));
    } catch (err) {
      const message = err instanceof ApiError ? AI_MESSAGES[err.code] ?? describeError(err) : describeError(err);
      setTurns((ts) => ts.map((t) => (t.id === id ? { id, question: q, status: 'error', message } : t)));
    }
  }

  // Pergunta vinda de outra tela (ex.: "Por que é atípico?"): envia assim que a conta carrega.
  const prefilled = useRef(false);
  useEffect(() => {
    if (prefilled.current || !account) return;
    const q = questionFromHash();
    if (q) {
      prefilled.current = true;
      void ask(q);
    }
  });

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' }); }, [turns]);

  function submit(event: FormEvent) {
    event.preventDefault();
    void ask(text);
  }

  return (
    <div className="cx-ai">
      <section className="cx-ai__intro">
        <span className="cx-ai__orb" aria-hidden="true"><Sparkles size={22} /></span>
        <div>
          <h2>Pergunte ao Valyra</h2>
          <p>A IA lê as evidências calculadas para a sua conta (saldo, transações, recorrências, projeção) e explica em linguagem simples. Ela <strong>não cria números</strong>: cada valor da resposta aparece abaixo com origem e período.</p>
        </div>
      </section>

      <div className="cx-thread" aria-live="polite">
        {turns.length === 0 && (
          <div className="cx-suggestions">
            <span className="cx-suggestions__title">Comece por uma destas</span>
            <div>
              {suggestions.map((s) => (
                <button key={s} type="button" className="cx-suggestion" disabled={!account} onClick={() => void ask(s)}>{s}</button>
              ))}
            </div>
          </div>
        )}
        {turns.map((t) => (
          <article key={t.id} className="cx-turn">
            <div className="cx-msg cx-msg--user"><span className="cx-msg__avatar" aria-hidden="true"><User size={14} /></span><p>{t.question}</p></div>
            <div className="cx-msg cx-msg--ai">
              <span className="cx-msg__avatar cx-msg__avatar--ai" aria-hidden="true"><Bot size={14} /></span>
              {t.status === 'loading' && <p className="cx-thinking"><Loader2 className="app-spin" size={15} aria-hidden="true" />Cruzando evidências da conta…</p>}
              {t.status === 'error' && <p className="cx-ai-error"><TriangleAlert size={15} aria-hidden="true" />{t.message}</p>}
              {t.status === 'done' && <Answer r={t.response} />}
            </div>
          </article>
        ))}
        <div ref={endRef} />
      </div>

      <form className="cx-composer" onSubmit={submit}>
        <label className="sr-only" htmlFor="cx-question">Sua pergunta</label>
        <textarea
          id="cx-question"
          rows={1}
          value={text}
          maxLength={2000}
          placeholder={account ? 'Pergunte sobre seu saldo, gastos ou projeção…' : 'Carregando conta…'}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); void ask(text); } }}
        />
        <button type="submit" className="cx-send" disabled={!text.trim() || !account || busy} aria-label="Enviar pergunta"><ArrowUp size={18} /></button>
      </form>
      <p className="cx-ai__fine">Respostas explicam dados sintéticos da demonstração; não são recomendação financeira.</p>
    </div>
  );
};
