import type { FC, ReactNode } from 'react';
import { AlertTriangle, Inbox, Loader2 } from 'lucide-react';
import { describeError } from './api/client';
import type { ApiState } from './useApi';

export const Loading: FC<{ label?: string }> = ({ label = 'Carregando…' }) => (
  <p className="app-state" role="status"><Loader2 className="app-spin" size={18} aria-hidden="true" />{label}</p>
);

export const ErrorState: FC<{ error: unknown; onRetry?: () => void }> = ({ error, onRetry }) => (
  <div className="app-state app-state--error" role="alert">
    <AlertTriangle size={18} aria-hidden="true" />
    <span>{describeError(error)}</span>
    {onRetry && <button type="button" className="button button--outline button--sm" onClick={onRetry}>Tentar de novo</button>}
  </div>
);

export const Empty: FC<{ children: ReactNode }> = ({ children }) => (
  <p className="app-state app-state--empty"><Inbox size={18} aria-hidden="true" />{children}</p>
);

/** Mostra carregando/erro e só renderiza `children` com dados. */
export function Async<T>({ state, onRetry, children }: { state: ApiState<T>; onRetry?: () => void; children: (data: T) => ReactNode }) {
  if (state.status === 'error' && state.data === undefined) return <ErrorState error={state.error} onRetry={onRetry} />;
  if (state.data === undefined) return <Loading />;
  return (
    <>
      {state.status === 'error' && <ErrorState error={state.error} onRetry={onRetry} />}
      {children(state.data)}
    </>
  );
}

export type Notice = { kind: 'success' | 'error'; text: string } | null;

export const NoticeBar: FC<{ notice: Notice; onClose: () => void }> = ({ notice, onClose }) =>
  notice ? (
    <div className={`app-notice app-notice--${notice.kind}`} role={notice.kind === 'error' ? 'alert' : 'status'}>
      <span>{notice.text}</span>
      <button type="button" className="button button--ghost button--sm" onClick={onClose} aria-label="Fechar aviso">×</button>
    </div>
  ) : null;

export const Card: FC<{ title: string; action?: ReactNode; children: ReactNode; className?: string }> = ({ title, action, children, className }) => (
  <section className={`app-card${className ? ` ${className}` : ''}`}>
    <header className="app-card__header"><h2>{title}</h2>{action}</header>
    {children}
  </section>
);
