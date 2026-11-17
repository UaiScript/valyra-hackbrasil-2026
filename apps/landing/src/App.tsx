/** SPDX-License-Identifier: Apache-2.0 — adapted from the supplied Valyra export. */
import { useEffect, useState } from 'react';
import type { Language } from './types/content';
import { CONTENT } from './content';
import {
  TerminalTopNavigation,
  TerminalHeroWithCockpit,
  RefinedBentoGrid,
  HowItWorks,
  AlternativeAlphaSuite,
  InteractiveStressLab,
  ProjectPrinciples,
  SystemRedirectBanner,
  TerminalFooter,
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
    <div id="top" className="site-shell">
      <a className="skip-link" href="#main">{lang === 'pt' ? 'Pular para o conteúdo' : 'Skip to content'}</a>
      <TerminalTopNavigation lang={lang} onToggleLang={setLang} systemUrl={systemUrl} />
      <main id="main">
        <p className="demo-notice" role="note">
          <span className="demo-notice__dot" aria-hidden="true" />
          {CONTENT[lang].demoNotice}
        </p>
        <TerminalHeroWithCockpit lang={lang} systemUrl={systemUrl} />
        <RefinedBentoGrid lang={lang} />
        <HowItWorks lang={lang} />
        <AlternativeAlphaSuite lang={lang} systemUrl={systemUrl} />
        <InteractiveStressLab lang={lang} systemUrl={systemUrl} />
        <ProjectPrinciples lang={lang} />
        <SystemRedirectBanner lang={lang} systemUrl={systemUrl} />
      </main>
      <TerminalFooter lang={lang} />
    </div>
  );
}
