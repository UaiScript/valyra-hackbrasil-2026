import type { FC } from 'react';
import { Database, Eye, FileCode2, LockKeyhole, ShieldCheck } from 'lucide-react';
import { CONTENT } from '../content';
import type { Language } from '../types/content';

export const ProjectPrinciples: FC<{ lang: Language }> = ({ lang }) => {
  const t = CONTENT[lang].proof;
  const principles = lang === 'pt'
    ? [
        { icon: Database, title: 'Origem em contexto', text: 'A proposta é apresentar fonte, data e premissas junto dos dados utilizados — não apenas um número isolado.' },
        { icon: Eye, title: 'Limitações visíveis', text: 'Dados ausentes, estimativas e incertezas devem ser identificados para que uma explicação não pareça mais precisa do que é.' },
        { icon: LockKeyhole, title: 'Privacidade desde a landing', text: 'Esta página não solicita cadastro, não conecta contas bancárias e não coleta informações financeiras.' },
      ]
    : [
        { icon: Database, title: 'Sources in context', text: 'The goal is to show source, date and assumptions alongside the data — not just an isolated number.' },
        { icon: Eye, title: 'Visible limitations', text: 'Missing data, estimates and uncertainty should be identified so an explanation never appears more precise than it is.' },
        { icon: LockKeyhole, title: 'Privacy from the landing page', text: 'This page does not request registration, connect bank accounts or collect financial information.' },
      ];

  return (
    <section id="transparencia" className="section section--principles">
      <div className="container">
        <div className="principles-layout">
          <div className="principles-intro">
            <div className="eyebrow"><span className="eyebrow__line" />{t.sectionTag}</div>
            <h2>{lang === 'pt' ? 'Confiança não é um detalhe. É parte do produto.' : 'Trust is not an afterthought. It is part of the product.'}</h2>
            <p>{lang === 'pt'
              ? 'O Valyra está sendo desenvolvido com foco em explicabilidade: deixar claro o que é observado, o que é estimado e de onde cada informação vem.'
              : 'Valyra is being developed with explainability in mind: making clear what is observed, what is estimated and where each piece of information comes from.'}</p>
            <div className="principles-note"><ShieldCheck size={18} aria-hidden="true" /><span>{lang === 'pt' ? 'Projeto em desenvolvimento aberto. Funcionalidades e limitações podem ser acompanhadas no repositório.' : 'Open development. Features and limitations can be followed in the repository.'}</span></div>
          </div>
          <div className="principles-list">
            {principles.map((principle, index) => {
              const Icon = principle.icon;
              return (
                <article key={principle.title} className="principle-item">
                  <span className="principle-item__icon"><Icon size={19} aria-hidden="true" /></span>
                  <div><span className="principle-item__number">0{index + 1}</span><h3>{principle.title}</h3><p>{principle.text}</p></div>
                </article>
              );
            })}
          </div>
        </div>
        <div className="open-project-strip">
          <div><FileCode2 size={20} aria-hidden="true" /><strong>{lang === 'pt' ? 'Construído às claras' : 'Built in the open'}</strong></div>
          <p>{lang === 'pt' ? 'Código, decisões e evolução do projeto estão disponíveis publicamente.' : 'Code, decisions and project progress are publicly available.'}</p>
          <span className="open-project-strip__status">{lang === 'pt' ? 'DESENVOLVIMENTO ABERTO' : 'OPEN DEVELOPMENT'}</span>
        </div>
      </div>
    </section>
  );
};
