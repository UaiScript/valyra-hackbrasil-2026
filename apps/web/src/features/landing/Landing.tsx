import { useEffect, useId, useRef, useState, type MouseEvent } from 'react';
import { Brand, Icon } from '../../shared/components/Icon';
import { money } from '../../shared/format';
import { AudienceSection } from './AudienceSection';
import { FinancePreview, PlanningPreview, ProductPreview, RadarPreview } from './ProductPreviews';
import { foodIllustration, personalPreview } from './previewModel';
import { demoHref } from '../../app/routes';

const repo = 'https://github.com/UaiScript/valyra-hackbrasil-2026';
const demo = demoHref('overview', 'personal');

// O hash pertence ao roteador do app. Âncoras locais rolam e focam a seção sem trocar essa rota.
function goToSection(event: MouseEvent<HTMLAnchorElement>, id: string) {
  event.preventDefault();
  const section = document.getElementById(id);
  section?.scrollIntoView({ behavior: 'instant', block: 'start' });
  section?.querySelector<HTMLElement>('h2')?.focus({ preventScroll: true });
}

function LandingHeader() {
  const [open, setOpen] = useState(false);
  const menuId = useId();
  const menuButton = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    // O menu aparece antes do botão no DOM: mover o foco evita que Tab pule seus links no celular.
    if (open) document.getElementById(menuId)?.querySelector<HTMLAnchorElement>('a')?.focus();
  }, [open, menuId]);
  return (
    <header
      className="lp-header landing-wrap"
      onKeyDown={(event) => {
        if (event.key === 'Escape' && open) {
          setOpen(false);
          menuButton.current?.focus();
        }
      }}
    >
      <Brand />
      <nav
        id={menuId}
        className={`lp-main-nav${open ? ' is-open' : ''}`}
        aria-label="Navegação principal da landing"
      >
        <a
          href="#como-funciona"
          onClick={(event) => {
            goToSection(event, 'como-funciona');
            setOpen(false);
          }}
        >
          Como funciona
        </a>
        <a
          href="#para-quem"
          onClick={(event) => {
            goToSection(event, 'para-quem');
            setOpen(false);
          }}
        >
          Para quem
        </a>
        <a
          href="#o-projeto"
          onClick={(event) => {
            goToSection(event, 'o-projeto');
            setOpen(false);
          }}
        >
          O projeto
        </a>
        <a className="lp-mobile-demo" href={demo}>
          Explorar demonstração
          <Icon name="arrow" size={16} />
        </a>
      </nav>
      <a href={demo} className="button button-primary lp-header-cta">
        Explorar demonstração
        <Icon name="arrow" size={16} />
      </a>
      <button
        ref={menuButton}
        type="button"
        className="lp-menu-button"
        aria-label={open ? 'Fechar menu' : 'Abrir menu'}
        aria-expanded={open}
        aria-controls={menuId}
        onClick={() => setOpen((value) => !value)}
      >
        <svg
          viewBox="0 0 24 24"
          width="22"
          height="22"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.6"
          strokeLinecap="round"
          aria-hidden="true"
        >
          <path d={open ? 'M6 6l12 12M18 6 6 18' : 'M4 6h16M4 12h16M4 18h16'} />
        </svg>
      </button>
    </header>
  );
}

