# Valyra — contexto para agentes

## Produto

Inteligência financeira para planejar o orçamento e compreender o contexto dos investimentos.

## Regras invioláveis

- Sem data leakage: respeite published_at/as_of e as revisões conhecidas no corte; observação, publicação e ingestão são instantes distintos.
- O LLM explica evidências; nunca gera números, probabilidades ou causalidade sem suporte verificável.
- Somente dados sintéticos ou públicos com uso permitido; não versione .env, tokens, dados pessoais ou dumps.
- Dinheiro Finance usa centavos inteiros no banco, API e frontend, sufixo *_cents e conversão sem float. Precisão de Alpha/IA continua pendente.
- Não edite código gerado em packages/contracts/ ou apps/web/src/lib/api/; regenere pelo exportador correspondente.
- Sem ADR aceita para uma nova decisão arquitetural, pergunte ao humano. Solicitações explícitas já autorizadas orientam a tarefa; propostas não viram decisões aceitas automaticamente.
- Preserve branches, alterações locais, stashes e dados; commit/push/merge/publicação exigem autorização. Nunca apague volumes para validar uma entrega.
- Texto público usa Valyra; preserve nomes técnicos valyre/@valyre/web ao integrar a base web histórica. A landing independente se chama @valyra/landing.
- Comentários em português explicam o porquê de regras não evidentes. Não altere registros históricos para aparentar verificações atuais.
- CLAUDE.md contém apenas @AGENTS.md; não duplique conteúdo entre eles.

## Comandos

Na raiz, com GNU Make, uv e Docker Compose; instalação e Windows em [CONTRIBUTING.md](CONTRIBUTING.md).

| Área | Comandos disponíveis |
| --- | --- |
| Backend | make sync; make dev; make test; make test-domain; make lint; make migrate; make seed; make openapi |
| Landing | npm --prefix apps/landing ci --ignore-scripts; npm --prefix apps/landing run dev; npm --prefix apps/landing run check; npm --prefix apps/landing run build; npm --prefix apps/landing test |
| Aplicação web futura | npm run dev/check/format:check são comandos da base histórica, indisponíveis neste checkout |
| Documentação | python infra/check_docs.py |

Make aceita UV=/caminho/uv e ENV_FILE=/caminho/configuração. Usa .env existente ou .env.example, sem sobrescrever configuração. Suíte de banco exige TEST_DATABASE_URL no processo e banco dedicado. make test-domain não conecta ao banco.

## Mapa de pastas

- services/api/: [contexto de backend](services/api/AGENTS.md), core HTTP, Finance (ORM, domínio CSV, importação e consultas HTTP), Alembic e testes.
- apps/landing/: [página estática isolada](apps/landing/README.md), apontando inicialmente ao repositório oficial.
- packages/contracts/: OpenAPI gerado; infra/postgres/init/: criação idempotente do banco de testes.
- docs/: arquitetura, glossário, ADRs e specs. .github/: CI, templates e revisão.
- datasets/samples/: dados sintéticos de demonstração (CSV de transações), nunca dados reais.
- apps/web, pipelines e experiments são caminhos planejados, não funcionalidades implementadas.

## Onde buscar contexto

- Quando a tarefa envolver arquitetura/estado real → leia [docs/architecture.md](docs/architecture.md).
- Quando envolver decisões → leia [ADR-0001](docs/adr/0001-monolito-modular.md), [ADR-0008](docs/adr/0008-review-por-agente.md), [ADR-0009](docs/adr/0009-dinheiro-em-centavos.md) e [template](docs/adr/0000-template.md).
- Quando envolver termos → leia [docs/glossary.md](docs/glossary.md).
- Quando envolver schema, CSV ou HTTP → leia [docs/modelagem-db.md](docs/modelagem-db.md), [docs/api-design.md](docs/api-design.md), [docs/revisao-modelagem.md](docs/revisao-modelagem.md).
- Quando envolver fundação e propostas → leia [docs/spec-tecnica.md](docs/spec-tecnica.md).
- Quando envolver CI/revisão/proteções → leia [docs/github-setup.md](docs/github-setup.md).
- Para localizar referências → leia [docs/README.md](docs/README.md). Use caminhos comuns, sem imports @.

## Fluxo de trabalho

- Branch curta tipo/escopo-descricao a partir da base combinada; confira status e dependências primeiro.
- Conventional Commits: tipo(escopo): descrição; escopos api, web, pipelines, contracts, infra, docs, experiments. Registre assistência por ferramenta e atribua trabalho reaproveitado.
- PR com Closes #N ao concluir, ou Refs #N quando houver pendências/for solicitado não fechar a issue.
- Mudança de convenção atualiza AGENTS.md no mesmo PR; mudança de contrato regenera OpenAPI e avisa consumidores.
- Checks aplicáveis e uma aprovação humana antes de merge por squash. Review por agente não substitui a aprovação humana nem comprova execução de testes.
