// Apoio da tela Pergunte ao Valyra. Tipos vêm do OpenAPI gerado (operação ai_explain,
// ADR-0011); a chamada fica aqui para tratar a API publicada que ainda não tem a rota.
import type { DecimalValue, EvidenceItem, ExplainResponse, IntegerValue, MoneyValue, TextValue } from '../../lib/api/schema';
import { ROUTES } from '../router';
import { formatCents } from '../money';
import { ApiError, api } from './client';

export type { EvidenceItem, ExplainResponse };

export async function explain(accountId: string, question: string, signal?: AbortSignal): Promise<ExplainResponse> {
  try {
    return await api.explain({ account_id: accountId, question }, signal);
  } catch (err) {
    // 404 sem envelope: a API publicada ainda não tem a rota de IA (o 404 conhecido usa ACCOUNT_NOT_FOUND).
    if (err instanceof ApiError && err.status === 404 && err.code === 'HTTP_ERROR') {
      throw new ApiError(404, 'AI_NOT_DEPLOYED', 'A explicação por IA ainda não está publicada nesta API.');
    }
    throw err;
  }
}

/**
 * O OpenAPI gerado descreve `value` como união discriminada que o gerador não expande;
 * o formato real é um dos quatro abaixo, reconhecido pelo campo presente. Valores chegam
 * prontos do servidor: dinheiro em centavos inteiros e decimal como texto.
 */
export function formatEvidenceValue(value: unknown): string {
  const v = value as Partial<MoneyValue & IntegerValue & DecimalValue & TextValue> | null;
  if (!v) return '—';
  if (typeof v.amount_cents === 'number') return formatCents(v.amount_cents);
  if (typeof v.value_int === 'number') return String(v.value_int);
  if (typeof v.value_decimal === 'string') return `${v.value_decimal.replace('.', ',')} ${v.unit ?? ''}`.trim();
  if (typeof v.value_text === 'string') return v.value_text;
  return '—';
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
