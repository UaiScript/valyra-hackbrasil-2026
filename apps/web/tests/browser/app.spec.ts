import { expect, test } from '@playwright/test';
import type { Page, Route } from '@playwright/test';

// A API é simulada por page.route: o teste roda no CI sem PostgreSQL nem FastAPI.
// Os formatos seguem packages/contracts/openapi.json.
const ACCOUNT = { id: '00000000-0000-0000-0000-000000000101', name: 'Conta principal', balance_cents: 500000, balance_as_of: '2026-11-01' };
const CATEGORIES = [
  { id: 'c-mercado', slug: 'mercado', name: 'Mercado', kind: 'expense' },
  { id: 'c-lazer', slug: 'lazer', name: 'Lazer', kind: 'expense' },
  { id: 'c-salario', slug: 'salario', name: 'Salário', kind: 'income' },
];
const TX = {
  id: 't-1', date: '2026-11-03', description: 'Supermercado BH', amount_cents: -8990,
  category: { id: 'c-mercado', slug: 'mercado', name: 'Mercado' },
  category_source: 'rule', category_confidence: null, predicted_category_id: 'c-mercado',
  is_recurring: false, anomaly_score: null, is_anomaly: false,
};
const TX_FLAGS = {
  ...TX, id: 't-2', description: 'Cemig energia', amount_cents: -19884,
  is_recurring: true, anomaly_score: '1.0000', is_anomaly: true,
};
const SUMMARY = {
  account_id: null, month: '2026-11', today: '2026-11-07', realized_balance_cents: 487010,
  income_cents: 650000, expenses_cents: -230000, net_cents: 420000,
  categories: [
    { category: { ...CATEGORIES[2] }, total_cents: 650000, count: 1 },
    { category: { ...CATEGORIES[0] }, total_cents: -180000, count: 4 },
    { category: { ...CATEGORIES[1] }, total_cents: -50000, count: 2 },
  ],
};
const PROJECTION = {
  account_id: ACCOUNT.id, today: '2026-11-07', start_balance_cents: 487010, variable_daily_cents: -7950, days: 3,
  min_balance_cents: 473520, min_balance_date: '2026-11-09',
  items: [
    { date: '2026-11-08', recurrences: [], recurring_cents: 0, variable_cents: -7950, balance_cents: 479060 },
    { date: '2026-11-09', recurrences: [{ description: 'Netflix.com', amount_cents: -5590 }], recurring_cents: -5590, variable_cents: -7950, balance_cents: 465520 },
    { date: '2026-11-10', recurrences: [], recurring_cents: 0, variable_cents: -7950, balance_cents: 473520 },
  ],
};
const ALERT = {
  id: 'a-1', kind: 'cash_pressure', severity: 'warning', status: 'new', title: 'Saldo previsto negativo',
  message: 'A projeção dos próximos 30 dias indica saldo mínimo de -R$ 1.248,94 em 03/12/2026.',
  evidence: { days: 30, today: '2026-11-07', start_balance_cents: 145410, min_balance_cents: -124894, min_balance_date: '2026-12-03' },
  account_id: ACCOUNT.id, created_at: '2026-11-07T12:00:00Z', read_at: null,
};
const BUDGETS = {
  month: '2026-11', today: '2026-11-07', total_limit_cents: 200000, total_spent_cents: 180000,
  days_left: 24, daily_allowance_cents: 833,
  items: [{ category: { ...CATEGORIES[0] }, limit_cents: 150000, spent_cents: 180000, remaining_cents: -30000, status: 'over' }],
};
const page1 = <T,>(items: T[]) => ({ items, total: items.length, limit: 50, offset: 0 });
const json = (route: Route, body: unknown, status = 200) => route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });

