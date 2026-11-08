import type { FC } from 'react';
import { CONTENT } from '../content';
import type { Language } from '../types/content';
import { REPOSITORY_URL } from '../links';

export const TerminalFooter: FC<{ lang: Language }> = ({ lang }) => {
  const t = CONTENT[lang].footer;
  const nav = CONTENT[lang].nav;

  return (
    <footer className="bg-[#060a12] text-slate-400 py-16 border-t border-white/8">
      <div className="max-w-[1400px] mx-auto px-6 space-y-12">

        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">

          <div className="md:col-span-2 space-y-3">
            <div className="text-lg font-extrabold text-white tracking-tight flex items-center gap-2">
              <span>VALYRA</span>
              <span className="text-[#38BDF8] text-xs font-mono px-1.5 py-0.5 rounded bg-blue-500/10 border border-blue-500/20">DEMO</span>
            </div>
            <p className="text-xs text-slate-400 max-w-sm leading-relaxed font-mono">
              {t.tagline}
            </p>
            <div className="text-[11px] text-slate-600 pt-2 font-mono">
              {t.institutionalNotice}
            </div>
          </div>

          <div className="space-y-3">
            <div className="text-xs font-mono font-bold uppercase tracking-wider text-white">
              {t.quickLinksTitle}
            </div>
            <ul className="space-y-2 text-xs font-mono text-slate-400">
              <li><a href="#cockpit" className="hover:text-white transition-colors">{nav.cockpit}</a></li>
              <li><a href="#capacidades" className="hover:text-white transition-colors">{nav.capabilities}</a></li>
              <li><a href="#alternative-alpha" className="hover:text-white transition-colors">{nav.alternativeAlpha}</a></li>
              <li><a href="#simulador" className="hover:text-white transition-colors">{nav.simulator}</a></li>
            </ul>
          </div>

          <div className="space-y-3">
            <div className="text-xs font-mono font-bold uppercase tracking-wider text-white">
              {t.legalTitle}
            </div>
            <ul className="space-y-2 text-xs font-mono text-slate-400">
              <li><a href={REPOSITORY_URL} rel="noopener noreferrer" className="hover:text-white">{t.terms}</a></li>
              <li><span>{t.privacy}</span></li>
              <li><span>{t.disclaimer}</span></li>
            </ul>
          </div>

        </div>

        <div className="pt-8 border-t border-white/8 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs font-mono text-slate-500">
          <span>{t.copyright}</span>
          <div className="flex items-center gap-4">
            <span className="text-emerald-400">UaiScript</span>
            <span>Hack Brasil 2026</span>
          </div>
        </div>

      </div>
    </footer>
  );
};
