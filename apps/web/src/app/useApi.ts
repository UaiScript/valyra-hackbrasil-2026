import { useCallback, useEffect, useState } from 'react';

export type ApiState<T> =
  | { status: 'loading'; data?: T }
  | { status: 'success'; data: T }
  | { status: 'error'; error: unknown; data?: T };

/** Carrega dados da API; refaz quando `deps` mudam e cancela respostas atrasadas. */
export function useApi<T>(load: (signal: AbortSignal) => Promise<T>, deps: unknown[]) {
  const [state, setState] = useState<ApiState<T>>({ status: 'loading' });
  const [version, setVersion] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    setState((prev) => ({ status: 'loading', data: prev.data }));
    load(controller.signal).then(
      (data) => setState({ status: 'success', data }),
      (error) => {
        if (!controller.signal.aborted) setState((prev) => ({ status: 'error', error, data: prev.data }));
      },
    );
    return () => controller.abort();
    // `load` muda a cada render; quem chama declara as dependências reais em `deps`.
  }, [...deps, version]);

  const reload = useCallback(() => setVersion((v) => v + 1), []);
  return { state, reload, setState };
}
