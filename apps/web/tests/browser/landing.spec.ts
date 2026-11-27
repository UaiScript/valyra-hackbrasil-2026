import { test, expect, type Page } from '@playwright/test';

const repository = 'https://github.com/UaiScript/valyra-hackbrasil-2026';

// Abaixo de 22rem o seletor de idioma do cabeçalho some e só existe dentro do menu móvel.
async function chooseLanguage(page: Page, label: 'PT' | 'EN') {
  const inline = page.locator('.language-switch').getByRole('button', { name: label, exact: true });
  if (!(await inline.isVisible())) await page.locator('.mobile-menu-toggle').click();
  await page.getByRole('button', { name: label, exact: true }).click();
}

test('loads without runtime errors or third-party requests, with honest demo content', async ({ page }) => {
  const errors: string[] = [];
  const external: string[] = [];
  page.on('pageerror', e => errors.push(e.message));
  page.on('request', r => { if (new URL(r.url()).hostname !== '127.0.0.1') external.push(r.url()); });
  await page.goto('/');
  await expect(page.getByRole('heading', { level: 1 })).toContainText('Inteligência financeira');
  await expect(page.getByRole('note')).toContainText('exemplos sintéticos');
  await expect(page.locator('meta[http-equiv="Content-Security-Policy"]')).toHaveAttribute('content', /connect-src 'self'/);
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

test('demo buttons open the Finance app inside the same build', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.route('**/health', r => r.fulfill({ contentType: 'application/json', body: '{"status":"ok","postgres":"ok"}' }));
  await page.route('**/api/v1/**', r => r.fulfill({ contentType: 'application/json', body: '{"items":[],"total":0,"limit":50,"offset":0}' }));
  await page.goto('/');
  const demo = page.locator('[data-demo-cta]');
  expect(await demo.count()).toBeGreaterThanOrEqual(3);
  for (const link of await demo.all()) await expect(link).toHaveAttribute('href', '#/app');
  await page.locator('header [data-demo-cta]').click();
  await expect(page).toHaveURL(/#\/app$/);
  await expect(page.getByRole('heading', { level: 1, name: 'Central' })).toBeVisible();
  // Respostas vazias da API não podem derrubar a Central depois do primeiro desenho.
  await page.waitForLoadState('networkidle');
  await expect(page.getByRole('heading', { level: 1, name: 'Central' })).toBeVisible();
  expect(errors).toEqual([]);
});

test('language switch persists and updates document language', async ({ page }) => {
  await page.goto('/');
  await chooseLanguage(page, 'EN');
  await expect(page.locator('html')).toHaveAttribute('lang', 'en');
  await expect(page.getByRole('heading', { level: 1 })).toContainText('Financial intelligence');
  await expect(page.locator('header [data-primary-cta]')).toHaveText('View repository');
  await page.reload();
  await expect(page.locator('html')).toHaveAttribute('lang', 'en');
  await chooseLanguage(page, 'PT');
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
  await chooseLanguage(page, 'EN');
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


test('showcases all three modules with the problem, features, product preview and CTA', async ({ page }) => {
  await page.goto('/');
  const modules = page.locator('.module-row');
  await expect(modules).toHaveCount(3);

  const expectedModules = ['Valyra Finance', 'Alternative Alpha', 'Valyra AI'];
  for (let index = 0; index < expectedModules.length; index += 1) {
    const module = modules.nth(index);
    await expect(module.getByRole('heading', { level: 3, name: expectedModules[index] })).toBeVisible();
    await expect(module.locator('.module-problem')).toContainText(/problema|problem/i);
    await expect(module.locator('.module-features li')).toHaveCount(3);
    await expect(module.locator('.module-row__visual')).toBeVisible();
    const cta = module.getByRole('link');
    await expect(cta).toHaveAttribute('href', repository);
    await expect(cta).toHaveAttribute('target', '_blank');
  }

  await chooseLanguage(page, 'EN');
  await expect(page.locator('#capacidades')).toContainText('The problem it solves');
  await expect(page.locator('#capacidades')).toContainText('What it brings together');
});

test('presents the product sections and mobile navigation', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('heading', { name: /Valyra Finance/ })).toBeVisible();
  await expect(page.locator('#como-funciona')).toBeVisible();
  await expect(page.locator('#transparencia')).toContainText(/origem|sources/i);
  await page.setViewportSize({ width: 390, height: 844 });
  const menuButton = page.getByRole('button', { name: /Abrir menu|Open menu/ });
  await menuButton.click();
  await expect(page.locator('#mobile-navigation')).toHaveAttribute('data-open', 'true');
  await page.locator('#mobile-navigation').getByRole('link', { name: /Como funciona|How it works/ }).click();
  await expect(page).toHaveURL(/#como-funciona|#how-it-works/);
  await expect(page.locator('#mobile-navigation')).toHaveAttribute('data-open', 'false');
});

test('layout stays within the viewport and internal links have real targets', async ({ page }, testInfo) => {
  await page.goto('/');
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  // "#/app" é rota do app (hash routing), não âncora da página; é coberta no teste dos botões de demonstração.
  const missingTargets = await page.locator('a[href^="#"]:not([href^="#/"])').evaluateAll(links =>
    links.map(a => a.getAttribute('href')!.slice(1)).filter(id => !document.getElementById(id)));
  expect(missingTargets).toEqual([]);
  await page.keyboard.press('Tab');
  await expect(page.getByRole('link', { name: 'Pular para o conteúdo' })).toBeFocused();
  await page.keyboard.press('Escape');
  await page.locator('h1').click();
  await page.screenshot({ path: testInfo.outputPath('landing.png'), fullPage: true });
});
