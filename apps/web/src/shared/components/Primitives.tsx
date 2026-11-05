import { useId, type ReactNode } from 'react';
import type { Transaction } from '../types/domain';
import { money, shortDate } from '../format';

export function Badge({ children, light = false }: { children: ReactNode; light?: boolean }) {
  return <span className={`badge${light ? ' badge-light' : ''}`}>{children}</span>;
}

export function PageHeading({ title, description }: { title: string; description?: string }) {
  return (
    <header className="page-heading">
      <h1 tabIndex={-1} data-page-heading>
        {title}
      </h1>
      {description && <p>{description}</p>}
    </header>
  );
}

export function Metric({
  label,
  value,
  note,
  emphasis = false,
}: {
  label: string;
  value: string;
  note: string;
  emphasis?: boolean;
}) {
  return (
    <div className={`metric${emphasis ? ' metric-emphasis' : ''}`}>
      <span className="metric-label">{label}</span>
      <strong>{value}</strong>
      <small>{note}</small>
    </div>
  );
}

export function TransactionTable({
  transactions,
  caption,
}: {
  transactions: Transaction[];
  caption: string;
}) {
  const hintId = useId();
  return (
    <>
      <p id={hintId} className="table-mobile-hint">
        Role a tabela para ver todas as colunas.
      </p>
      <div
        className="table-scroll"
        role="region"
        aria-label="Lançamentos financeiros"
        aria-describedby={hintId}
        tabIndex={0}
      >
        <table>
          <caption>{caption}</caption>
          <colgroup>
            <col className="description-column" />
            <col className="category-column" />
            <col className="date-column" />
            <col className="value-column" />
          </colgroup>
          <thead>
            <tr>
              <th scope="col">Descrição</th>
              <th scope="col">Categoria</th>
              <th scope="col">Data</th>
              <th scope="col" className="numeric">
                Valor
              </th>
            </tr>
          </thead>
          <tbody>
            {transactions.map((item) => (
              <tr key={item.id}>
                <th scope="row">
                  <span className="transaction-description">{item.description}</span>
                  <small className="transaction-direction">
                    {item.amountCents > 0 ? 'Entrada' : 'Saída'}
                  </small>
                </th>
                <td>
                  <span className="category-tag">{item.category}</span>
                </td>
                <td className="nowrap">
                  <time dateTime={item.date}>{shortDate(item.date)}</time>
                </td>
                <td className={`numeric ${item.amountCents > 0 ? 'income-value' : ''}`}>
                  {item.amountCents > 0 ? '+ ' : '− '}
                  {money(Math.abs(item.amountCents))}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {transactions.length === 0 && (
          <p className="empty-state">
            Nenhum lançamento para estes filtros. Experimente outra categoria ou limpe a busca.
          </p>
        )}
      </div>
    </>
  );
}
