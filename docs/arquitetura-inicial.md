# Arquitetura da Valyra

Este documento foi atualizado no endereço existente para preservar referências. Comece pelo [índice seletivo](README.md); regras financeiras ficam em [regras-de-negocio.md](regras-de-negocio.md) e execução, em [desenvolvimento.md](desenvolvimento.md).

## Organização e pontos de entrada

Os caminhos da tabela são relativos à raiz.

| Área                    | Caminho                                                                | Responsabilidade                                                                                        |
| ----------------------- | ---------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| Entrada HTML/React      | `apps/web/index.html`, `apps/web/src/main.tsx`                         | Idioma/metadados, montagem React e ordem dos estilos                                                    |
| Composição              | `apps/web/src/app/App.tsx`                                             | Landing ou Workspace, evento de hash, título e foco                                                     |
| Rotas                   | `apps/web/src/app/routes.ts`                                           | Catálogo de telas, interpretação do hash e construção de links com perfil                               |
| Shell/perfis            | `apps/web/src/features/workspace/`                                     | Navegação, carga dos exemplos, perfis e preferências por contexto                                       |
| Landing                 | `apps/web/src/features/landing/`                                       | Página, abas, prévias de apresentação e modelo derivado dos exemplos                                    |
| Telas internas          | `apps/web/src/features/`                                               | Pastas `overview`, `finance`, `planning` e `radar`: resumo, consulta, compromissos e contexto econômico |
| Domínio financeiro      | `apps/web/src/features/finance/calculations.ts`                        | Totais, filtros, categorias e subtração de compromissos                                                 |
| Apresentação do gráfico | `apps/web/src/features/planning/chartGeometry.ts`, `BalanceChart.tsx`  | Escala/datas/degraus e consulta de valores já calculados                                                |
| Componentes comuns      | `apps/web/src/shared/components/Primitives.tsx`, `Icon.tsx`            | Badge, PageHeading, Metric, TransactionTable, ícones e marca                                            |
| Contratos/formatos      | `apps/web/src/shared/types/domain.ts`, `apps/web/src/shared/format.ts` | Tipos TypeScript, centavos em reais e datas civis                                                       |
| Leitura e fixtures      | `apps/web/src/data/demoRepository.ts`, `apps/web/src/data/demo/`       | Adaptador local e JSON separados por perfil                                                             |
| Apoio Python            | `scripts/check_demo_data.py`, `scripts/serve_web.py`                   | Validação de dados e servidor estático local                                                            |

Não há pacote de backend, roteador externo, gerenciador global de estado ou biblioteca de gráficos. React/React DOM são as dependências de runtime. Vite/TypeScript, Vitest/Happy DOM e Prettier são ferramentas de desenvolvimento.

## Rotas e navegação

O hash é o estado de navegação. `demoNavigation` em `app/routes.ts` fornece os rótulos/ícones à sidebar e às prévias, e os títulos ao App. `parseHashRoute` valida a tela; `demoHref(screen, profile)` constrói os atalhos com perfil explícito.

| Hash                               | Tela            |
| ---------------------------------- | --------------- |
| `#/` (também hash vazio ou `#`)    | Landing         |
| `#/demo/overview?profile=personal` | Visão geral     |
| `#/demo/finance?profile=personal`  | Financeiro      |
| `#/demo/planning?profile=personal` | Planejamento    |
| `#/demo/radar?profile=personal`    | Radar econômico |

Substituir `personal` por `business` seleciona Empresa. Perfil ausente ou não reconhecido mantém o fallback Pessoal; tela ou caminho não suportado mostra a página de caminho não encontrado. Esse comportamento foi preservado na extração das rotas.

A landing usa rolagem/foco para suas seções sem enviar os hashes de âncora ao roteador. O gráfico reabre a memória de cálculo e transfere o foco sem alterar a rota. Acessibilidade de navegação não deve ser perdida ao trocar esses handlers por links brutos.

## Fluxo dos dados e estado

```text
JSON por perfil → demoRepository.getWorkspace(profile) → Workspace → tela → cálculos/apresentação
                                   └────────────────→ AudienceSection → prévia do perfil
landingExample (Pessoal) → previewModel → prévias fixas e exemplo editorial da landing
```

O repositório retorna uma cópia independente a cada leitura. A Promise é um contrato local; não representa requisição HTTP. Componentes de aplicação não leem as fixtures diretamente. Testes e o validador Python podem acessá-las para conferência.

`App` guarda a rota. `Workspace` guarda carga/erro, tentativa e interesses separados por perfil. O hash preserva o perfil na recarga; as preferências da sessão não são persistidas. A tela usa uma chave composta por perfil e seção para reiniciar filtros e detalhes locais.

`Workspace` e `AudienceSection` associam o resultado ao perfil solicitado e descartam callbacks de leituras antigas. A regra impede mostrar números Pessoais com título Empresa, inclusive quando um futuro adaptador tiver latência. No Financeiro, o filtro pertence à tela; no Radar, as preferências pertencem ao Workspace. A aba da landing tem estado próprio.

As funções de cálculo não alteram os registros. `previewModel` deriva os recortes comerciais da mesma base. A hipótese de alimentação é isolada do planejamento; as fórmulas e premissas estão nas [regras de negócio](regras-de-negocio.md).

## Estilos e componentes

`main.tsx` importa, em ordem, `tokens.css`, `global.css`, `landing.css` e `workspace.css`, todos em `apps/web/src/shared/styles/`. Tokens e identidade estão em [DESIGN.md](../apps/web/DESIGN.md). Estilos locais da landing não devem modificar o shell; tabelas, números e estados de foco são compartilhados conforme a função.

`Primitives.tsx` contém os componentes visuais pequenos já reutilizados, incluindo a tabela financeira. `Icon.tsx` contém a família SVG e o símbolo da marca. Não há arquivos de reexportação ou pasta genérica de utilitários necessária para essas responsabilidades.

## Integrações atuais e ponto de extensão

A única leitura de dados é local. `DemoRepository` e `DemoDataset`, em `shared/types/domain.ts`, definem o contrato que um adaptador HTTP futuro deverá cumprir, com validação em tempo de execução, centavos, datas ISO e isolamento por perfil.

FastAPI, persistência, autenticação e IA são propostas. Não existem endpoints, migrações, `HttpRepository` ou modelo conectados para reutilizar. Quando essa fatia for autorizada, substitua o adaptador no ponto de composição, sem espalhar `fetch` pelas telas. Perfil demonstrativo não substitui autorização no servidor; fontes e explicações de IA exigirão proveniência e premissas.

## Testes e manutenção

Os testes ficam junto dos módulos: `app/` protege rotas e fluxos entre telas; `data/` protege cópias/isolamento; `finance/` protege regras; `planning/` protege a representação dos compromissos; `landing/` protege menu, abas e consistência dos exemplos. Happy DOM não substitui inspeção visual.

Comente intenções em português, mantenha as regras fora da renderização e atualize apenas a documentação afetada. Não crie uma segunda fonte de regras em prévias, gráficos ou documentos históricos.
