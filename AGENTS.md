# Valyra — contexto para agentes

## Produto em uma frase

Plataforma de inteligência financeira pessoal que permite antecipar dificuldades de orçamento e compreender riscos econômicos relevantes para investimentos.

## Regras invioláveis

- Sem data leakage: respeite `published_at`, `as_of` e a revisão conhecida no corte; observação, publicação e ingestão são instantes diferentes.
- O LLM nunca gera números: cálculos e fontes verificáveis fornecem os valores; a IA explica evidências sem inventar probabilidades ou causalidade.
- Somente dados sintéticos ou públicos com condições de uso verificadas; nunca versione dados pessoais, segredos, credenciais ou `.env`.
- Dinheiro usa centavos inteiros no banco, na API e no frontend, com nomes `*_cents`; sem `float`. Preserve as pendências de precisão de Alpha/IA da modelagem, sem arredondamento tácito.
- Não edite código gerado em `packages/contracts/` ou `apps/web/src/lib/api/`; regenere pelo comando correspondente quando disponível.
- Sem ADR aceita para uma nova decisão arquitetural, pergunte ao humano. Solicitações explícitas já autorizadas orientam a tarefa; não transforme propostas dos specs em decisões aceitas.
- Confira branch e `git status`; preserve trabalho dos colegas. Não faça commit, push, merge, deploy pago ou remoção de dados sem autorização.
- Textos públicos usam Valyra; preserve nomes técnicos `valyre` e `@valyre/web` ao integrar o frontend existente.
- Comentários em português explicam o porquê de regras não evidentes; evite narrar cada linha, abstrações sem consumidor e dependências sem necessidade.
- Não altere registros históricos para fazê-los parecer verificações atuais. Diferencie implementado, demonstrativo e planejado.
- `CLAUDE.md` contém apenas `@AGENTS.md`; não duplique conteúdo entre eles. Preserve configurações existentes de ferramentas e skills.

## Comandos

Execute na raiz. Consulte [CONTRIBUTING.md](CONTRIBUTING.md) antes de usar comandos previstos.

| Área | Comandos | Estado neste checkout |
| --- | --- | --- |
| Banco local | `docker compose --env-file .env.example config --quiet`; `docker compose --env-file .env.example up -d --wait postgres` | Disponíveis |
| Backend | `make dev`, `make test`, `make lint`, `make migrate`, `make seed`, `make openapi` | Previstos; Makefile/API ainda não integrados |
| Frontend | `npm ci`, `npm run dev`, `npm run check`, `npm run format:check` | Preservados da base web em outra branch; indisponíveis aqui |

Não invente checks bem-sucedidos. A CI `api` deve falhar explicitamente enquanto faltarem os pré-requisitos das Issues #8–#10.

## Mapa de pastas

- `.github/`: CI, forms, template de PR e prompt de revisão.
- `docs/`: specs, arquitetura, glossário, ADRs e procedimentos.
- `services/api/`: [contexto de backend](services/api/AGENTS.md); nesta etapa contém instruções, sem implementação da API.
- `apps/web/`: frontend previsto; não existe neste checkout. Ao integrar a base, preserve features, rotas, contratos e o adaptador de dados existentes.
- `packages/contracts/`, `pipelines/` e `datasets/samples/`: caminhos previstos; não presumir que arquivos já existam.

## Onde buscar contexto

- Quando a tarefa envolver arquitetura ou estado real → leia [docs/architecture.md](docs/architecture.md).
- Quando envolver decisão arquitetural → leia as ADRs em `docs/adr/`, começando por [0001](docs/adr/0001-monolito-modular.md), [0008](docs/adr/0008-review-por-agente.md) e [0009](docs/adr/0009-dinheiro-em-centavos.md).
- Quando envolver termos do domínio → leia [docs/glossary.md](docs/glossary.md).
- Quando envolver schema, CSV ou HTTP → leia [docs/modelagem-db.md](docs/modelagem-db.md), [docs/api-design.md](docs/api-design.md) e [docs/revisao-modelagem.md](docs/revisao-modelagem.md).
- Quando envolver regras/propostas da fundação → leia [docs/spec-tecnica.md](docs/spec-tecnica.md), observando as marcações de status.
- Quando envolver CI ou configuração do GitHub → leia [docs/github-setup.md](docs/github-setup.md).
- Para localizar outras referências → leia [docs/README.md](docs/README.md). Use caminhos comuns; importações com `@` pertencem somente aos arquivos CLAUDE.md.

## Fluxo de trabalho

- Uma Issue com objetivo, responsável e critérios de aceite por tarefa; branch curta `tipo/escopo-descricao` a partir da base combinada.
- Conventional Commits: `tipo(escopo): descrição`; escopos `api`, `web`, `pipelines`, `contracts`, `infra`, `docs`, `experiments`.
- PR com `Closes #N` quando concluir a Issue, verificação proporcional e documentação afetada atualizada.
- Se uma convenção mudar, atualize o `AGENTS.md` correspondente no mesmo PR. Mudança de contrato exige regeneração e aviso ao time.
- Checks aplicáveis, review por agente e uma aprovação humana antes do merge por squash. Não alegue que proteções ou integrações remotas estão configuradas sem evidência.
