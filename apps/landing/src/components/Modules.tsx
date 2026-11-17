import type { FC, ReactNode } from 'react';
import { ArrowUpRight, BrainCircuit, ChartNoAxesCombined, Compass, Database, Sparkles } from 'lucide-react';
import { CONTENT } from '../content';
import type { Language } from '../types/content';

const moduleIcons: ReactNode[] = [
  <ChartNoAxesCombined size={22} aria-hidden="true" />,
  <Compass size={22} aria-hidden="true" />,
  <BrainCircuit size={22} aria-hidden="true" />,
];

export const RefinedBentoGrid: FC<{ lang: Language }> = ({ lang }) => {
  const t = CONTENT[lang].capabilities;

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
            <article className="module-row" key={item.number}>
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
                <ul className="module-points">
                  {item.bullets.map((bullet) => <li key={bullet}><span aria-hidden="true">—</span>{bullet}</li>)}
                </ul>
              </div>
              <div className="module-row__visual" aria-label={lang === 'pt' ? 'Prévia ilustrativa do módulo' : 'Illustrative module preview'}>
                {index === 0 && (
                  <div className="finance-preview">
                    <div className="mini-window-bar"><span /><span /><span /><small>Finance / overview</small></div>
                    <div className="finance-preview__balance"><span>{lang === 'pt' ? 'Saldo projetado' : 'Projected balance'}</span><strong>R$ 4.820,00</strong><small><i />{lang === 'pt' ? 'Exemplo ilustrativo' : 'Illustrative example'}</small></div>
                    <div className="finance-preview__bars">{[42, 68, 51, 82, 59, 75, 92].map((height, i) => <span key={i} style={{ height: `${height}%` }} />)}</div>
                  </div>
                )}
                {index === 1 && (
                  <div className="alpha-preview">
                    <div className="mini-window-bar"><span /><span /><span /><small>Alternative Alpha / signals</small></div>
                    <div className="alpha-preview__signal"><span>{lang === 'pt' ? 'Sinal monitorado' : 'Monitored signal'}</span><strong>{lang === 'pt' ? 'Clima & produção' : 'Weather & production'}</strong></div>
                    <div className="alpha-preview__source"><Database size={14} /><span>{lang === 'pt' ? 'Fonte e data em contexto' : 'Source and date in context'}</span><ArrowUpRight size={14} /></div>
                  </div>
                )}
                {index === 2 && (
                  <div className="ai-preview">
                    <div className="mini-window-bar"><span /><span /><span /><small>Valyra AI / explanation</small></div>
                    <div className="ai-preview__bubble"><Sparkles size={14} /><span>{lang === 'pt' ? 'O que mudou no cenário?' : 'What changed in this scenario?'}</span></div>
                    <div className="ai-preview__answer"><span /><span /><span /></div>
                    <small>{lang === 'pt' ? 'Resposta com fontes e limitações' : 'Answer with sources and limitations'}</small>
                  </div>
                )}
              </div>
              <span className="module-row__status">{item.metricHighlight.value}</span>
            </article>
          ))}
        </div>
        <p className="section-footnote"><span className="status-dot" />{lang === 'pt' ? 'As interfaces e os valores apresentados são protótipos visuais; os módulos ainda estão em desenvolvimento.' : 'The interfaces and values shown are visual prototypes; the modules are still under development.'}</p>
      </div>
    </section>
  );
};
