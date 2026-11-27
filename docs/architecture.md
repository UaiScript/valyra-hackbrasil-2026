# Arquitetura do Valyra

Visão operacional da branch integrada. Histórico e propostas permanecem nos três specs abaixo; não comprovam funcionalidades disponíveis.

```text
apps/web — React/TypeScript: landing estática em / e aplicação Finance em #/app
                         | /api/v1/finance (importação, consultas, resumo, projeção, orçamento) · /api/v1/alerts · /api/v1/ai
services/api — FastAPI único: /health, Finance (13 operações), Alerts (2 operações), IA (1 operação) e OpenAPI
core · finance (router → service → domínio CSV | analytics | repository → ORM)
     · alerts (router → service → domínio | repository → ORM; Finance chama só o service)
        | PostgreSQL 18
        + pipelines → DuckDB/Parquet/fontes públicas (planejado)
        + ai / router → service → cliente Gemini/OpenAI | domínio → schemas
                + Finance via service público (referência e movimentações)
        + alpha (planejado)
```

## Estado efetivo

- Core: create_app, CORS por origem configurada, erros AppError/validação, demo, paginação, operationIds, /health com SELECT 1 (200/503) e exportador OpenAPI. Fundação mínima das #8/#9 adicionada para viabilizar #11/#12.
- Persistência Finance do PR #17: User (core), Account, ImportBatch, ImportRejection, Category, Transaction, uma Base, migração 0001_finance_inicial e seed idempotente. Dados existentes são preservados e conflitos do seed revertem suas inserções.
- Domínio CSV do PR #19: UTF-8/BOM/CRLF, Decimal/centavos/BIGINT, rejeições, linhas físicas e registros multilinha, SHA-256 por ocorrência e categorias por regras/sinal. Biblioteca padrão, sem I/O externo, banco, HTTP ou IA.
- Importação Finance da Issue #14: `POST /api/v1/finance/accounts/{account_id}/import-batches` (multipart `file`, até 1 MiB) e consulta de lotes em `GET /api/v1/finance/import-batches` e `/import-batches/{id}`. O service grava lote, rejeições e transações em uma única transação, com `ON CONFLICT (account_id, row_hash) DO NOTHING`; falha técnica desfaz tudo. Contas de outro usuário respondem como inexistentes. Exemplo sintético em `datasets/samples/transactions_demo.csv`.
- Consultas Finance da Issue #15: `GET /api/v1/finance/accounts`, `PATCH /api/v1/finance/accounts/{id}` (nome, saldo de referência em centavos e data, todos omissíveis), `GET /api/v1/finance/transactions` (filtros `account_id`, `date_from`, `date_to`, `category_id`; data decrescente) e `GET /api/v1/finance/categories` (por `kind` e `name`). Todas paginadas e restritas ao usuário demo. Campos ainda não calculados (`is_recurring`, anomalia) não são expostos.
- Correção de categoria da Issue #42: `PATCH /api/v1/finance/transactions/{id}` com `{category_id}`; grava `category_source = user` e preserva a sugestão original (`predicted_category_id`, `category_confidence`). Transação de outro usuário responde 404 como inexistente; tipo da categoria precisa corresponder ao sinal.
- Cálculos Finance das Issues #43–#46 (ADR-0010): saldo realizado e resumo mensal (`GET /api/v1/finance/summary`), recorrência e gasto atípico recalculados na importação e na correção de categoria, e projeção de caixa sob demanda (`GET /api/v1/finance/accounts/{id}/projection`). Funções puras em `finance/analytics.py`, sem banco, HTTP ou relógio.
- Alertas da Issue #47: módulo `alerts/` com a tabela `alerts` (migração `0002_alerts`, só `cash_pressure`), `GET /api/v1/alerts` e `PATCH /api/v1/alerts/{id}`. A importação cria, na mesma transação, um alerta de pressão de caixa por conta por mês quando a projeção de 30 dias fica negativa, e o `POST` devolve `alerts_created`. Texto por template, sem LLM.
- Orçamento por categoria: tabela `budgets` (migração `0003_budgets`), `GET /api/v1/finance/budgets`, `PUT` e `DELETE /api/v1/finance/budgets/{category_id}`. Um limite mensal em centavos por categoria de saída; o consumo do mês é calculado na leitura com o mesmo recorte do resumo mensal (só realizado até hoje), e o status vira `warning` a partir de 80% e `over` acima de 100%.
- Landing do PR #18, movida para apps/web no PR #64: números sintéticos identificados; botões "Abrir demonstração" levam ao app em #/app e os links de repositório ao GitHub. O destino futuro HTTPS é configurado no build, não pelo visitante.
- Aplicação Finance em apps/web (#/app): visão geral com saldo realizado e projeção de 30 dias, resumo mensal por categoria, projeção de caixa, transações com filtros, selos de recorrente/atípico e correção de categoria, alertas de pressão de caixa e importação de CSV com rejeições. Consome as 12 operações de Finance e Alerts e /health, com tipos gerados de packages/contracts/openapi.json em src/lib/api/. Valores em centavos formatados sem float. Usuário demo, sem login.
- CI: PostgreSQL/Compose, API consolidada e workflow independente da landing. Claude preparado; configuração externa e primeiro review são verificação separada. Resultados desta integração no PR e em [integração](integracao-11-12.md).
- IA: cliente Gemini com saída estruturada e parsing estrito, timeout e tentativas limitadas; testes com HTTP simulado. Fallback GPT-4o-mini ativo quando `OPENAI_API_KEY` estiver configurada; controle de gasto pelo hard spend limit do painel da OpenAI ([ADR-0002](adr/0002-provedor-llm.md)). Contratos tipados e resolução de citações da [ADR-0011](adr/0011-contrato-evidencias-ia.md): o LLM devolve IDs e o servidor recupera dados originais. O domínio revalida metadados e confere os literais numéricos contra as citações ([regras e limites](ai-validation.md)); não certifica semântica ou causalidade. O [serviço](ai-service.md) autoriza via Finance público, monta saldo de referência e até vinte movimentações, executa o cliente e valida a resposta. Contexto/cliente substituíveis nos testes; dados ausentes geram limitações e contexto vazio não chama provedor. A rota HTTP está descrita abaixo; persistência de conversas permanece pendente. Configuração no [guia](ai-client.md).
- HTTP IA: `POST /api/v1/ai/explain`, operação `ai_explain`, recebe somente pergunta/conta, usa a identidade demo e devolve explicação validada com evidências originais. Erros conhecidos usam o envelope existente, declarado no OpenAPI. Jornada sintética com SDK/transporte simulado e integração Finance real com PostgreSQL dedicado; smoke com provedor real depende de chave local. Contrato e roteiro em [ai-http.md](ai-http.md).
- Não implementados: categorização ML, sinais, replay, pipelines, DuckDB, alertas `market_signal` (com o Alpha) e integração de resumo/projeção/orçamento/Alpha ao serviço IA.

## Fronteiras

Um backend modular, conforme [ADR-0001](adr/0001-monolito-modular.md). Router → service → domain/repository, verificado pelo contrato de camadas; core não importa Finance nem Alerts; Alerts não importa Finance e Finance usa Alerts só pelo service; domínio não importa banco/HTTP/IA. Contratos import-linter oficiais estão no pyproject da API. FKs cruzadas não autorizam acesso a repositories de outro domínio.

Dinheiro Finance usa centavos inteiros ([ADR-0009](adr/0009-dinheiro-em-centavos.md)); datas de negócio são DATE e instantes UTC. Conta tem saldo de referência (fechamento), não cálculo realizado diário; convenções de cálculo na [ADR-0010](adr/0010-calculos-finance.md). Valores BIGINT além da precisão segura do JavaScript exigem alinhamento antes do frontend consumir esses extremos.

No desenho futuro, pipelines escrevem sinais append-only e API apenas lê; observação/publicação/ingestão são tempos distintos. as_of seleciona somente revisões publicadas no corte. LLM explica evidências, nunca calcula ou inventa números. O contexto IA já recusa metadados fora do corte. O domínio IA também confere literais numéricos e referências contra um snapshot revalidado. O serviço IA já autoriza a conta via Finance e usa corte corrente do servidor; consulta/seleção de revisões Alpha continua pendente do respectivo serviço.

## Frontend e remoção

A landing não depende da API; a aplicação em #/app é carregada sob demanda e chama a API pela mesma origem (proxy do Vite) ou por VITE_API_URL. Execução e configuração em [apps/web/README.md](../apps/web/README.md). A [arquitetura inicial do frontend na branch histórica](https://github.com/UaiScript/valyra-hackbrasil-2026/blob/9c2a87c2e992f83db7c84f37e0e0737ae16e06f4/docs/arquitetura-inicial.md) ainda não é um arquivo local. Não recuperar essa base ou renomear valyre/@valyre/web sem tarefa própria.

## Histórico das decisões

- [Fundação técnica](spec-tecnica.md).
- [Modelagem](modelagem-db.md), distinguindo autorizado e proposto.
- [Contrato Finance/API](api-design.md), incluindo operações HTTP futuras.
- [Registro da migração/seed](revisao-modelagem.md).

Hospedagem, configuração do limite externo para fallback LLM, licença de cotações e precisão monetária Alpha e persistência de falhas de importação continuam pendências registradas. Não inferir aprovação de todo o desenho a partir das ADRs específicas.
