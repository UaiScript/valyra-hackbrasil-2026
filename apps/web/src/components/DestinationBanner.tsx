import type { FC } from 'react';
import { ArrowUpRight, Code2 } from 'lucide-react';
import { CONTENT } from '../content';
import type { Language } from '../types/content';

export const SystemRedirectBanner: FC<{ lang: Language; systemUrl: string }> = ({ lang, systemUrl }) => {
  const t = CONTENT[lang].ctaBanner;
  return (
    <section className="closing-section">
      <div className="container closing-layout">
        <div>
          <div className="eyebrow eyebrow--on-dark"><span className="eyebrow__line" />{t.deploymentBadge}</div>
          <h2>{t.title}</h2>
          <p>{t.description}</p>
        </div>
        <div className="closing-action">
          <a href={systemUrl} rel="noopener noreferrer" data-primary-cta="true" className="button button--light button--large">
            <Code2 size={18} aria-hidden="true" />{t.button}<ArrowUpRight size={17} aria-hidden="true" />
          </a>
          <span>{t.dockerInfo}</span>
        </div>
      </div>
    </section>
  );
};
