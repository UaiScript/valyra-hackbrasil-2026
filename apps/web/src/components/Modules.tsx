import type { FC, ReactNode } from 'react';
import {
  ArrowUpRight,
  BrainCircuit,
  ChartNoAxesCombined,
  Check,
  Compass,
  Database,
  MessageCircle,
  Newspaper,
  Sparkles,
  Wallet,
} from 'lucide-react';
import { CONTENT } from '../content';
import type { Language } from '../types/content';

const moduleIcons: ReactNode[] = [
  <ChartNoAxesCombined key="finance" size={22} aria-hidden="true" />,
  <Compass key="alpha" size={22} aria-hidden="true" />,
  <BrainCircuit key="ai" size={22} aria-hidden="true" />,
];

export const RefinedBentoGrid: FC<{ lang: Language; systemUrl: string }> = ({ lang, systemUrl }) => {
  const t = CONTENT[lang].capabilities;
  const isPt = lang === 'pt';
  const financeTransactions = isPt
    ? [
        { name: 'Moradia', category: 'Essencial', amount: 'R$ 1.450,00', marker: 'M' },
        { name: 'Mercado', category: 'Alimentação', amount: 'R$ 620,00', marker: 'M' },
        { name: 'Transporte', category: 'Mobilidade', amount: 'R$ 280,00', marker: 'T' },
      ]
    : [
        { name: 'Housing', category: 'Essential', amount: 'R$ 1,450.00', marker: 'H' },
        { name: 'Groceries', category: 'Food', amount: 'R$ 620.00', marker: 'G' },
        { name: 'Transport', category: 'Mobility', amount: 'R$ 280.00', marker: 'T' },
      ];

  return (
    <section id="capacidades" className="section section--modules">
      <div className="container">
        <div className="section-heading section-heading--split">
          <div>
            <div className="eyebrow"><span className="eyebrow__line" />{t.sectionTag}</div>
            <h2>{t.title}</h2>
          </div>
          <p>{t.subtitle}</p>
        </div>

        <div className="module-list">
          {t.items.map((item, index) => (
            <article className={`module-row module-row--${index + 1}`} key={item.number}>
              <div className="module-row__number">{item.number}</div>

              <div className="module-row__main">
                <div className="module-row__titleline">
                  <span className={`module-icon module-icon--${index + 1}`}>{moduleIcons[index]}</span>
                  <div>
                    <span className="module-tag">{item.tag}</span>
                    <h3>{item.title}</h3>
                    <p className="module-row__subtitle">{item.subtitle}</p>
                  </div>
                </div>

                <p className="module-row__description">{item.description}</p>

                <div className="module-problem">
                  <span className="data-label">{t.problemLabel}</span>
                  <p>{item.problem}</p>
                </div>

                <div className="module-features">
                  <span className="data-label">{t.featuresLabel}</span>
                  <ul className="module-points">
                    {item.bullets.map((bullet) => (
                      <li key={bullet}><Check size={14} aria-hidden="true" />{bullet}</li>
                    ))}
                  </ul>
                </div>

                <a
                  className="module-cta"
                  href={systemUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  data-primary-cta="true"
                  aria-label={`${item.ctaLabel} — ${item.title}`}
                >
                  {item.ctaLabel}
                  <ArrowUpRight size={16} aria-hidden="true" />
                </a>
              </div>

              <div className="module-row__visual" role="group" aria-label={`${item.title} — ${t.demoLabel}`}>
                <div className="module-preview__heading">
                  <span className="data-label">{t.demoLabel}</span>
                  <span className="module-preview__status">{isPt ? 'DADOS SINTÉTICOS' : 'SYNTHETIC DATA'}</span>
                </div>

                {index === 0 && (
                  <div className="finance-preview">
                    <div className="mini-window-bar">
                      <span /><span /><span />
                      <small>{isPt ? 'Finance / orçamento' : 'Finance / budget'}</small>
                    </div>
                    <div className="finance-preview__overview">
                      <div>
                        <span className="data-label">{isPt ? 'Disponível no mês' : 'Available this month'}</span>
                        <strong>R$ 2.480,00</strong>
                        <small>{isPt ? 'Saldo estimado · exemplo' : 'Estimated balance · sample'}</small>
                      </div>
                      <span className="finance-preview__icon"><Wallet size={18} aria-hidden="true" /></span>
                    </div>
                    <div className="finance-preview__budget">
                      <div><span>{isPt ? 'Orçamento utilizado' : 'Budget used'}</span><strong>68%</strong></div>
                      <div className="finance-preview__track" role="progressbar" aria-label={isPt ? 'Orçamento utilizado no exemplo' : 'Sample budget used'} aria-valuemin={0} aria-valuemax={100} aria-valuenow={68}>
                        <span />
                      </div>
                      <small>{isPt ? 'R$ 4.080 de R$ 6.000 · valores fictícios' : 'R$ 4,080 of R$ 6,000 · fictional values'}</small>
                    </div>
                    <div className="finance-preview__transactions">
                      <div className="finance-preview__list-heading">
                        <strong>{isPt ? 'Transações recentes' : 'Recent transactions'}</strong>
                        <span>{isPt ? 'Ver todas' : 'View all'}</span>
                      </div>
                      {financeTransactions.map((transaction) => (
                        <div className="finance-transaction" key={transaction.name}>
                          <span className="finance-transaction__mark">{transaction.marker}</span>
                          <span className="finance-transaction__description"><strong>{transaction.name}</strong><small>{transaction.category}</small></span>
                          <strong className="finance-transaction__amount">− {transaction.amount}</strong>
                        </div>
                      ))}
                    </div>
                    <div className="finance-preview__forecast">
                      <span>{isPt ? 'Projeção de despesas até o fim do mês' : 'Projected expenses by month-end'}</span>
                      <strong>R$ 5.420,00</strong>
                    </div>
                  </div>
                )}

                {index === 1 && (
                  <div className="alpha-preview">
                    <div className="mini-window-bar">
                      <span /><span /><span />
                      <small>Alternative Alpha / radar</small>
                    </div>
                    <div className="alpha-preview__topline">
                      <div><span className="data-label">{isPt ? 'Tema em observação' : 'Topic under observation'}</span><strong>{isPt ? 'Cadeia da soja · MT' : 'Soy supply chain · MT'}</strong></div>
                      <span className="alpha-preview__counter">03 {isPt ? 'SINAIS' : 'SIGNALS'}</span>
                    </div>
                    <div className="alpha-preview__indicator">
                      <div><span>{isPt ? 'Índice de oferta · sintético' : 'Supply index · synthetic'}</span><strong>+0,8%</strong></div>
                      <div className="alpha-preview__bars" aria-hidden="true">
                        {[36, 48, 43, 62, 55, 74, 68, 86].map((height, barIndex) => <span key={barIndex} style={{ height: `${height}%` }} />)}
                      </div>
                    </div>
                    <div className="alpha-preview__signals">
                      <div className="alpha-signal"><span className="alpha-signal__icon"><ChartNoAxesCombined size={15} aria-hidden="true" /></span><span><strong>{isPt ? 'Clima e produção' : 'Weather & production'}</strong><small>{isPt ? 'Indicador ilustrativo' : 'Illustrative indicator'}</small></span><em>{isPt ? 'Monitorar' : 'Watch'}</em></div>
                      <div className="alpha-signal"><span className="alpha-signal__icon"><Database size={15} aria-hidden="true" /></span><span><strong>{isPt ? 'Logística e frete' : 'Logistics & freight'}</strong><small>{isPt ? 'Dado alternativo · demo' : 'Alternative data · demo'}</small></span><em>{isPt ? 'Em análise' : 'Review'}</em></div>
                      <div className="alpha-signal"><span className="alpha-signal__icon"><Newspaper size={15} aria-hidden="true" /></span><span><strong>{isPt ? 'Oferta e preços' : 'Supply & prices'}</strong><small>{isPt ? 'Pauta ilustrativa' : 'Illustrative topic'}</small></span><em>{isPt ? 'Contexto' : 'Context'}</em></div>
                    </div>
                    <div className="alpha-preview__briefing">
                      <div><Newspaper size={14} aria-hidden="true" /><strong>{isPt ? 'Nota de contexto' : 'Context note'}</strong><span>{isPt ? 'EXEMPLO' : 'SAMPLE'}</span></div>
                      <p>{isPt ? 'Uma alteração no custo de transporte pode afetar o escoamento da produção. O sinal precisa ser verificado com dados e fontes.' : 'A change in transportation costs may affect crop distribution. The signal must be checked against data and sources.'}</p>
                      <small>{isPt ? 'Fonte demonstrativa · sem observação de mercado' : 'Demonstration source · no market observation'}</small>
                    </div>
                  </div>
                )}

                {index === 2 && (
                  <div className="ai-preview">
                    <div className="mini-window-bar">
                      <span /><span /><span />
                      <small>Valyra AI / assistant</small>
                    </div>
                    <div className="ai-preview__identity"><span><Sparkles size={16} aria-hidden="true" /></span><div><strong>Valyra AI</strong><small>{isPt ? 'Explicações com contexto' : 'Context-aware explanations'}</small></div></div>
                    <div className="ai-preview__question">
                      <span className="data-label">{isPt ? 'Sua pergunta' : 'Your question'}</span>
                      <p>{isPt ? 'Como o cenário econômico pode afetar meu orçamento?' : 'How could the economic environment affect my budget?'}</p>
                    </div>
                    <div className="ai-preview__context">
                      <span>{isPt ? 'Orçamento pessoal · exemplo' : 'Personal budget · sample'}</span>
                      <span>{isPt ? 'Cenário econômico · exemplo' : 'Economic context · sample'}</span>
                    </div>
                    <div className="ai-preview__answer">
                      <div><MessageCircle size={14} aria-hidden="true" /><strong>{isPt ? 'Uma explicação possível' : 'A possible explanation'}</strong></div>
                      <p>{isPt ? 'Se despesas essenciais aumentarem enquanto sua renda permanecer estável, a margem disponível no mês pode diminuir. A intensidade depende das categorias e das premissas consideradas.' : 'If essential expenses rise while your income remains stable, the amount available each month may decrease. The impact depends on the categories and assumptions considered.'}</p>
                      <div className="ai-preview__sources"><span>{isPt ? 'Contextos considerados' : 'Contexts considered'}</span><span>{isPt ? 'Despesas pessoais' : 'Personal expenses'}</span><span>{isPt ? 'Cenário de preços' : 'Price scenario'}</span></div>
                    </div>
                  </div>
                )}
              </div>

              <span className="module-row__status">{item.metricHighlight.value}</span>
            </article>
          ))}
        </div>
        <p className="section-footnote"><span className="status-dot" />{isPt
          ? 'As telas e os valores são protótipos visuais com dados sintéticos. As funcionalidades e integrações descritas representam o escopo do produto em desenvolvimento.'
          : 'Screens and values are visual prototypes with synthetic data. The described features and integrations represent the scope of a product in development.'}</p>
      </div>
    </section>
  );
};
