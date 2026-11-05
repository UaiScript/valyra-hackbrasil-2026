import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { App } from './app/App';
import './shared/styles/tokens.css';
import './shared/styles/global.css';
import './shared/styles/landing.css';
import './shared/styles/workspace.css';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
