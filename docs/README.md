# Contexto da Valyra

**Comece aqui e leia somente a área da tarefa.** A Valyra conecta organização financeira, planejamento e contexto econômico para Pessoal e Empresa. A versão atual é uma landing e uma demonstração navegável com dados sintéticos; a IA e as integrações são propostas, não serviços conectados.

Stack: React + TypeScript + Vite, Vitest/Happy DOM e Prettier. Python usa a biblioteca padrão para validar os exemplos e servir o build. [Estado e verificações atuais](estado-atual.md).

## Escolha o caminho

Todos os caminhos abaixo são relativos à raiz do repositório.

| Tarefa                                              | Leitura necessária                                                                                        | Comece no código                                                                                                                                                                                               |
| --------------------------------------------------- | --------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Instalar, executar ou resolver problema de ambiente | [Desenvolvimento](desenvolvimento.md)                                                                     | [package.json](../package.json), [scripts/](../scripts/)                                                                                                                                                       |
| Landing page                                        | [Sistema visual](../apps/web/DESIGN.md), [regras do exemplo](regras-de-negocio.md)                        | [features/landing/](../apps/web/src/features/landing/), [landing.css](../apps/web/src/shared/styles/landing.css)                                                                                               |
| Navegação ou uma tela interna                       | [Arquitetura](arquitetura-inicial.md), [desenvolvimento](desenvolvimento.md)                              | [app/routes.ts](../apps/web/src/app/routes.ts), [Workspace.tsx](../apps/web/src/features/workspace/Workspace.tsx)                                                                                              |
| Componentes e design                                | [Sistema visual](../apps/web/DESIGN.md); [arquitetura](arquitetura-inicial.md) se mudar responsabilidades | [Primitives.tsx](../apps/web/src/shared/components/Primitives.tsx), [Icon.tsx](../apps/web/src/shared/components/Icon.tsx), [styles/](../apps/web/src/shared/styles/)                                          |
| Financeiro e cálculos                               | [Regras de negócio](regras-de-negocio.md)                                                                 | [calculations.ts](../apps/web/src/features/finance/calculations.ts), [Finance.tsx](../apps/web/src/features/finance/Finance.tsx)                                                                               |
| Planejamento                                        | [Regras de negócio](regras-de-negocio.md)                                                                 | [Planning.tsx](../apps/web/src/features/planning/Planning.tsx), [BalanceChart.tsx](../apps/web/src/features/planning/BalanceChart.tsx), [chartGeometry.ts](../apps/web/src/features/planning/chartGeometry.ts) |
| Radar e contexto econômico                          | [Regras de negócio](regras-de-negocio.md), [escopo](escopo-mvp.md)                                        | [Radar.tsx](../apps/web/src/features/radar/Radar.tsx), [domain.ts](../apps/web/src/shared/types/domain.ts)                                                                                                     |
| Dados e integração futura                           | [Arquitetura](arquitetura-inicial.md), [regras](regras-de-negocio.md)                                     | [demoRepository.ts](../apps/web/src/data/demoRepository.ts), [data/demo/](../apps/web/src/data/demo/), [check_demo_data.py](../scripts/check_demo_data.py)                                                     |
| Testes e regressões                                 | [Desenvolvimento](desenvolvimento.md)                                                                     | Testes `*.test.ts` / `*.test.tsx` junto dos módulos; [App.test.tsx](../apps/web/src/app/App.test.tsx) cobre o fluxo entre telas                                                                                |
| Produto e participação no evento                    | [Escopo](escopo-mvp.md), [checklist do hackathon](hackathon-checklist.md)                                 | [PRODUCT.md](../apps/web/PRODUCT.md) registra o contexto confirmado                                                                                                                                            |

## Onde ficam as responsabilidades

`apps/web/src/app/` compõe a aplicação e resolve o hash. `features/` contém as telas e a landing. `shared/` contém apresentação, formatos e contratos comuns; `data/` fornece exemplos locais. O mapa técnico está em [arquitetura-inicial.md](arquitetura-inicial.md), mantido nesse endereço para preservar os links existentes.

## Registros anteriores, para consulta pontual

- [Primeira entrega](verificacao-inicial.md), [refinamento do app](refinamento-interface.md) e [reconstrução da landing](landing-reconstrucao.md) são registros históricos. Nomes e contagens de testes refletem cada etapa; não substituem [estado-atual.md](estado-atual.md).
- [FARO_BASE_PRODUTO_NEGOCIO_E_IMPLEMENTACAO_v1.md](FARO_BASE_PRODUTO_NEGOCIO_E_IMPLEMENTACAO_v1.md) é um arquivo legado vazio. Não assuma regras a partir dele.
- As convenções de contribuição estão em [CONTRIBUTING.md](../CONTRIBUTING.md); instruções de trabalho para agentes, em [AGENTS.md](../AGENTS.md).
