import type { FC } from 'react';
import { CONTENT } from '../content';
import type { Language } from '../types/content';

export const DemoMetrics: FC<{ lang: Language }> = ({ lang }) => {
  const ticker = CONTENT[lang].tickerStrip;

  return (
    <section id="performance" className="py-16 bg-[#080e18] border-b border-white/8">
      <div className="max-w-[1400px] mx-auto px-6">

        <div className="text-xs font-mono font-semibold tracking-wider text-slate-400 mb-6 text-center">
          {ticker.title}
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {ticker.items.map((item, idx) => (
            <div
              key={idx}
              className="bg-[#0c1524] rounded-xl p-5 border border-white/8 hover:border-[#2563EB]/50 transition-all shadow-sm group"
            >
              <div className="text-xs font-mono text-slate-400 truncate">
                {item.label}
              </div>
              <div className="text-3xl font-extrabold text-white font-mono-tabular mt-2 tracking-tight group-hover:text-[#38BDF8] transition-colors">
                {item.value}
              </div>
              <div className="mt-3 flex items-center justify-between text-xs font-mono">
                <span className="text-emerald-400 font-semibold">{item.change}</span>
                <span className="text-slate-500">{item.benchmark}</span>
              </div>
              <div className="mt-1 text-[11px] text-slate-500 truncate">
                {item.subtext}
              </div>
            </div>
          ))}
        </div>

      </div>
    </section>
  );
};
