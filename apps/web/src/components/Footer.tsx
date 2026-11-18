import type { FC } from 'react';
import { ArrowUpRight } from 'lucide-react';
import { CONTENT } from '../content';
import type { Language } from '../types/content';
import { REPOSITORY_URL } from '../links';

export const TerminalFooter: FC<{ lang: Language }> = ({ lang }) => {
  const t = CONTENT[lang].footer;
  const nav = CONTENT[lang].nav;
  const links = [
    { href: '#capacidades', label: nav.capabilities },
    { href: '#como-funciona', label: lang === 'pt' ? 'Como funciona' : 'How it works' },
    { href: '#alternative-alpha', label: nav.alternativeAlpha },
    { href: '#transparencia', label: lang === 'pt' ? 'Transparência' : 'Transparency' },
  ];

  return (
    <footer className="site-footer">
      <div className="container">
        <div className="footer-main">
          <div className="footer-brand">
            <a href="#top" className="brand brand--footer"><span className="brand__mark" aria-hidden="true">V</span><span className="brand__word">valyra<span className="brand__period">.</span></span></a>
            <p>{t.tagline}</p>
            <span className="footer-project-label">UAISCRIPT · HACK BRASIL 2026</span>
          </div>
          <div className="footer-column"><h3>{t.quickLinksTitle}</h3><ul>{links.map((link) => <li key={link.href}><a href={link.href}>{link.label}</a></li>)}</ul></div>
          <div className="footer-column"><h3>{t.legalTitle}</h3><ul><li><a href={REPOSITORY_URL} rel="noopener noreferrer">{t.terms}<ArrowUpRight size={13} aria-hidden="true" /></a></li><li><span>{t.privacy}</span></li><li><span>{t.disclaimer}</span></li></ul></div>
        </div>
        <div className="footer-bottom"><span>{t.copyright}</span><span>{t.institutionalNotice}</span></div>
      </div>
    </footer>
  );
};