async function mockApi(page: Page) {
  const calls: { method: string; url: string; body: string | null }[] = [];
  await page.route('**/health', (r) => json(r, { status: 'ok', postgres: 'ok' }));
  await page.route('**/api/v1/alerts**', (route) => {
    const req = route.request();
    const url = new URL(req.url());
    calls.push({ method: req.method(), url: url.pathname + url.search, body: req.postData() });
    if (req.method() === 'PATCH') return json(route, { ...ALERT, status: 'read', read_at: '2026-11-07T13:00:00Z' });
    return json(route, page1([ALERT]));
  });
  await page.route('**/api/v1/finance/**', (route) => {
    const req = route.request();
    const url = new URL(req.url());
    calls.push({ method: req.method(), url: url.pathname + url.search, body: req.postData() });
    if (url.pathname.endsWith('/accounts')) return json(route, page1([ACCOUNT]));
    if (url.pathname.endsWith('/categories')) return json(route, page1(CATEGORIES));
    if (url.pathname.endsWith('/import-batches') && req.method() === 'GET') return json(route, page1([]));
    if (url.pathname.endsWith('/transactions')) return json(route, page1([TX, TX_FLAGS]));
    if (url.pathname.endsWith('/summary')) return json(route, SUMMARY);
    if (url.pathname.endsWith('/projection')) return json(route, PROJECTION);
    if (url.pathname.endsWith('/budgets')) return json(route, BUDGETS);
    if (url.pathname.includes('/budgets/') && req.method() === 'PUT') return json(route, BUDGETS);
    if (url.pathname.endsWith('/transactions/t-1') && req.method() === 'PATCH') {
      return json(route, { ...TX, category: { id: 'c-lazer', slug: 'lazer', name: 'Lazer' }, category_source: 'user' });
    }
    if (url.pathname.endsWith('/import-batches') && req.method() === 'POST') {
      return json(route, {
        id: 'b-1', status: 'completed', rows_total: 3, rows_imported: 1, rows_duplicated: 1, rows_rejected: 1,
        rejections: [{ line_number: 4, reason: 'invalid_amount', raw_line: '2026-11-03,Mercado,"-89,90"' }],
        alerts_created: 1,
      }, 201);
    }
    return json(route, { error: { code: 'NOT_FOUND', message: 'Rota não simulada', details: {} } }, 404);
  });
  return calls;
}

test('central mostra saldo em centavos formatado e status da API', async ({ page }) => {
  await mockApi(page);
  await page.goto('/#/app');
  await expect(page.getByRole('heading', { level: 1, name: 'Central' })).toBeVisible();
  await expect(page.getByText('R$ 5.000,00')).toBeVisible();
  await expect(page.getByText('API conectada')).toBeVisible();
  await expect(page.getByText('-R$ 89,90', { exact: true })).toBeVisible();
});

test('correção de categoria envia PATCH e só oferece categorias do mesmo tipo', async ({ page }) => {
  const calls = await mockApi(page);
  await page.goto('/#/app/transacoes');
  const select = page.getByLabel('Categoria de Supermercado BH');
  await expect(select.locator('option')).toHaveText(['Mercado', 'Lazer']);
  await select.selectOption('c-lazer');
  await expect(page.getByText('“Supermercado BH” agora está em Lazer.')).toBeVisible();
  const patch = calls.find((c) => c.method === 'PATCH');
  expect(patch?.url).toBe('/api/v1/finance/transactions/t-1');
  expect(JSON.parse(patch?.body ?? '{}')).toEqual({ category_id: 'c-lazer' });
});

test('filtro de período vira query string da API', async ({ page }) => {
  const calls = await mockApi(page);
  await page.goto('/#/app/transacoes');
  await page.getByLabel('De', { exact: true }).fill('2026-11-01');
  await expect.poll(() => calls.some((c) => c.url.includes('date_from=2026-11-01'))).toBe(true);
});

test('importação mostra contadores e linhas rejeitadas', async ({ page }) => {
  await mockApi(page);
  await page.goto('/#/app/importar');
  await page.getByLabel('Arquivo').setInputFiles({ name: 'extrato.csv', mimeType: 'text/csv', buffer: Buffer.from('date,description,amount\n') });
  await page.getByRole('button', { name: 'Importar' }).click();
  await expect(page.getByRole('heading', { name: 'Resultado da importação' })).toBeVisible();
  await expect(page.getByText('Valor inválido (use ponto decimal, ex.: -89.90)')).toBeVisible();
  await expect(page.getByText('A importação gerou 1 alerta de pressão de caixa.')).toBeVisible();
});

test('central separa saldo realizado de hoje e projeção dos próximos 30 dias', async ({ page }) => {
  await mockApi(page);
  await page.goto('/#/app');
  await expect(page.getByText('R$ 4.870,10', { exact: true })).toBeVisible();
  await expect(page.getByText('Saldo realizado · 07/11/2026')).toBeVisible();
  await expect(page.getByText('Saldo previsto · 30 dias')).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Projeção semanal' })).toBeVisible();
  await expect(page.getByText('Saldo previsto negativo')).toBeVisible();
  // "Cabe por dia" vem pronto do back, em centavos; a tela só formata.
  await expect(page.getByText('Cabe por dia')).toBeVisible();
  await expect(page.getByText('R$ 8,33', { exact: true })).toBeVisible();
  await expect(page.getByText('24 dias restantes · 90% usado')).toBeVisible();
});

