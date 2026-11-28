import { useEffect, useRef, useState } from 'react';
import type { FC } from 'react';
import { AlertTriangle, ArrowUpRight, BellOff, Check, Info, Sparkles, X } from 'lucide-react';
import { askHref } from './api/ai';
import { api, describeError } from './api/client';
import type { AlertOut } from '../lib/api/schema';
import { ALERTS_CHANGED } from './alertsEvents';
import { formatCents, formatShortDate } from './money';
import { ROUTES } from './router';
import { useApi } from './useApi';

/*
 * Janela pequena de alertas, aberta pelo sino e pelos atalhos de alerta da Central.
 * Mostra o essencial de cada alerta; a tela completa (#/app/alertas) continua no rodapé
 * da janela para quem quiser todos os números que geraram o alerta.
 */
export const AlertsPopover: FC<{ open: boolean; onClose: () => void }> = ({ open, onClose }) => {
  const alerts = useApi((s) => api.listAlerts(s), [open]);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const boxRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    setError(null);
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    // Clique fora fecha; o próprio sino e os atalhos reabrem pelo clique deles.
    const onDown = (e: PointerEvent) => {
      const target = e.target as Element | null;
      if (boxRef.current?.contains(target as Node) || target?.closest('[data-alerts-trigger]')) return;
      onClose();
    };
    // Ao fechar, o foco volta para quem abriu a janela (sino ou atalho), para quem usa teclado.
    const opener = document.activeElement as HTMLElement | null;
    window.addEventListener('keydown', onKey);
    window.addEventListener('pointerdown', onDown);
    boxRef.current?.focus();
    return () => {
      window.removeEventListener('keydown', onKey);
      window.removeEventListener('pointerdown', onDown);
      const active = document.activeElement;
      if (opener?.isConnected && (active === null || active === document.body || boxRef.current?.contains(active))) opener.focus();
    };
  }, [open, onClose]);

  async function markRead(alert: AlertOut) {
    setBusyId(alert.id);
    try {
      const updated = await api.markAlertRead(alert.id);
      alerts.setState((prev) => (prev.data ? { status: 'success', data: { ...prev.data, items: prev.data.items.map((a) => (a.id === updated.id ? updated : a)) } } : prev));
      window.dispatchEvent(new Event(ALERTS_CHANGED));
    } catch (err) {
      setError(describeError(err));
    } finally {
      setBusyId(null);
    }
  }

  if (!open) return null;
  const items = [...(alerts.state.data?.items ?? [])].sort((a, b) => (a.status === b.status ? b.created_at.localeCompare(a.created_at) : a.status === 'new' ? -1 : 1));
  const fresh = items.filter((a) => a.status === 'new').length;

  return (
    <div ref={boxRef} className="cx-alerts-pop" role="dialog" aria-label="Alertas" tabIndex={-1}>
      <header className="cx-alerts-pop__head">
        <div>
          <h2>Alertas</h2>
          <small>{alerts.state.data ? (fresh ? `${fresh} ${fresh === 1 ? 'novo' : 'novos'}` : 'Nenhum novo') : 'Carregando…'}</small>
        </div>
        <button type="button" className="cx-chat-panel__btn" onClick={onClose} aria-label="Fechar alertas"><X size={16} aria-hidden="true" /></button>
      </header>
      {error && <p className="cx-alerts-pop__error" role="alert">{error}</p>}
      {alerts.state.status === 'error' && <p className="cx-alerts-pop__error" role="alert">{describeError(alerts.state.error)} <button type="button" className="app-link" onClick={alerts.reload}>Tentar de novo</button></p>}
      {alerts.state.data && items.length === 0 && (
        <div className="cx-alerts-pop__empty">
          <BellOff size={22} aria-hidden="true" />
          <p>Nenhum alerta por enquanto. A projeção de 30 dias está acima de zero.</p>
        </div>
      )}
      {items.length > 0 && (
        <ul className="cx-alerts-pop__list">
          {items.slice(0, 4).map((a) => {
            const Icon = a.severity === 'warning' ? AlertTriangle : Info;
            return (
              <li key={a.id} className={`cx-alerts-pop__item cx-alerts-pop__item--${a.severity}${a.status === 'read' ? ' is-read' : ''}`}>
                <span className="cx-alerts-pop__icon" aria-hidden="true"><Icon size={16} /></span>
                <div>
                  <b>{a.title}</b>
                  <small>Menor saldo previsto {formatCents(a.evidence.min_balance_cents)} em {formatShortDate(a.evidence.min_balance_date)}</small>
                  <span className="cx-alerts-pop__actions">
                    <a href={askHref(`O que explica o alerta "${a.title}" com menor saldo previsto em ${formatShortDate(a.evidence.min_balance_date)}?`)} onClick={onClose}><Sparkles size={13} aria-hidden="true" />Por quê?</a>
                    {a.status === 'new' && (
                      <button type="button" disabled={busyId === a.id} onClick={() => void markRead(a)}>
                        <Check size={13} aria-hidden="true" />{busyId === a.id ? 'Marcando…' : 'Marcar como lido'}
                      </button>
                    )}
                  </span>
                </div>
              </li>
            );
          })}
        </ul>
      )}
      <a className="cx-alerts-pop__all" href={ROUTES.alerts} data-full="true" onClick={onClose}>Ver todos os alertas<ArrowUpRight size={14} aria-hidden="true" /></a>
    </div>
  );
};
