import { useState } from 'react';
import type { FC } from 'react';
import { ArrowUpRight, Check } from 'lucide-react';
import { CONTENT, ALPHA_MODELS } from '../content';
import type { Language, AlphaModel } from '../types/content';

export const AlternativeAlphaSuite: FC<{ lang: Language; systemUrl: string }> = ({ lang, systemUrl }) => {
  const models = ALPHA_MODELS[lang];
  const [selectedId, setSelectedId] = useState<'liquidity' | 'regime' | 'factorDrift'>('liquidity');
  const t = CONTENT[lang].alternativeAlpha;
  const currentModel: AlphaModel = models.find((model) => model.id === selectedId) || models[0];
  const points = currentModel.dataPoints;
  const maxVal = Math.max(...points) * 1.05;
  const minVal = Math.min(...points) * 0.95;
  const pathCoordinates = points.map((value, index) => {
    const x = (index / (points.length - 1)) * 600;
    const y = 170 - ((value - minVal) / (maxVal - minVal)) * 145 - 10;
    return `${x},${y}`;
  }).join(' ');

  return (
    <section id="alternative-alpha" className="section section--alpha">
      <div className="container">
        <div className="alpha-heading">
          <div>
            <div className="eyebrow eyebrow--on-dark"><span className="eyebrow__line" />{t.sectionTag}</div>
            <h2>{t.title}<span className="alpha-heading__period">.</span></h2>
          </div>
          <p>{t.description}</p>
        </div>

        <div className="research-console">
          <div className="research-console__header">
            <div className="research-console__title"><span className="console-mark">A</span><div><strong>{lang === 'pt' ? 'Explorador de sinais' : 'Signal explorer'}</strong><small>{lang === 'pt' ? 'Exemplo de pesquisa' : 'Research example'}</small></div></div>
            <span className="badge badge--warning">{lang === 'pt' ? 'DADOS SINTÉTICOS' : 'SYNTHETIC DATA'}</span>
          </div>
          <div className="research-console__content">
            <div className="research-models">
              <span className="data-label">{t.modelSelectorLabel}</span>
              <div className="research-models__list">
                {models.map((model) => (
                  <button key={model.id} type="button" aria-pressed={selectedId === model.id} onClick={() => setSelectedId(model.id)}>
                    <span><small>{model.tag}</small><strong>{model.name}</strong></span>
                    {selectedId === model.id && <Check size={17} aria-hidden="true" />}
                  </button>
                ))}
              </div>
            </div>

            <div className="research-detail">
              <div className="research-metrics">
                <div><span>{t.signalSpread}</span><strong>{currentModel.alphaSpread}</strong></div>
                <div><span>{t.sharpeRatio}</span><strong>{currentModel.sharpe}</strong></div>
                <div><span>{t.confidenceScore}</span><strong>{currentModel.confidence}</strong></div>
                <div><span>{t.executionLatency}</span><strong>{currentModel.latency}</strong></div>
              </div>
              <div className="research-visuals">
                <div className="research-chart">
                  <div className="research-chart__heading"><span>{t.historicalYield}</span><span className="badge badge--warning">DEMO</span></div>
                  <svg viewBox="0 0 600 190" role="img" aria-label={lang === 'pt' ? 'Série ilustrativa de pesquisa' : 'Illustrative research series'} preserveAspectRatio="none">
                    {[35, 80, 125, 170].map((y) => <line key={y} x1="0" y1={y} x2="600" y2={y} className="chart-grid-line chart-grid-line--dark" />)}
                    <polyline points={pathCoordinates} className="chart-line chart-line--bright" />
                    <circle cx="600" cy={Number(pathCoordinates.split(' ').at(-1)?.split(',')[1] || 0)} r="5" className="chart-point chart-point--active" />
                  </svg>
                  <p>{currentModel.description}</p>
                </div>
                <div className="research-factors">
                  <span className="data-label">{t.activeWeights}</span>
                  {currentModel.factors.map((factor) => (
                    <div className="research-factor" key={factor.name}>
                      <span>{factor.name}<small>{lang === 'pt' ? 'Peso fictício' : 'Fictional weight'} · {factor.weight}</small></span>
                      <strong>{factor.delta}</strong>
                    </div>
                  ))}
                  <a href={systemUrl} rel="noopener noreferrer" data-primary-cta="true" className="text-link text-link--light">
                    {t.terminalAction}<ArrowUpRight size={16} aria-hidden="true" />
                  </a>
                </div>
              </div>
            </div>
          </div>
        </div>
        <p className="alpha-disclaimer">{lang === 'pt' ? 'Esta visualização não utiliza dados observados, não executa modelos e não representa recomendação de investimento.' : 'This visualization does not use observed data, run models or represent investment advice.'}</p>
      </div>
    </section>
  );
};
