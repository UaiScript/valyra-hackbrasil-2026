# Arquitetura do Valyra

Visão operacional da branch integrada. Histórico e propostas permanecem nos três specs abaixo; não comprovam funcionalidades disponíveis.

```text
apps/landing — React/TypeScript, estática → repositório oficial (futura aplicação configurável)
apps/web — aplicação React planejada
                         | /api/v1 (Finance HTTP ainda planejado)
services/api — FastAPI único: /health e OpenAPI
core · finance (ORM + domínio CSV)
        | PostgreSQL 18
        + pipelines → DuckDB/Parquet/fontes públicas (planejado)
        + alpha · alerts · ai / provedor LLM (planejado)
```

## Estado efetivo

- Core: create_app, CORS por origem configurada, erros AppError/validação, demo, paginação, operationIds, /health com SELECT 1 (200/503) e exportador OpenAPI. Fundação mínima das #8/#9 adicionada para viabilizar #11/#12.
- Persistência Finance do PR #17: User (core), Account, ImportBatch, ImportRejection, Category, Transaction, uma Base, migração 0001_finance_inicial e seed idempotente. Dados existentes são preservados e conflitos do seed revertem suas inserções.
- Domínio CSV do PR #19: UTF-8/BOM/CRLF, Decimal/centavos/BIGINT, rejeições, linhas físicas e registros multilinha, SHA-256 por ocorrência e categorias por regras/sinal. Biblioteca padrão, sem I/O externo, banco, HTTP ou IA. Ainda não há importação persistida ou endpoints Finance.
- Landing do PR #18: pacote independente apps/landing com build e testes próprios; números sintéticos identificados. CTA aponta ao GitHub. O destino futuro HTTPS é configurado no build, não pelo visitante.
- CI: PostgreSQL/Compose, API consolidada e workflow independente da landing. Claude preparado; configuração externa e primeiro review são verificação separada. Resultados desta integração no PR e em [integração](integracao-11-12.md).
- Não implementados: aplicação apps/web, endpoints #14/#15, projeções, categorização ML, sinais, replay, pipelines, DuckDB, alertas e IA.

## Fronteiras

Um backend modular, conforme [ADR-0001](adr/0001-monolito-modular.md). Router → service → domain/repository; core não importa Finance; domínio não importa banco/HTTP/IA. Contratos import-linter oficiais estão no pyproject da API. FKs cruzadas não autorizam acesso a repositories de outro domínio.

Dinheiro Finance usa centavos inteiros ([ADR-0009](adr/0009-dinheiro-em-centavos.md)); datas de negócio são DATE e instantes UTC. Conta tem saldo de referência, não cálculo realizado diário. Valores BIGINT além da precisão segura do JavaScript exigem alinhamento antes do frontend consumir esses extremos.

No desenho futuro, pipelines escrevem sinais append-only e API apenas lê; observação/publicação/ingestão são tempos distintos. as_of seleciona somente revisões publicadas no corte. LLM explica evidências, nunca calcula ou inventa números. Esses mecanismos ainda não existem no código.

## Frontend e remoção

A landing não ocupa apps/web nem depende da API. Execução, configuração e remoção estão em [apps/landing/README.md](../apps/landing/README.md). A [arquitetura inicial do frontend na branch histórica](https://github.com/UaiScript/valyra-hackbrasil-2026/blob/9c2a87c2e992f83db7c84f37e0e0737ae16e06f4/docs/arquitetura-inicial.md) ainda não é um arquivo local. Não recuperar essa base ou renomear valyre/@valyre/web sem tarefa própria.

## Histórico das decisões

- [Fundação técnica](spec-tecnica.md).
- [Modelagem](modelagem-db.md), distinguindo autorizado e proposto.
- [Contrato Finance/API](api-design.md), incluindo operações HTTP futuras.
- [Registro da migração/seed](revisao-modelagem.md).

Hospedagem, LLM, licença de cotações, precisão Alpha/IA e persistência de falhas de importação continuam pendências registradas. Não inferir aprovação de todo o desenho a partir das ADRs específicas.
