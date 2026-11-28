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

export type AlphaSignalSource = {
  /** date-time */ ingested_at: string;
  kind?: string;
  /** date */ observation_date: string;
  /** date-time */ published_at: string;
  published_at_estimated: boolean;
  revision_id: number;
  /** uuid */ signal_id: string;
  signal_key: string;
  /** uuid */ source_id: string;
  /** uri */ source_url: string;
};

/** Previsões refeitas em datas passadas: a faixa de 80% acertou `hits` de `trials`. */
export type BacktestOut = {
  hits: number;
  horizon_label: string;
  model_mae: string | null;
  naive_mae: string | null;
  trials: number;
};

/** Quantis dos cenários simulados: 80% entre p10 e p90, 95% entre p2_5 e p97_5. */
export type BandOut = {
  p10: string;
  p2_5: string;
  p50: string;
  p90: string;
  p97_5: string;
};

export type Body_finance_create_import_batch = {
  file: string;
};

export type BudgetOut = {
  category: CategoryOut;
  limit_cents: number;
  remaining_cents: number;
  spent_cents: number;
  status: "ok" | "warning" | "over";
};

/** Orçamento do mês: limite e consumo realizado até hoje, sem previsão. */
export type BudgetReportOut = {
  daily_allowance_cents: number | null;
  days_left: number;
  items: BudgetOut[];
  month: string;
  /** date */ today: string;
  total_limit_cents: number;
  total_spent_cents: number;
};

/** Define ou troca o limite mensal da categoria; limite é positivo e em centavos. */
export type BudgetUpsert = {
  limit_cents: number;
};

export type CalculationInputScope = {
  account_id?: string | null;
  import_batch_ids?: string[];
  period: EvidencePeriod;
  record_ids?: string[];
};

