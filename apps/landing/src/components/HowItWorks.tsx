import type { FC } from 'react';
import { ArrowRight, ClipboardList, Compass, MessagesSquare } from 'lucide-react';
import type { Language } from '../types/content';

const steps = {
  pt: [
    { number: '01', title: 'Organize', description: 'Reúna transações, categorias e objetivos para entender o ponto de partida.', icon: ClipboardList },
    { number: '02', title: 'Contextualize', description: 'Observe fatores econômicos, dados disponíveis e as premissas por trás de cada cenário.', icon: Compass },
    { number: '03', title: 'Compreenda', description: 'Transforme números e evidências em explicações acessíveis, sem esconder incertezas.', icon: MessagesSquare },
  ],
  en: [
    { number: '01', title: 'Organize', description: 'Bring transactions, categories and goals together to understand your starting point.', icon: ClipboardList },
    { number: '02', title: 'Add context', description: 'Consider economic factors, available data and the assumptions behind each scenario.', icon: Compass },
    { number: '03', title: 'Understand', description: 'Turn numbers and evidence into clear explanations without hiding uncertainty.', icon: MessagesSquare },
  ],
};

export const HowItWorks: FC<{ lang: Language }> = ({ lang }) => (
  <section id="como-funciona" className="section section--how">
    <div className="container">
      <div className="how-intro">
        <div>
          <div className="eyebrow"><span className="eyebrow__line" />{lang === 'pt' ? 'UMA JORNADA CONECTADA' : 'A CONNECTED JOURNEY'}</div>
          <h2>{lang === 'pt' ? 'Do dado à decisão, com contexto.' : 'From data to decisions, with context.'}</h2>
        </div>
        <p>{lang === 'pt'
          ? 'O Valyra está sendo pensado para aproximar planejamento financeiro, pesquisa econômica e explicações baseadas em evidências — em vez de tratar cada informação isoladamente.'
          : 'Valyra is being designed to bring financial planning, economic research and evidence-based explanations together — instead of treating every piece of information in isolation.'}</p>
      </div>
      <div className="process-steps">
        {steps[lang].map((step, index) => {
          const Icon = step.icon;
          return (
            <article className="process-step" key={step.number}>
              <div className="process-step__top">
                <span>{step.number}</span>
                <Icon size={21} aria-hidden="true" />
              </div>
              <h3>{step.title}</h3>
              <p>{step.description}</p>
              {index < 2 && <ArrowRight className="process-step__arrow" size={19} aria-hidden="true" />}
            </article>
          );
        })}
      </div>
      <p className="section-footnote"><span className="status-dot" />{lang === 'pt' ? 'Fluxo conceitual da plataforma — as integrações e automações ainda estão em desenvolvimento.' : 'Conceptual platform flow — integrations and automations are still in development.'}</p>
    </div>
  </section>
);
