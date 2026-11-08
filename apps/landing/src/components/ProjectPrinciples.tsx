import type { FC } from 'react';
import { CONTENT } from '../content';
import type { Language } from '../types/content';

export const ProjectPrinciples: FC<{ lang: Language }> = ({ lang }) => {
  const t = CONTENT[lang].proof;

  return (
    <section className="py-20 bg-[#080e18] border-b border-white/8">
      <div className="max-w-[1400px] mx-auto px-6">

        <div className="text-center max-w-2xl mx-auto mb-14">
          <div className="text-xs font-mono font-bold uppercase tracking-wider text-[#38BDF8] mb-2">
            {t.sectionTag}
          </div>
          <h2 className="text-3xl font-extrabold text-white tracking-tight mb-2">
            {t.title}
          </h2>
          <p className="text-sm sm:text-base text-slate-400">
            {t.subtitle}
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {t.stats.map((stat, i) => (
            <div
              key={i}
              className="p-6 rounded-2xl bg-[#0b1424] border border-white/8 text-center hover:border-white/20 transition-all shadow-sm"
            >
              <div className="text-4xl font-extrabold text-[#38BDF8] font-mono-tabular tracking-tight mb-1">
                {stat.value}
              </div>
              <div className="text-sm font-bold text-white mb-1">
                {stat.label}
              </div>
              <div className="text-xs text-slate-400">
                {stat.detail}
              </div>
            </div>
          ))}
        </div>

      </div>
    </section>
  );
};
