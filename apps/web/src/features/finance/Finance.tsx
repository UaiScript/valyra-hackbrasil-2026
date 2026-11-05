import { useId, useState } from 'react';
import type { DemoDataset, FinanceFilter, ProfileId } from '../../shared/types/domain';
import { summarize, filterTransactions } from './calculations';
import { money } from '../../shared/format';
import { Metric, PageHeading, TransactionTable } from '../../shared/components/Primitives';
import { profiles } from '../workspace/profiles';
import { Icon } from '../../shared/components/Icon';

const initialFilter: FinanceFilter = { direction: 'all', category: 'all', search: '' };

export function Finance({ data, profile }: { data: DemoDataset; profile: ProfileId }) {
  // Workspace remonta a tela ao trocar o perfil: um filtro de Moradia não pode ocultar o caixa da Empresa.
  const [filter, setFilter] = useState<FinanceFilter>(initialFilter);
  const config = profiles[profile];
  const searchId = useId();
  const isFiltered =
    filter.search !== '' || filter.category !== 'all' || filter.direction !== 'all';
  const transactions = filterTransactions(data.transactions, filter);
  const totals = summarize(transactions);
  const categories = [...new Set(data.transactions.map((item) => item.category))].sort();
  return (
    <>
      <PageHeading
        title="Financeiro"
        description="Consulte os lançamentos. Os totais acompanham os filtros aplicados."
      />
      <div className="metrics-row">
        <Metric
          label="Resultado da seleção"
          value={money(totals.netCents)}
          note="Entradas − saídas, sem saldo inicial"
          emphasis
        />
        <Metric
          label={config.income}
          value={money(totals.incomeCents)}
          note="Nos lançamentos filtrados"
        />
        <Metric
          label={config.expense}
          value={money(totals.expenseCents)}
          note="Nos lançamentos filtrados"
        />
      </div>
      <section className="panel finance-panel">
        <div className="panel-heading">
          <h2>{profile === 'personal' ? 'Lançamentos do período' : 'Lançamentos de caixa'}</h2>
          <span className="result-count" role="status" aria-live="polite">
            {transactions.length} de {data.transactions.length} lançamentos
          </span>
        </div>
        <form
          className="finance-filters"
          role="search"
          aria-label="Filtrar lançamentos"
          onSubmit={(event) => event.preventDefault()}
        >
          <label htmlFor={searchId}>
            Buscar lançamento
            <span className="search-field">
              <Icon name="search" size={16} />
              <input
                id={searchId}
                type="search"
                placeholder="Descrição ou categoria"
                value={filter.search}
                onChange={(event) => setFilter({ ...filter, search: event.target.value })}
              />
            </span>
          </label>
          <label>
            Movimento
            <select
              value={filter.direction}
              onChange={(event) =>
                setFilter({
                  ...filter,
                  direction: event.target.value as FinanceFilter['direction'],
                })
              }
            >
              <option value="all">Todos</option>
              <option value="income">Entradas</option>
              <option value="expense">Saídas</option>
            </select>
          </label>
          <label>
            Categoria
            <select
              value={filter.category}
              onChange={(event) => setFilter({ ...filter, category: event.target.value })}
            >
              <option value="all">Todas</option>
              {categories.map((category) => (
                <option key={category}>{category}</option>
              ))}
            </select>
          </label>
          <button
            type="button"
            className="button button-subtle"
            onClick={() => setFilter(initialFilter)}
            disabled={!isFiltered}
          >
            Limpar filtros
          </button>
        </form>
        <TransactionTable
          transactions={[...transactions].sort((a, b) => b.date.localeCompare(a.date))}
          caption={`Mais recentes primeiro · Valyra ${config.name} · valores em reais`}
        />
        <div className="table-total">
          <span>Resultado dos lançamentos exibidos</span>
          <strong>{money(totals.netCents)}</strong>
        </div>
      </section>
      <details className="calculation-help">
        <summary>
          Como o resultado é calculado?
          <Icon name="chevron" size={16} />
        </summary>
        <div>
          <p>
            Receitas e entradas têm valor positivo; despesas e saídas, negativo. O resultado é a
            soma dos registros selecionados. Na visão geral, o saldo também inclui{' '}
            {money(data.openingBalanceCents)} de saldo inicial sintético.
          </p>
          <p>
            Nenhum evento do Radar altera os lançamentos. Inclusão, edição e importação de dados
            serão discutidas na próxima etapa.
          </p>
        </div>
      </details>
    </>
  );
}
