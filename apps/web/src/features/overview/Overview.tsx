import type { DemoDataset, ProfileId } from '../../shared/types/domain';
import { summarize, expenseCategories, projectCommitments } from '../finance/calculations';
import { money, shortDate } from '../../shared/format';
import { Metric, PageHeading, TransactionTable } from '../../shared/components/Primitives';
import { Icon } from '../../shared/components/Icon';
import { profiles } from '../workspace/profiles';
import { demoHref } from '../../app/routes';

const percentage = new Intl.NumberFormat('pt-BR', { style: 'percent', maximumFractionDigits: 1 });

export function Overview({ data, profile }: { data: DemoDataset; profile: ProfileId }) {
  const config = profiles[profile];
  const totals = summarize(data.transactions, data.openingBalanceCents);
  const categories = expenseCategories(data.transactions);
  const projected = projectCommitments(totals.balanceCents, data.commitments);
  const remaining = projected.at(-1)?.balanceCents ?? totals.balanceCents;
  const commitmentsCents = data.commitments.reduce((sum, item) => sum + item.amountCents, 0);
  const nextCommitment = projected[0];
  const signal = data.radar[0];
  // O perfil também acompanha os atalhos do conteúdo, não apenas a navegação lateral.
  const financeHref = demoHref('finance', profile);

  return (
    <>
      <PageHeading title="Visão geral" description={config.description} />
      <div className="financial-summary">
        <div className="metrics-row">
          <Metric
            label={config.balance}
            value={money(totals.balanceCents)}
            note="Saldo inicial + resultado do período"
            emphasis
          />
          <Metric
            label={config.income}
            value={money(totals.incomeCents)}
            note="Registradas no período"
          />
          <Metric
            label={config.expense}
            value={money(totals.expenseCents)}
            note="Registradas no período"
          />
        </div>
        <div className="balance-equation">
          <span>
            Saldo inicial <b>{money(data.openingBalanceCents)}</b>
          </span>
          <Icon name="plus" size={16} />
          <span>
            Resultado do período <b>{money(totals.netCents)}</b>
          </span>
        </div>
      </div>
      <div className="overview-grid">
        <section className="expense-panel panel">
          <div className="panel-heading">
            <h2>{config.expense} por categoria</h2>
            <a href={financeHref} className="icon-link" aria-label="Ver todos os lançamentos">
              <Icon name="arrow" size={18} />
            </a>
          </div>
          <p className="section-description">
            Total registrado: <strong>{money(totals.expenseCents)}</strong>
          </p>
          <div className="category-bars">
            {categories.map((item) => {
              const share = totals.expenseCents > 0 ? item.amountCents / totals.expenseCents : 0;
              return (
                <div key={item.label}>
                  <div className="category-label">
                    <span>{item.label}</span>
                    <span className="category-amount">
                      <b>{money(item.amountCents)}</b>
                      <small>{percentage.format(share)}</small>
                    </span>
                  </div>
                  <div className="bar-track" aria-hidden="true">
                    <span style={{ width: `${share * 100}%` }} />
                  </div>
                </div>
              );
            })}
          </div>
          {categories.length === 0 && (
            <p className="empty-state">Nenhuma saída registrada neste exemplo.</p>
          )}
          <p className="panel-footnote">
            Participação no total de {config.expense.toLocaleLowerCase('pt-BR')} do período.
          </p>
        </section>
        <section className="planning-highlight">
          <div className="panel-heading">
            <h2>Próximos compromissos</h2>
            <span>{data.commitments.length} previstos</span>
          </div>
          <dl className="commitment-summary">
            <div>
              <dt>Total comprometido</dt>
              <dd>{money(commitmentsCents)}</dd>
            </div>
            <div className="remaining-value">
              <dt>Saldo após compromissos</dt>
              <dd>{money(remaining)}</dd>
            </div>
          </dl>
          {nextCommitment && (
            <p className="next-commitment">
              Próximo: <strong>{nextCommitment.description}</strong>
              <time dateTime={nextCommitment.date}>{shortDate(nextCommitment.date)}</time>
            </p>
          )}
          <p className="highlight-note">
            Simulação: saldo atual menos os compromissos, sem novas entradas.
          </p>
          <a href={demoHref('planning', profile)} className="text-link">
            Ver planejamento <Icon name="arrow" size={18} />
          </a>
        </section>
      </div>
      <section className="panel recent-panel">
        <div className="panel-heading">
          <h2>Últimos movimentos</h2>
          <a href={financeHref} className="text-link">
            Ver todos <Icon name="arrow" size={16} />
          </a>
        </div>
        <TransactionTable
          transactions={[...data.transactions]
            .sort((a, b) => b.date.localeCompare(a.date))
            .slice(0, 3)}
          caption="Mais recentes primeiro · 3 lançamentos demonstrativos · valores em reais"
        />
      </section>
      {signal && (
        <section className="radar-inline">
          <div className="signal-source">
            <Icon name="radar" size={18} />
            <span>Radar econômico</span>
          </div>
          <div>
            <div className="signal-meta">
              <span>{signal.topic}</span>
              <span>Cenário fictício</span>
            </div>
            <h2>{signal.title}</h2>
            <p>{signal.context}</p>
          </div>
          <a href={demoHref('radar', profile)} className="text-link">
            Ver contexto <Icon name="arrow" size={16} />
          </a>
        </section>
      )}
    </>
  );
}
