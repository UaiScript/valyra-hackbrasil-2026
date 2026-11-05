export type ProfileId = 'personal' | 'business';
export type ScreenId = 'overview' | 'finance' | 'planning' | 'radar';

export interface Transaction {
  id: string;
  date: string;
  description: string;
  category: string;
  /** Positivo = entrada; negativo = saída. Inteiros evitam erros de ponto flutuante em dinheiro. */
  amountCents: number;
}

export interface Commitment {
  id: string;
  date: string;
  description: string;
  /** Saída futura positiva, subtraída somente na simulação; não é uma Transaction realizada. */
  amountCents: number;
}

export interface RadarEvent {
  id: string;
  topic: string;
  region: string;
  title: string;
  summary: string;
  context: string;
  limitation: string;
  premise: string;
}

export interface DemoDataset {
  openingBalanceCents: number;
  transactions: Transaction[];
  commitments: Commitment[];
  interests: string[];
  radar: RadarEvent[];
}

export interface FinanceFilter {
  direction: 'all' | 'income' | 'expense';
  category: string;
  search: string;
}

export interface DemoRepository {
  /** Leitura atual local. HTTP futuro deve validar centavos, datas ISO e perfil antes de retornar. */
  getWorkspace(profile: ProfileId): Promise<DemoDataset>;
}
