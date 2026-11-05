import type { ProfileId } from '../../shared/types/domain';

export const profiles = {
  personal: {
    name: 'Pessoal',
    description: 'Acompanhe suas receitas, despesas e os próximos compromissos.',
    income: 'Receitas',
    expense: 'Despesas',
    balance: 'Saldo disponível',
    interests: 'Temas de interesse',
  },
  business: {
    name: 'Empresa',
    description: 'Acompanhe entradas, saídas e os próximos compromissos do caixa.',
    income: 'Entradas',
    expense: 'Saídas',
    balance: 'Saldo em caixa',
    interests: 'Exposições operacionais',
  },
} satisfies Record<ProfileId, Record<string, string>>;
