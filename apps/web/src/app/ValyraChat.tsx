import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import type { FC, FormEvent, ReactNode } from 'react';
import { ArrowUp, Bot, Loader2, Maximize2, Sparkles, TriangleAlert, User, X } from 'lucide-react';
import { api, ApiError, describeError } from './api/client';
import { AI_MESSAGES, explain } from './api/ai';
import type { ExplainResponse } from './api/ai';
import type { AccountOut } from '../lib/api/schema';
import { Answer } from './AiAnswer';
import { ROUTES } from './router';
import { useApi } from './useApi';
import { useProfile } from './useProfile';

/*
 * Conversa com a Valyra AI compartilhada entre a barra lateral de chat e a tela cheia
 * (#/app/valyra-ai). A conversa mora aqui, acima das duas, para que abrir em tela cheia
 * ou voltar para a barra continue o mesmo diálogo em vez de começar outro.
 */

const SUGGESTIONS = [
  'Por que meu saldo previsto fica negativo nos próximos dias?',
  'Onde estou gastando mais neste mês?',
  'Quais gastos fogem do meu padrão?',
  'Quais contas fixas vencem nas próximas semanas?',
  'O que mudou nos meus gastos em relação ao mês passado?',
  'Meu orçamento aguenta até o fim do mês?',
];

export type Turn =
  | { id: number; question: string; status: 'loading' }
  | { id: number; question: string; status: 'done'; response: ExplainResponse }
  | { id: number; question: string; status: 'error'; message: string };

type ChatState = {
  account: AccountOut | undefined;
  turns: Turn[];
  busy: boolean;
  suggestions: string[];
  ask: (question: string) => void;
  panelOpen: boolean;
  /** Abre a barra de chat; com pergunta, envia assim que a conta estiver carregada. */
  openPanel: (question?: string) => void;
  closePanel: () => void;
};

const ChatContext = createContext<ChatState | null>(null);

export function useValyraChat(): ChatState {
  const ctx = useContext(ChatContext);
  if (!ctx) throw new Error('useValyraChat fora do ValyraChatProvider');
  return ctx;
}

/** Pergunta embutida num link do tipo #/app/valyra-ai?q=... */
export function questionFromHref(href: string): string {
  const i = href.indexOf('?');
  if (i < 0) return '';
  return new URLSearchParams(href.slice(i + 1)).get('q') ?? '';
}

export const ValyraChatProvider: FC<{ children: ReactNode }> = ({ children }) => {
  const accounts = useApi((s) => api.listAccounts(s), []);
  const account = accounts.state.data?.items[0];
  const [turns, setTurns] = useState<Turn[]>([]);
  const [panelOpen, setPanelOpen] = useState(false);
  const [pending, setPending] = useState<string | null>(null);
  const nextId = useRef(1);
  const busy = turns.some((t) => t.status === 'loading');
  const { profile } = useProfile();
  // Perguntas do perfil primeiro, completadas pelas gerais, sem repetir: a grade fica com 6.
  const suggestions = useMemo(() => [...new Set([...profile.questions, ...SUGGESTIONS])].slice(0, SUGGESTIONS.length), [profile.questions]);

  const ask = useCallback(async (question: string) => {
    const q = question.trim();
    if (!q || !account || busy) return;
    const id = nextId.current++;
    setTurns((ts) => [...ts, { id, question: q, status: 'loading' }]);
    try {
      const response = await explain(account.id, q);
      setTurns((ts) => ts.map((t) => (t.id === id ? { id, question: q, status: 'done', response } : t)));
    } catch (err) {
      const message = err instanceof ApiError ? AI_MESSAGES[err.code] ?? describeError(err) : describeError(err);
      setTurns((ts) => ts.map((t) => (t.id === id ? { id, question: q, status: 'error', message } : t)));
    }
  }, [account, busy]);

  // Pergunta pedida antes da conta carregar (ex.: "Por quê?" logo ao abrir o app).
  useEffect(() => {
    if (pending && account && !busy) {
      setPending(null);
      void ask(pending);
    }
  }, [pending, account, busy, ask]);

  const openPanel = useCallback((question?: string) => {
    setPanelOpen(true);
    if (question?.trim()) setPending(question);
  }, []);
  const closePanel = useCallback(() => setPanelOpen(false), []);

  const value = useMemo<ChatState>(() => ({
    account, turns, busy, suggestions, ask: (q) => void ask(q), panelOpen, openPanel, closePanel,
  }), [account, turns, busy, suggestions, ask, panelOpen, openPanel, closePanel]);

  return <ChatContext.Provider value={value}>{children}</ChatContext.Provider>;
};

