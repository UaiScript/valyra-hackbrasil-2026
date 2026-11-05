import personal from './demo/personal.json';
import business from './demo/business.json';
import type { DemoDataset, DemoRepository, ProfileId } from '../shared/types/domain';

const datasets = { personal, business } satisfies Record<ProfileId, DemoDataset>;

// Uma cópia por leitura impede que um componente altere os exemplos de outro perfil.
// Não há requisição HTTP nem API simulada: a Promise mantém o contrato para a futura FastAPI.
export const demoRepository: DemoRepository = {
  async getWorkspace(profile) {
    return structuredClone(datasets[profile]);
  },
};

export const landingExample: DemoDataset = structuredClone(personal);
