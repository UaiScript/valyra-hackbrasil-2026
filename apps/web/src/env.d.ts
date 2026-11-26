/// <reference types="vite/client" />
declare const __DESTINATION__: { readonly url: string; readonly kind: 'repository' | 'application' };

interface ImportMetaEnv {
  /** Origem da API para builds publicados; vazio usa a mesma origem (proxy do Vite). */
  readonly VITE_API_URL?: string;
}
