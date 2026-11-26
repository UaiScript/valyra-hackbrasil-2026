import { useState } from 'react';
import type { FC } from 'react';
import { ArrowDownRight, ArrowRight, ArrowUpRight, ChartNoAxesCombined, CircleHelp, ShieldCheck } from 'lucide-react';
import { CONTENT, COCKPIT_TIMEFRAMES } from '../content';
import { DEMO_HASH } from '../links';
import type { Language, Timeframe } from '../types/content';

export const TerminalHeroWithCockpit: FC<{ lang: Language; systemUrl: string }> = ({ lang, systemUrl }) => {
  const hero = CONTENT[lang].hero;
  const cockpit = CONTENT[lang].cockpit;
  const [selectedTf, setSelectedTf] = useState<Timeframe>('1M');
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);
  const tfData = COCKPIT_TIMEFRAMES[selectedTf];
  const points = tfData.points;
  const minVal = Math.min(...points) * 0.99;
  const maxVal = Math.max(...points) * 1.01;
  const svgWidth = 650;
  const svgHeight = 220;
  const coordinates = points.map((value, index) => {
    const x = (index / (points.length - 1)) * (svgWidth - 40) + 20;
    const y = svgHeight - ((value - minVal) / (maxVal - minVal)) * (svgHeight - 40) - 20;
    return { x, y };
  });
  const pathCoordinates = coordinates.map(({ x, y }) => `${x},${y}`).join(' ');
  const areaCoordinates = `20,${svgHeight - 10} ${pathCoordinates} ${svgWidth - 20},${svgHeight - 10}`;
  const activePointIndex = hoverIndex ?? points.length - 1;
  const activeValue = points[activePointIndex];
  const activeDate = tfData.dates[activePointIndex] || 'Demo';

  return (
    <section className="hero-section">
      <div className="container hero-layout">
        <div className="hero-copy">
          <div className="eyebrow"><span className="eyebrow__line" />{hero.kicker}</div>
          <h1>{hero.titleLine1} <em>{hero.titleLine2}</em></h1>
          <p className="hero-copy__description">{hero.subtitle}</p>
          <div className="hero-actions">
            <a href={DEMO_HASH} data-demo-cta="true" className="button button--primary button--large">
              {CONTENT[lang].nav.openDemo}<ArrowRight size={18} aria-hidden="true" />
            </a>
            <a href={systemUrl} rel="noopener noreferrer" data-primary-cta="true" className="button button--outline button--large">
              {hero.ctaPrimary}<ArrowUpRight size={18} aria-hidden="true" />
            </a>
            <a href="#capacidades" className="text-link">{lang === 'pt' ? 'Conheça os módulos' : 'Explore the modules'}<ArrowDownRight size={17} aria-hidden="true" /></a>
          </div>
          <div className="hero-assurances">
            <span><ShieldCheck size={15} aria-hidden="true" />{lang === 'pt' ? 'Dados e premissas identificados' : 'Identified data and assumptions'}</span>
            <span><CircleHelp size={15} aria-hidden="true" />{lang === 'pt' ? 'Sem promessas de rentabilidade' : 'No return promises'}</span>
          </div>
        </div>

        <div className="product-preview" id="cockpit">
          <div className="product-preview__topline">
            <div className="product-preview__identity">
              <span className="product-preview__icon"><ChartNoAxesCombined size={17} aria-hidden="true" /></span>
              <div>
                <strong>{cockpit.title}</strong>
                <span>{lang === 'pt' ? 'Painel de demonstração' : 'Demonstration dashboard'}</span>
              </div>
            </div>
            <span className="badge badge--warning">{cockpit.feedLabel}</span>
          </div>

          <div className="product-preview__body">
            <div className="preview-heading">
              <div>
                <span className="data-label">{cockpit.spreadLabel}</span>
                <strong className="preview-value tabular-nums">{activeValue.toFixed(2)} <small>pts</small></strong>
              </div>
              <div className="preview-change">
                <span>{lang === 'pt' ? 'Variação do exemplo' : 'Sample change'}</span>
                <strong>{tfData.spreadChange}</strong>
              </div>
            </div>

            <div className="chart-toolbar">
              <span>{lang === 'pt' ? 'Série ilustrativa' : 'Illustrative series'}</span>
              <div className="timeframe-switch" aria-label={lang === 'pt' ? 'Período do gráfico' : 'Chart period'}>
                {(['1D', '1W', '1M', '1Y'] as Timeframe[]).map((timeframe) => (
                  <button
                    key={timeframe}
                    type="button"
                    aria-pressed={selectedTf === timeframe}
                    onClick={() => { setSelectedTf(timeframe); setHoverIndex(null); }}
                  >{timeframe}</button>
                ))}
              </div>
            </div>
            <div className="preview-chart" onMouseLeave={() => setHoverIndex(null)}>
              <svg
                viewBox={`0 0 ${svgWidth} ${svgHeight}`}
                role="img"
                aria-label={lang === 'pt' ? 'Gráfico de linha com valores sintéticos' : 'Line chart with synthetic values'}
                preserveAspectRatio="none"
                onMouseMove={(event) => {
                  const bounds = event.currentTarget.getBoundingClientRect();
                  const ratio = Math.max(0, Math.min(1, (event.clientX - bounds.left) / bounds.width));
                  setHoverIndex(Math.round(ratio * (points.length - 1)));
                }}
              >
                {[40, 90, 140, 190].map((y) => <line key={y} x1="20" y1={y} x2="630" y2={y} className="chart-grid-line" />)}
                <polygon points={areaCoordinates} className="chart-area" />
                <polyline points={pathCoordinates} className="chart-line" />
                {coordinates.map(({ x, y }, index) => (
                  <g key={index}>
                    {index === activePointIndex && <line x1={x} y1="8" x2={x} y2="210" className="chart-active-line" />}
                    <circle cx={x} cy={y} r={index === activePointIndex ? 5 : 2.5} className={index === activePointIndex ? 'chart-point chart-point--active' : 'chart-point'} />
                  </g>
                ))}
              </svg>
            </div>
            <div className="chart-footnote">
              <span>{lang === 'pt' ? 'Ponto selecionado' : 'Selected point'}: <strong>{activeDate}</strong></span>
              <span>{lang === 'pt' ? 'Horizonte' : 'Period'}: <strong>{selectedTf}</strong></span>
            </div>

            <div className="preview-summary">
              <div><span>{cockpit.sharpeLabel}</span><strong>{tfData.sharpe}</strong></div>
              <div><span>{cockpit.varLabel}</span><strong>{tfData.var99}</strong></div>
              <div><span>{cockpit.factorComposition}</span><strong>{tfData.activeFactor}</strong></div>
            </div>
          </div>
          <div className="product-preview__footnote">
            <span className="status-dot" />{lang === 'pt' ? 'Interface estática com dados sintéticos — não conectada a contas ou mercados.' : 'Static interface with synthetic data — not connected to accounts or markets.'}
          </div>
        </div>
      </div>
      <div className="hero-bottomline container">
        <span>{lang === 'pt' ? 'UMA PLATAFORMA EM DESENVOLVIMENTO ABERTO' : 'A PLATFORM IN OPEN DEVELOPMENT'}</span>
        <span className="hero-bottomline__rule" />
        <span>{lang === 'pt' ? 'Uaiscript · Hack Brasil 2026' : 'UaiScript · Hack Brasil 2026'}</span>
      </div>
    </section>
  );
};
