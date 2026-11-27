// Cliente HTTP escrito à mão sobre os tipos gerados em src/lib/api/schema.ts.
// Base vazia = mesma origem: em dev/preview o Vite repassa /api e /health para a API.
import type {
  AccountOut,
  AlertOut,
  BudgetReportOut,
  FinanceGetBudgetsQuery,
  FinanceGetSummaryQuery,
  ImportBatchCreatedOut,
  PageAlertOut,
  ProjectionOut,
  SummaryOut,
  AccountUpdate,
  ErrorResponse,
  ExplainRequest,
  ExplainResponse,
  FinanceListTransactionsQuery,
  HealthResponse,
  ImportBatchOut,
  PageAccountOut,
  PageCategoryOut,
  PageImportBatchSummaryOut,
  PageTransactionOut,
  TransactionOut,
} from '../../lib/api/schema';

const BASE_URL = (import.meta.env.VITE_API_URL ?? '').replace(/\/$/, '');

/** Erro no envelope do backend: {"error": {"code", "message", "details"}}. */
export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
    readonly details: Record<string, unknown> = {},
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

// boolean entra desde o filtro is_recurring da #44; String(false) vira "false", que o FastAPI aceita.
type Query = Record<string, string | number | boolean | null | undefined>;

function buildUrl(path: string, query?: Query): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query ?? {})) {
    // Filtro vazio é omitido: a API trata ausência como "sem filtro".
    if (value !== undefined && value !== null && value !== '') params.set(key, String(value));
  }
  const qs = params.toString();
  return `${BASE_URL}${path}${qs ? `?${qs}` : ''}`;
}

async function request<T>(method: string, path: string, init: { query?: Query; json?: unknown; body?: BodyInit; signal?: AbortSignal } = {}): Promise<T> {
  let response: Response;
  try {
    response = await fetch(buildUrl(path, init.query), {
      method,
      signal: init.signal,
      headers: init.json !== undefined ? { 'Content-Type': 'application/json' } : undefined,
      body: init.json !== undefined ? JSON.stringify(init.json) : init.body,
    });
  } catch (error) {
    if ((error as Error).name === 'AbortError') throw error;
    throw new ApiError(0, 'NETWORK_ERROR', 'Não foi possível falar com a API. Ela está rodando?');
  }
  const text = await response.text();
  const data: unknown = text ? safeJson(text) : null;
  if (!response.ok) {
    const envelope = data as Partial<ErrorResponse> | null;
    const err = envelope?.error;
    throw new ApiError(response.status, err?.code ?? 'HTTP_ERROR', err?.message ?? `Erro HTTP ${response.status}`, err?.details ?? {});
  }
  return data as T;
}

function safeJson(text: string): unknown {
  try { return JSON.parse(text); } catch { return null; }
}

const id = encodeURIComponent;

export const api = {
  health: (signal?: AbortSignal) => request<HealthResponse>('GET', '/health', { signal }),

  listAccounts: (signal?: AbortSignal) =>
    request<PageAccountOut>('GET', '/api/v1/finance/accounts', { query: { limit: 200 }, signal }),

  updateAccount: (accountId: string, body: AccountUpdate) =>
    request<AccountOut>('PATCH', `/api/v1/finance/accounts/${id(accountId)}`, { json: body }),

  listCategories: (signal?: AbortSignal) =>
    request<PageCategoryOut>('GET', '/api/v1/finance/categories', { query: { limit: 200 }, signal }),

  listTransactions: (query: FinanceListTransactionsQuery, signal?: AbortSignal) =>
    request<PageTransactionOut>('GET', '/api/v1/finance/transactions', { query, signal }),

  updateTransactionCategory: (transactionId: string, categoryId: string) =>
    request<TransactionOut>('PATCH', `/api/v1/finance/transactions/${id(transactionId)}`, { json: { category_id: categoryId } }),

  listImportBatches: (query: { limit?: number; offset?: number } = {}, signal?: AbortSignal) =>
    request<PageImportBatchSummaryOut>('GET', '/api/v1/finance/import-batches', { query, signal }),

  getImportBatch: (batchId: string, signal?: AbortSignal) =>
    request<ImportBatchOut>('GET', `/api/v1/finance/import-batches/${id(batchId)}`, { signal }),

  importCsv: (accountId: string, file: File) => {
    const form = new FormData();
    form.append('file', file);
    return request<ImportBatchCreatedOut>('POST', `/api/v1/finance/accounts/${id(accountId)}/import-batches`, { body: form });
  },

  getSummary: (query: FinanceGetSummaryQuery, signal?: AbortSignal) =>
    request<SummaryOut>('GET', '/api/v1/finance/summary', { query, signal }),

  getProjection: (accountId: string, days: number, signal?: AbortSignal) =>
    request<ProjectionOut>('GET', `/api/v1/finance/accounts/${id(accountId)}/projection`, { query: { days }, signal }),

  getBudgets: (query: FinanceGetBudgetsQuery, signal?: AbortSignal) =>
    request<BudgetReportOut>('GET', '/api/v1/finance/budgets', { query, signal }),

  setBudget: (categoryId: string, limitCents: number) =>
    request<BudgetReportOut>('PUT', `/api/v1/finance/budgets/${id(categoryId)}`, { json: { limit_cents: limitCents } }),

  deleteBudget: (categoryId: string) =>
    request<null>('DELETE', `/api/v1/finance/budgets/${id(categoryId)}`),

  listAlerts: (signal?: AbortSignal) =>
    request<PageAlertOut>('GET', '/api/v1/alerts', { query: { limit: 200 }, signal }),

  explain: (body: ExplainRequest, signal?: AbortSignal) =>
    request<ExplainResponse>('POST', '/api/v1/ai/explain', { json: body, signal }),

  markAlertRead: (alertId: string) =>
    request<AlertOut>('PATCH', `/api/v1/alerts/${id(alertId)}`, { json: { status: 'read' } }),
};

/** Mensagens em português para códigos conhecidos do backend; demais usam a mensagem da API. */
const MESSAGES: Record<string, string> = {
  FILE_TOO_LARGE: 'O arquivo passa do limite de 1 MiB.',
  CSV_ENCODING: 'O arquivo precisa estar em UTF-8.',
  CSV_MISSING_COLUMNS: 'O cabeçalho deve ter as colunas date, description e amount.',
  CSV_TOO_MANY_ROWS: 'O arquivo tem mais de 5000 linhas de dados.',
  ACCOUNT_NOT_FOUND: 'Conta não encontrada.',
  CATEGORY_KIND_MISMATCH: 'Essa categoria não combina com o tipo da transação (entrada ou saída).',
  TRANSACTION_NOT_FOUND: 'Transação não encontrada.',
  CATEGORY_NOT_FOUND: 'Categoria não encontrada.',
  ALERT_NOT_FOUND: 'Alerta não encontrado.',
  BUDGET_NOT_FOUND: 'Essa categoria não tem limite definido.',
  BALANCE_UNAVAILABLE: 'O saldo de referência da conta é posterior a hoje. Ajuste a data do saldo na visão geral para calcular a projeção.',
};

export function describeError(error: unknown): string {
  if (error instanceof ApiError) return MESSAGES[error.code] ?? error.message;
  return 'Algo deu errado. Tente novamente.';
}
