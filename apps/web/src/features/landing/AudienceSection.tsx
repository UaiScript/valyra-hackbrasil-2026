import { useEffect, useId, useRef, useState, type KeyboardEvent } from 'react';
import { demoRepository } from '../../data/demoRepository';
import { Icon } from '../../shared/components/Icon';
import type { DemoDataset, ProfileId } from '../../shared/types/domain';
import { ProductPreview } from './ProductPreviews';
import { personalPreview, previewModel } from './previewModel';
import { demoHref } from '../../app/routes';

const content = {
  personal: {
    tab: 'Para você',
    title: 'Entenda o que entra, o que sai e o que já está comprometido.',
    description:
      'Um ponto de partida para acompanhar seu orçamento e olhar os próximos compromissos com mais contexto.',
    benefits: [
      'Consulte receitas e despesas por categoria.',
      'Veja o saldo depois dos compromissos previstos.',
      'Explore temas de interesse no Radar.',
    ],
    cta: 'Explorar o perfil Pessoal',
  },
  business: {
    tab: 'Para sua empresa',
    title: 'Acompanhe o caixa e os compromissos do próximo ciclo.',
    description:
      'A mesma estrutura, com entradas, saídas e temas relacionados à realidade da operação.',
    benefits: [
      'Acompanhe entradas e saídas do caixa.',
      'Confira os próximos vencimentos e o saldo resultante.',
      'Explore exposições como insumos e logística.',
    ],
    cta: 'Explorar o perfil Empresa',
  },
} as const;
const profileOrder: ProfileId[] = ['personal', 'business'];

export function AudienceSection() {
  const [profile, setProfile] = useState<ProfileId>('personal');
  const [loaded, setLoaded] = useState<{ profile: ProfileId; data: DemoDataset }>({
    profile: 'personal',
    data: personalPreview.data,
  });
  const [failed, setFailed] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const id = useId();
  const tabs = useRef<Partial<Record<ProfileId, HTMLButtonElement | null>>>({});
  const copy = content[profile];
  const model = loaded.profile === profile ? previewModel(loaded.data) : null;

  useEffect(() => {
    let active = true;
    setFailed(false);
    demoRepository
      .getWorkspace(profile)
      .then((data) => {
        if (active) setLoaded({ profile, data });
      })
      .catch(() => {
        if (active) setFailed(true);
      });
    // A prévia também descarta respostas tardias; o título Empresa nunca acompanha números Pessoais.
    return () => {
      active = false;
    };
  }, [profile, attempt]);

  function handleTabKey(event: KeyboardEvent<HTMLButtonElement>, current: ProfileId) {
    const index = profileOrder.indexOf(current);
    const next =
      event.key === 'Home'
        ? 0
        : event.key === 'End'
          ? 1
          : event.key === 'ArrowRight'
            ? (index + 1) % 2
            : event.key === 'ArrowLeft'
              ? (index + 1) % 2
              : null;
    if (next === null) return;
    event.preventDefault();
    setProfile(profileOrder[next]);
    tabs.current[profileOrder[next]]?.focus();
  }

  return (
    <section
      className="lp-audience lp-section landing-wrap"
      id="para-quem"
      aria-labelledby="audience-title"
    >
      <div className="lp-section-heading">
        <h2 id="audience-title" tabIndex={-1}>
          O seu contexto muda.
          <br />A clareza continua.
        </h2>
        <p>
          Escolha a experiência que faz sentido para você. Dois perfis, a mesma base para organizar
          os números e fazer perguntas melhores.
        </p>
      </div>
      <div className="lp-tabs" role="tablist" aria-label="Experiências da Valyra">
        {profileOrder.map((item) => (
          <button
            type="button"
            role="tab"
            key={item}
            id={`${id}-${item}`}
            ref={(element) => {
              tabs.current[item] = element;
            }}
            aria-selected={profile === item}
            aria-controls={`${id}-panel`}
            tabIndex={profile === item ? 0 : -1}
            onClick={() => setProfile(item)}
            onKeyDown={(event) => handleTabKey(event, item)}
          >
            <Icon name={item === 'personal' ? 'person' : 'business'} size={18} />
            {content[item].tab}
          </button>
        ))}
      </div>
      <div
        className="lp-audience-panel"
        role="tabpanel"
        id={`${id}-panel`}
        aria-labelledby={`${id}-${profile}`}
        tabIndex={0}
      >
        <div className="lp-audience-copy">
          <h3>{copy.title}</h3>
          <p>{copy.description}</p>
          <ul>
            {copy.benefits.map((benefit) => (
              <li key={benefit}>
                <Icon name="check" size={18} />
                <span>{benefit}</span>
              </li>
            ))}
          </ul>
          <a className="button button-primary" href={demoHref('overview', profile)}>
            {copy.cta}
            <Icon name="arrow" size={18} />
          </a>
        </div>
        <div className="lp-audience-preview" aria-busy={!model && !failed}>
          {failed ? (
            <div className="lp-preview-error" role="alert">
              <p>A prévia deste perfil não carregou.</p>
              <button
                type="button"
                className="button button-subtle"
                onClick={() => setAttempt((value) => value + 1)}
              >
                Tentar novamente
              </button>
            </div>
          ) : model ? (
            <ProductPreview model={model} profile={profile} compact />
          ) : (
            <div className="lp-preview-loading" role="status">
              Carregando a prévia do perfil {copy.tab === 'Para você' ? 'Pessoal' : 'Empresa'}…
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
