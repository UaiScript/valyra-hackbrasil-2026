// Código gerado por apps/web/scripts/generate-api-types.mjs a partir de
// packages/contracts/openapi.json. Não edite: rode `npm run gen:api`.

export type AccountOut = {
  /** date */ balance_as_of: string;
  balance_cents: number;
  /** uuid */ id: string;
  name: string;
};

/** Campos omissíveis; null explícito é recusado, pois nenhuma coluna da conta aceita nulo. */
export type AccountUpdate = {
  /** date */ balance_as_of?: string;
  balance_cents?: number;
  name?: string;
};

export type AlertOut = {
  /** uuid */ account_id: string;
  /** date-time */ created_at: string;
  evidence: CashPressureEvidenceOut;
  /** uuid */ id: string;
  kind: string;
  message: string;
  read_at: string | null;
  severity: "info" | "warning";
  status: "new" | "read";
  title: string;
};

export type AlertUpdate = {
  status: string;
};

export type Body_finance_create_import_batch = {
  file: string;
};

/** Snapshot da projeção que gerou o alerta; valores previstos, não realizados. */
export type CashPressureEvidenceOut = {
  days: number;
  min_balance_cents: number;
  /** date */ min_balance_date: string;
  start_balance_cents: number;
  /** date */ today: string;
};

export type CategoryOut = {
  /** uuid */ id: string;
  kind: "expense" | "income";
  name: string;
  slug: string;
};

export type CategoryTotalOut = {
  category: CategoryOut;
  count: number;
  total_cents: number;
};

export type ErrorBody = {
  code: string;
  details: Record<string, unknown>;
  message: string;
};

/** Forma única de toda resposta de erro; declarada no OpenAPI por error_responses(). */
export type ErrorResponse = {
  error: ErrorBody;
};

export type HealthResponse = {
  postgres: "ok" | "error";
  status: "ok" | "degraded";
};

export type ImportBatchCreatedOut = {
  alerts_created: number;
  /** uuid */ id: string;
  rejections: ImportRejectionOut[];
  rows_duplicated: number;
  rows_imported: number;
  rows_rejected: number;
  rows_total: number;
  status: "processing" | "completed" | "failed";
};

export type ImportBatchOut = {
  /** uuid */ id: string;
  rejections: ImportRejectionOut[];
  rows_duplicated: number;
  rows_imported: number;
  rows_rejected: number;
  rows_total: number;
  status: "processing" | "completed" | "failed";
};

export type ImportBatchSummaryOut = {
  /** uuid */ id: string;
  rows_duplicated: number;
  rows_imported: number;
  rows_rejected: number;
  rows_total: number;
  status: "processing" | "completed" | "failed";
};

export type ImportRejectionOut = {
  line_number: number;
  raw_line: string;
  reason: string;
};

export type PageAccountOut = {
  items: AccountOut[];
  limit: number;
  offset: number;
  total: number;
};

export type PageAlertOut = {
  items: AlertOut[];
  limit: number;
  offset: number;
  total: number;
};

export type PageCategoryOut = {
  items: CategoryOut[];
  limit: number;
  offset: number;
  total: number;
};

export type PageImportBatchSummaryOut = {
  items: ImportBatchSummaryOut[];
  limit: number;
  offset: number;
  total: number;
};

export type PageTransactionOut = {
  items: TransactionOut[];
  limit: number;
  offset: number;
  total: number;
};

export type ProjectedRecurrenceOut = {
  amount_cents: number;
  description: string;
};

export type ProjectionDayOut = {
  balance_cents: number;
  /** date */ date: string;
  recurrences: ProjectedRecurrenceOut[];
  recurring_cents: number;
  variable_cents: number;
};

/** Projeção da Issue #46: valores previstos, separados do saldo realizado de partida. */
export type ProjectionOut = {
  /** uuid */ account_id: string;
  days: number;
  items: ProjectionDayOut[];
  min_balance_cents: number;
  /** date */ min_balance_date: string;
  start_balance_cents: number;
  /** date */ today: string;
  variable_daily_cents: number;
};

/** Resumo da Issue #43: saldo realizado de hoje e movimentações realizadas do mês. */
export type SummaryOut = {
  account_id: string | null;
  categories: CategoryTotalOut[];
  expenses_cents: number;
  income_cents: number;
  month: string;
  net_cents: number;
  realized_balance_cents: number | null;
  /** date */ today: string;
};

export type TransactionCategoryOut = {
  /** uuid */ id: string;
  name: string;
  slug: string;
};

export type TransactionOut = {
  amount_cents: number;
  anomaly_score: string | null;
  category: TransactionCategoryOut;
  category_confidence: string | null;
  category_source: "rule" | "model" | "user";
  /** date */ date: string;
  description: string;
  /** uuid */ id: string;
  is_anomaly: boolean;
  is_recurring: boolean;
  /** uuid */ predicted_category_id: string;
};

/** Correção de categoria; category_id é obrigatório e null é recusado. */
export type TransactionUpdate = {
  /** uuid */ category_id: string;
};

export type AlertsListQuery = {
  limit?: number;
  offset?: number;
};

export type FinanceListAccountsQuery = {
  limit?: number;
  offset?: number;
};

export type FinanceGetProjectionQuery = {
  days?: number;
};

export type FinanceListCategoriesQuery = {
  limit?: number;
  offset?: number;
};

export type FinanceListImportBatchesQuery = {
  limit?: number;
  offset?: number;
};

export type FinanceGetSummaryQuery = {
  account_id?: string | null;
  month?: string | null;
};

export type FinanceListTransactionsQuery = {
  account_id?: string | null;
  date_from?: string | null;
  date_to?: string | null;
  category_id?: string | null;
  is_recurring?: boolean | null;
  is_anomaly?: boolean | null;
  limit?: number;
  offset?: number;
};

export const OPERATIONS = {
  alerts_list: { method: 'GET', path: '/api/v1/alerts' },
  alerts_update: { method: 'PATCH', path: '/api/v1/alerts/{id}' },
  finance_list_accounts: { method: 'GET', path: '/api/v1/finance/accounts' },
  finance_create_import_batch: { method: 'POST', path: '/api/v1/finance/accounts/{account_id}/import-batches' },
  finance_update_account: { method: 'PATCH', path: '/api/v1/finance/accounts/{id}' },
  finance_get_projection: { method: 'GET', path: '/api/v1/finance/accounts/{id}/projection' },
  finance_list_categories: { method: 'GET', path: '/api/v1/finance/categories' },
  finance_list_import_batches: { method: 'GET', path: '/api/v1/finance/import-batches' },
  finance_get_import_batch: { method: 'GET', path: '/api/v1/finance/import-batches/{id}' },
  finance_get_summary: { method: 'GET', path: '/api/v1/finance/summary' },
  finance_list_transactions: { method: 'GET', path: '/api/v1/finance/transactions' },
  finance_update_transaction: { method: 'PATCH', path: '/api/v1/finance/transactions/{id}' },
  system_health: { method: 'GET', path: '/health' },
} as const;
