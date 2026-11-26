# Arquitetura do Valyra

Visão operacional da branch integrada. Histórico e propostas permanecem nos três specs abaixo; não comprovam funcionalidades disponíveis.

```text
apps/web — React/TypeScript: landing estática em / e aplicação Finance em #/app
                         | /api/v1/finance (importação de CSV e consultas)
services/api — FastAPI único: /health, Finance (8 operações no total) e OpenAPI
core · finance (router → service → domínio CSV | repository → ORM)
        | PostgreSQL 18
        + pipelines → DuckDB/Parquet/fontes públicas (planejado)
        + alpha · alerts · ai / provedor LLM (planejado)
```

## Estado efetivo

- Core: create_app, CORS por origem configurada, erros AppError/validação, demo, paginação, operationIds, /health com SELECT 1 (200/503) e exportador OpenAPI. Fundação mínima das #8/#9 adicionada para viabilizar #11/#12.
- Persistência Finance do PR #17: User (core), Account, ImportBatch, ImportRejection, Category, Transaction, uma Base, migração 0001_finance_inicial e seed idempotente. Dados existentes são preservados e conflitos do seed revertem suas inserções.
- Domínio CSV do PR #19: UTF-8/BOM/CRLF, Decimal/centavos/BIGINT, rejeições, linhas físicas e registros multilinha, SHA-256 por ocorrência e categorias por regras/sinal. Biblioteca padrão, sem I/O externo, banco, HTTP ou IA.
- Importação Finance da Issue #14: `POST /api/v1/finance/accounts/{account_id}/import-batches` (multipart `file`, até 1 MiB) e consulta de lotes em `GET /api/v1/finance/import-batches` e `/import-batches/{id}`. O service grava lote, rejeições e transações em uma única transação, com `ON CONFLICT (account_id, row_hash) DO NOTHING`; falha técnica desfaz tudo. Contas de outro usuário respondem como inexistentes. Exemplo sintético em `datasets/samples/transactions_demo.csv`.
- Consultas Finance da Issue #15: `GET /api/v1/finance/accounts`, `PATCH /api/v1/finance/accounts/{id}` (nome, saldo de referência em centavos e data, todos omissíveis), `GET /api/v1/finance/transactions` (filtros `account_id`, `date_from`, `date_to`, `category_id`; data decrescente) e `GET /api/v1/finance/categories` (por `kind` e `name`). Todas paginadas e restritas ao usuário demo. Campos ainda não calculados (`is_recurring`, anomalia) não são expostos.
- Correção de categoria da Issue #42: `PATCH /api/v1/finance/transactions/{id}` com `{category_id}`; grava `category_source = user` e preserva a sugestão original (`predicted_category_id`, `category_confidence`). Transação de outro usuário responde 404 como inexistente; tipo da categoria precisa corresponder ao sinal.
- Landing do PR #18, movida para apps/web no PR #64: números sintéticos identificados; CTA aponta ao GitHub. O destino futuro HTTPS é configurado no build, não pelo visitante.
- Aplicação Finance em apps/web (#/app): visão geral de contas, transações com filtros e correção de categoria, importação de CSV com rejeições. Consome somente as 8 operações Finance e /health, com tipos gerados de packages/contracts/openapi.json em src/lib/api/. Valores em centavos formatados sem float. Usuário demo, sem login.
- CI: PostgreSQL/Compose, API consolidada e workflow independente da landing. Claude preparado; configuração externa e primeiro review são verificação separada. Resultados desta integração no PR e em [integração](integracao-11-12.md).
- Não implementados no Finance: resumo, projeção de saldo, detecção de recorrência e de gastos atípicos. Fora do Finance: projeções, categorização ML, sinais, replay, pipelines, DuckDB, alertas e IA.

## Fronteiras

Um backend modular, conforme [ADR-0001](adr/0001-monolito-modular.md). Router → service → domain/repository, verificado pelo contrato de camadas; core não importa Finance; domínio não importa banco/HTTP/IA. Contratos import-linter oficiais estão no pyproject da API. FKs cruzadas não autorizam acesso a repositories de outro domínio.

Dinheiro Finance usa centavos inteiros ([ADR-0009](adr/0009-dinheiro-em-centavos.md)); datas de negócio são DATE e instantes UTC. Conta tem saldo de referência (fechamento), não cálculo realizado diário; convenções de cálculo na [ADR-0010](adr/0010-calculos-finance.md). Valores BIGINT além da precisão segura do JavaScript exigem alinhamento antes do frontend consumir esses extremos.

No desenho futuro, pipelines escrevem sinais append-only e API apenas lê; observação/publicação/ingestão são tempos distintos. as_of seleciona somente revisões publicadas no corte. LLM explica evidências, nunca calcula ou inventa números. Esses mecanismos ainda não existem no código.

## Frontend e remoção

A landing não depende da API; a aplicação em #/app é carregada sob demanda e chama a API pela mesma origem (proxy do Vite) ou por VITE_API_URL. Execução e configuração em [apps/web/README.md](../apps/web/README.md). A [arquitetura inicial do frontend na branch histórica](https://github.com/UaiScript/valyra-hackbrasil-2026/blob/9c2a87c2e992f83db7c84f37e0e0737ae16e06f4/docs/arquitetura-inicial.md) ainda não é um arquivo local. Não recuperar essa base ou renomear valyre/@valyre/web sem tarefa própria.

## Histórico das decisões

- [Fundação técnica](spec-tecnica.md).
- [Modelagem](modelagem-db.md), distinguindo autorizado e proposto.
- [Contrato Finance/API](api-design.md), incluindo operações HTTP futuras.
- [Registro da migração/seed](revisao-modelagem.md).

Hospedagem, LLM, licença de cotações, precisão Alpha/IA e persistência de falhas de importação continuam pendências registradas. Não inferir aprovação de todo o desenho a partir das ADRs específicas.
