import { useState } from 'react';
import type { FC, FormEvent } from 'react';
import { ApiError, api } from '../api/client';
import { BellRing } from 'lucide-react';
import type { ImportBatchCreatedOut, ImportBatchOut } from '../../lib/api/schema';
import { ROUTES } from '../router';
import { Async, Card, Empty, ErrorState } from '../ui';
import { useApi } from '../useApi';

const MAX_BYTES = 1_048_576; // mesmo limite do backend (MAX_FILE_BYTES); a API valida de novo.

const REASON_LABEL: Record<string, string> = {
  invalid_date: 'Data inválida (use AAAA-MM-DD)',
  invalid_amount: 'Valor inválido (use ponto decimal, ex.: -89.90)',
  zero_amount: 'Valor zero',
  empty_description: 'Descrição vazia',
  wrong_column_count: 'Número de colunas incorreto',
};

const BatchResult: FC<{ batch: ImportBatchOut | ImportBatchCreatedOut }> = ({ batch }) => (
  <div className="app-stack">
    {'alerts_created' in batch && batch.alerts_created > 0 && (
      <a className="app-inline-alert" href={ROUTES.alerts}>
        <BellRing size={18} aria-hidden="true" />
        <span>
          {batch.alerts_created === 1 ? 'A importação gerou 1 alerta de pressão de caixa.' : `A importação gerou ${batch.alerts_created} alertas de pressão de caixa.`}
          {' '}<strong>Ver alertas</strong>
        </span>
      </a>
    )}
    <dl className="app-stats">
      <div><dt>Linhas lidas</dt><dd>{batch.rows_total}</dd></div>
      <div><dt>Importadas</dt><dd>{batch.rows_imported}</dd></div>
      <div><dt>Duplicadas</dt><dd>{batch.rows_duplicated}</dd></div>
      <div><dt>Rejeitadas</dt><dd>{batch.rows_rejected}</dd></div>
    </dl>
    {batch.rejections.length > 0 && (
      <div className="app-table-wrap">
        <table className="app-table">
          <caption>Linhas rejeitadas</caption>
          <thead><tr><th>Linha</th><th>Motivo</th><th>Conteúdo</th></tr></thead>
          <tbody>
            {batch.rejections.map((r) => (
              <tr key={r.line_number}><td>{r.line_number}</td><td>{REASON_LABEL[r.reason] ?? r.reason}</td><td><code>{r.raw_line}</code></td></tr>
            ))}
          </tbody>
        </table>
      </div>
    )}
    {batch.rows_imported > 0 && <a className="app-link" href={ROUTES.transactions}>Ver transações importadas</a>}
  </div>
);

export const ImportCsv: FC = () => {
  const accounts = useApi((s) => api.listAccounts(s), []);
  const history = useApi((s) => api.listImportBatches({ limit: 10 }, s), []);
  const [accountId, setAccountId] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [sending, setSending] = useState(false);
  const [result, setResult] = useState<ImportBatchCreatedOut | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [localError, setLocalError] = useState<string | null>(null);

  const selectedAccount = accountId || accounts.state.data?.items[0]?.id || '';

  async function submit(event: FormEvent) {
    event.preventDefault();
    setLocalError(null);
    setError(null);
    if (!file) { setLocalError('Escolha um arquivo CSV.'); return; }
    if (file.size > MAX_BYTES) { setLocalError('O arquivo passa do limite de 1 MiB.'); return; }
    if (!selectedAccount) { setLocalError('Nenhuma conta disponível.'); return; }
    setSending(true);
    try {
      setResult(await api.importCsv(selectedAccount, file));
      history.reload();
    } catch (err) {
      setResult(null);
      setError(err);
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="app-stack">
      <Card title="Enviar extrato">
        <p className="app-muted">CSV em UTF-8 com cabeçalho <code>date,description,amount</code>, datas AAAA-MM-DD e valores com ponto decimal (saídas negativas). Linhas repetidas de importações anteriores são ignoradas.</p>
        <form className="app-form app-form--inline" onSubmit={submit}>
          <label>Conta
            <select value={selectedAccount} onChange={(e) => setAccountId(e.target.value)} disabled={!accounts.state.data}>
              {accounts.state.data?.items.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
            </select>
          </label>
          <label>Arquivo<input type="file" accept=".csv,text/csv" onChange={(e) => setFile(e.target.files?.[0] ?? null)} /></label>
          <button type="submit" className="button button--primary" disabled={sending}>{sending ? 'Importando…' : 'Importar'}</button>
        </form>
        {localError && <p className="app-field-error" role="alert">{localError}</p>}
        {accounts.state.status === 'error' && <ErrorState error={accounts.state.error} onRetry={accounts.reload} />}
        {error !== null && <ErrorState error={error} />}
        {error instanceof ApiError && (error.status === 413 || error.status === 422) && (
          <p className="app-muted">Nada foi gravado: arquivo recusado não gera lote nem transações.</p>
        )}
      </Card>

      {result && <Card title="Resultado da importação"><BatchResult batch={result} /></Card>}

      <Card title="Histórico">
        <Async state={history.state} onRetry={history.reload}>
          {(page) => page.items.length === 0 ? <Empty>Nenhuma importação ainda.</Empty> : (
            <div className="app-table-wrap">
              <table className="app-table">
                <thead><tr><th>Lote</th><th>Status</th><th>Linhas</th><th>Importadas</th><th>Duplicadas</th><th>Rejeitadas</th></tr></thead>
                <tbody>
                  {page.items.map((b) => (
                    <tr key={b.id}>
                      <td><code>{b.id.slice(0, 8)}</code></td>
                      <td><span className={`app-badge app-badge--${b.status}`}>{b.status === 'completed' ? 'Concluído' : b.status === 'failed' ? 'Falhou' : 'Processando'}</span></td>
                      <td>{b.rows_total}</td><td>{b.rows_imported}</td><td>{b.rows_duplicated}</td><td>{b.rows_rejected}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Async>
      </Card>
    </div>
  );
};