export function Landing() {
  const illustration = foodIllustration(personalPreview);
  return (
    <div className="landing">
      <LandingHeader />
      <main id="main-content" tabIndex={-1}>
        <section className="lp-hero landing-wrap" aria-labelledby="landing-title">
          <h1 id="landing-title" data-page-heading tabIndex={-1}>
            Suas finanças conectadas ao que acontece na economia.
          </h1>
          <p>
            Organize receitas, despesas e compromissos. Explore como mudanças na economia podem
            entrar no planejamento da sua vida ou do seu negócio.
          </p>
          <div className="lp-hero-actions">
            <a className="button button-primary" href={demo}>
              Explorar demonstração
              <Icon name="arrow" size={18} />
            </a>
            <a
              className="button lp-button-secondary"
              href="#como-funciona"
              onClick={(event) => goToSection(event, 'como-funciona')}
            >
              Ver como funciona
              <Icon name="chevron" size={18} />
            </a>
          </div>
          <span className="lp-hero-support">Sem cadastro. Com dados demonstrativos.</span>
        </section>
        <section
          className="lp-main-preview landing-wide"
          aria-label="Prévia panorâmica da Valyra Pessoal"
        >
          <ProductPreview model={personalPreview} profile="personal" />
          <div className="lp-preview-caption">
            <p>Uma visão do seu dinheiro, com os próximos compromissos à vista.</p>
            <span>Demonstração com dados fictícios</span>
          </div>
        </section>

        <AudienceSection />

        <section className="lp-how" id="como-funciona" aria-labelledby="how-title">
          <div className="landing-wrap lp-section">
            <div className="lp-section-heading">
              <h2 id="how-title" tabIndex={-1}>
                Do seu orçamento a uma decisão com contexto.
              </h2>
              <p>
                Um exemplo pessoal mostra a diferença entre um registro, uma hipótese econômica e
                uma premissa que você consegue conferir.
              </p>
            </div>
            <div className="lp-context-example">
              <article>
                <h3>
                  <span>Micro</span>Os registros do exemplo
                </h3>
                <p>
                  A categoria Alimentação soma <strong>{money(illustration.referenceCents)}</strong>{' '}
                  no período demonstrativo.
                </p>
                <div className="lp-context-value">
                  {money(illustration.referenceCents)}
                  <small>Valor de referência registrado</small>
                </div>
                <p className="lp-auxiliary">
                  Esse valor vem dos mesmos lançamentos exibidos no Financeiro.
                </p>
              </article>
              <article>
                <h3>
                  <span>Macro</span>Uma mudança hipotética
                </h3>
                <p>
                  E se uma compra equivalente custasse <strong>5% a mais</strong>?
                </p>
                <div className="lp-context-question">O que isso mudaria na próxima compra?</div>
                <p className="lp-auxiliary">
                  Cenário fictício, sem notícia, cotação ou fonte verificada.
                </p>
              </article>
              <article>
                <h3>
                  <span>Premissa explícita</span>Uma conta para avaliar
                </h3>
                <p>Usando o mesmo valor de referência, a compra hipotética seria:</p>
                <div className="lp-context-value">
                  {money(illustration.hypotheticalCents)}
                  <small>
                    {money(illustration.referenceCents)} × 1,05 · diferença de{' '}
                    {money(illustration.differenceCents)}
                  </small>
                </div>
                <p className="lp-auxiliary">
                  Exemplo aritmético, arredondado para centavos. Não altera saldo, registros ou
                  compromissos.
                </p>
              </article>
            </div>
            <div className="lp-ai-direction">
              <Icon name="info" size={20} />
              <p>
                <strong>E a IA?</strong> Tornar relações, evidências e premissas compreensíveis é a
                direção de evolução. Nesta versão, as explicações são editoriais: não há IA
                conectada nem cálculo automático de impacto econômico.
              </p>
            </div>
          </div>
        </section>

        <section
          className="lp-finance-section lp-section landing-wrap"
          aria-labelledby="finance-title"
        >
          <div className="lp-feature-copy">
            <h2 id="finance-title">Saiba o que movimenta o seu saldo.</h2>
            <p>
              Consulte entradas e saídas por categoria, tipo de movimento ou descrição. Os totais
              acompanham os filtros e usam os mesmos registros da tabela.
            </p>
            <a href={demoHref('finance', 'personal')} className="lp-feature-link">
              Explorar o Financeiro
              <Icon name="arrow" size={18} />
            </a>
          </div>
          <FinancePreview model={personalPreview} />
        </section>

        <section className="lp-planning-section" aria-labelledby="planning-title">
          <div className="landing-wrap lp-section">
            <div className="lp-planning-heading">
              <h2 id="planning-title">Veja o que já está comprometido.</h2>
              <p>
                Confira os próximos vencimentos e o saldo após cada compromisso. Uma subtração
                transparente, com a memória de cálculo disponível na demonstração.
              </p>
              <a href={demoHref('planning', 'personal')} className="lp-feature-link">
                Explorar o Planejamento
                <Icon name="arrow" size={18} />
              </a>
            </div>
            <PlanningPreview model={personalPreview} />
          </div>
        </section>

        <section className="lp-radar-section lp-section landing-wrap" aria-labelledby="radar-title">
          <div className="lp-feature-copy">
            <h2 id="radar-title">Acompanhe temas que conversam com o seu plano.</h2>
            <p>
              No Radar, explore assuntos de interesse pessoal ou exposições da operação. Cada
              exemplo traz contexto, premissa e limites para a leitura.
            </p>
            <p className="lp-auxiliary">
              Os cenários atuais são fictícios. Fontes verificadas e IA fazem parte da evolução
              planejada.
            </p>
            <a href={demoHref('radar', 'personal')} className="lp-feature-link">
              Explorar o Radar
              <Icon name="arrow" size={18} />
            </a>
          </div>
          <RadarPreview model={personalPreview} />
        </section>

        <section className="lp-project" id="o-projeto" aria-labelledby="project-title">
          <div className="landing-wrap lp-section lp-project-layout">
            <div className="lp-project-copy">
              <h2 id="project-title" tabIndex={-1}>
                Uma demonstração em evolução.
              </h2>
              <p>
                A Valyra é um projeto em equipe para o Hack Brasil 2026. Esta versão permite
                explorar a organização financeira, os compromissos e o Radar com dados sintéticos.
              </p>
              <p>
                Conexão bancária, notícias em tempo real e IA operacional ainda não estão
                disponíveis. A demonstração não solicita seus dados financeiros.
              </p>
              <a href={repo} target="_blank" rel="noreferrer" className="lp-feature-link">
                Acompanhar o projeto no GitHub
                <Icon name="external" size={16} />
              </a>
            </div>
            <div className="lp-faq" aria-label="Dúvidas sobre a demonstração">
              <details>
                <summary>
                  Preciso conectar meu banco?
                  <Icon name="plus" size={18} />
                </summary>
                <p>
                  Não. Você pode explorar a demonstração sem cadastro. Não existe conexão bancária
                  ou coleta de informações financeiras reais nesta versão.
                </p>
              </details>
              <details>
                <summary>
                  Os dados da demonstração são reais?
                  <Icon name="plus" size={18} />
                </summary>
                <p>
                  Não. Os lançamentos, compromissos e eventos são sintéticos. Os totais são
                  calculados a partir desses registros de exemplo.
                </p>
              </details>
              <details>
                <summary>
                  Posso explorar os dois perfis?
                  <Icon name="plus" size={18} />
                </summary>
                <p>
                  Sim. Pessoal e Empresa compartilham a navegação, com dados e linguagem próprios.
                  Use as abas desta página ou o seletor de perfil na demonstração.
                </p>
              </details>
              <details>
                <summary>
                  A IA já está conectada?
                  <Icon name="plus" size={18} />
                </summary>
                <p>
                  Ainda não. As explicações atuais são editoriais. O planejamento subtrai os
                  compromissos; ele não calcula o efeito de uma notícia nem prevê novas receitas.
                </p>
              </details>
            </div>
          </div>
        </section>

        <section className="lp-final-cta landing-wrap">
          <div>
            <h2>Explore a Valyra na prática.</h2>
            <p>Conheça os números, os compromissos e as perguntas que dão contexto ao plano.</p>
          </div>
          <a className="button button-primary" href={demo}>
            Explorar demonstração
            <Icon name="arrow" size={18} />
          </a>
        </section>
      </main>
      <footer className="lp-footer">
        <div className="landing-wrap lp-footer-main">
          <div>
            <Brand />
            <p>Entenda os sinais. Decida com clareza.</p>
          </div>
          <nav aria-label="Links do projeto">
            <a href={demoHref('overview', 'personal')}>Pessoal</a>
            <a href={demoHref('overview', 'business')}>Empresa</a>
            <a href={repo} target="_blank" rel="noreferrer">
              Repositório
              <Icon name="external" size={14} />
            </a>
          </nav>
        </div>
        <div className="landing-wrap lp-footer-bottom">
          <span>Valyra · Hack Brasil 2026</span>
          <p>
            Demonstração educativa. Não constitui aconselhamento financeiro, recomendação de
            investimento ou garantia de resultado.
          </p>
        </div>
      </footer>
    </div>
  );
}
