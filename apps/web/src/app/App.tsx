import { useEffect, useState } from 'react';
import { Landing } from '../features/landing/Landing';
import { Workspace } from '../features/workspace/Workspace';
import { demoNavigation, parseHashRoute } from './routes';

export function App() {
  const [route, setRoute] = useState(() => parseHashRoute(window.location.hash));
  useEffect(() => {
    const update = () => setRoute(parseHashRoute(window.location.hash));
    window.addEventListener('hashchange', update);
    return () => window.removeEventListener('hashchange', update);
  }, []);

  useEffect(() => {
    window.scrollTo(0, 0);
    // A troca de rota também precisa ser percebida por quem navega com teclado/leitor de tela.
    document.querySelector<HTMLElement>('[data-page-heading]')?.focus({ preventScroll: true });
    // O parser só devolve telas do catálogo, portanto o título correspondente sempre existe.
    const title =
      route.kind === 'demo'
        ? demoNavigation.find((item) => item.id === route.screen)!.title
        : 'Entenda os sinais. Decida com clareza.';
    document.title = `Valyra — ${title}`;
  }, [route]);

  return (
    <>
      <a
        className="skip-link"
        href="#main-content"
        onClick={(event) => {
          event.preventDefault();
          document.getElementById('main-content')?.focus();
        }}
      >
        Pular para o conteúdo
      </a>
      {route.kind === 'landing' ? (
        <Landing />
      ) : route.kind === 'demo' ? (
        <Workspace screen={route.screen} profile={route.profile} />
      ) : (
        <main id="main-content" className="not-found" tabIndex={-1}>
          <p className="eyebrow">VALYRA / CAMINHO NÃO ENCONTRADO</p>
          <h1 data-page-heading tabIndex={-1}>
            Vamos encontrar seu rumo.
          </h1>
          <p>Esta página não existe na demonstração.</p>
          <a href="#/" className="button button-primary">
            Voltar ao início
          </a>
        </main>
      )}
    </>
  );
}
