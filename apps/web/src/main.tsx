import { StrictMode, Suspense, lazy } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import { isAppHash, useHash } from './app/router';
import './index.css';

// O app financeiro só é baixado quando alguém abre #/app; a landing segue leve.
const FinanceApp = lazy(() => import('./app/FinanceApp'));

function Root() {
  const hash = useHash();
  if (isAppHash(hash)) {
    return <Suspense fallback={<p className="app-boot">Carregando Valyra…</p>}><FinanceApp /></Suspense>;
  }
  return <App />;
}

createRoot(document.getElementById('root')!).render(<StrictMode><Root /></StrictMode>);
