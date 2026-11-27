// Contrato de POST /api/v1/ai/explain (ADR-0011, branch breno/infra_IA-ML). Só os campos
// que a tela exibe. Quando a rota entrar no OpenAPI da main, trocar por tipos gerados
// em src/lib/api/schema.ts e mover a chamada para client.ts.
import { ApiError } from './client';
import { ROUTES } from '../router';

export type EvidenceValue =
  | { kind: 'money'; amount_cents: number; currency: 'BRL' }
  | { kind: 'integer'; value_int: number; unit: 'count' }
  | { kind: 'decimal'; value_decimal: string; unit: string }
  | { kind: 'text'; value_text: string };

export type EvidenceItem = {
  evidence_id: string;
  metric_key: string;
  label: string;
  basis: 'reference' | 'observed' | 'projected';
  value: EvidenceValue;
  period: { start: string; end: string };
  source: { kind: 'finance_record' | 'calculation' | 'alpha_signal'; method_key?: string; record_type?: string };
};

export type ExplainResponse = {
  answer: string;
  as_of: string;
  evidences: EvidenceItem[];
  uncertainty: 'baixa' | 'média' | 'alta';
  limitations: string[];
};

const BASE_URL = (import.meta.env.VITE_API_URL ?? '').replace(/\/$/, '');

export async function explain(accountId: string, question: string, signal?: AbortSignal): Promise<ExplainResponse> {
  let response: Response;
  try {
    response = await fetch(`${BASE_URL}/api/v1/ai/explain`, {
      method: 'POST',
      signal,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ account_id: accountId, question }),
    });
  } catch (error) {
    if ((error as Error).name === 'AbortError') throw error;
    throw new ApiError(0, 'NETWORK_ERROR', 'Não foi possível falar com a API. Ela está rodando?');
  }
  const text = await response.text();
  let data: unknown = null;
  try { data = text ? JSON.parse(text) : null; } catch { data = null; }
  if (!response.ok) {
    const err = (data as { error?: { code?: string; message?: string } } | null)?.error;
    // 404 sem envelope: a API publicada ainda não tem a rota de IA.
    if (response.status === 404 && !err) throw new ApiError(404, 'AI_NOT_DEPLOYED', 'A explicação por IA ainda não está publicada nesta API.');
    throw new ApiError(response.status, err?.code ?? 'HTTP_ERROR', err?.message ?? `Erro HTTP ${response.status}`);
  }
  return data as ExplainResponse;
}

/** Link para a tela da IA com a pergunta já preenchida. */
export function askHref(question: string): string {
  return `${ROUTES.ai}?q=${encodeURIComponent(question)}`;
}

export const AI_MESSAGES: Record<string, string> = {
  AI_UNAVAILABLE: 'O provedor de IA está sem chave, cota ou acesso agora. Os números do painel continuam valendo.',
  AI_CONFIGURATION_ERROR: 'A explicação por IA não está configurada neste ambiente.',
  AI_CONTEXT_INVALID: 'Não foi possível montar as evidências para essa conta.',
  AI_INVALID_RESPONSE: 'A resposta da IA não passou na validação das evidências e foi descartada.',
  AI_NOT_DEPLOYED: 'A explicação por IA ainda não está publicada nesta API.',
};
