// Dinheiro chega da API em centavos inteiros (ADR-0009). Formatação e leitura usam
// só aritmética de strings/BigInt: nunca dividimos por 100 em ponto flutuante.

/** Formata centavos como BRL, ex.: -12990 → "-R$ 129,90". */
export function formatCents(cents: number): string {
  if (!Number.isSafeInteger(cents)) throw new RangeError('Valor em centavos fora da faixa segura');
  const negative = cents < 0;
  const digits = String(negative ? -cents : cents).padStart(3, '0');
  const reais = digits.slice(0, -2).replace(/\B(?=(\d{3})+(?!\d))/g, '.');
  return `${negative ? '-' : ''}R$ ${reais},${digits.slice(-2)}`;
}

/**
 * Lê um valor digitado em reais ("1.234,56", "1234,5", "-89,90", "1500") e devolve
 * centavos inteiros, ou null se o texto não for um valor válido.
 */
export function parseReaisToCents(text: string): number | null {
  const clean = text.trim().replace(/^R\$\s*/i, '');
  const match = /^(-)?(\d{1,3}(?:\.\d{3})+|\d+)(?:,(\d{1,2}))?$/.exec(clean);
  if (!match) return null;
  const [, sign, intPart, frac = ''] = match;
  const cents = BigInt(intPart.replace(/\./g, '')) * 100n + BigInt(frac.padEnd(2, '0') || '0');
  const value = sign ? -cents : cents;
  // BIGINT do banco vai além do inteiro seguro do JS; recusamos para não perder precisão.
  if (value > BigInt(Number.MAX_SAFE_INTEGER) || value < BigInt(Number.MIN_SAFE_INTEGER)) return null;
  return Number(value);
}

/** Centavos para o texto editável do formulário, ex.: 421050 → "4210,50". */
export function centsToInput(cents: number): string {
  return formatCents(cents).replace('R$ ', '').replace(/\./g, '');
}

/** Data de negócio ISO (AAAA-MM-DD) para DD/MM/AAAA, sem passar por Date e fuso. */
export function formatIsoDate(iso: string): string {
  const [y, m, d] = iso.split('-');
  return d && m && y ? `${d}/${m}/${y}` : iso;
}

const MONTHS = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro'];
const MONTHS_SHORT = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez'];

/** Mês AAAA-MM por extenso, ex.: "2026-10" → "outubro de 2026". */
export function formatMonth(month: string): string {
  const [y, m] = month.split('-');
  const name = MONTHS[Number(m) - 1];
  return name && y ? `${name} de ${y}` : month;
}

/** Soma `delta` meses a AAAA-MM com aritmética inteira, sem Date nem fuso. */
export function shiftMonth(month: string, delta: number): string {
  const [y, m] = month.split('-').map(Number);
  const index = y * 12 + (m - 1) + delta;
  return `${Math.floor(index / 12)}-${String((index % 12) + 1).padStart(2, '0')}`;
}

/** Data ISO curta para eixos e marcadores, ex.: "2026-11-09" → "9 nov". */
export function formatShortDate(iso: string): string {
  const [, m, d] = iso.split('-');
  const name = MONTHS_SHORT[Number(m) - 1];
  return name && d ? `${Number(d)} ${name}` : iso;
}

/**
 * Score de gasto atípico chega como texto decimal ("0.8125", NUMERIC no banco).
 * Mostramos duas casas com vírgula por manipulação de texto, sem converter para float.
 * É um indicador heurístico (ADR-0010), não uma probabilidade: não exibimos como %.
 */
export function formatScore(score: string): string {
  const [int = '0', frac = ''] = score.split('.');
  return `${int},${frac.padEnd(2, '0').slice(0, 2)}`;
}
