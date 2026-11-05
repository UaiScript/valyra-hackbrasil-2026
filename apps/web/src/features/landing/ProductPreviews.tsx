import { Icon } from '../../shared/components/Icon';
import { money, shortDate } from '../../shared/format';
import type { ProfileId } from '../../shared/types/domain';
import { profiles } from '../workspace/profiles';
import type { PreviewModel } from './previewModel';
import { demoHref, demoNavigation } from '../../app/routes';

const percent = new Intl.NumberFormat('pt-BR', { style: 'percent', maximumFractionDigits: 1 });

export function ProductPreview({
  model,
  profile,
  compact = false,
}: {
  model: PreviewModel;
  profile: ProfileId;
  compact?: boolean;
}) {
  const labels = profiles[profile];
  const Title = compact ? 'h4' : 'h2';
  const SectionTitle = compact ? 'h5' : 'h3';
  return (
    <div className={`lp-product${compact ? ' lp-product-compact' : ''}`}>
      <div className="lp-product-top">
        <span className="lp-product-name">
          Valyra <span>/</span> Visão geral
        </span>
        <span className="lp-demo-label">{labels.name} · Dados demonstrativos</span>
      </div>
      <div className="lp-product-layout">
        <nav className="lp-product-nav" aria-label={`Seções da prévia ${labels.name}`}>
          <span className="lp-preview-context">{labels.name}</span>
          {demoNavigation.map((item) => (
            <a
              href={demoHref(item.id, profile)}
              key={item.id}
              className={item.id === 'overview' ? 'is-current' : ''}
            >
              <Icon name={item.icon} size={17} />
              <span>{item.label}</span>
            </a>
          ))}
        </nav>
        <div className="lp-product-content">
          <div className="lp-preview-heading">
            <Title>
              {profile === 'personal' ? 'Seu panorama financeiro' : 'O panorama do seu caixa'}
            </Title>
            <span>1–5 nov 2026</span>
          </div>
          <dl className="lp-preview-totals">
            <div>
              <dt>{labels.balance}</dt>
              <dd>{money(model.totals.balanceCents)}</dd>
            </div>
            <div>
              <dt>{labels.income}</dt>
              <dd>{money(model.totals.incomeCents)}</dd>
            </div>
            <div>
              <dt>{labels.expense}</dt>
              <dd>{money(model.totals.expenseCents)}</dd>
            </div>
          </dl>
          <div className="lp-preview-reconciliation">
            Saldo inicial de {money(model.data.openingBalanceCents)} + resultado de{' '}
            {money(model.totals.netCents)}
          </div>
          <div className="lp-preview-detail">
            <section className="lp-preview-categories">
              <SectionTitle>
                Maiores categorias de {labels.expense.toLocaleLowerCase('pt-BR')}
              </SectionTitle>
              <p>Total do período: {money(model.totals.expenseCents)}</p>
              {model.categories.slice(0, 3).map((item) => (
                <div className="lp-preview-category" key={item.label}>
                  <div>
                    <span>{item.label}</span>
                    <b>{money(item.amountCents)}</b>
                    <small>
                      {percent.format(
                        model.totals.expenseCents > 0
                          ? item.amountCents / model.totals.expenseCents
                          : 0,
                      )}
                    </small>
                  </div>
                  <div className="lp-preview-track" aria-hidden="true">
                    <span
                      style={{
                        width: `${model.totals.expenseCents > 0 ? (item.amountCents / model.totals.expenseCents) * 100 : 0}%`,
                      }}
                    />
                  </div>
                </div>
              ))}
            </section>
            {!compact && (
              <section className="lp-preview-commitments">
                <SectionTitle>Próximos compromissos</SectionTitle>
                <p>
                  {model.commitments.length} previstos · {money(model.committedCents)}
                </p>
                {model.commitments.slice(0, 2).map((item) => (
                  <div key={item.id}>
                    <span>
                      <b>{item.description}</b>
                      <time dateTime={item.date}>{shortDate(item.date)}</time>
                    </span>
                    <strong>{money(item.amountCents)}</strong>
                  </div>
                ))}
                <div className="lp-preview-remaining">
                  <span>Saldo após compromissos</span>
                  <strong>{money(model.remainingCents)}</strong>
                </div>
                <small>Subtração de compromissos. Sem novas entradas.</small>
              </section>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export function FinancePreview({ model }: { model: PreviewModel }) {
  return (
    <figure className="lp-finance-preview">
      <figcaption>
        <strong>
          Financeiro <span>/ Pessoal</span>
        </strong>
        <span>Dados demonstrativos</span>
      </figcaption>
      <div className="lp-finance-summary">
        <span>Resultado do período</span>
        <strong>{money(model.totals.netCents)}</strong>
        <small>Receitas − despesas, sem saldo inicial</small>
      </div>
      <table>
        <caption>Alguns lançamentos · mais recentes primeiro</caption>
        <thead>
          <tr>
            <th scope="col">Lançamento</th>
            <th scope="col">Categoria</th>
            <th scope="col">Valor</th>
          </tr>
        </thead>
        <tbody>
          {model.recent.map((item) => (
            <tr key={item.id}>
              <th scope="row">
                {item.description}
                <small>
                  {shortDate(item.date)} · {item.amountCents > 0 ? 'Entrada' : 'Saída'}
                  <span className="lp-category-inline"> · {item.category}</span>
                </small>
              </th>
              <td>{item.category}</td>
              <td>
                {item.amountCents > 0 ? '+' : '−'} {money(Math.abs(item.amountCents))}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </figure>
  );
}

export function PlanningPreview({ model }: { model: PreviewModel }) {
  return (
    <figure className="lp-planning-preview">
      <figcaption>
        <strong>Planejamento / Pessoal</strong>
        <span>Simulação aritmética · dados fictícios</span>
      </figcaption>
      <div className="lp-planning-result">
        <span>Saldo após {model.commitments.length} compromissos</span>
        <strong>{money(model.remainingCents)}</strong>
        <p>
          {money(model.totals.balanceCents)} de saldo − {money(model.committedCents)} de
          compromissos
        </p>
      </div>
      <ol className="lp-planning-dates">
        {model.commitments.map((item) => (
          <li key={item.id}>
            <time dateTime={item.date}>{shortDate(item.date)}</time>
            <b>{item.description}</b>
            <span>− {money(item.amountCents)}</span>
            <strong>{money(item.balanceCents)}</strong>
            <small>Saldo resultante</small>
          </li>
        ))}
      </ol>
      <p className="lp-preview-note">
        O cálculo usa apenas os compromissos listados. Não prevê renda nem aplica hipóteses do
        Radar.
      </p>
    </figure>
  );
}

export function RadarPreview({ model }: { model: PreviewModel }) {
  return (
    <figure className="lp-radar-preview">
      <figcaption>
        <strong>
          Radar econômico <span>/ Pessoal</span>
        </strong>
        <span>Exemplos ilustrativos</span>
      </figcaption>
      {model.data.radar.slice(0, 2).map((event) => (
        <article key={event.id}>
          <div>
            <span>{event.topic}</span>
            <span>Cenário fictício</span>
          </div>
          <h3>{event.title}</h3>
          <p>{event.summary}</p>
          <small>{event.limitation}</small>
        </article>
      ))}
    </figure>
  );
}
