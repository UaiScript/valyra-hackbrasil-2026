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
};
const page1 = <T,>(items: T[]) => ({ items, total: items.length, limit: 50, offset: 0 });
const json = (route: Route, body: unknown, status = 200) => route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });

async function mockApi(page: Page) {
  const calls: { method: string; url: string; body: string | null }[] = [];
  await page.route('**/health', (r) => json(r, { status: 'ok', postgres: 'ok' }));
  await page.route('**/api/v1/finance/**', (route) => {
    const req = route.request();
    const url = new URL(req.url());
    calls.push({ method: req.method(), url: url.pathname + url.search, body: req.postData() });
    if (url.pathname.endsWith('/accounts')) return json(route, page1([ACCOUNT]));
    if (url.pathname.endsWith('/categories')) return json(route, page1(CATEGORIES));
    if (url.pathname.endsWith('/import-batches') && req.method() === 'GET') return json(route, page1([]));
    if (url.pathname.endsWith('/transactions')) return json(route, page1([TX]));
    if (url.pathname.endsWith('/transactions/t-1') && req.method() === 'PATCH') {
      return json(route, { ...TX, category: { id: 'c-lazer', slug: 'lazer', name: 'Lazer' }, category_source: 'user' });
    }
    if (url.pathname.endsWith('/import-batches') && req.method() === 'POST') {
      return json(route, {
        id: 'b-1', status: 'completed', rows_total: 3, rows_imported: 1, rows_duplicated: 1, rows_rejected: 1,
        rejections: [{ line_number: 4, reason: 'invalid_amount', raw_line: '2026-11-03,Mercado,"-89,90"' }],
      }, 201);
    }
    return json(route, { error: { code: 'NOT_FOUND', message: 'Rota não simulada', details: {} } }, 404);
  });
  return calls;
}

test('visão geral mostra saldo em centavos formatado e status da API', async ({ page }) => {
  await mockApi(page);
  await page.goto('/#/app');
  await expect(page.getByRole('heading', { level: 1, name: 'Visão geral' })).toBeVisible();
  await expect(page.getByText('R$ 5.000,00')).toBeVisible();
  await expect(page.getByText('API conectada')).toBeVisible();
  await expect(page.getByText('-R$ 89,90')).toBeVisible();
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
});

test('API fora do ar gera estado de erro com nova tentativa', async ({ page }) => {
  await page.route('**/health', (r) => r.abort());
  await page.route('**/api/v1/finance/**', (r) => r.abort());
  await page.goto('/#/app');
  await expect(page.getByText('API indisponível')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Tentar de novo' }).first()).toBeVisible();
});
