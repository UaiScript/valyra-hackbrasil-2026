// Endereço da API usado pela aplicação (#/app), avaliado pelo Vite no build.
// VITE_API_URL vazio: o front chama a mesma origem e o proxy do Vite repassa
// para VITE_API_PROXY_TARGET (padrão: API local do `make dev`).
export const DEFAULT_PROXY_TARGET = 'http://127.0.0.1:8000';

function parseOrigin(raw, name) {
  let url;
  try {
    url = new URL(raw);
  } catch {
    throw new Error(`${name} deve ser uma URL absoluta.`);
  }
  if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password) {
    throw new Error(`${name} deve usar http(s) e não pode conter credenciais.`);
  }
  // HTTP só é aceito em loopback; fora disso a API precisa de HTTPS.
  const loopback = ['127.0.0.1', 'localhost', '[::1]'].includes(url.hostname);
  if (url.protocol === 'http:' && !loopback) {
    throw new Error(`${name} fora de localhost deve usar HTTPS.`);
  }
  if (url.pathname !== '/' || url.search || url.hash) {
    throw new Error(`${name} deve ser apenas a origem, sem caminho.`);
  }
  return url.origin;
}

export function resolveApi(env) {
  const proxyTarget = parseOrigin(env.VITE_API_PROXY_TARGET?.trim() || DEFAULT_PROXY_TARGET, 'VITE_API_PROXY_TARGET');
  const rawApi = env.VITE_API_URL?.trim();
  const apiOrigin = rawApi ? parseOrigin(rawApi, 'VITE_API_URL') : null;
  // A CSP do build libera só a própria origem e, se houver, a origem explícita da API.
  const connectSrc = apiOrigin ? `'self' ${apiOrigin}` : "'self'";
  return { proxyTarget, apiOrigin, connectSrc };
}
