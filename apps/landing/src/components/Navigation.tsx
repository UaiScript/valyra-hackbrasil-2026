import type { FC } from 'react';
import { ExternalLink } from 'lucide-react';
import { CONTENT } from '../content';
import type { Language } from '../types/content';

interface NavigationProps {
  lang: Language;
  onToggleLang: (lang: Language) => void;
  systemUrl: string;
}

export const TerminalTopNavigation: FC<NavigationProps> = ({
  lang,
  onToggleLang,
  systemUrl,
}) => {
  const t = CONTENT[lang].nav;

  return (
    <header className="sticky top-0 z-40 w-full bg-[#070c14]/90 backdrop-blur-md border-b border-white/8 transition-all">
      <div className="max-w-[1400px] mx-auto px-4 sm:px-6 min-h-20 py-3 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-4 shrink-0">
          <a href="#top" className="flex items-center gap-3 group">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[#2563EB] to-[#102A56] border border-blue-400/30 flex items-center justify-center text-white font-extrabold text-sm tracking-widest shadow-sm shadow-blue-500/20 transition-transform group-hover:scale-105">
              V
            </div>
            <div className="flex flex-col">
              <span className="text-lg font-extrabold tracking-tight text-white flex items-center gap-1.5">
                VALYRA <span className="text-[#38BDF8] text-xs font-mono font-semibold tracking-normal px-1.5 py-0.5 rounded bg-blue-500/10 border border-blue-500/20">DEMO</span>
              </span>
            </div>
          </a>
          <div className="hidden 2xl:flex items-center gap-2 pl-4 border-l border-white/10 text-[11px] font-mono-tabular text-emerald-400">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            <span>{t.systemLive}</span>
          </div>
        </div>
        <nav className="hidden 2xl:flex items-center gap-5 text-[13px] font-medium text-slate-300">
          <a
            href="#cockpit"
            className="hover:text-white transition-colors whitespace-nowrap shrink-0 py-1 hover:text-[#38BDF8]"
          >
            {t.cockpit}
          </a>
          <a
            href="#capacidades"
            className="hover:text-white transition-colors whitespace-nowrap shrink-0 py-1 hover:text-[#38BDF8]"
          >
            {t.capabilities}
          </a>
          <a
            href="#alternative-alpha"
            className="hover:text-white transition-colors whitespace-nowrap shrink-0 py-1 hover:text-[#38BDF8]"
          >
            {t.alternativeAlpha}
          </a>
          <a
            href="#simulador"
            className="hover:text-white transition-colors whitespace-nowrap shrink-0 py-1 hover:text-[#38BDF8]"
          >
            {t.simulator}
          </a>
          <a
            href="#performance"
            className="hover:text-white transition-colors whitespace-nowrap shrink-0 py-1 hover:text-[#38BDF8]"
          >
            {t.performance}
          </a>
        </nav>
        <div className="flex items-center gap-3 shrink-0">
          <div className="flex items-center p-1 bg-[#0d1626] rounded-lg border border-white/10">
            <button
              onClick={() => onToggleLang('pt')} aria-pressed={lang === 'pt'}
              className={`px-2.5 py-1 text-xs font-mono-tabular font-semibold rounded-md transition-all whitespace-nowrap ${
                lang === 'pt'
                  ? 'bg-[#2563EB] text-white shadow-xs'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              PT
            </button>
            <button
              onClick={() => onToggleLang('en')} aria-pressed={lang === 'en'}
              className={`px-2.5 py-1 text-xs font-mono-tabular font-semibold rounded-md transition-all whitespace-nowrap ${
                lang === 'en'
                  ? 'bg-[#2563EB] text-white shadow-xs'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              EN
            </button>
          </div>
          <a
            href={systemUrl} rel="noopener noreferrer" data-primary-cta="true"
            className="flex items-center gap-2 px-3 sm:px-5 py-2.5 text-xs font-bold text-white bg-gradient-to-r from-[#2563EB] to-[#1d4ed8] hover:from-[#1d4ed8] hover:to-[#1e40af] active:scale-[0.98] rounded-xl shadow-lg shadow-blue-600/25 border border-blue-400/30 transition-all whitespace-nowrap shrink-0"
          >
            <span>{t.accessSystem}</span>
            <ExternalLink className="w-3.5 h-3.5" />
          </a>
        </div>

      </div>
    </header>
  );
};
