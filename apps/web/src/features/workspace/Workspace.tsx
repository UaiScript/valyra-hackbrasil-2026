import { useEffect, useState } from 'react';
import { demoRepository } from '../../data/demoRepository';
import type { DemoDataset, ProfileId, ScreenId } from '../../shared/types/domain';
import { Brand, Icon } from '../../shared/components/Icon';
import { Overview } from '../overview/Overview';
import { Finance } from '../finance/Finance';
import { Planning } from '../planning/Planning';
import { Radar } from '../radar/Radar';
import { profiles } from './profiles';
import { demoHref, demoNavigation } from '../../app/routes';

export function Workspace({ screen, profile }: { screen: ScreenId; profile: ProfileId }) {
  const [loaded, setLoaded] = useState<{ profile: ProfileId; data: DemoDataset } | null>(null);
  const [error, setError] = useState(false);
  const [attempt, setAttempt] = useState(0);
  // Preferências da sessão são guardadas por perfil. Categoria de interesse pessoal não vira exposição empresarial.
  const [interests, setInterests] = useState<Record<ProfileId, string[] | null>>({
    personal: null,
    business: null,
  });
  const config = profiles[profile];

  useEffect(() => {
    let active = true;
    setError(false);
    demoRepository
      .getWorkspace(profile)
      .then((data) => {
        if (active) setLoaded({ profile, data });
      })
      .catch(() => {
        if (active) setError(true);
      });
    // Impede resposta tardia de um adaptador futuro de mostrar os dados do perfil anterior.
    return () => {
      active = false;
    };
  }, [profile, attempt]);

  const data = loaded?.profile === profile ? loaded.data : null;
  const activeInterests = interests[profile] ?? data?.interests ?? [];

  useEffect(() => {
    if (data)
      document.querySelector<HTMLElement>('[data-page-heading]')?.focus({ preventScroll: true });
  }, [data, screen, profile]);

  return (
    <div className="workspace">
      <aside className="sidebar">
        <Brand light />
        <p className="workspace-label">Perfil de demonstração</p>
        <div className="profile-switch" role="group" aria-label="Selecionar perfil da demonstração">
          {(['personal', 'business'] as const).map((id) => (
            <button
              key={id}
              type="button"
              aria-pressed={profile === id}
              onClick={() => {
                window.location.hash = demoHref(screen, id);
              }}
            >
              <Icon name={id === 'personal' ? 'person' : 'business'} size={16} />
              {profiles[id].name}
            </button>
          ))}
        </div>
        <nav aria-label="Navegação da demonstração">
          {demoNavigation.map((item) => (
            <a
              key={item.id}
              href={demoHref(item.id, profile)}
              aria-current={screen === item.id ? 'page' : undefined}
            >
              <Icon name={item.icon} />
              <span>{item.label}</span>
            </a>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <a href="#/" className="sidebar-back">
            <Icon name="arrow" size={16} style={{ transform: 'rotate(180deg)' }} /> Voltar ao início
          </a>
        </div>
      </aside>
      <div className="workspace-body">
        <header className="workspace-topbar">
          <div className="workspace-period">
            <Icon name="finance" size={16} />
            <span>1–5 de novembro de 2026</span>
            <span className="period-detail">Período demonstrativo</span>
          </div>
          <details className="demo-info">
            <summary>
              <Icon name="info" size={16} />
              Demonstração
              <Icon name="chevron" size={16} />
            </summary>
            <div className="demo-info-content">
              <h2>Sobre esta demonstração</h2>
              <p>
                Todos os valores, compromissos e cenários são fictícios. Não há conexão bancária,
                persistência, notícias em tempo real ou IA conectada.
              </p>
              <p>
                Os totais usam os lançamentos de exemplo. Simulações e interpretações ficam
                separadas dos valores registrados.
              </p>
              <p>
                Você está no perfil <strong>{config.name}</strong>. A seleção de temas é mantida
                separadamente durante esta sessão.
              </p>
            </div>
          </details>
        </header>
        <main
          id="main-content"
          className="workspace-main"
          tabIndex={-1}
          aria-busy={!data && !error}
        >
          {error ? (
            <div className="empty-state" role="alert">
              <h1 data-page-heading tabIndex={-1}>
                Não foi possível abrir os exemplos.
              </h1>
              <p>
                Os dados de {config.name} não foram carregados. Tente abrir a demonstração
                novamente.
              </p>
              <button
                className="button button-dark"
                onClick={() => setAttempt((value) => value + 1)}
              >
                Tentar novamente
              </button>
            </div>
          ) : !data ? (
            <div className="workspace-loading" role="status">
              <p>Carregando os exemplos do perfil {config.name}…</p>
              <div className="loading-summary" aria-hidden="true">
                <span />
                <span />
                <span />
              </div>
              <div className="loading-content" aria-hidden="true" />
            </div>
          ) : (
            <div key={`${profile}-${screen}`} className="screen-content">
              {screen === 'overview' && <Overview data={data} profile={profile} />}
              {screen === 'finance' && <Finance data={data} profile={profile} />}
              {screen === 'planning' && <Planning data={data} profile={profile} />}
              {screen === 'radar' && (
                <Radar
                  data={data}
                  profile={profile}
                  interests={activeInterests}
                  onInterestsChange={(next) =>
                    setInterests((previous) => ({ ...previous, [profile]: next }))
                  }
                />
              )}
            </div>
          )}
        </main>
        <footer className="workspace-footer">
          <span>Valyra · Dados demonstrativos</span>
          <span>Demonstração educativa · sem aconselhamento financeiro</span>
        </footer>
      </div>
    </div>
  );
}
