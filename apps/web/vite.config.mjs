import { defineConfig, loadEnv } from 'vite';
import { fileURLToPath } from 'node:url';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import { resolveDestination } from './config/destination.mjs';
import { resolveApi } from './config/api.mjs';

export default defineConfig(({ mode, command }) => {
  // Vite's root is this package. The backend's .env is not loaded here.
  const root = fileURLToPath(new URL('.', import.meta.url));
  const env = loadEnv(mode, root, 'VITE_');
  const destination = resolveDestination(env);
  const apiConfig = resolveApi(env);
  // Em dev/preview o Vite repassa as rotas da API: o navegador fala só com a mesma origem.
  const proxy = { '/api': apiConfig.proxyTarget, '/health': apiConfig.proxyTarget };
  return {
    root,
    base: './',
    plugins: [react(), tailwindcss(), {
      name: 'landing-production-policy',
      transformIndexHtml(html) {
        if (command !== 'build') return html;
        return html.replace('<meta charset="UTF-8" />', `<meta charset="UTF-8" />
    <meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self'; font-src 'self'; connect-src ${apiConfig.connectSrc}; base-uri 'none'; form-action 'none'; object-src 'none'" />`);
      },
    }],
    define: { __DESTINATION__: JSON.stringify(destination) },
    server: { host: '127.0.0.1', port: 3000, strictPort: true, fs: { strict: true, allow: [root] }, proxy },
    preview: { host: '127.0.0.1', port: 4173, strictPort: true, proxy },
    build: { sourcemap: false },
  };
});
