import { useId } from 'react';
import type { DemoDataset, ProfileId } from '../../shared/types/domain';
import { summarize, projectCommitments } from '../finance/calculations';
import { money, shortDate } from '../../shared/format';
import { PageHeading, Badge } from '../../shared/components/Primitives';
import { Icon } from '../../shared/components/Icon';
import { BalanceChart } from './BalanceChart';

export function Planning({ data, profile }: { data: DemoDataset; profile: ProfileId }) {
  const total = summarize(data.transactions, data.openingBalanceCents);
  const points = projectCommitments(total.balanceCents, data.commitments);
  const committed = data.commitments.reduce((sum, item) => sum + item.amountCents, 0);
  const remaining = points.at(-1)?.balanceCents ?? total.balanceCents;
  const tableId = useId();

  return (
    <>
      <PageHeading
        title="Planejamento"
        description={
          profile === 'personal'
            ? 'Confira os compromissos e o saldo após cada vencimento.'
            : 'Confira os compromissos do caixa e o saldo após cada vencimento.'
        }
      />
      <div className="planning-grid">
        <section className="panel projection-panel">
          <div className="panel-heading">
            <h2>Saldo após compromissos</h2>
            <Badge>Simulação</Badge>
          </div>
          <div className="projection-summary">
            <div>
              <span>Saldo realizado</span>
              <strong>{money(total.balanceCents)}</strong>
            </div>
            <span aria-hidden="true">−</span>
            <div>
              <span>Compromissos</span>
              <strong>{money(committed)}</strong>
            </div>
            <span aria-hidden="true">=</span>
            <div>
              <span>Saldo resultante</span>
              <strong className="projection-value">{money(remaining)}</strong>
            </div>
          </div>
          <p className="projection-premise">
            Saldo de 5 nov menos os compromissos abaixo. Não prevê renda, juros ou efeitos
            econômicos.
          </p>
          <BalanceChart
            initialCents={total.balanceCents}
            points={points}
            referenceDate="2026-11-05"
            tableId={tableId}
          />
          <details className="calculation-help calculation-memory" open>
            <summary>
              Memória de cálculo
              <Icon name="chevron" size={16} />
            </summary>
            <div
              className="table-scroll"
              role="region"
              aria-label="Saldo por compromisso"
              id={tableId}
              tabIndex={0}
            >
              <table>
                <caption>Dados sintéticos · valores em reais</caption>
                <thead>
                  <tr>
                    <th scope="col">Data e compromisso</th>
                    <th scope="col" className="numeric">
                      Saída
                    </th>
                    <th scope="col" className="numeric">
                      Saldo resultante
                    </th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <th scope="row">
                      <span className="transaction-description">5 nov · saldo realizado</span>
                      <small className="transaction-direction">Ponto de partida</small>
                    </th>
                    <td className="numeric">—</td>
                    <td className="numeric">{money(total.balanceCents)}</td>
                  </tr>
                  {points.map((item) => (
                    <tr key={item.id}>
                      <th scope="row">
                        <time dateTime={item.date}>{shortDate(item.date)}</time>
                        <span className="transaction-direction">{item.description}</span>
                      </th>
                      <td className="numeric">− {money(item.amountCents)}</td>
                      <td className="numeric">{money(item.balanceCents)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </details>
        </section>
        <aside className="commitments-panel">
          <div className="panel-heading">
            <h2>Compromissos previstos</h2>
            <span className="result-count">{points.length} no exemplo</span>
          </div>
          <ol className="commitment-list">
            {points.map((item) => (
              <li key={item.id}>
                <time dateTime={item.date}>{shortDate(item.date)}</time>
                <strong>{item.description}</strong>
                <span>{money(item.amountCents)}</span>
              </li>
            ))}
          </ol>
          {points.length === 0 && (
            <p className="empty-state">Nenhum compromisso previsto neste exemplo.</p>
          )}
          <p className="panel-footnote">
            Ainda não são saídas realizadas. Os valores são subtraídos apenas nesta simulação.
          </p>
          <details className="calculation-help">
            <summary>
              Premissas e próxima etapa
              <Icon name="chevron" size={16} />
            </summary>
            <div>
              <p>
                Já funciona: ordenação dos vencimentos e subtração de cada compromisso do saldo.
              </p>
              <p>
                A linha em degraus não representa o comportamento diário do dinheiro. Ela não prevê
                renda e não usa IA ou cotações de mercado.
              </p>
              <p>
                Próxima etapa: cenários editáveis e recorrência, após revisão das regras pela
                equipe.
              </p>
            </div>
          </details>
        </aside>
      </div>
    </>
  );
}
