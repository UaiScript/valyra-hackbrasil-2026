import type { FC } from 'react';
import { Cpu, ExternalLink } from 'lucide-react';
import { CONTENT } from '../content';
import type { Language } from '../types/content';

export const SystemRedirectBanner: FC<{
  lang: Language;
  systemUrl: string;
}> = ({ lang, systemUrl }) => {
  const t = CONTENT[lang].ctaBanner;

  return (
    <section className="py-20 bg-gradient-to-b from-[#09111e] to-[#060a12] text-white border-b border-white/8">
      <div className="max-w-[1400px] mx-auto px-6">

        <div className="max-w-4xl mx-auto text-center space-y-6">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-500/10 border border-blue-500/20 text-xs font-mono text-[#38BDF8]">
            <Cpu className="w-3.5 h-3.5" />
            <span>{t.deploymentBadge}</span>
          </div>

          <h2 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-white [text-wrap:balance]">
            {t.title}
          </h2>
          <p className="text-base sm:text-lg text-slate-300 leading-relaxed max-w-2xl mx-auto [text-wrap:balance]">
            {t.description}
          </p>

          <div className="pt-4 flex flex-col sm:flex-row items-center justify-center gap-4">
            <a
              href={systemUrl} rel="noopener noreferrer" data-primary-cta="true"
              className="w-full sm:w-auto flex items-center justify-center gap-3 px-9 py-4 text-sm font-bold text-white bg-[#2563EB] hover:bg-[#1D4ED8] active:scale-[0.98] rounded-xl shadow-xl shadow-blue-600/30 border border-blue-400/40 transition-all whitespace-nowrap"
            >
              <span>{t.button}</span>
              <ExternalLink className="w-4 h-4" />
            </a>
          </div>

          <div className="pt-2 text-xs font-mono text-slate-500 flex items-center justify-center gap-2">
            <span>{t.dockerInfo}</span>
          </div>
        </div>

      </div>
    </section>
  );
};
