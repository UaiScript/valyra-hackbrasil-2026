import { useState } from 'react';
import type { FC } from 'react';
import { ArrowUpRight, GitBranch } from 'lucide-react';
import { CONTENT, MACRO_SCENARIOS } from '../content';
import type { Language } from '../types/content';

export const InteractiveStressLab: FC<{ lang: Language; systemUrl: string }> = ({ lang, systemUrl }) => {
  const scenarios = MACRO_SCENARIOS[lang];
  const [activeScenarioId, setActiveScenarioId] = useState<string>('inflation');
  const t = CONTENT[lang].simulator;
  const currentScenario = scenarios.find((scenario) => scenario.id === activeScenarioId) || scenarios[0];

  return (
    <section id="simulador" className="section section--scenarios">
      <div className="container">
        <div className="section-heading section-heading--split">
          <div>
            <div className="eyebrow"><span className="eyebrow__line" />{t.sectionTag}</div>
            <h2>{t.title}</h2>
          </div>
          <p>{t.description}</p>
        </div>
        <div className="scenario-explorer">
          <div className="scenario-explorer__top">
            <div><GitBranch size={17} aria-hidden="true" /><strong>{lang === 'pt' ? 'Explorador de cenários' : 'Scenario explorer'}</strong></div>
            <span className="badge badge--warning">{lang === 'pt' ? 'EXEMPLOS ESTÁTICOS' : 'STATIC EXAMPLES'}</span>
          </div>
          <div className="scenario-explorer__body">
            <span className="data-label">{t.scenarioLabel}</span>
            <div className="scenario-options">
              {scenarios.map((scenario) => (
                <button key={scenario.id} type="button" aria-pressed={activeScenarioId === scenario.id} onClick={() => setActiveScenarioId(scenario.id)}>
                  <strong>{scenario.name}</strong><span>{scenario.description}</span>
                </button>
              ))}
            </div>
            <div className="scenario-results">
              <div><span>{t.projectedSpread}</span><strong>{currentScenario.alphaImpact}</strong><small>{lang === 'pt' ? 'Valor fictício, sem previsão' : 'Fictional value, not a forecast'}</small></div>
              <div><span>{t.maxDrawdown}</span><strong>{currentScenario.portfolioDrawdown}</strong><small>{lang === 'pt' ? 'Sem garantia de resultado' : 'No guaranteed outcome'}</small></div>
              <div className="scenario-results__context"><span>{t.regimeIndicator}</span><strong>{currentScenario.regimeState}</strong><p><b>{t.hedgingRecommendation}:</b> {currentScenario.hedgingAction}</p></div>
            </div>
            <div className="scenario-explorer__footer">
              <p>{t.testNotice}</p>
              <a href={systemUrl} rel="noopener noreferrer" data-primary-cta="true" className="text-link">{CONTENT[lang].nav.accessSystem}<ArrowUpRight size={16} aria-hidden="true" /></a>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
