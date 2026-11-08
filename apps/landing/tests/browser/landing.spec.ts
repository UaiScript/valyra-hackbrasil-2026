import { test, expect } from '@playwright/test';

const repository = 'https://github.com/UaiScript/valyra-hackbrasil-2026';

test('loads without runtime errors or third-party requests, with honest demo content', async ({ page }) => {
  const errors: string[] = [];
  const external: string[] = [];
  page.on('pageerror', e => errors.push(e.message));
  page.on('request', r => { if (new URL(r.url()).hostname !== '127.0.0.1') external.push(r.url()); });
  await page.goto('/');
  await expect(page.getByRole('heading', { level: 1 })).toContainText('Inteligência financeira');
  await expect(page.getByRole('note')).toContainText('exemplos sintéticos');
  await expect(page.locator('meta[http-equiv="Content-Security-Policy"]')).toHaveAttribute('content', /connect-src 'none'/);
  await expect(page.locator('body')).not.toContainText(/MOTOR DOCKER ATIVO|Capital Monitorado|FEED CME|FIX Protocol|Convexidade dinâmica ativada|Proteção estrita de cauda/);
  expect(errors).toEqual([]);
  expect(external).toEqual([]);
});

test('every access link leads to the official repository, even with stale stored destinations', async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem('valyra_system_url', 'javascript:alert(1)'));
  await page.goto('/');
  const links = page.locator('[data-primary-cta]');
  expect(await links.count()).toBeGreaterThanOrEqual(5);
  for (const link of await links.all()) await expect(link).toHaveAttribute('href', repository);
  await expect(page.getByRole('button', { name: /Configurar|Configure/ })).toHaveCount(0);
  // Intercept only the destination so the test verifies actual navigation without visiting GitHub.
  await page.route(repository, route => route.fulfill({ contentType: 'text/html', body: '<p>Repository destination</p>' }));
  await page.locator('header [data-primary-cta]').click();
  await expect(page).toHaveURL(repository);
});

test('language switch persists and updates document language', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('button', { name: 'EN', exact: true }).click();
  await expect(page.locator('html')).toHaveAttribute('lang', 'en');
  await expect(page.getByRole('heading', { level: 1 })).toContainText('Financial intelligence');
  await expect(page.locator('header [data-primary-cta]')).toHaveText('View repository');
  await page.reload();
  await expect(page.locator('html')).toHaveAttribute('lang', 'en');
  await page.getByRole('button', { name: 'PT', exact: true }).click();
  await expect(page.locator('html')).toHaveAttribute('lang', 'pt-BR');
});

test('the page works when browser storage is disabled', async ({ page }) => {
  await page.addInitScript(() => {
    Object.defineProperty(window, 'localStorage', { get() { throw new Error('Storage disabled'); } });
  });
  const errors: string[] = [];
  page.on('pageerror', e => errors.push(e.message));
  await page.goto('/');
  await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
  await page.getByRole('button', { name: 'EN', exact: true }).click();
  await expect(page.locator('html')).toHaveAttribute('lang', 'en');
  expect(errors).toEqual([]);
});

test('timeframe, research example and scenario controls change their visible data', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('button', { name: '1Y', exact: true }).click();
  await expect(page.getByText('128.60 pts', { exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: '1Y', exact: true })).toHaveAttribute('aria-pressed', 'true');
  await page.getByRole('button', { name: /Comércio exterior/ }).click();
  await expect(page.locator('#alternative-alpha').getByText('+3.92%', { exact: true }).last()).toBeVisible();
  await page.getByRole('button', { name: /Liquidez ilustrativa/ }).click();
  await expect(page.locator('#simulador').getByText('+5.12%', { exact: true })).toBeVisible();
});

test('layout stays within the viewport and internal links have real targets', async ({ page }, testInfo) => {
  await page.goto('/');
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  const missingTargets = await page.locator('a[href^="#"]').evaluateAll(links =>
    links.map(a => a.getAttribute('href')!.slice(1)).filter(id => !document.getElementById(id)));
  expect(missingTargets).toEqual([]);
  await page.keyboard.press('Tab');
  await expect(page.getByRole('link', { name: 'Pular para o conteúdo' })).toBeFocused();
  await page.keyboard.press('Escape');
  await page.locator('h1').click();
  await page.screenshot({ path: testInfo.outputPath('landing.png'), fullPage: true });
});
