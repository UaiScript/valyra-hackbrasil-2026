import { useState } from 'react';
import type { FC } from 'react';
import { ArrowUpRight, Menu, X } from 'lucide-react';
import { CONTENT } from '../content';
import type { Language } from '../types/content';

interface NavigationProps {
  lang: Language;
  onToggleLang: (lang: Language) => void;
  systemUrl: string;
}

export const TerminalTopNavigation: FC<NavigationProps> = ({ lang, onToggleLang, systemUrl }) => {
  const [menuOpen, setMenuOpen] = useState(false);
  const t = CONTENT[lang].nav;
  const links = [
    { href: '#capacidades', label: t.capabilities },
    { href: '#como-funciona', label: lang === 'pt' ? 'Como funciona' : 'How it works' },
    { href: '#alternative-alpha', label: t.alternativeAlpha },
    { href: '#transparencia', label: lang === 'pt' ? 'Transparência' : 'Transparency' },
  ];

  const closeMenu = () => setMenuOpen(false);

  return (
    <header className="site-header">
      <div className="site-header__inner container">
        <a href="#top" className="brand" aria-label="Valyra — início" onClick={closeMenu}>
          <span className="brand__mark" aria-hidden="true">V</span>
          <span className="brand__word">valyra<span className="brand__period">.</span></span>
        </a>

        <nav className={`site-nav${menuOpen ? ' site-nav--open' : ''}`} aria-label={lang === 'pt' ? 'Navegação principal' : 'Main navigation'}>
          {links.map((link) => (
            <a key={link.href} href={link.href} onClick={closeMenu}>{link.label}</a>
          ))}
        </nav>

        <div className="site-header__actions">
          <div className="language-switch" aria-label={lang === 'pt' ? 'Selecionar idioma' : 'Select language'}>
            <button type="button" onClick={() => { onToggleLang('pt'); closeMenu(); }} aria-pressed={lang === 'pt'}>PT</button>
            <button type="button" onClick={() => { onToggleLang('en'); closeMenu(); }} aria-pressed={lang === 'en'}>EN</button>
          </div>
          <a href={systemUrl} rel="noopener noreferrer" data-primary-cta="true" className="button button--primary header-cta">
            {t.accessSystem}<ArrowUpRight size={16} aria-hidden="true" />
          </a>
          <button
            type="button"
            className="mobile-menu-toggle"
            aria-label={menuOpen ? (lang === 'pt' ? 'Fechar menu' : 'Close menu') : (lang === 'pt' ? 'Abrir menu' : 'Open menu')}
            aria-expanded={menuOpen}
            aria-controls="mobile-navigation"
            onClick={() => setMenuOpen((open) => !open)}
          >
            {menuOpen ? <X size={21} /> : <Menu size={21} />}
          </button>
        </div>
        <nav id="mobile-navigation" className="mobile-navigation" data-open={menuOpen} aria-label={lang === 'pt' ? 'Navegação móvel' : 'Mobile navigation'}>
          {links.map((link) => (
            <a key={link.href} href={link.href} onClick={closeMenu}>{link.label}</a>
          ))}
          <div className="mobile-language-switch" aria-label={lang === 'pt' ? 'Selecionar idioma' : 'Select language'}>
            <span>{lang === 'pt' ? 'Idioma' : 'Language'}</span>
            <div>
              <button type="button" onClick={() => { onToggleLang('pt'); closeMenu(); }} aria-pressed={lang === 'pt'}>PT</button>
              <button type="button" onClick={() => { onToggleLang('en'); closeMenu(); }} aria-pressed={lang === 'en'}>EN</button>
            </div>
          </div>
          <a href={systemUrl} rel="noopener noreferrer" onClick={closeMenu}>
            {t.accessSystem}<ArrowUpRight size={16} aria-hidden="true" />
          </a>
        </nav>
      </div>
    </header>
  );
};
