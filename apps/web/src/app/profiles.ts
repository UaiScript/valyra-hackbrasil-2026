/*
 * Perfis da demonstração: cada um diz como a Valyra se adapta a um tipo de cliente.
 *
 * Os perfis são só dados. Trocar uma persona é editar este arquivo, sem mexer em telas:
 * a Central, o menu, o ticker, o radar Alpha, o relatório da semana e o Pergunte ao Valyra
 * leem daqui o que destacar. Os números continuam vindo da API e são os mesmos para todos
 * os perfis (mesmo usuário demo, mesmos dados sintéticos); muda a experiência, não o dado.
 *
 * Os três perfis abaixo são provisórios, pensados para a trilha 5 e para o modelo de
 * receita proposto (B2C freemium + B2B2C com bancos e cooperativas). A persona final
 * ainda será definida pelo time.
 */

export type ModuleId = 'finance' | 'alpha' | 'ai';

/** O que a faixa do topo da Central mostra. */
export type TickerMode = 'bolsa' | 'manchetes' | 'clima';

/** Tema do radar Alpha aberto primeiro (mesmos ids dos filtros da tela). */
export type AlphaFocus = 'todos' | 'juros' | 'inflacao' | 'acoes' | 'clima';

/** Rotas do app que um atalho pode abrir (mesmos ids de router.ts). */
export type ShortcutRoute = 'overview' | 'summary' | 'budgets' | 'projection' | 'transactions' | 'alerts' | 'alpha' | 'news';

export type ProfileShortcut =
  | { module: Exclude<ModuleId, 'ai'>; route: ShortcutRoute; title: string; hint: string }
  | { module: 'ai'; question: string; title: string; hint: string };

export type Profile = {
  id: string;
  /** Nome curto do perfil, mostrado no seletor. */
  name: string;
  /** Quem é, em uma linha. */
  persona: string;
  /** A dor principal que a Valyra resolve para esse perfil. */
  need: string;
  /** Como esse cliente chega e paga (modelo de negócio). */
  plan: string;
  /** Letra do avatar no cabeçalho. */
  initial: string;
  /** Módulos na ordem em que aparecem no menu; o primeiro é o foco do perfil. */
  modules: [ModuleId, ModuleId, ModuleId];
  ticker: TickerMode;
  alphaFocus: AlphaFocus;
  /** Temas do relatório da semana que sobem para o topo, em ordem (chaves da API). */
  newsThemes: string[];
  /** Um atalho por módulo na faixa "Para você" da Central. */
  shortcuts: [ProfileShortcut, ProfileShortcut, ProfileShortcut];
  /** Perguntas sugeridas no Pergunte ao Valyra, antes das gerais. */
  questions: string[];
};

