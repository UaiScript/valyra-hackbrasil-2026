import { useMemo, useState } from 'react';
import type { FC } from 'react';
import { api, describeError } from '../api/client';
import type { CategoryOut, FinanceListTransactionsQuery, TransactionOut } from '../../lib/api/schema';
import { formatIsoDate } from '../money';
import { Amount, SOURCE_LABEL } from '../TransactionRow';
import { Async, Card, Empty, NoticeBar } from '../ui';
import type { Notice } from '../ui';
import { useApi } from '../useApi';

const PAGE_SIZE = 25;

// A API recusa categoria de despesa em entrada e vice-versa (CATEGORY_KIND_MISMATCH);
// o seletor já oferece só as categorias compatíveis com o sinal do valor.
const kindFor = (t: TransactionOut): CategoryOut['kind'] => (t.amount_cents < 0 ? 'expense' : 'income');

const CategorySelect: FC<{ t: TransactionOut; categories: CategoryOut[]; onChange: (categoryId: string) => Promise<void> }> = ({ t, categories, onChange }) => {
  const [saving, setSaving] = useState(false);
  const options = categories.filter((c) => c.kind === kindFor(t));
  return (
    <select
      aria-label={`Categoria de ${t.description}`}
      value={t.category.id}
      disabled={saving}
      onChange={async (e) => {
        setSaving(true);
        try { await onChange(e.target.value); } finally { setSaving(false); }
      }}
    >
      {options.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
    </select>
  );
};

export const Transactions: FC = () => {
  const [filters, setFilters] = useState<FinanceListTransactionsQuery>({});
  const [offset, setOffset] = useState(0);
  const [notice, setNotice] = useState<Notice>(null);

  const accounts = useApi((s) => api.listAccounts(s), []);
  const categories = useApi((s) => api.listCategories(s), []);
  const query = useMemo(() => ({ ...filters, limit: PAGE_SIZE, offset }), [filters, offset]);
  const txs = useApi((s) => api.listTransactions(query, s), [query]);

  const categoryList = categories.state.data?.items ?? [];
  const setFilter = (key: keyof FinanceListTransactionsQuery, value: string) => {
    setOffset(0);
    setFilters((f) => ({ ...f, [key]: value || undefined }));
  };

  async function correct(t: TransactionOut, categoryId: string) {
    try {
      const updated = await api.updateTransactionCategory(t.id, categoryId);
      const page = txs.state.data;
      if (page) txs.setState({ status: 'success', data: { ...page, items: page.items.map((x) => (x.id === updated.id ? updated : x)) } });
      setNotice({ kind: 'success', text: `“${t.description}” agora está em ${updated.category.name}.` });
    } catch (err) {
      setNotice({ kind: 'error', text: describeError(err) });
    }
  }

  return (
    <div className="app-stack">
      <NoticeBar notice={notice} onClose={() => setNotice(null)} />
      <Card title="Filtros">
        <div className="app-filters">
          <label>Conta
            <select value={filters.account_id ?? ''} onChange={(e) => setFilter('account_id', e.target.value)}>
              <option value="">Todas</option>
              {accounts.state.data?.items.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
            </select>
          </label>
          <label>Categoria
            <select value={filters.category_id ?? ''} onChange={(e) => setFilter('category_id', e.target.value)}>
              <option value="">Todas</option>
              {categoryList.map((c) => <option key={c.id} value={c.id}>{c.name} ({c.kind === 'expense' ? 'saída' : 'entrada'})</option>)}
            </select>
          </label>
          <label>De<input type="date" value={filters.date_from ?? ''} onChange={(e) => setFilter('date_from', e.target.value)} /></label>
          <label>Até<input type="date" value={filters.date_to ?? ''} onChange={(e) => setFilter('date_to', e.target.value)} /></label>
          <button type="button" className="button button--ghost button--sm" onClick={() => { setFilters({}); setOffset(0); }}>Limpar</button>
        </div>
      </Card>

      <Card title="Transações">
        <Async state={txs.state} onRetry={txs.reload}>
          {(page) => page.items.length === 0 ? <Empty>Nenhuma transação com esses filtros.</Empty> : (
            <>
              <div className="app-table-wrap">
                <table className="app-table">
                  <thead><tr><th>Data</th><th>Descrição</th><th>Categoria</th><th>Origem</th><th className="app-num">Valor</th></tr></thead>
                  <tbody>
                    {page.items.map((t) => (
                      <tr key={t.id}>
                        <td>{formatIsoDate(t.date)}</td>
                        <td>{t.description}</td>
                        <td>{categoryList.length ? <CategorySelect t={t} categories={categoryList} onChange={(id) => correct(t, id)} /> : t.category.name}</td>
                        <td><span className={`app-badge app-badge--${t.category_source}`}>{SOURCE_LABEL[t.category_source]}</span></td>
                        <td className="app-num"><Amount cents={t.amount_cents} /></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <nav className="app-pager" aria-label="Paginação">
                <span className="app-muted">{page.offset + 1}–{page.offset + page.items.length} de {page.total}</span>
                <button type="button" className="button button--outline button--sm" disabled={page.offset === 0 || txs.state.status === 'loading'} onClick={() => setOffset(Math.max(0, page.offset - PAGE_SIZE))}>Anterior</button>
                <button type="button" className="button button--outline button--sm" disabled={page.offset + page.items.length >= page.total || txs.state.status === 'loading'} onClick={() => setOffset(page.offset + PAGE_SIZE)}>Próxima</button>
              </nav>
            </>
          )}
        </Async>
      </Card>
    </div>
  );
};