test('orçamento mostra consumo, status e envia limite em centavos', async ({ page }) => {
  const calls = await mockApi(page);
  await page.goto('/#/app/orcamento');
  await expect(page.getByText('R$ 1.800,00 / R$ 1.500,00')).toBeVisible();
  await expect(page.getByText('Passou R$ 300,00 do limite.')).toBeVisible();
  await expect(page.getByRole('link', { name: 'Por quê?' })).toHaveAttribute('href', /valyra-ai\?q=/);
  await page.getByRole('button', { name: 'Definir limite' }).click();
  await page.getByLabel('Limite mensal em reais').fill('600,50');
  await page.getByRole('button', { name: 'Salvar' }).click();
  await expect.poll(() => calls.find((c) => c.method === 'PUT')?.url).toBe('/api/v1/finance/budgets/c-lazer');
  expect(JSON.parse(calls.find((c) => c.method === 'PUT')?.body ?? '{}')).toEqual({ limit_cents: 60050 });
});

test('Pergunte ao Valyra avisa quando a rota de IA não existe na API', async ({ page }) => {
  await mockApi(page);
  await page.route('**/api/v1/ai/explain', (r) => r.fulfill({ status: 404, contentType: 'application/json', body: '{"detail":"Not Found"}' }));
  await page.goto('/#/app/valyra-ai');
  await page.getByRole('button', { name: 'Onde estou gastando mais neste mês?' }).click();
  await expect(page.getByText('A explicação por IA ainda não está publicada nesta API.')).toBeVisible();
});

test('resumo do mês mostra totais, categorias e navega para o mês anterior', async ({ page }) => {
  const calls = await mockApi(page);
  await page.goto('/#/app/resumo');
  await expect(page.getByRole('heading', { name: 'novembro de 2026' })).toBeVisible();
  await expect(page.getByText('R$ 4.200,00')).toBeVisible();
  await expect(page.getByText('-R$ 1.800,00')).toBeVisible();
  await expect(page.getByText('78% do total')).toBeVisible();
  await page.getByRole('button', { name: 'Mês anterior' }).click();
  await expect.poll(() => calls.some((c) => c.url.includes('/summary') && c.url.includes('month=2026-10'))).toBe(true);
});

test('projeção mostra saldo previsto, recorrências e troca o horizonte', async ({ page }) => {
  const calls = await mockApi(page);
  await page.goto('/#/app/projecao');
  await expect(page.getByText('R$ 4.735,20').first()).toBeVisible();
  await expect(page.getByRole('img', { name: /Projeção de 3 dias/ })).toBeVisible();
  await expect(page.getByText('Netflix.com')).toBeVisible();
  await page.getByRole('radio', { name: '60 dias' }).click();
  await expect.poll(() => calls.some((c) => c.url.includes('/projection?days=60'))).toBe(true);
});

test('alerta mostra evidências e marcar como lido envia PATCH', async ({ page }) => {
  const calls = await mockApi(page);
  await page.goto('/#/app/alertas');
  await expect(page.getByRole('heading', { name: 'Saldo previsto negativo' })).toBeVisible();
  await expect(page.getByText('-R$ 1.248,94', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Marcar como lido' }).click();
  await expect(page.getByText('Alerta marcado como lido.')).toBeVisible();
  const patch = calls.find((c) => c.method === 'PATCH' && c.url.startsWith('/api/v1/alerts/'));
  expect(JSON.parse(patch?.body ?? '{}')).toEqual({ status: 'read' });
});

test('transações exibem selos de recorrente e atípico e filtram por eles', async ({ page }) => {
  const calls = await mockApi(page);
  await page.goto('/#/app/transacoes');
  const row = page.getByRole('row', { name: /Cemig energia/ });
  await expect(row.getByText('Recorrente')).toBeVisible();
  await expect(row.getByText('Atípico')).toBeVisible();
  await expect(row.getByText('1,00')).toBeVisible();
  await page.getByRole('button', { name: 'Só recorrentes' }).click();
  await expect.poll(() => calls.some((c) => c.url.includes('is_recurring=true'))).toBe(true);
});

test('indicador da API se recupera quando a primeira checagem falha (API acordando)', async ({ page }) => {
  await mockApi(page);
  let first = true;
  await page.unroute('**/health');
  await page.route('**/health', (r) => {
    if (first) { first = false; return json(r, { status: 'degraded', postgres: 'error' }, 503); }
    return json(r, { status: 'ok', postgres: 'ok' });
  });
  await page.goto('/#/app');
  await expect(page.getByText('API indisponível, tentando de novo')).toBeVisible();
  // Trocar de tela dispara nova checagem, sem esperar o intervalo.
  await page.goto('/#/app/transacoes');
  await expect(page.getByText('API conectada')).toBeVisible();
});

test('API fora do ar gera estado de erro com nova tentativa', async ({ page }) => {
  await page.route('**/health', (r) => r.abort());
  await page.route('**/api/v1/finance/**', (r) => r.abort());
  await page.route('**/api/v1/alerts**', (r) => r.abort());
  await page.goto('/#/app');
  await expect(page.getByText('API indisponível')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Tentar de novo' }).first()).toBeVisible();
});