export type CalculationSource = {
  /** date-time */ computed_at: string;
  input_evidence_ids?: string[];
  input_scope: CalculationInputScope;
  kind?: string;
  method_key: string;
  method_version: string;
  module: "finance" | "alpha";
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

export type ChanceOut = {
  event_label: string;
  pct: string;
};

export type ChartPointOut = {
  /** date */ day: string;
  value: string;
};

export type DecimalValue = {
  kind?: string;
  unit: "%" | "pp" | "fraction" | "count" | "t" | "kg" | "ha" | "kg/ha" | "t/ha" | "mm" | "°C" | "index";
  value_decimal: string;
};

export type DerivedSignalOut = {
  evidence_keys: string[];
  key: string;
  limitations: string[];
  /** date */ observation_date: string;
  /** date-time */ published_at: string;
  rule: string;
  summary: string;
  theme: "juros" | "inflacao" | "acoes" | "clima";
  title: string;
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

export type EvidenceItem = {
  basis: "reference" | "observed" | "projected";
  evidence_id: string;
  label: string;
  metric_key: string;
  period: EvidencePeriod;
  source: unknown;
  value: unknown;
};

export type EvidencePeriod = {
  /** date */ end: string;
  /** date */ start: string;
};

/** Entrada HTTP: contexto e identidade do usuário não vêm do navegador. */
export type ExplainRequest = {
  /** uuid */ account_id: string;
  question: string;
};

/** Resposta HTTP montada com as evidências originais do servidor. */
export type ExplainResponse = {
  answer: string;
  /** date-time */ as_of: string;
  evidences: EvidenceItem[];
  limitations: string[];
  uncertainty: "baixa" | "média" | "alta";
};

export type FanPointOut = {
  band: BandOut;
  /** date */ day: string;
};

export type FinanceRecordSource = {
  import_batch_id?: string | null;
  kind?: string;
  /** uuid */ record_id: string;
  record_type: "account" | "transaction";
  /** date-time */ recorded_at: string;
};

export type ForecastOut = {
  backtest: BacktestOut | null;
  chance: ChanceOut | null;
  chart_unit: string;
  current: string;
  current_label: string;
  data_origin: "coleta" | "reserva" | "misto";
  fan: FanPointOut[];
  headline: BandOut;
  history: ChartPointOut[];
  horizon: number;
  horizon_label: string;
  inputs: InputSeriesOut[];
  key: string;
  limitations: string[];
  method: "holt_damped" | "random_walk";
  method_label: string;
  method_version: string;
  params: Record<string, unknown>;
  paths: number;
  question: string;
  tickers?: TickerRangeOut[];
  title: string;
  unit: string;
  unit_label: string;
  view: ViewOut;
};

/** Previsões do perfil no corte `as_of`, calculadas em código, sem LLM. */
export type ForecastsOut = {
  /** date-time */ as_of: string;
  /** date-time */ computed_at: string;
  items: ForecastOut[];
  notes: string[];
  profile: "orcamento-apertado" | "comecando-a-investir" | "investidor" | null;
};

export type HealthResponse = {
  postgres: "ok" | "error";
  status: "ok" | "degraded";
};

export type HistoryPointOut = {
  /** date */ observation_date: string;
  value: string;
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

export type IndicatorOut = {
  history: HistoryPointOut[];
  key: string;
  kind: string;
  latest: PointOut;
  periodicity: "daily" | "monthly";
  previous: PointOut | null;
  region: RegionOut | null;
  source: SourceOut;
  theme: "juros" | "inflacao" | "acoes" | "clima";
  title: string;
  unit: string;
  unit_label: string;
};

export type InputSeriesOut = {
  /** date */ first_day: string;
  key: string;
  /** date */ last_day: string;
  last_ingested_at: string | null;
  last_published_at: string | null;
  observations: number;
  origin: "coleta" | "reserva";
  published_at_estimated: boolean;
  source: InputSourceOut;
  title: string;
};

export type InputSourceOut = {
  license: string;
  name: string;
  slug: string;
  url: string;
};

export type IntegerValue = {
  kind?: string;
  unit?: string;
  value_int: number;
};

export type MoneyValue = {
  amount_cents: number;
  currency?: string;
  kind?: string;
};

export type NewsItemOut = {
  image_credit: string | null;
  image_url: string | null;
  /** date-time */ ingested_at: string;
  /** date */ observation_date: string;
  /** date-time */ published_at: string;
  signal_key: string;
  source: SourceOut;
  summary: string;
  tickers: string[];
  title: string;
  url: string;
};

export type NewsThemeOut = {
  category_slugs: string[];
  items: NewsItemOut[];
  key: string;
  radar_theme: string | null;
  title: string;
  why: string;
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

export type PointOut = {
  /** date-time */ ingested_at: string;
  /** date */ observation_date: string;
  /** date-time */ published_at: string;
  published_at_estimated: boolean;
  revision_id: number;
  signal_key: string;
  source_url: string;
  value: string;
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

/** Radar econômico no corte `as_of`: só revisões publicadas até esse instante. */
export type RadarOut = {
  /** date-time */ as_of: string;
  indicators: IndicatorOut[];
  last_ingested_at: string | null;
  signals: DerivedSignalOut[];
  sources: SourceStatusOut[];
};

export type RegionOut = {
  name: string;
  production: string;
  slug: string;
};

export type SourceOut = {
  license: string;
  name: string;
  slug: string;
  url: string;
};

export type SourceStatusOut = {
  last_ingested_at: string | null;
  series_count: number;
  source: SourceOut;
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

export type TextValue = {
  kind?: string;
  value_text: string;
};

export type TickerRangeOut = {
  band: BandOut;
  chance_up_pct: string;
  daily_vol_pct: string;
  ticker: string;
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

/** Leitura da Valyra por regra fixa sobre os números acima; não é recomendação. */
export type ViewOut = {
  headline: string;
  rule: string;
  stance: "atencao" | "neutra" | "favoravel";
  text: string;
};

/** Notícias publicadas nos 7 dias até `as_of`, agrupadas por tema pela regra `rule`. */
export type WeeklyNewsOut = {
  /** date-time */ as_of: string;
  last_ingested_at: string | null;
  rule: string;
  sources: SourceOut[];
  themes: NewsThemeOut[];
  total_items: number;
  unmatched_items: number;
  /** date-time */ week_start: string;
};

export type AlertsListQuery = {
  limit?: number;
  offset?: number;
};

export type AlphaGetForecastsQuery = {
  profile?: "orcamento-apertado" | "comecando-a-investir" | "investidor" | null;
  as_of?: string | null;
};

export type AlphaGetWeeklyNewsQuery = {
  as_of?: string | null;
};

export type AlphaGetRadarQuery = {
  as_of?: string | null;
};

export type FinanceListAccountsQuery = {
  limit?: number;
  offset?: number;
};

export type FinanceGetProjectionQuery = {
  days?: number;
};

export type FinanceGetBudgetsQuery = {
  month?: string | null;
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
  ai_explain: { method: 'POST', path: '/api/v1/ai/explain' },
  alerts_list: { method: 'GET', path: '/api/v1/alerts' },
  alerts_update: { method: 'PATCH', path: '/api/v1/alerts/{id}' },
  alpha_get_forecasts: { method: 'GET', path: '/api/v1/alpha/forecasts' },
  alpha_get_weekly_news: { method: 'GET', path: '/api/v1/alpha/news/weekly' },
  alpha_get_radar: { method: 'GET', path: '/api/v1/alpha/radar' },
  finance_list_accounts: { method: 'GET', path: '/api/v1/finance/accounts' },
  finance_create_import_batch: { method: 'POST', path: '/api/v1/finance/accounts/{account_id}/import-batches' },
  finance_update_account: { method: 'PATCH', path: '/api/v1/finance/accounts/{id}' },
  finance_get_projection: { method: 'GET', path: '/api/v1/finance/accounts/{id}/projection' },
  finance_get_budgets: { method: 'GET', path: '/api/v1/finance/budgets' },
  finance_delete_budget: { method: 'DELETE', path: '/api/v1/finance/budgets/{category_id}' },
  finance_set_budget: { method: 'PUT', path: '/api/v1/finance/budgets/{category_id}' },
  finance_list_categories: { method: 'GET', path: '/api/v1/finance/categories' },
  finance_list_import_batches: { method: 'GET', path: '/api/v1/finance/import-batches' },
  finance_get_import_batch: { method: 'GET', path: '/api/v1/finance/import-batches/{id}' },
  finance_get_summary: { method: 'GET', path: '/api/v1/finance/summary' },
  finance_list_transactions: { method: 'GET', path: '/api/v1/finance/transactions' },
  finance_update_transaction: { method: 'PATCH', path: '/api/v1/finance/transactions/{id}' },
  system_health: { method: 'GET', path: '/health' },
} as const;