/** Sugestões, mensagens e campo de pergunta: o mesmo miolo na barra e na tela cheia. */
export const ChatBody: FC<{ compact?: boolean; autoFocus?: boolean }> = ({ compact = false, autoFocus = false }) => {
  const { account, turns, busy, suggestions, ask } = useValyraChat();
  const [text, setText] = useState('');
  const endRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const inputId = compact ? 'cx-question-panel' : 'cx-question';

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' }); }, [turns]);
  useEffect(() => { if (autoFocus) inputRef.current?.focus(); }, [autoFocus]);

  function send(q: string) {
    if (!q.trim() || busy || !account) return;
    setText('');
    ask(q);
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    send(text);
  }

  return (
    <>
      <div className="cx-thread" aria-live="polite">
        {turns.length === 0 && (
          <div className="cx-suggestions">
            <span className="cx-suggestions__title">Comece por uma destas</span>
            <div>
              {(compact ? suggestions.slice(0, 4) : suggestions).map((s) => (
                <button key={s} type="button" className="cx-suggestion" disabled={!account} onClick={() => send(s)}>{s}</button>
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
        <label className="sr-only" htmlFor={inputId}>Sua pergunta</label>
        <textarea
          ref={inputRef}
          id={inputId}
          rows={1}
          value={text}
          maxLength={2000}
          placeholder={account ? 'Pergunte sobre seu saldo, gastos ou projeção…' : 'Carregando conta…'}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(text); } }}
        />
        <button type="submit" className="cx-send" disabled={!text.trim() || !account || busy} aria-label="Enviar pergunta"><ArrowUp size={18} /></button>
      </form>
      <p className="cx-ai__fine">Respostas explicam dados sintéticos da demonstração; não são recomendação financeira.</p>
    </>
  );
};

/** Barra lateral de chat, aberta sobre a tela atual; "Tela cheia" leva à página completa. */
export const ChatPanel: FC = () => {
  const { panelOpen, closePanel } = useValyraChat();
  const panelRef = useRef<HTMLElement>(null);

  useEffect(() => {
    if (!panelOpen) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') closePanel(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [panelOpen, closePanel]);

  if (!panelOpen) return null;
  return (
    <div className="cx-chat-layer">
      <button type="button" className="cx-chat-scrim" aria-label="Fechar chat" tabIndex={-1} onClick={closePanel} />
      <aside ref={panelRef} className="cx-chat-panel" role="dialog" aria-modal="false" aria-labelledby="cx-chat-title">
        <header className="cx-chat-panel__head">
          <span className="cx-chat-panel__orb" aria-hidden="true"><Sparkles size={16} /></span>
          <div>
            <h2 id="cx-chat-title">Pergunte ao Valyra</h2>
            <small>Explica as evidências da sua conta, sem criar números</small>
          </div>
          <a className="cx-chat-panel__btn" href={ROUTES.ai} data-full="true" onClick={closePanel} aria-label="Abrir em tela cheia" title="Abrir em tela cheia"><Maximize2 size={16} aria-hidden="true" /></a>
          <button type="button" className="cx-chat-panel__btn" onClick={closePanel} aria-label="Fechar chat" title="Fechar (Esc)"><X size={17} aria-hidden="true" /></button>
        </header>
        <div className="cx-chat-panel__body">
          <ChatBody compact autoFocus />
        </div>
      </aside>
    </div>
  );
};
