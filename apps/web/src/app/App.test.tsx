// @vitest-environment happy-dom
import { StrictMode, act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { App } from './App';
import { money } from '../shared/format';
import { demoRepository } from '../data/demoRepository';
import personal from '../data/demo/personal.json';
import business from '../data/demo/business.json';

// DOM simulado testa o comportamento React; não substitui conferir layout no navegador real.
(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT =
  true;

let host: HTMLDivElement;
let root: Root;

async function navigate(hash: string) {
  await act(async () => {
    window.history.replaceState(null, '', hash);
    window.dispatchEvent(new HashChangeEvent('hashchange'));
  });
}

async function click(element: HTMLElement | null) {
  expect(element).not.toBeNull();
  await act(async () => {
    element!.click();
  });
}

async function openNavigation(label: string) {
  const link = [...host.querySelectorAll<HTMLAnchorElement>('.sidebar nav a')].find(
    (item) => item.textContent?.trim() === label,
  );
  expect(link).toBeDefined();
  await navigate(link!.getAttribute('href')!);
}

async function switchProfile(label: string) {
  await click(
    [...host.querySelectorAll<HTMLButtonElement>('.profile-switch button')].find(
      (item) => item.textContent?.trim() === label,
    )!,
  );
  // A âncora por hash produz um evento assíncrono no navegador. O teste o entrega explicitamente.
  await navigate(window.location.hash);
}

beforeEach(async () => {
  window.history.replaceState(null, '', '#/');
  host = document.createElement('div');
  document.body.append(host);
  root = createRoot(host);
  await act(async () => {
    root.render(
      <StrictMode>
        <App />
      </StrictMode>,
    );
  });
});

afterEach(async () => {
  await act(async () => root.unmount());
  host.remove();
  vi.restoreAllMocks();
});

describe('navegação e isolamento no DOM', () => {
  it('abre a experiência Empresa pela landing e mantém o contexto nas quatro seções', async () => {
    const entry = host.querySelector<HTMLAnchorElement>(
      'a[href="#/demo/overview?profile=business"]',
    );
    expect(entry).not.toBeNull();
    await navigate(entry!.getAttribute('href')!);
    expect(host.querySelector('h1')?.textContent).toBe('Visão geral');
    expect(host.querySelector('.metric strong')?.textContent).toBe(money(1955000));
    for (const section of ['Financeiro', 'Planejamento', 'Radar', 'Visão geral']) {
      await openNavigation(section);
      expect(host.querySelector('.profile-switch button[aria-pressed="true"]')?.textContent).toBe(
        'Empresa',
      );
      expect(window.location.hash).toContain('profile=business');
      expect(host.querySelector('nav a[aria-current="page"]')?.textContent).toBe(section);
    }
  });

  it('filtra registros e reinicia a seleção ao trocar de perfil', async () => {
    await navigate('#/demo/finance');
    const category = host.querySelectorAll('select')[1];
    await act(async () => {
      category.value = 'Moradia';
      category.dispatchEvent(new Event('change', { bubbles: true }));
    });
    expect(host.querySelectorAll('tbody tr')).toHaveLength(2);
    expect(host.querySelector('.table-total strong')?.textContent).toBe(money(-201840));
    await switchProfile('Empresa');
    expect(host.querySelectorAll('select')[1].value).toBe('all');
    expect(host.querySelectorAll('tbody tr')).toHaveLength(6);
    expect(host.querySelector('tbody')?.textContent).not.toContain('Conta de energia');
    expect(host.querySelector('.table-total strong')?.textContent).toBe(money(1115000));
    await switchProfile('Pessoal');
    expect(host.querySelectorAll('select')[1].value).toBe('all');
    expect(host.querySelectorAll('tbody tr')).toHaveLength(7);
  });

  it('combina busca e movimento, mostra vazio e limpa filtros', async () => {
    await navigate('#/demo/finance');
    const search = host.querySelector<HTMLInputElement>('input[type="search"]')!;
    const direction = host.querySelector('select')!;
    await act(async () => {
      // O setter nativo entrega ao React o mesmo evento de edição que o navegador produziria.
      Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')!.set!.call(
        search,
        'energia',
      );
      search.dispatchEvent(new Event('input', { bubbles: true }));
      direction.value = 'expense';
      direction.dispatchEvent(new Event('change', { bubbles: true }));
    });
    expect(host.querySelectorAll('tbody tr')).toHaveLength(1);
    expect(host.querySelector('.table-total strong')?.textContent).toBe(money(-21840));
    await act(async () => {
      direction.value = 'income';
      direction.dispatchEvent(new Event('change', { bubbles: true }));
    });
    expect(host.querySelectorAll('tbody tr')).toHaveLength(0);
    expect(host.querySelector('.empty-state')?.textContent).toContain('Nenhum lançamento');
    await click(
      [...host.querySelectorAll('button')].find((item) => item.textContent === 'Limpar filtros')!,
    );
    expect(host.querySelectorAll('tbody tr')).toHaveLength(7);
    expect(search.value).toBe('');
  });

  it('preserva temas separadamente e limpa detalhes ao trocar perfil', async () => {
    await navigate('#/demo/radar');
    await click(host.querySelector<HTMLInputElement>('input[type="checkbox"]'));
    expect(host.querySelectorAll('.radar-event')).toHaveLength(2);
    const detail = host.querySelector('.radar-event details') as HTMLDetailsElement;
    await click(detail.querySelector('summary'));
    expect(detail.open).toBe(true);
    expect(detail.textContent).toContain('Exemplo ilustrativo');
    await switchProfile('Empresa');
    expect(host.querySelectorAll('.radar-event')).toHaveLength(3);
    expect(host.querySelector<HTMLDetailsElement>('.radar-event details')?.open).toBe(false);
    expect(host.querySelector('.interests-fieldset legend')?.textContent).toBe(
      'Exposições operacionais',
    );
    expect(host.querySelector('.interest-options')?.textContent).not.toContain('Custo de vida');
    await switchProfile('Pessoal');
    expect(host.querySelectorAll('.radar-event')).toHaveLength(2);
    expect(host.querySelector<HTMLInputElement>('input[type="checkbox"]')?.checked).toBe(false);
  });

  it('mantém as premissas do planejamento e oferece caminho para rota desconhecida', async () => {
    await navigate('#/demo/planning');
    expect(host.querySelector('.projection-value')?.textContent).toBe(money(467280));
    expect(host.querySelector('main')?.textContent).toContain('não prevê renda');
    expect(host.querySelector('.balance-chart')?.getAttribute('aria-label')).toContain('saldo');
    expect(host.querySelectorAll('.chart-point')).toHaveLength(4);
    expect(host.querySelector('.calculation-memory table')?.textContent).toContain(money(467280));
    await navigate('#/pagina-inexistente');
    expect(host.querySelector('h1')?.textContent).toBe('Vamos encontrar seu rumo.');
    expect(host.querySelector('a.button')?.getAttribute('href')).toBe('#/');
  });

  it('direciona foco ao título e fornece acesso direto ao conteúdo', async () => {
    await navigate('#/demo/overview');
    expect(document.activeElement).toBe(host.querySelector('h1'));
    await click(host.querySelector('.skip-link'));
    expect(document.activeElement).toBe(host.querySelector('main'));
  });

  it('preserva Empresa em todos os atalhos da Visão geral', async () => {
    await navigate('#/demo/overview?profile=business');
    const shortcuts = [...host.querySelectorAll<HTMLAnchorElement>('main a[href^="#/demo/"]')];
    expect(shortcuts.length).toBeGreaterThan(3);
    for (const shortcut of shortcuts) {
      const href = shortcut.getAttribute('href')!;
      expect(href).toContain('profile=business');
      await navigate(href);
      expect(host.querySelector('.profile-switch button[aria-pressed="true"]')?.textContent).toBe(
        'Empresa',
      );
    }
  });

  it('atualiza o saldo ao focar uma data e abre a alternativa textual completa', async () => {
    await navigate('#/demo/planning');
    const points = host.querySelectorAll<HTMLButtonElement>('.chart-point');
    await act(async () => points[1].focus());
    expect(points[1].getAttribute('aria-pressed')).toBe('true');
    expect(host.querySelector('.chart-readout')?.textContent).toContain('Internet');
    expect(host.querySelector('.chart-readout strong')?.textContent).toBe(money(543780));
    await click(points[3]);
    expect(host.querySelector('.chart-readout strong')?.textContent).toBe(money(467280));
    const picker = host.querySelector<HTMLSelectElement>('.chart-date-picker select')!;
    await act(async () => {
      picker.value = '2';
      picker.dispatchEvent(new Event('change', { bubbles: true }));
    });
    expect(host.querySelector('.chart-readout strong')?.textContent).toBe(money(509780));
    const memory = host.querySelector<HTMLDetailsElement>('.calculation-memory')!;
    await click(memory.querySelector('summary'));
    expect(memory.open).toBe(false);
    await click(host.querySelector('.chart-explanation a'));
    expect(memory.open).toBe(true);
    expect(document.activeElement).toBe(memory.querySelector('.table-scroll'));
    expect(window.location.hash).toBe('#/demo/planning');
  });

  it('explica o modo demonstração e mantém a identidade oficial', async () => {
    await navigate('#/demo/finance');
    const info = host.querySelector<HTMLDetailsElement>('.demo-info')!;
    expect(info.open).toBe(false);
    await click(info.querySelector('summary'));
    expect(info.open).toBe(true);
    expect(info.textContent).toContain('Não há conexão bancária');
    expect(info.textContent).toContain('IA conectada');
    expect(document.title).toBe('Valyra — Financeiro');
    expect(host.textContent).not.toMatch(/Valyre|Faro/);
    expect(host.querySelector('.brand')?.getAttribute('aria-label')).toBe('Valyra, página inicial');
    const clear = [...host.querySelectorAll<HTMLButtonElement>('button')].find(
      (item) => item.textContent === 'Limpar filtros',
    )!;
    expect(clear.disabled).toBe(true);
  });

  it('oferece recuperação quando todos os temas forem desmarcados', async () => {
    await navigate('#/demo/radar');
    for (const checkbox of host.querySelectorAll<HTMLInputElement>('.interest-options input'))
      await click(checkbox);
    expect(host.querySelectorAll('.radar-event')).toHaveLength(0);
    expect(host.querySelector('.empty-state')?.textContent).toContain('Nenhum tema selecionado');
    await click(host.querySelector('.empty-state button'));
    expect(host.querySelectorAll('.radar-event')).toHaveLength(3);
  });

  it('informa falha de carga e permite tentar novamente', async () => {
    const request = vi
      .spyOn(demoRepository, 'getWorkspace')
      .mockRejectedValue(new Error('Falha de teste'));
    await navigate('#/demo/overview');
    expect(host.querySelector('[role="alert"]')?.textContent).toContain('Não foi possível abrir');
    request.mockResolvedValue(structuredClone(personal));
    await click(host.querySelector('[role="alert"] button'));
    expect(host.querySelector('[role="alert"]')).toBeNull();
    expect(host.querySelector('.metric strong')?.textContent).toBe(money(555770));
  });

  it('mostra carregamento sem reutilizar registros de outro perfil', async () => {
    await navigate('#/demo/finance');
    let resolveRequest: (data: typeof personal) => void = () => {};
    const pending = new Promise<typeof personal>((resolve) => {
      resolveRequest = resolve;
    });
    vi.spyOn(demoRepository, 'getWorkspace').mockReturnValue(pending);
    await switchProfile('Empresa');
    expect(host.querySelector('main')?.getAttribute('aria-busy')).toBe('true');
    expect(host.querySelector('.workspace-loading')?.textContent).toContain('Carregando');
    expect(host.querySelector('table')).toBeNull();
    await act(async () => resolveRequest(structuredClone(business)));
    expect(host.querySelector('main')?.getAttribute('aria-busy')).toBe('false');
    expect(host.querySelectorAll('tbody tr')).toHaveLength(6);
    expect(host.querySelector('tbody')?.textContent).not.toContain('Conta de energia');
  });

  it.each(['personal', 'business'])(
    'mantém as quatro seções operacionais no perfil %s',
    async (profile) => {
      const expected = {
        overview: 'Visão geral',
        finance: 'Financeiro',
        planning: 'Planejamento',
        radar: 'Radar econômico',
      };
      for (const [screen, title] of Object.entries(expected)) {
        await navigate(`#/demo/${screen}?profile=${profile}`);
        expect(host.querySelector('h1')?.textContent).toBe(title);
        expect(document.title).toBe(`Valyra — ${title}`);
        expect(host.querySelector('main')?.getAttribute('aria-busy')).toBe('false');
        expect(host.querySelector('.profile-switch button[aria-pressed="true"]')?.textContent).toBe(
          profile === 'personal' ? 'Pessoal' : 'Empresa',
        );
      }
    },
  );
});
