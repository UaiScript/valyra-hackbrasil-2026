import { useState } from 'react';
import type { FC } from 'react';
import { ChevronRight } from 'lucide-react';
import { CONTENT, ALPHA_MODELS } from '../content';
import type { Language, AlphaModel } from '../types/content';

export const AlternativeAlphaSuite: FC<{
  lang: Language;
  systemUrl: string;
}> = ({ lang, systemUrl }) => {
  const models = ALPHA_MODELS[lang];
  const [selectedId, setSelectedId] = useState<'liquidity' | 'regime' | 'factorDrift'>('liquidity');
  const t = CONTENT[lang].alternativeAlpha;

  const currentModel: AlphaModel = models.find((m) => m.id === selectedId) || models[0];

  const points = currentModel.dataPoints;
  const maxVal = Math.max(...points) * 1.05;
  const minVal = Math.min(...points) * 0.95;
  const svgWidth = 600;
  const svgHeight = 180;

  const pathCoordinates = points
    .map((val, idx) => {
      const x = (idx / (points.length - 1)) * svgWidth;
      const y = svgHeight - ((val - minVal) / (maxVal - minVal)) * (svgHeight - 20) - 10;
      return `${x},${y}`;
    })
    .join(' ');

  const areaCoordinates = `0,${svgHeight} ${pathCoordinates} ${svgWidth},${svgHeight}`;

  return (
    <section id="alternative-alpha" className="py-24 bg-[#080e18] text-white border-b border-white/8">
      <div className="max-w-[1400px] mx-auto px-6">

        <div className="max-w-3xl mb-12">
          <div className="inline-flex items-center gap-2 text-xs font-mono font-bold uppercase tracking-wider text-[#38BDF8] mb-2">
            <span className="w-2 h-2 rounded-full bg-[#2563EB]" />
            <span>{t.sectionTag}</span>
          </div>
          <h2 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-white mb-4">
            {t.title}
          </h2>
          <p className="text-base sm:text-lg text-slate-300 leading-relaxed">
            {t.description}
          </p>
        </div>
        <div className="bg-[#0b1424] rounded-2xl border border-white/12 p-6 sm:p-8 lg:p-10 shadow-2xl space-y-8">
          <div>
            <div className="text-xs uppercase font-mono tracking-wider text-slate-400 font-semibold mb-3">
              {t.modelSelectorLabel}
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              {models.map((model) => {
                const isActive = model.id === selectedId;
                return (
                  <button
                    key={model.id} aria-pressed={selectedId === model.id}
                    onClick={() => setSelectedId(model.id)}
                    className={`text-left p-4 rounded-xl border transition-all ${
                      isActive
                        ? 'bg-[#2563EB] border-[#38BDF8] text-white shadow-lg shadow-blue-900/50'
                        : 'bg-[#070c14] border-white/8 text-slate-300 hover:bg-white/5 hover:text-white'
                    }`}
                  >
                    <div className="flex items-center justify-between text-xs font-mono-tabular opacity-90 mb-1">
                      <span>{model.tag}</span>
                      <span className="font-semibold">{model.alphaSpread}</span>
                    </div>
                    <div className="font-bold text-sm leading-snug">{model.name}</div>
                  </button>
                );
              })}
            </div>
          </div>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 p-5 bg-[#070c14] rounded-xl border border-white/8">
            <div>
              <div className="text-xs font-mono text-slate-400 mb-1">{t.signalSpread}</div>
              <div className="text-2xl font-bold font-mono-tabular text-[#38BDF8]">
                {currentModel.alphaSpread}
              </div>
            </div>
            <div>
              <div className="text-xs font-mono text-slate-400 mb-1">{t.sharpeRatio}</div>
              <div className="text-2xl font-bold font-mono-tabular text-white">
                {currentModel.sharpe}
              </div>
            </div>
            <div>
              <div className="text-xs font-mono text-slate-400 mb-1">{t.confidenceScore}</div>
              <div className="text-2xl font-bold font-mono-tabular text-emerald-400">
                {currentModel.confidence}
              </div>
            </div>
            <div>
              <div className="text-xs font-mono text-slate-400 mb-1">{t.executionLatency}</div>
              <div className="text-2xl font-bold font-mono-tabular text-white">
                {currentModel.latency}
              </div>
            </div>
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">

            <div className="lg:col-span-7 bg-[#070c14] rounded-xl p-5 border border-white/8">
              <div className="flex items-center justify-between mb-4">
                <div className="text-xs font-mono font-semibold text-slate-300">
                  {t.historicalYield}
                </div>
                <span className="text-xs font-mono-tabular text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                  {currentModel.alphaSpread} · DEMO
                </span>
              </div>

              <div className="w-full overflow-hidden">
                <svg
                  viewBox={`0 0 ${svgWidth} ${svgHeight}`}
                  className="w-full h-44 drop-shadow"
                  preserveAspectRatio="none"
                >
                  <defs>
                    <linearGradient id="alphaGradient" x1="0%" y1="0%" x2="0%" y2="100%">
                      <stop offset="0%" stopColor="#2563EB" stopOpacity="0.45" />
                      <stop offset="100%" stopColor="#2563EB" stopOpacity="0.0" />
                    </linearGradient>
                  </defs>

                  <polygon points={areaCoordinates} fill="url(#alphaGradient)" />
                  <polyline
                    fill="none"
                    stroke="#38BDF8"
                    strokeWidth="3"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    points={pathCoordinates}
                  />

                  {points.length > 0 && (
                    <circle
                      cx={svgWidth}
                      cy={
                        svgHeight -
                        ((points[points.length - 1] - minVal) / (maxVal - minVal)) *
                          (svgHeight - 20) -
                        10
                      }
                      r="5"
                      fill="#38BDF8"
                      stroke="#ffffff"
                      strokeWidth="2"
                    />
                  )}
                </svg>
              </div>

              <div className="text-xs text-slate-400 mt-3 font-mono">
                {currentModel.description}
              </div>
            </div>
            <div className="lg:col-span-5 bg-[#070c14] rounded-xl p-5 border border-white/8 space-y-4">
              <div className="text-xs font-mono font-semibold text-slate-300">
                {t.activeWeights}
              </div>

              <div className="space-y-3">
                {currentModel.factors.map((f, i) => (
                  <div
                    key={i}
                    className="p-3 bg-white/5 rounded-lg border border-white/5 flex items-center justify-between text-xs"
                  >
                    <div>
                      <div className="font-medium text-white">{f.name}</div>
                      <div className="text-slate-400 text-[11px] font-mono-tabular mt-0.5">
                        {lang === 'pt' ? 'Peso fictício:' : 'Fictional weight:'} {f.weight}
                      </div>
                    </div>
                    <div className="font-mono-tabular font-bold text-[#38BDF8] bg-blue-500/15 px-2 py-1 rounded">
                      {f.delta}
                    </div>
                  </div>
                ))}
              </div>

              <a
                href={systemUrl} rel="noopener noreferrer" data-primary-cta="true"
                className="w-full mt-2 flex items-center justify-center gap-2 py-3 px-4 text-xs font-bold text-white bg-[#2563EB] hover:bg-[#1d4ed8] rounded-xl transition-all shadow-md shadow-blue-600/20"
              >
                <span>{t.terminalAction}</span>
                <ChevronRight className="w-4 h-4" />
              </a>
            </div>

          </div>

        </div>

      </div>
    </section>
  );
};
