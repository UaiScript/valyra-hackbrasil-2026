# Arquitetura do Valyra

Referência operacional da arquitetura confirmada pelo usuário: **monorepo com backend FastAPI único, modular por domínio**. A proposta anterior de três microsserviços não orienta esta implementação. Consulte a [ADR-0001](adr/0001-monolito-modular.md).

## Visão do sistema

```text
apps/web — React / TypeScript                   [a integrar]
                    |
             HTTPS /api/v1
                    |
services/api — FastAPI único                    [a implementar]
core · finance · alpha · alerts · ai
        |            |             |
    PostgreSQL   DuckDB/Parquet  Provedor LLM    [a definir]
        ^            ^
        +-- pipelines/ -- fontes externas      [a implementar]
```

PostgreSQL já é executável via Compose. As demais conexões representam o desenho alvo; nenhum serviço de aplicação foi criado por estes documentos. DuckDB é embarcado, Parquet é formato de arquivo; não são novos microsserviços.

## Estado deste checkout

| Parte | Estado |
| --- | --- |
| PostgreSQL 18 | Compose com volume persistente, porta em loopback e health check |
| CI `postgres` | Valida configuração, inicialização e consulta autenticada; execução anterior confirmada pelo usuário |
| CI `api` | Preparada para as interfaces das Issues #8–#10; falha explicitamente se faltarem API, Makefile, lockfile ou migrations |
| Contexto, ADRs, templates e revisão Claude | Arquivos definidos nesta entrega; configuração remota/primeiro comentário ainda precisam de validação |
| API, models, tabelas de negócio, Alembic, seed | Ainda não implementados; `services/api/` contém instruções |
| Frontend | Não integrado neste checkout; há protótipo em outra branch |
| Pipeline econômico, DuckDB/Parquet e LLM | Ainda não implementados; fonte/provedor e detalhes analíticos pendentes |

## Backend e dados previstos

| Módulo | Responsabilidade e tabelas previstas |
| --- | --- |
| `core` | Configuração, erros, sessão de banco, demo; `users` |
| `finance` | Contas, CSV, categorização e cálculos; `accounts`, `import_batches`, `import_rejections`, `categories`, `transactions` |
| `alpha` | Fontes, versões de sinais e ativos; `sources`, `signals`, `signal_sectors`, `sectors`, `assets`, `asset_sector_exposures`, `watchlist_items`, `holdings` |
| `alerts` | Alertas persistidos por template; `alerts` |
| `ai` | Explicações e evidências; `conversations`, `messages`, `message_evidences` |

São **tabelas do desenho**, não tabelas já criadas. A primeira migração planejada cobre apenas `users` e as cinco tabelas Finance. A adição do módulo interno `alerts` vem da modelagem em revisão; não cria serviço independente.

Dependência interna: router → service → domain/repository. Entre módulos, casos de uso acessam o service público; core não depende dos domínios. FKs cruzadas não autorizam repositories cruzados. Veja [instruções da API](../services/api/AGENTS.md).

Dinheiro Finance é BIGINT em centavos e inteiro JSON; [ADR-0009](adr/0009-dinheiro-em-centavos.md). Timestamps são UTC; datas de negócio são civis. A precisão de preço médio e evidências monetárias genéricas de Alpha/IA exige alinhamento específico.

No desenho, pipelines inserem sinais/relações, e a API apenas os lê. Sinais são append-only: revisões do mesmo `signal_key` são linhas distintas. Replay considera somente publicações e revisões disponíveis em `as_of`. Triggers, papéis e consulta temporal ainda serão implementados. A IA explica evidências e valores calculados, com provedor substituível; pode começar por templates determinísticos.

## Frontend

A referência existente é o [detalhe do frontend em `willian/base-do-projeto`](https://github.com/UaiScript/valyra-hackbrasil-2026/blob/willian/base-do-projeto/docs/arquitetura-inicial.md), observado na referência Git local. Esse arquivo ainda não está neste checkout; integrar a base antes de atualizar seu documento local, preservando histórico e trabalho dos colegas.

Ao integrar, preservar nomes técnicos `valyre`/`@valyre/web`, centavos inteiros, features, rotas e adaptador de dados. Os comandos npm já definidos nessa base não comprovam disponibilidade aqui. Não adicionar um job web até os manifestos e comandos reais estarem integrados.

## Histórico das decisões e desenho detalhado

- [Fundação técnica](spec-tecnica.md): limites e organização do monorepo, regras e propostas de fluxo.
- [Modelagem PostgreSQL](modelagem-db.md): entidades, revisões e integridade, distinguindo registrado e proposto.
- [Design da API Finance](api-design.md): contratos registrados de dados, CSV e HTTP.
- [Preparação de migrations/seed](revisao-modelagem.md): dependências e lacunas ainda abertas.

Esses documentos continuam como histórico dos acordos e propostas; as ADRs aceitas registram escolhas específicas. Hospedagem, provedor LLM, licença de cotações e replay permanecem pendentes. Não ampliar este status para alegar produto, CI completa ou deploy concluídos.
