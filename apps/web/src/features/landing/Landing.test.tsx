// @vitest-environment happy-dom
import { StrictMode, act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { Landing } from './Landing';
import { money } from '../../shared/format';
import { demoRepository } from '../../data/demoRepository';
import personal from '../../data/demo/personal.json';
import business from '../../data/demo/business.json';

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT =
  true;
let root: Root;
let host: HTMLDivElement;

beforeEach(async () => {
  window.history.replaceState(null, '', '#/');
  host = document.createElement('div');
  document.body.append(host);
  root = createRoot(host);
  await act(async () =>
    root.render(
      <StrictMode>
        <Landing />
      </StrictMode>,
    ),
  );
});
afterEach(async () => {
  await act(async () => root.unmount());
  host.remove();
  vi.restoreAllMocks();
});
const tabs = () => host.querySelectorAll<HTMLButtonElement>('[role="tab"]');
const panel = () => host.querySelector<HTMLElement>('[role="tabpanel"]')!;
async function click(element: HTMLElement | null) {
  expect(element).not.toBeNull();
  await act(async () => element!.click());
}

describe('interações da landing', () => {
  it('começa em Pessoal e mostra uma prévia consistente com os registros', () => {
    expect(host.querySelector('h1')?.textContent).toBe(
      'Suas finanças conectadas ao que acontece na economia.',
    );
    expect(tabs()[0].getAttribute('aria-selected')).toBe('true');
    expect(host.querySelector('.lp-main-preview .lp-preview-totals dd')?.textContent).toBe(
      money(555770),
    );
    expect(host.querySelector('.lp-planning-result strong')?.textContent).toBe(money(467280));
    expect(host.querySelectorAll('h1')).toHaveLength(1);
  });

  it('troca título, dados, benefícios e destino ao selecionar Empresa', async () => {
    await click(tabs()[1]);
    expect(panel().querySelector('h3')?.textContent).toContain('Acompanhe o caixa');
    expect(panel().querySelector('.lp-preview-totals dd')?.textContent).toBe(money(1955000));
    expect(panel().querySelector('.lp-audience-copy ul')?.textContent).toContain(
      'entradas e saídas do caixa',
    );
    expect(
      panel().querySelector<HTMLAnchorElement>('.lp-audience-copy > a')?.getAttribute('href'),
    ).toBe('#/demo/overview?profile=business');
    expect(panel().querySelector('.lp-product-nav')?.textContent).not.toContain('Temas pessoais');
    await click(tabs()[0]);
    expect(panel().querySelector('.lp-preview-totals dd')?.textContent).toBe(money(555770));
  });

  it('permite alternar abas com setas, Home e End mantendo foco e roving tabindex', async () => {
    await act(async () => {
      tabs()[0].focus();
      tabs()[0].dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowRight', bubbles: true }));
    });
    expect(document.activeElement).toBe(tabs()[1]);
    expect(tabs()[1].getAttribute('aria-selected')).toBe('true');
    expect(tabs()[0].tabIndex).toBe(-1);
    await act(async () =>
      tabs()[1].dispatchEvent(new KeyboardEvent('keydown', { key: 'Home', bubbles: true })),
    );
    expect(document.activeElement).toBe(tabs()[0]);
    await act(async () =>
      tabs()[0].dispatchEvent(new KeyboardEvent('keydown', { key: 'End', bubbles: true })),
    );
    expect(document.activeElement).toBe(tabs()[1]);
    await act(async () =>
      tabs()[1].dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowLeft', bubbles: true })),
    );
    expect(document.activeElement).toBe(tabs()[0]);
    expect(panel().getAttribute('aria-labelledby')).toBe(tabs()[0].id);
  });

  it('abre o menu, fecha com Escape e devolve o foco ao controle', async () => {
    const button = host.querySelector<HTMLButtonElement>('.lp-menu-button')!;
    expect(button.getAttribute('aria-expanded')).toBe('false');
    await click(button);
    expect(button.getAttribute('aria-expanded')).toBe('true');
    expect(document.activeElement).toBe(host.querySelector('.lp-main-nav a'));
    expect(button.getAttribute('aria-label')).toBe('Fechar menu');
    await act(async () =>
      button.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true })),
    );
    expect(button.getAttribute('aria-expanded')).toBe('false');
    expect(document.activeElement).toBe(button);
    expect(host.querySelector('.lp-mobile-demo')?.getAttribute('href')).toContain('/demo/overview');
  });

  it('navega pelas seções sem enviar o hash de âncora ao roteador interno', async () => {
    const target = host.querySelector<HTMLElement>('#como-funciona')!;
    const scroll = vi.fn();
    target.scrollIntoView = scroll;
    await click(host.querySelector('.lp-main-nav a[href="#como-funciona"]'));
    expect(scroll).toHaveBeenCalledOnce();
    expect(document.activeElement).toBe(host.querySelector('#how-title'));
    expect(window.location.hash).toBe('#/');
  });

  it('apresenta a hipótese e o planejamento como cálculos diferentes', () => {
    const example = host.querySelector('.lp-context-example')!;
    expect(example.textContent).toContain(money(51020));
    expect(example.textContent).toContain('× 1,05');
    expect(example.textContent).toContain('Não altera saldo');
    expect(example.textContent).not.toContain(money(467280));
    expect(host.querySelector('.lp-ai-direction')?.textContent).toContain('não há IA conectada');
    expect(host.querySelector('.lp-planning-preview')?.textContent).toContain('Não prevê renda');
  });

  it('mantém os links para os quatro módulos e para o repositório real', () => {
    for (const screen of ['overview', 'finance', 'planning', 'radar']) {
      expect(host.querySelector(`a[href="#/demo/${screen}?profile=personal"]`)).not.toBeNull();
    }
    expect(host.querySelector('a[href="#/demo/overview?profile=business"]')).not.toBeNull();
    expect(
      host.querySelector('a[href="https://github.com/UaiScript/valyra-hackbrasil-2026"]'),
    ).not.toBeNull();
    expect(
      [...host.querySelectorAll('a')].some(
        (link) => !link.getAttribute('href') || link.getAttribute('href') === '#',
      ),
    ).toBe(false);
    expect(host.querySelectorAll('.lp-faq details')).toHaveLength(4);
  });

  it('oferece nova tentativa se a leitura do perfil falhar', async () => {
    const request = vi
      .spyOn(demoRepository, 'getWorkspace')
      .mockRejectedValue(new Error('Falha de teste'));
    await click(tabs()[1]);
    expect(panel().querySelector('[role="alert"]')?.textContent).toContain('não carregou');
    request.mockResolvedValue(structuredClone(business));
    await click(panel().querySelector('[role="alert"] button'));
    expect(panel().querySelector('.lp-preview-totals dd')?.textContent).toBe(money(1955000));
  });

  it('descarta a resposta de Empresa depois de voltar para Pessoal', async () => {
    let resolveBusiness: (data: typeof business) => void = () => {};
    const pending = new Promise<typeof business>((resolve) => {
      resolveBusiness = resolve;
    });
    vi.spyOn(demoRepository, 'getWorkspace').mockImplementation((profile) =>
      profile === 'business' ? pending : Promise.resolve(structuredClone(personal)),
    );
    await click(tabs()[1]);
    expect(panel().querySelector('.lp-audience-preview')?.getAttribute('aria-busy')).toBe('true');
    expect(panel().querySelector('.lp-preview-totals')).toBeNull();
    await click(tabs()[0]);
    await act(async () => resolveBusiness(structuredClone(business)));
    expect(panel().querySelector('.lp-preview-totals dd')?.textContent).toBe(money(555770));
    expect(tabs()[0].getAttribute('aria-selected')).toBe('true');
  });
});
