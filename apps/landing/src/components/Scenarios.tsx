import { useState } from 'react';
import type { FC } from 'react';
import { ChevronRight } from 'lucide-react';
import { CONTENT, MACRO_SCENARIOS } from '../content';
import type { Language } from '../types/content';

export const InteractiveStressLab: FC<{
  lang: Language;
  systemUrl: string;
}> = ({ lang, systemUrl }) => {
  const scenarios = MACRO_SCENARIOS[lang];
  const [activeScenarioId, setActiveScenarioId] = useState<string>('inflation');
  const t = CONTENT[lang].simulator;

  const currentScenario =
    scenarios.find((s) => s.id === activeScenarioId) || scenarios[0];

  return (
    <section id="simulador" className="py-24 bg-[#070c14] border-b border-white/8">
      <div className="max-w-[1400px] mx-auto px-6">

        <div className="max-w-3xl mb-12">
          <div className="text-xs font-mono font-bold uppercase tracking-wider text-[#38BDF8] mb-2">
            {t.sectionTag}
          </div>
          <h2 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight mb-4">
            {t.title}
          </h2>
          <p className="text-base sm:text-lg text-slate-300 leading-relaxed">
            {t.description}
          </p>
        </div>

        <div className="bg-[#0b1424] rounded-2xl border border-white/10 p-6 sm:p-8 lg:p-10 shadow-xl space-y-8">
          <div>
            <div className="text-xs font-mono font-semibold text-slate-400 mb-3">
              {t.scenarioLabel}
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
              {scenarios.map((sc) => {
                const isActive = sc.id === activeScenarioId;
                return (
                  <button
                    key={sc.id} aria-pressed={activeScenarioId === sc.id}
                    onClick={() => setActiveScenarioId(sc.id)}
                    className={`p-4 text-left rounded-xl border transition-all ${
                      isActive
                        ? 'bg-[#12223d] border-[#38BDF8] text-white shadow-md'
                        : 'bg-[#070c14] border-white/8 text-slate-400 hover:text-white'
                    }`}
                  >
                    <div className="text-xs font-bold mb-1">
                      <span className={isActive ? 'text-[#38BDF8]' : 'text-slate-200'}>
                        {sc.name}
                      </span>
                    </div>
                    <div className="text-xs text-slate-400 line-clamp-2">
                      {sc.description}
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 pt-2">

            <div className="p-5 rounded-xl bg-[#070c14] border border-blue-500/30">
              <div className="text-xs font-mono text-slate-400 mb-1">
                {t.projectedSpread}
              </div>
              <div className="text-3xl font-extrabold text-[#38BDF8] font-mono-tabular">
                {currentScenario.alphaImpact}
              </div>
              <div className="text-[11px] font-mono text-slate-400 mt-2">
                {lang === 'pt' ? 'Valor fictício, sem previsão' : 'Fictional value, not a forecast'}
              </div>
            </div>

            <div className="p-5 rounded-xl bg-[#070c14] border border-white/8">
              <div className="text-xs font-mono text-slate-400 mb-1">
                {t.maxDrawdown}
              </div>
              <div className="text-3xl font-extrabold text-white font-mono-tabular">
                {currentScenario.portfolioDrawdown}
              </div>
              <div className="text-[11px] font-mono text-emerald-400 font-semibold mt-2">
                {lang === 'pt' ? 'Sem garantia de resultado' : 'No guaranteed outcome'}
              </div>
            </div>

            <div className="p-5 rounded-xl bg-[#070c14] border border-white/8 lg:col-span-2">
              <div className="text-xs font-mono text-slate-400 mb-1">
                {t.regimeIndicator}
              </div>
              <div className="text-lg font-bold text-white mb-2">
                {currentScenario.regimeState}
              </div>
              <div className="text-xs text-slate-300">
                <strong className="text-[#38BDF8]">{t.hedgingRecommendation}:</strong>{' '}
                {currentScenario.hedgingAction}
              </div>
            </div>

          </div>

          <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-4 border-t border-white/10 text-xs font-mono text-slate-400">
            <span>{t.testNotice}</span>
            <a
              href={systemUrl} rel="noopener noreferrer" data-primary-cta="true"
              className="text-[#38BDF8] hover:text-white font-semibold flex items-center gap-1.5 whitespace-nowrap transition-colors"
            >
              <span>{CONTENT[lang].nav.accessSystem}</span>
              <ChevronRight className="w-4 h-4" />
            </a>
          </div>

        </div>

      </div>
    </section>
  );
};
