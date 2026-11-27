import { useState } from 'react';
import type { FC } from 'react';
import { AlertTriangle, BellOff, Check, Info, Sparkles } from 'lucide-react';
import { askHref } from '../api/ai';
import { api, describeError } from '../api/client';
import type { AlertOut } from '../../lib/api/schema';
import { formatCents, formatIsoDate } from '../money';
import { ROUTES } from '../router';
import { Async, NoticeBar } from '../ui';
import type { Notice } from '../ui';
import { useApi } from '../useApi';
import { ALERTS_CHANGED } from '../alertsEvents';

/** Avisa o menu lateral para recontar alertas novos depois de uma mudança. */
export { ALERTS_CHANGED };

// created_at é timestamp UTC; para exibir só a data usamos o calendário de São Paulo,
// o mesmo da regra de "hoje" do backend (ADR-0010).
const createdDate = (iso: string) => new Intl.DateTimeFormat('pt-BR', { dateStyle: 'medium', timeZone: 'America/Sao_Paulo' }).format(new Date(iso));

const AlertItem: FC<{ alert: AlertOut; onRead: (a: AlertOut) => Promise<void> }> = ({ alert, onRead }) => {
  const [busy, setBusy] = useState(false);
  const e = alert.evidence;
  const Icon = alert.severity === 'warning' ? AlertTriangle : Info;
  return (
    <li className={`vx-alert vx-alert--${alert.severity}${alert.status === 'read' ? ' vx-alert--read' : ''}`}>
      <span className="vx-alert__icon" aria-hidden="true"><Icon size={20} /></span>
      <div className="vx-alert__body">
        <header>
          <h3>{alert.title}</h3>
          {alert.status === 'new' ? <span className="app-badge app-badge--new">Novo</span> : <span className="app-badge">Lido</span>}
        </header>
        <p>{alert.message}</p>
        <dl className="vx-evidence" aria-label="Números que geraram o alerta">
          <div><dt>Saldo em {formatIsoDate(e.today)}</dt><dd>{formatCents(e.start_balance_cents)}</dd></div>
          <div><dt>Menor saldo previsto</dt><dd className={e.min_balance_cents < 0 ? 'vx-totals__neg' : undefined}>{formatCents(e.min_balance_cents)}</dd></div>
          <div><dt>Data do menor saldo</dt><dd>{formatIsoDate(e.min_balance_date)}</dd></div>
          <div><dt>Horizonte</dt><dd>{e.days} dias</dd></div>
        </dl>
        <footer>
          <span className="app-muted">Criado em {createdDate(alert.created_at)}. Valores previstos no momento do alerta.</span>
          <span className="vx-alert__actions">
            <a className="button button--ghost button--sm" href={askHref('Por que meu saldo previsto fica abaixo de zero nos próximos 30 dias?')}><Sparkles size={14} aria-hidden="true" />Por quê?</a>
            <a className="button button--ghost button--sm" href={ROUTES.projection}>Ver projeção atual</a>
            {alert.status === 'new' && (
              <button type="button" className="button button--outline button--sm" disabled={busy} onClick={async () => { setBusy(true); try { await onRead(alert); } finally { setBusy(false); } }}>
                <Check size={14} aria-hidden="true" />{busy ? 'Marcando…' : 'Marcar como lido'}
              </button>
            )}
          </span>
        </footer>
      </div>
    </li>
  );
};

export const Alerts: FC = () => {
  const alerts = useApi((s) => api.listAlerts(s), []);
  const [notice, setNotice] = useState<Notice>(null);

  async function markRead(alert: AlertOut) {
    try {
      const updated = await api.markAlertRead(alert.id);
      // Atualização funcional: com cliques seguidos, cada resposta parte da lista mais recente.
      alerts.setState((prev) => (prev.data ? { status: 'success', data: { ...prev.data, items: prev.data.items.map((a) => (a.id === updated.id ? updated : a)) } } : prev));
      window.dispatchEvent(new Event(ALERTS_CHANGED));
      setNotice({ kind: 'success', text: 'Alerta marcado como lido.' });
    } catch (err) {
      setNotice({ kind: 'error', text: describeError(err) });
    }
  }

  return (
    <div className="app-stack app-stack--loose">
      <NoticeBar notice={notice} onClose={() => setNotice(null)} />
      <p className="vx-lede">
        Um alerta de pressão de caixa aparece quando a projeção de 30 dias de uma conta fica abaixo de zero. Ele é calculado a cada importação de CSV, no máximo uma vez por conta a cada mês.
      </p>
      <Async state={alerts.state} onRetry={alerts.reload}>
        {(page) => page.items.length === 0 ? (
          <div className="vx-empty">
            <BellOff size={28} aria-hidden="true" />
            <h2>Nenhum alerta por enquanto</h2>
            <p>A projeção de 30 dias de todas as contas está acima de zero. <a className="app-link" href={ROUTES.projection}>Ver projeção</a></p>
          </div>
        ) : (
          <ul className="vx-alerts">
            {[...page.items].sort((a, b) => (a.status === b.status ? b.created_at.localeCompare(a.created_at) : a.status === 'new' ? -1 : 1))
              .map((a) => <AlertItem key={a.id} alert={a} onRead={markRead} />)}
          </ul>
        )}
      </Async>
    </div>
  );
};
