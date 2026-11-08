import type { FC } from 'react';
import { Activity, Sliders, ShieldCheck, CheckCircle2 } from 'lucide-react';
import { CONTENT } from '../content';
import type { Language } from '../types/content';

export const RefinedBentoGrid: FC<{ lang: Language }> = ({ lang }) => {
  const t = CONTENT[lang].capabilities;

  return (
    <section id="capacidades" className="py-24 bg-[#070c14] border-b border-white/8">
      <div className="max-w-[1400px] mx-auto px-6">
        <div className="max-w-3xl mb-16">
          <div className="text-xs font-mono font-bold uppercase tracking-wider text-[#38BDF8] mb-2">
            {t.sectionTag}
          </div>
          <h2 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight mb-4">
            {t.title}
          </h2>
          <p className="text-base sm:text-lg text-slate-300 leading-relaxed">
            {t.subtitle}
          </p>
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {t.items.map((item, idx) => (
            <div
              key={idx}
              className="bg-[#0b1424] rounded-2xl p-7 border border-white/10 hover:border-[#2563EB]/60 transition-all flex flex-col justify-between group shadow-lg hover:shadow-blue-900/10"
            >
              <div>
                <div className="flex items-center justify-between mb-5">
                  <div className="flex items-center gap-2">
                    <span className="text-2xl font-extrabold text-[#38BDF8] font-mono-tabular">
                      {item.number}
                    </span>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-white/5 border border-white/10 text-slate-400">
                      {item.tag}
                    </span>
                  </div>

                  <div className="w-9 h-9 rounded-lg bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-[#38BDF8]">
                    {idx === 0 && <Activity className="w-4 h-4" />}
                    {idx === 1 && <Sliders className="w-4 h-4" />}
                    {idx === 2 && <ShieldCheck className="w-4 h-4" />}
                  </div>
                </div>

                <h3 className="text-xl font-bold text-white mb-2 leading-snug">
                  {item.title}
                </h3>
                <div className="text-xs font-semibold text-[#38BDF8] mb-4">
                  {item.subtitle}
                </div>
                <p className="text-xs text-slate-300 leading-relaxed mb-6">
                  {item.description}
                </p>
                <div className="mb-6 p-4 rounded-xl bg-[#070c14] border border-white/8">
                  <div className="text-[11px] font-mono text-slate-400 mb-2 flex items-center justify-between">
                    <span>{lang === 'pt' ? 'Visual ilustrativo' : 'Illustrative visual'}</span>
                    <span className="text-emerald-400 font-semibold font-mono-tabular">
                      {item.metricHighlight.value}
                    </span>
                  </div>
                  {item.microChartType === 'matrix' && (
                    <div className="grid grid-cols-3 gap-1.5 text-center text-[10px] font-mono">
                      <div className="p-2 rounded bg-emerald-500/15 border border-emerald-500/30 text-emerald-300">
                        <div>EXP</div>
                        <div className="font-bold">88.4%</div>
                      </div>
                      <div className="p-2 rounded bg-amber-500/15 border border-amber-500/30 text-amber-300">
                        <div>NEU</div>
                        <div className="font-bold">9.2%</div>
                      </div>
                      <div className="p-2 rounded bg-rose-500/15 border border-rose-500/30 text-rose-300">
                        <div>REC</div>
                        <div className="font-bold">2.4%</div>
                      </div>
                    </div>
                  )}
                  {item.microChartType === 'bars' && (
                    <div className="flex items-end justify-between gap-2 h-14 pt-2">
                      {item.dataPoints.map((dp, dpIdx) => (
                        <div key={dpIdx} className="flex-1 h-full flex flex-col items-center justify-end gap-1">
                          <div
                            className="w-full rounded-t bg-gradient-to-t from-[#2563EB] to-[#38BDF8] transition-all hover:brightness-125"
                            style={{ height: `${dp}%` }}
                          />
                          <span className="text-[9px] font-mono text-slate-500">F{dpIdx + 1}</span>
                        </div>
                      ))}
                    </div>
                  )}
                  {item.microChartType === 'curve' && (
                    <div className="h-14 flex items-center">
                      <svg viewBox="0 0 200 40" className="w-full h-full">
                        <polyline
                          fill="none"
                          stroke="#ef4444"
                          strokeWidth="1.5"
                          strokeDasharray="2 2"
                          points="0,15 40,25 80,38 120,35 160,32 200,30"
                        />
                        <polyline
                          fill="none"
                          stroke="#10b981"
                          strokeWidth="2.5"
                          points="0,15 40,18 80,22 120,20 160,18 200,16"
                        />
                      </svg>
                    </div>
                  )}
                </div>
                <ul className="space-y-2 mb-6">
                  {item.bullets.map((bullet, bIdx) => (
                    <li key={bIdx} className="flex items-start gap-2 text-xs text-slate-300">
                      <CheckCircle2 className="w-3.5 h-3.5 text-[#38BDF8] shrink-0 mt-0.5" />
                      <span>{bullet}</span>
                    </li>
                  ))}
                </ul>
              </div>
              <div className="pt-4 border-t border-white/10 flex items-center justify-between">
                <span className="text-xs text-slate-400">{item.metricHighlight.label}</span>
                <span className="text-lg font-bold text-white font-mono-tabular">
                  {item.metricHighlight.value}
                </span>
              </div>
            </div>
          ))}
        </div>

      </div>
    </section>
  );
};