export const PROFILES: Profile[] = [
  {
    id: 'orcamento-apertado',
    name: 'Orçamento apertado',
    persona: 'Camila, 29, CLT em BH: o salário acaba antes do mês',
    need: 'Ter um limite diário claro e ver o aperto antes de ele chegar',
    plan: 'Plano grátis (B2C freemium)',
    initial: 'C',
    modules: ['finance', 'ai', 'alpha'],
    ticker: 'manchetes',
    alphaFocus: 'todos',
    newsThemes: ['alimentos', 'renda', 'juros'],
    shortcuts: [
      { module: 'finance', route: 'budgets', title: 'Quanto cabe por dia', hint: 'Tetos por categoria e o valor diário até o fim do mês' },
      { module: 'alpha', route: 'news', title: 'O que pesa no mercado', hint: 'Manchetes da semana ligadas às suas categorias' },
      { module: 'ai', question: 'Meu orçamento aguenta até o fim do mês?', title: 'Meu orçamento aguenta?', hint: 'Resposta com os cálculos do Finance citados' },
    ],
    questions: ['Meu orçamento aguenta até o fim do mês?', 'Onde estou gastando mais neste mês?'],
  },
  {
    id: 'comecando-a-investir',
    name: 'Começando a investir',
    persona: 'Guarda no CDB e comprou as primeiras ações',
    need: 'Entender o cenário (juros, inflação, bolsa) sem virar especialista',
    plan: 'Plano Premium (assinatura do freemium)',
    initial: 'I',
    modules: ['alpha', 'finance', 'ai'],
    ticker: 'bolsa',
    alphaFocus: 'acoes',
    newsThemes: ['acoes', 'juros'],
    shortcuts: [
      { module: 'alpha', route: 'alpha', title: 'Radar de juros e ações', hint: 'Selic, CDI, IPCA e a variação do dia, com fonte e data' },
      { module: 'finance', route: 'summary', title: 'Quanto sobrou no mês', hint: 'Entradas, saídas e resultado para guardar' },
      { module: 'ai', question: 'O que o radar mostra sobre juros e ações nesta semana?', title: 'O que mudou no cenário?', hint: 'Explicação com os sinais do radar citados' },
    ],
    questions: ['O que o radar mostra sobre juros e ações nesta semana?', 'O que mudou nos meus gastos em relação ao mês passado?'],
  },
  {
    id: 'cooperado-agro',
    name: 'Cooperado do agro',
    persona: 'Pequeno produtor de grãos, cliente de cooperativa de crédito',
    need: 'Atravessar a entressafra com caixa e acompanhar o clima do campo',
    plan: 'Via cooperativa parceira (B2B2C)',
    initial: 'A',
    modules: ['finance', 'alpha', 'ai'],
    ticker: 'clima',
    alphaFocus: 'clima',
    newsThemes: ['agro', 'juros'],
    shortcuts: [
      { module: 'finance', route: 'projection', title: 'Caixa dos próximos meses', hint: 'Saldo previsto com contas fixas e média de gastos' },
      { module: 'alpha', route: 'alpha', title: 'Chuva nas regiões produtoras', hint: 'Acumulado de 30 dias contra a média de 10 anos' },
      { module: 'ai', question: 'Como está a chuva nas regiões produtoras do radar?', title: 'Como está o clima?', hint: 'Leitura dos sinais de clima, sem prever preço' },
    ],
    questions: ['Como está a chuva nas regiões produtoras do radar?', 'Por que meu saldo previsto fica negativo nos próximos dias?'],
  },
];

/**
 * Experiência padrão antes de alguém escolher um perfil: ordem dos módulos da landing,
 * radar completo e perguntas gerais. Não aparece no seletor.
 */
export const NEUTRAL_PROFILE: Profile = {
  id: 'neutro',
  name: 'Demonstração',
  persona: 'Usuário demo, dados sintéticos',
  need: 'Conhecer os três módulos',
  plan: 'Demonstração',
  initial: 'D',
  modules: ['finance', 'alpha', 'ai'],
  ticker: 'bolsa',
  alphaFocus: 'todos',
  newsThemes: [],
  // Não aparecem (sem perfil, a Central mostra o seletor), mas não dependem da ordem da lista.
  shortcuts: [
    { module: 'finance', route: 'overview', title: 'Central', hint: 'Saldo realizado, projeção e orçamento' },
    { module: 'alpha', route: 'alpha', title: 'Radar econômico', hint: 'Juros, inflação, ações e clima' },
    { module: 'ai', question: 'Onde estou gastando mais neste mês?', title: 'Pergunte ao Valyra', hint: 'Explicações com evidências citadas' },
  ],
  questions: [],
};

/** Perfil salvo, ou null se o id não existe mais (perfil renomeado ou removido). */
export function findProfile(id: string | null | undefined): Profile | null {
  return PROFILES.find((p) => p.id === id) ?? null;
}

export const TICKER_MODES: TickerMode[] = ['bolsa', 'manchetes', 'clima'];

export function isTickerMode(value: unknown): value is TickerMode {
  return typeof value === 'string' && (TICKER_MODES as string[]).includes(value);
}

/** Ordena itens pela prioridade do perfil; os que não estão na lista mantêm a ordem original. */
export function byPriority<T>(items: T[], keyOf: (item: T) => string, priority: string[]): T[] {
  const rank = (item: T) => {
    const i = priority.indexOf(keyOf(item));
    return i < 0 ? priority.length : i;
  };
  return items.map((item, index) => ({ item, index })).sort((a, b) => rank(a.item) - rank(b.item) || a.index - b.index).map(({ item }) => item);
}
