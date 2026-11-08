export const REPOSITORY_URL = 'https://github.com/UaiScript/valyra-hackbrasil-2026';

// This module is evaluated by Vite, before any public files are generated.
export function resolveDestination(env) {
  const kind = env.VITE_DESTINATION_KIND?.trim() || 'repository';
  const raw = env.VITE_SYSTEM_URL?.trim() || REPOSITORY_URL;
  if (!['repository', 'application'].includes(kind)) {
    throw new Error('VITE_DESTINATION_KIND deve ser repository ou application.');
  }
  if (kind === 'application' && (!env.VITE_SYSTEM_URL?.trim() || raw === REPOSITORY_URL)) {
    throw new Error('Informe explicitamente a URL da aplicação ao usar application.');
  }
  let url;
  try {
    url = new URL(raw);
  } catch {
    throw new Error('VITE_SYSTEM_URL deve ser uma URL HTTPS absoluta.');
  }
  if (url.protocol !== 'https:' || url.username || url.password) {
    throw new Error('VITE_SYSTEM_URL deve usar HTTPS e não pode conter credenciais.');
  }
  if (kind === 'repository' && url.href !== REPOSITORY_URL) {
    throw new Error('O destino repository deve apontar para o repositório oficial.');
  }
  return { url: url.href, kind };
}
