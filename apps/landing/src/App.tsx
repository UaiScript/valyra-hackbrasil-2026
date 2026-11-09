/** SPDX-License-Identifier: Apache-2.0 — adapted from the supplied Valyra export. */
import { useEffect, useState } from 'react';
import type { Language } from './types/content';
import { CONTENT } from './content';
import {
  TerminalTopNavigation, TerminalHeroWithCockpit, DemoMetrics,
  RefinedBentoGrid, AlternativeAlphaSuite, InteractiveStressLab,
  ProjectPrinciples, SystemRedirectBanner, TerminalFooter,
} from './components';

function initialLanguage(): Language {
  try { return localStorage.getItem('valyra_lang') === 'en' ? 'en' : 'pt'; }
  catch { return 'pt'; }
}

export default function App() {
  const [lang, setLang] = useState<Language>(initialLanguage);
  useEffect(() => {
    document.documentElement.lang = lang === 'pt' ? 'pt-BR' : 'en';
    try { localStorage.setItem('valyra_lang', lang); } catch { /* Storage is optional. */ }
  }, [lang]);
  const systemUrl = __DESTINATION__.url;
  return (
    <div id="top" className="min-h-screen bg-[#070c14] text-slate-100 flex flex-col antialiased selection:bg-[#2563EB]/30 selection:text-[#38BDF8]">
      <a className="skip-link" href="#main">{lang === 'pt' ? 'Pular para o conteúdo' : 'Skip to content'}</a>
      <TerminalTopNavigation lang={lang} onToggleLang={setLang} systemUrl={systemUrl} />
      <main id="main" className="flex-1">
        <p className="demo-notice" role="note">{CONTENT[lang].demoNotice}</p>
        <TerminalHeroWithCockpit lang={lang} systemUrl={systemUrl} />
        <DemoMetrics lang={lang} />
        <RefinedBentoGrid lang={lang} />
        <AlternativeAlphaSuite lang={lang} systemUrl={systemUrl} />
        <InteractiveStressLab lang={lang} systemUrl={systemUrl} />
        <ProjectPrinciples lang={lang} />
        <SystemRedirectBanner lang={lang} systemUrl={systemUrl} />
      </main>
      <TerminalFooter lang={lang} />
    </div>
  );
}
