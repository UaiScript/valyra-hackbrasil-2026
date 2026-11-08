import { useState } from 'react';
import type { FC } from 'react';
import { Activity, Terminal, ArrowUpRight, ChevronRight } from 'lucide-react';
import { CONTENT, COCKPIT_TIMEFRAMES } from '../content';
import type { Language, Timeframe } from '../types/content';

export const TerminalHeroWithCockpit: FC<{
  lang: Language;
  systemUrl: string;
}> = ({ lang, systemUrl }) => {
  const hero = CONTENT[lang].hero;
  const cockpit = CONTENT[lang].cockpit;

  // Estado do horizonte temporal selecionado no Cockpit (1D, 1W, 1M, 1Y)
  const [selectedTf, setSelectedTf] = useState<Timeframe>('1M');
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);

  const tfData = COCKPIT_TIMEFRAMES[selectedTf];
  const points = tfData.points;
  const minVal = Math.min(...points) * 0.99;
  const maxVal = Math.max(...points) * 1.01;
  const svgWidth = 650;
  const svgHeight = 220;

  // Cálculo das coordenadas SVG da curva do Cockpit
  const pathCoordinates = points
    .map((val, idx) => {
      const x = (idx / (points.length - 1)) * (svgWidth - 40) + 20;
      const y = svgHeight - ((val - minVal) / (maxVal - minVal)) * (svgHeight - 40) - 20;
      return `${x},${y}`;
    })
    .join(' ');

  const areaCoordinates = `20,${svgHeight - 10} ${pathCoordinates} ${svgWidth - 20},${svgHeight - 10}`;

  // Ponto ativo sob inspeção de mouse
  const activePointIndex = hoverIndex !== null ? hoverIndex : points.length - 1;
  const activeValue = points[activePointIndex];
  const activeDate = tfData.dates[activePointIndex] || 'Demo';

  return (
    <section className="relative pt-12 pb-20 bg-terminal-grid bg-glow-radial border-b border-white/8 overflow-hidden">
      <div className="max-w-[1400px] mx-auto px-6">
        <div className="max-w-4xl mx-auto text-center space-y-5 mb-14">

          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-500/10 border border-blue-500/20 text-xs font-mono font-semibold tracking-wider text-[#38BDF8]">
            <Terminal className="w-3.5 h-3.5" />
            <span>{hero.kicker}</span>
          </div>

          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold text-white tracking-tight leading-[1.12] [text-wrap:balance]">
            {hero.titleLine1}{' '}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#60A5FA] via-[#38BDF8] to-[#93C5FD]">
              {hero.titleLine2}
            </span>
          </h1>

          <p className="text-base sm:text-lg text-slate-300 font-normal leading-relaxed max-w-2xl mx-auto [text-wrap:balance]">
            {hero.subtitle}
          </p>

          <div className="pt-2 flex flex-col sm:flex-row items-center justify-center gap-4">
            <a
              href={systemUrl} rel="noopener noreferrer" data-primary-cta="true"
              className="w-full sm:w-auto flex items-center justify-center gap-2.5 px-8 py-3.5 text-sm font-bold text-white bg-[#2563EB] hover:bg-[#1D4ED8] active:scale-[0.98] rounded-xl shadow-xl shadow-blue-600/30 border border-blue-400/40 transition-all whitespace-nowrap"
            >
              <span>{hero.ctaPrimary}</span>
              <ArrowUpRight className="w-4 h-4" />
            </a>

            <a
              href="#cockpit"
              className="w-full sm:w-auto flex items-center justify-center gap-2 px-6 py-3.5 text-sm font-semibold text-slate-200 bg-[#0d1626] hover:bg-[#13223b] border border-white/10 hover:border-white/20 active:scale-[0.98] rounded-xl transition-all whitespace-nowrap"
            >
              <Activity className="w-4 h-4 text-[#38BDF8]" />
              <span>{hero.ctaSecondary}</span>
            </a>
          </div>

        </div>
        <div id="cockpit" className="relative rounded-2xl bg-[#09111e] border border-white/12 shadow-2xl overflow-hidden backdrop-blur-xl">
          <div className="px-5 py-3.5 bg-[#0d1728] border-b border-white/10 flex flex-wrap items-center justify-between gap-4">

            <div className="flex items-center gap-3">
              <div className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-rose-500/80" />
                <span className="w-2.5 h-2.5 rounded-full bg-amber-500/80" />
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-500/80" />
              </div>
              <span className="text-xs font-mono font-bold text-slate-300 tracking-wider">
                {cockpit.title}
              </span>
            </div>
            <div className="flex items-center gap-1 p-0.5 bg-[#070c14] rounded-lg border border-white/10">
              {(['1D', '1W', '1M', '1Y'] as Timeframe[]).map((tf) => (
                <button
                  key={tf} aria-pressed={selectedTf === tf}
                  onClick={() => {
                    setSelectedTf(tf);
                    setHoverIndex(null);
                  }}
                  className={`px-3 py-1 text-xs font-mono font-semibold rounded-md transition-all ${
                    selectedTf === tf
                      ? 'bg-[#2563EB] text-white shadow-xs'
                      : 'text-slate-400 hover:text-white'
                  }`}
                >
                  {tf}
                </button>
              ))}
            </div>

            <div className="flex items-center gap-2 text-xs font-mono text-slate-400">
              <span className="w-2 h-2 rounded-full bg-emerald-400" />
              <span>{cockpit.feedLabel}</span>
            </div>

          </div>
          <div className="grid grid-cols-1 lg:grid-cols-12 divide-y lg:divide-y-0 lg:divide-x divide-white/10">
            <div className="lg:col-span-8 p-6 space-y-4">

              <div className="flex flex-wrap items-end justify-between gap-4">
                <div>
                  <div className="text-xs font-mono text-slate-400 uppercase tracking-wider">
                    {cockpit.spreadLabel} ({selectedTf})
                  </div>
                  <div className="text-3xl font-extrabold font-mono-tabular text-white tracking-tight mt-1 flex items-baseline gap-2">
                    <span>{activeValue.toFixed(2)} pts</span>
                    <span className="text-sm font-semibold text-emerald-400">
                      {tfData.spreadChange}
                    </span>
                  </div>
                </div>

                <div className="text-right text-xs font-mono text-slate-400">
                  <div>{lang === 'pt' ? 'Período:' : 'Period:'} <span className="text-white">{activeDate}</span></div>
                  <div>{lang === 'pt' ? 'Exemplo:' : 'Example:'} <span className="text-[#38BDF8]">{tfData.activeFactor}</span></div>
                </div>
              </div>
              <div
                className="relative w-full h-56 cursor-crosshair overflow-hidden rounded-xl bg-[#070c14]/60 border border-white/5 p-2"
                onMouseLeave={() => setHoverIndex(null)}
              >
                <svg
                  viewBox={`0 0 ${svgWidth} ${svgHeight}`}
                  className="w-full h-full"
                  preserveAspectRatio="none"
                  onMouseMove={(e) => {
                    const rect = e.currentTarget.getBoundingClientRect();
                    const mouseX = e.clientX - rect.left;
                    const ratio = Math.max(0, Math.min(1, mouseX / rect.width));
                    const idx = Math.round(ratio * (points.length - 1));
                    setHoverIndex(idx);
                  }}
                >
                  <defs>
                    <linearGradient id="cockpitGradient" x1="0%" y1="0%" x2="0%" y2="100%">
                      <stop offset="0%" stopColor="#38BDF8" stopOpacity="0.35" />
                      <stop offset="100%" stopColor="#2563EB" stopOpacity="0.0" />
                    </linearGradient>
                  </defs>
                  <line x1="20" y1="40" x2={svgWidth - 20} y2="40" stroke="rgba(255,255,255,0.06)" strokeDasharray="4 4" />
                  <line x1="20" y1="90" x2={svgWidth - 20} y2="90" stroke="rgba(255,255,255,0.06)" strokeDasharray="4 4" />
                  <line x1="20" y1="140" x2={svgWidth - 20} y2="140" stroke="rgba(255,255,255,0.06)" strokeDasharray="4 4" />
                  <line x1="20" y1="190" x2={svgWidth - 20} y2="190" stroke="rgba(255,255,255,0.06)" strokeDasharray="4 4" />
                  <polygon points={areaCoordinates} fill="url(#cockpitGradient)" />
                  <polyline
                    fill="none"
                    stroke="#38BDF8"
                    strokeWidth="2.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    points={pathCoordinates}
                  />
                  {points.map((val, idx) => {
                    const x = (idx / (points.length - 1)) * (svgWidth - 40) + 20;
                    const y = svgHeight - ((val - minVal) / (maxVal - minVal)) * (svgHeight - 40) - 20;
                    const isActive = idx === activePointIndex;
                    return (
                      <g key={idx}>
                        {isActive && (
                          <line
                            x1={x}
                            y1="0"
                            x2={x}
                            y2={svgHeight}
                            stroke="#60A5FA"
                            strokeWidth="1"
                            strokeDasharray="3 3"
                          />
                        )}
                        <circle
                          cx={x}
                          cy={y}
                          r={isActive ? 5 : 2.5}
                          fill={isActive ? '#38BDF8' : '#2563EB'}
                          stroke="#ffffff"
                          strokeWidth={isActive ? 2 : 1}
                        />
                      </g>
                    );
                  })}
                </svg>
              </div>

              <div className="flex items-center justify-between text-[11px] font-mono text-slate-400">
                <span>{cockpit.inspectHint}</span>
                <span className="text-emerald-400 font-semibold">{lang === 'pt' ? 'Série sintética' : 'Synthetic series'}</span>
              </div>

            </div>
            <div className="lg:col-span-4 p-6 space-y-5 bg-[#0b1424]">

              <div className="grid grid-cols-2 gap-3">
                <div className="p-3.5 rounded-xl bg-white/5 border border-white/5">
                  <div className="text-[11px] font-mono text-slate-400 mb-1">
                    {cockpit.sharpeLabel}
                  </div>
                  <div className="text-2xl font-bold font-mono-tabular text-white">
                    {tfData.sharpe}
                  </div>
                </div>

                <div className="p-3.5 rounded-xl bg-white/5 border border-white/5">
                  <div className="text-[11px] font-mono text-slate-400 mb-1">
                    {cockpit.varLabel}
                  </div>
                  <div className="text-2xl font-bold font-mono-tabular text-amber-400">
                    {tfData.var99}
                  </div>
                </div>
              </div>
              <div className="space-y-3">
                <div className="text-xs font-mono font-semibold text-slate-300">
                  {cockpit.factorComposition}
                </div>

                <div className="space-y-2 text-xs font-mono-tabular">
                  <div>
                    <div className="flex justify-between text-slate-300 mb-1">
                      <span>{lang === 'pt' ? 'Orçamento ilustrativo' : 'Sample budget'}</span>
                      <span className="text-[#38BDF8]">38%</span>
                    </div>
                    <div className="w-full h-1.5 rounded-full bg-white/10 overflow-hidden">
                      <div className="h-full bg-[#38BDF8] rounded-full" style={{ width: '38%' }} />
                    </div>
                  </div>

                  <div>
                    <div className="flex justify-between text-slate-300 mb-1">
                      <span>Inflexão de Regime Real</span>
                      <span className="text-emerald-400">32%</span>
                    </div>
                    <div className="w-full h-1.5 rounded-full bg-white/10 overflow-hidden">
                      <div className="h-full bg-emerald-400 rounded-full" style={{ width: '32%' }} />
                    </div>
                  </div>

                  <div>
                    <div className="flex justify-between text-slate-300 mb-1">
                      <span>{lang === 'pt' ? 'Cenário ilustrativo' : 'Sample scenario'}</span>
                      <span className="text-blue-400">30%</span>
                    </div>
                    <div className="w-full h-1.5 rounded-full bg-white/10 overflow-hidden">
                      <div className="h-full bg-blue-400 rounded-full" style={{ width: '30%' }} />
                    </div>
                  </div>
                </div>
              </div>
              <a
                href={systemUrl} rel="noopener noreferrer" data-primary-cta="true"
                className="w-full flex items-center justify-center gap-2 py-3 px-4 text-xs font-bold text-white bg-[#2563EB] hover:bg-[#1D4ED8] rounded-xl transition-all shadow-md shadow-blue-600/20"
              >
                <span>{cockpit.launchConsole}</span>
                <ChevronRight className="w-4 h-4" />
              </a>

            </div>

          </div>

        </div>

      </div>
    </section>
  );
};
