# Modelagem de dados do Postgres — Design

| Campo | Valor |
|---|---|
| Status | Em revisão pelo time |
| Data | 07/11/2026 |
| Base | Documento de Alinhamento v0.3 e `2026-11-06-fundacao-tecnica-design.md` |
| Escopo | Schema do PostgreSQL: dados do app e tabela `signals` |
| Fora de escopo | Séries históricas em DuckDB/Parquet (spec próprio), modelos preditivos, telas |

## Como ler este documento

O conteúdo foi construído no brainstorming de 07/11 e está aberto à revisão do time. Itens marcados como **[Altera fundação]** mudam algo já definido no spec de fundação técnica; a seção 10 lista esses impactos.

---

## 1. Premissas do MVP

- **Um único usuário demo, sem login.** Mesmo assim existe a tabela `users` e as tabelas dependentes têm `user_id`, para não exigir migração se houver login no futuro.
- **Transações entram por upload de CSV** feito pelo usuário na demo.
- **Categorização automática** (regras/ML) com correção pelo usuário.
- **Alertas persistidos**, com status novo/lido.
- **Sinais ligados a ativos por setor**, com a justificativa guardada na relação ativo ↔ setor.
- **Watchlist com posições** (quantidade e preço médio).
- **Abordagem de histórico:** tabelas do app relacionais e atualizáveis; `signals` **somente inserção**, com revisões como linhas novas.

Alternativas descartadas para o histórico:

- `signals` atualizável com histórico em tabela separada: duas fontes da verdade e Replay dependente de reconstrução.
- Event sourcing geral: complexidade alta sem exigência do produto.

---

## 2. Diagrama entidade-relacionamento

O GitHub renderiza o diagrama abaixo automaticamente.

```mermaid
erDiagram
    users ||--o{ accounts : possui
    users ||--o{ watchlist_items : acompanha
    users ||--o{ alerts : recebe
    users ||--o{ conversations : conversa

    accounts ||--o{ import_batches : recebe
    accounts ||--o{ transactions : contem
    import_batches ||--o{ transactions : origina
    import_batches ||--o{ import_rejections : rejeita
    categories ||--o{ transactions : "categoria atual"
    categories ||--o{ transactions : "categoria prevista"

    assets ||--o{ watchlist_items : "e acompanhado"
    watchlist_items ||--o| holdings : "pode ter posicao"
    assets ||--o{ asset_sector_exposures : "exposto a"
    sectors ||--o{ asset_sector_exposures : agrupa

    sources ||--o{ signals : publica
    signals ||--o{ signal_sectors : afeta
    sectors ||--o{ signal_sectors : "e afetado"

    accounts |o--o{ alerts : "caixa"
    signals |o--o{ alerts : "mercado"
    assets |o--o{ alerts : "mercado"

    conversations ||--o{ messages : contem
    alerts |o--o{ messages : "explicado em"
    messages ||--o{ message_evidences : cita
    signals |o--o{ message_evidences : "evidencia"

    users {
        uuid id PK
        varchar name
        timestamptz created_at
    }
    accounts {
        uuid id PK
        uuid user_id FK
        varchar name
        numeric balance
        date balance_as_of
        timestamptz created_at
        timestamptz updated_at
    }
    import_batches {
        uuid id PK
        uuid account_id FK
        varchar file_name
        varchar status
        int rows_total
        int rows_imported
        int rows_duplicated
        int rows_rejected
        timestamptz created_at
        timestamptz completed_at
    }
    import_rejections {
        uuid id PK
        uuid import_batch_id FK
        int line_number
        varchar reason
        text raw_line
    }
    categories {
        uuid id PK
        varchar slug UK
        varchar name
        varchar kind
        timestamptz created_at
    }
    transactions {
        uuid id PK
        uuid account_id FK
        uuid import_batch_id FK
        date date
        text description
        numeric amount
        uuid category_id FK
        uuid predicted_category_id FK
        varchar category_source
        numeric category_confidence
        boolean is_recurring
        varchar recurrence_key
        numeric anomaly_score
        varchar row_hash
        timestamptz created_at
        timestamptz updated_at
    }
    assets {
        uuid id PK
        varchar ticker UK
        varchar name
        varchar asset_type
        timestamptz created_at
    }
    watchlist_items {
        uuid id PK
        uuid user_id FK
        uuid asset_id FK
        timestamptz created_at
    }
    holdings {
        uuid id PK
        uuid watchlist_item_id FK
        numeric quantity
        numeric average_price
        timestamptz created_at
        timestamptz updated_at
    }
    sectors {
        uuid id PK
        varchar slug UK
        varchar name
    }
    asset_sector_exposures {
        uuid asset_id PK
        uuid sector_id PK
        text rationale
        varchar source_url
    }
    sources {
        uuid id PK
        varchar slug UK
        varchar name
        varchar url
        varchar license
        timestamptz created_at
    }
    signals {
        uuid id PK
        varchar signal_key
        int revision_id
        uuid source_id FK
        varchar kind
        varchar title
        text summary
        date observation_date
        numeric value
        varchar unit
        numeric confidence
        jsonb payload
        timestamptz published_at
        boolean published_at_estimated
        timestamptz ingested_at
        varchar source_url
        timestamptz created_at
    }
    signal_sectors {
        uuid signal_id PK
        uuid sector_id PK
    }
    alerts {
        uuid id PK
        uuid user_id FK
        varchar kind
        varchar severity
        varchar status
        varchar title
        text message
        jsonb evidence
        uuid account_id FK
        uuid signal_id FK
        uuid asset_id FK
        varchar dedup_key
        timestamptz created_at
        timestamptz read_at
    }
    conversations {
        uuid id PK
        uuid user_id FK
        varchar title
        timestamptz created_at
        timestamptz updated_at
    }
    messages {
        uuid id PK
        uuid conversation_id FK
        varchar role
        text content
        varchar status
        text rejection_reason
        varchar uncertainty
        text[] limitations
        timestamptz as_of
        uuid alert_id FK
        varchar model
        varchar prompt_version
        int tokens_in
        int tokens_out
        timestamptz created_at
    }
    message_evidences {
        uuid id PK
        uuid message_id FK
        int position
        varchar label
        varchar value
        varchar unit
        varchar source_url
        timestamptz published_at
        uuid signal_id FK
    }
```

---

## 3. Convenções gerais

### 3.1 Identificadores

- Chave primária `UUID` com default `gen_random_uuid()`.
- Motivo: repositório e demo públicos (sem IDs sequenciais expostos) e escrita por API e pipelines sem disputa de sequência.

### 3.2 Nomes

Configurados uma vez na `MetaData` do SQLAlchemy:

- Tabelas em `snake_case` no plural; chaves estrangeiras `<entidade>_id`.
- Constraints com prefixos fixos: `pk_`, `fk_`, `uq_`, `ix_`, `ck_`.

```python
NAMING_CONVENTION = {
    "pk": "pk_%(table_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
}
```

### 3.3 Tipos

| Uso | Tipo | Regra |
|---|---|---|
| Dinheiro | `NUMERIC(14,2)` | Sempre BRL, nunca `float` |
| Valor de transação | `NUMERIC(14,2)` | Negativo = saída, positivo = entrada; `CHECK (amount <> 0)` |
| Quantidade de ativo | `NUMERIC(18,6)` | `CHECK (quantity > 0)` |
| Scores e confiança | `NUMERIC(4,3)` / `NUMERIC(5,4)` | Entre 0 e 1 |
| Data de negócio | `DATE` | Sem fuso |
| Instante | `TIMESTAMPTZ` | Gravado em UTC |
| Enum | `VARCHAR` + `CHECK` | Não usar enum nativo do Postgres |
| Estrutura variável | `JSONB` | Somente `alerts.evidence` e `signals.payload` |

### 3.4 Colunas padrão

- Toda tabela tem `created_at`; tabelas atualizáveis têm `updated_at`.
- `signals` não tem `updated_at`.
- Sem soft delete.

### 3.5 Donos das tabelas

| Módulo | Tabelas |
|---|---|
| `core/` | `users` |
| `finance/` | `accounts`, `import_batches`, `import_rejections`, `categories`, `transactions` |
| `alpha/` | `sources`, `signals`, `signal_sectors`, `sectors`, `assets`, `asset_sector_exposures`, `watchlist_items`, `holdings` |
| `alerts/` **[Altera fundação]** | `alerts` |
| `ai/` | `conversations`, `messages`, `message_evidences` |

Chaves estrangeiras entre módulos são permitidas no banco. Em código, o acesso continua só via `service` do outro módulo.

---

## 4. Finance

### 4.1 Tabelas

**`users`** (`core`): `id`, `name`, `created_at`.

**`accounts`**

| Coluna | Tipo | Observação |
|---|---|---|
| `id` | UUID | PK |
| `user_id` | UUID | FK `users` |
| `name` | VARCHAR | Ex.: "Conta principal" |
| `balance` | NUMERIC(14,2) | Informado pelo usuário |
| `balance_as_of` | DATE | Data em que `balance` valia |
| `created_at`, `updated_at` | TIMESTAMPTZ | |

**`import_batches`**

| Coluna | Tipo | Observação |
|---|---|---|
| `id` | UUID | PK |
| `account_id` | UUID | FK `accounts`; conta escolhida no upload |
| `file_name` | VARCHAR | |
| `status` | VARCHAR | `processing` \| `completed` \| `failed` |
| `rows_total`, `rows_imported`, `rows_duplicated`, `rows_rejected` | INT | |
| `created_at` | TIMESTAMPTZ | |
| `completed_at` | TIMESTAMPTZ NULL | |

**`import_rejections`**: `id`, `import_batch_id` (FK), `line_number`, `reason`, `raw_line`.

**`categories`**: `id`, `slug` (UNIQUE), `name`, `kind` (`expense` \| `income`), `created_at`. Lista fixa criada no seed.

**`transactions`**

| Coluna | Tipo | Observação |
|---|---|---|
| `id` | UUID | PK |
| `account_id` | UUID | FK `accounts` |
| `import_batch_id` | UUID | FK `import_batches` |
| `date` | DATE | |
| `description` | TEXT | |
| `amount` | NUMERIC(14,2) | Com sinal; `<> 0` |
| `category_id` | UUID | FK `categories`; categoria exibida |
| `predicted_category_id` | UUID | FK `categories`; sugestão original, preservada |
| `category_source` | VARCHAR | `rule` \| `model` \| `user` |
| `category_confidence` | NUMERIC(4,3) NULL | Confiança da sugestão |
| `is_recurring` | BOOLEAN | |
| `recurrence_key` | VARCHAR NULL | Descrição normalizada que agrupa recorrências |
| `anomaly_score` | NUMERIC(5,4) NULL | Recalculado a cada importação |
| `row_hash` | VARCHAR | Deduplicação |
| `created_at`, `updated_at` | TIMESTAMPTZ | |

Constraints e índices:

- `UNIQUE (account_id, row_hash)`
- `CHECK (amount <> 0)`
- `CHECK (category_source IN ('rule','model','user'))`
- Índices: `(account_id, date)`, `(category_id)`

### 4.2 Regras

- **Saldo de hoje** = `accounts.balance` + soma de `transactions.amount` com `date > balance_as_of`.
- **Projeção de 30 dias** = saldo de hoje + recorrentes previstas + estimativa de gastos variáveis. Calculada em `finance/domain.py`; não é armazenada.
- **Dashboard** (gasto por categoria, tendência, atípicos) é calculado a partir de `transactions` e `categories`; sem tabelas próprias.
- **Deduplicação**: `row_hash` = hash de `account_id` + `date` + `amount` + descrição normalizada + **índice da ocorrência** daquela combinação no arquivo. Duas transações idênticas no mesmo dia são aceitas; reenviar o CSV não duplica.
- **Correção de categoria** pelo usuário altera `category_id` e grava `category_source = 'user'`; `predicted_category_id` nunca muda. Isso permite medir a acurácia da categorização.
- **Regras de categorização** ficam no código (`finance/domain.py`), não em tabela.
- **Categorias** não são criadas pelo usuário.
- **Gasto atípico**: o dashboard filtra `anomaly_score` acima de um limiar definido no código.

---

## 5. Alpha

### 5.1 Fontes e sinais

**`sources`**: `id`, `slug` (UNIQUE, ex.: `conab`), `name`, `url`, `license`, `created_at`.

**`signals`** (somente inserção)

| Coluna | Tipo | Observação |
|---|---|---|
| `id` | UUID | PK |
| `signal_key` | VARCHAR | Identidade lógica, ex.: `conab:soja:mt:2025-26:produtividade` **[Altera fundação]** |
| `revision_id` | INT | 1, 2, 3… por `signal_key` |
| `source_id` | UUID | FK `sources` (a fonte) **[Altera fundação]** |
| `kind` | VARCHAR | `climate_anomaly` \| `crop_estimate` \| `export` \| `price_move` \| `news_event` |
| `title` | VARCHAR | |
| `summary` | TEXT | |
| `observation_date` | DATE | |
| `value` | NUMERIC NULL | |
| `unit` | VARCHAR NULL | |
| `confidence` | NUMERIC(4,3) NULL | Quando aplicável |
| `payload` | JSONB | Campos específicos da fonte |
| `published_at` | TIMESTAMPTZ | |
| `published_at_estimated` | BOOLEAN | `true` quando a data foi reconstituída |
| `ingested_at` | TIMESTAMPTZ | |
| `source_url` | VARCHAR | |
| `created_at` | TIMESTAMPTZ | |

Constraints e índices:

- `UNIQUE (signal_key, revision_id)`
- Índices: `(signal_key, published_at)`, `(published_at)`, `(kind)`

### 5.2 Regras dos sinais

- **Somente inserção**: um trigger bloqueia `UPDATE` e `DELETE` em `signals`. Revisão nova = linha nova com o mesmo `signal_key` e `revision_id` maior.
- **View `signals_current`**: revisão mais recente de cada `signal_key`, usada pelo radar ao vivo.
- **Corte temporal `as_of`**: para cada `signal_key`, a revisão mais recente com `published_at <= as_of`. Implementado em uma única função em `alpha/domain.py`.

```sql
SELECT DISTINCT ON (signal_key) *
FROM signals
WHERE published_at <= :as_of
ORDER BY signal_key, published_at DESC, revision_id DESC;
```

- **`published_at_estimated = true`** faz o Replay exibir "reconstituição ilustrativa", conforme o documento v0.3.

### 5.3 Setores e ativos

**`sectors`**: `id`, `slug` (UNIQUE, ex.: `agro_soja`), `name`.

**`signal_sectors`**: `signal_id` (FK), `sector_id` (FK), PK composta. Aponta para a linha da revisão, então cada revisão tem seus próprios setores.

**`assets`**: `id`, `ticker` (UNIQUE), `name`, `asset_type` (`stock` \| `fii` \| `etf`), `created_at`.

**`asset_sector_exposures`**

| Coluna | Tipo | Observação |
|---|---|---|
| `asset_id` | UUID | PK composta, FK `assets` |
| `sector_id` | UUID | PK composta, FK `sectors` |
| `rationale` | TEXT | Por que o ativo é exposto ao setor |
| `source_url` | VARCHAR | Fonte da justificativa |

Ligação sinal → ativo é **indireta**, por setor:

```
signals ─< signal_sectors >─ sectors ─< asset_sector_exposures >─ assets
```

- O pipeline marca setores afetados; não precisa conhecer ativos.
- A justificativa da exposição é o que o alerta mostra como "relação explícita com um setor/ativo".
- Ligação direta sinal ↔ ativo fica fora do MVP. Se necessária, entra como tabela nova `signal_assets`, sem alterar as existentes.

### 5.4 Watchlist e posições

**`watchlist_items`**: `id`, `user_id` (FK), `asset_id` (FK), `created_at`, `UNIQUE (user_id, asset_id)`.

**`holdings`**

| Coluna | Tipo | Observação |
|---|---|---|
| `id` | UUID | PK |
| `watchlist_item_id` | UUID | FK `watchlist_items`, UNIQUE, `ON DELETE CASCADE` |
| `quantity` | NUMERIC(18,6) | `CHECK (quantity > 0)` |
| `average_price` | NUMERIC(14,2) | |
| `created_at`, `updated_at` | TIMESTAMPTZ | |

Regras:

- Toda posição é um ativo acompanhado; a busca de sinais relevantes usa só a watchlist.
- Remover a posição mantém o ativo na watchlist; remover da watchlist remove a posição.
- Posições vêm pré-populadas no seed e podem ser editadas. Sem importação de nota de corretagem.
- **Valor de mercado não é armazenado**: quantidade × último preço, vindo das séries B3 no DuckDB. Dependência registrada para o spec de séries: consulta de último preço por ticker com `as_of`.
- Posições não entram na projeção de caixa.

---

## 6. Alertas

Módulo novo `alerts/` **[Altera fundação]**, chamado por `finance` e `alpha` via `service`.

**`alerts`**

| Coluna | Tipo | Observação |
|---|---|---|
| `id` | UUID | PK |
| `user_id` | UUID | FK `users` |
| `kind` | VARCHAR | `cash_pressure` \| `market_signal` |
| `severity` | VARCHAR | `info` \| `warning` |
| `status` | VARCHAR | `new` \| `read` |
| `title` | VARCHAR | Gerado por template no código |
| `message` | TEXT | Gerado por template no código |
| `evidence` | JSONB | Snapshot das evidências no momento da geração |
| `account_id` | UUID NULL | FK `accounts`; obrigatório se `cash_pressure` |
| `signal_id` | UUID NULL | FK `signals`; obrigatório se `market_signal` |
| `asset_id` | UUID NULL | FK `assets`; obrigatório se `market_signal` |
| `dedup_key` | VARCHAR | |
| `created_at` | TIMESTAMPTZ | |
| `read_at` | TIMESTAMPTZ NULL | |

Constraints e índices:

- `UNIQUE (user_id, dedup_key)`
- `CHECK` por tipo:
  - `kind = 'cash_pressure'` exige `account_id` e proíbe `signal_id`/`asset_id`.
  - `kind = 'market_signal'` exige `signal_id` e `asset_id` e proíbe `account_id`.
- Índice: `(user_id, status, created_at)`

Formato de `evidence` (mesmo formato de `message_evidences`):

```json
[
  { "label": "Saldo projetado em 30 dias", "value": "-320.00", "unit": "BRL",
    "source_url": null, "published_at": null },
  { "label": "Produtividade soja MT", "value": "3480", "unit": "kg/ha",
    "source_url": "https://...", "published_at": "2026-10-10T12:00:00Z" }
]
```

Regras:

- **Geração idempotente** por `generate_alerts()`, chamada:
  - ao concluir uma importação (pressão de caixa);
  - ao listar alertas (sinais publicados desde a última verificação × watchlist).
- **`dedup_key`**: `cash:<account_id>:<AAAA-MM>` ou `market:<signal_key>:<revision_id>:<ticker>`.
- Pipelines não chamam a API; o desacoplamento da fundação é mantido.
- **Sem LLM no texto do alerta**: título e mensagem vêm de templates com números calculados.
- **O Replay não usa `alerts`**. O Replay reconstrói o sinal a partir de `signals` com `as_of`; `alerts` guarda apenas alertas reais do app.
- **Telegram (P1)**: quando entrar, adicionar `delivered_at`. Fora do escopo agora.

---

## 7. Valyra AI

**`conversations`**: `id`, `user_id` (FK), `title`, `created_at`, `updated_at`.

**`messages`**

| Coluna | Tipo | Observação |
|---|---|---|
| `id` | UUID | PK |
| `conversation_id` | UUID | FK `conversations` |
| `role` | VARCHAR | `user` \| `assistant` |
| `content` | TEXT | |
| `status` | VARCHAR NULL | `ok` \| `rejected` \| `error` (só `assistant`) |
| `rejection_reason` | TEXT NULL | Ex.: número citado sem evidência |
| `uncertainty` | VARCHAR NULL | `low` \| `medium` \| `high` |
| `limitations` | TEXT[] NULL | |
| `as_of` | TIMESTAMPTZ NULL | Preenchido quando a pergunta é feita no Replay |
| `alert_id` | UUID NULL | FK `alerts`; "explicar este alerta" |
| `model`, `prompt_version` | VARCHAR NULL | |
| `tokens_in`, `tokens_out` | INT NULL | |
| `created_at` | TIMESTAMPTZ | |

Índice: `(conversation_id, created_at)`.

**`message_evidences`**

| Coluna | Tipo | Observação |
|---|---|---|
| `id` | UUID | PK |
| `message_id` | UUID | FK `messages` |
| `position` | INT | `UNIQUE (message_id, position)` |
| `label`, `value` | VARCHAR | |
| `unit` | VARCHAR NULL | |
| `source_url` | VARCHAR NULL | |
| `published_at` | TIMESTAMPTZ NULL | |
| `signal_id` | UUID NULL | FK `signals`; revisão exata usada |

Regras:

- A resposta estruturada do LLM é desmontada em colunas e em `message_evidences`, sem JSONB.
- Respostas rejeitadas pela validação são **guardadas** com `status = 'rejected'` e motivo, mas não exibidas como válidas. Servem para métricas honestas da validação.
- Com `as_of` preenchido, o service só fornece evidências publicadas até essa data.
- `model`, `prompt_version` e tokens alimentam a ADR-0002 (provedor e orçamento).

---

## 8. Migrações, seed e permissões

### 8.1 Migrações

- Histórico único em `services/api/alembic/`; todo PR que altera models traz sua migração.
- `--autogenerate` é rascunho e sempre revisado à mão.
- Trigger de `signals`, view `signals_current`, `CHECK`s e papéis do banco vão por `op.execute`.
- Migração já mergeada na `main` nunca é editada.
- Duas cabeças: quem mergear por último faz rebase e ajusta `down_revision`.
- CI:
  - `alembic upgrade head` em banco vazio;
  - `alembic check` (falha se model mudou sem migração);
  - falha se houver mais de uma cabeça.

### 8.2 Seed (`make seed`, idempotente)

| Dado | Observação |
|---|---|
| Usuário demo e conta principal | Saldo inicial sintético |
| Categorias | Lista fixa |
| Setores e fontes | Ex.: `agro_soja`; `inmet`, `conab`, `mdic`, `b3` |
| Ativos e exposições | Escolhidos e verificados pelo time, com justificativa e fonte; o seed não inventa relações |
| Watchlist e posições | Pré-populadas |
| CSV de transações | Sintético, em `datasets/samples/`, usado no upload da demo |

Sinais de exemplo **não** vêm do seed da API: são inseridos pelo pipeline em modo amostra, exercitando o caminho real de escrita.

### 8.3 Papéis do banco

| Papel | Permissões |
|---|---|
| `valyra_api` | Leitura e escrita nas tabelas do app; **somente leitura** em `signals` e `signal_sectors` |
| `valyra_pipelines` | `INSERT` em `signals` e `signal_sectors`; `SELECT` em `sources` e `sectors` |

Junto com o trigger, garante no banco que só os pipelines escrevem sinais e que nenhum sinal é alterado.

---

## 9. Testes obrigatórios

| Teste | Garante |
|---|---|
| `UPDATE` e `DELETE` em `signals` falham | Replay não é contaminado |
| `as_of` retorna a revisão correta e ignora revisões publicadas depois | Sem data leakage |
| Mesmo CSV importado duas vezes não duplica | Deduplicação |
| Duas transações idênticas no mesmo dia são aceitas | Índice de ocorrência |
| Linhas inválidas geram `import_rejections` e o lote conclui | Erros visíveis |
| `CHECK`s de `alerts` rejeitam combinações inválidas | Integridade por tipo |
| `generate_alerts()` executado duas vezes não duplica | Idempotência |
| Remover item da watchlist remove a posição | Cascata |
| Correção de categoria preserva `predicted_category_id` | Métrica de acurácia |
| Papel `valyra_api` não consegue inserir em `signals` | Permissões |

---

## 10. Impactos no spec de fundação **[Altera fundação]**

| Item | Fundação (06/11) | Este spec |
|---|---|---|
| Módulos do backend | `finance`, `alpha`, `ai` | + `alerts/`, chamado por `finance` e `alpha` via `service` |
| Identificação de sinais | "Mesmo `source_id`, novo `revision_id`" | `source_id` = fonte (FK); `signal_key` = identidade lógica; revisões compartilham `signal_key` |
| Acesso ao banco | Convenção: pipelines são o único escritor de sinais | Garantido por trigger e papéis do banco |

Após aprovação, o spec de fundação deve ser atualizado nas seções 2.1, 2.2, 2.3, 3.1 e 11.

---

## 11. Dependências para outros specs

- **Séries históricas (DuckDB/Parquet)**: consulta de último preço por ticker com `as_of`, usada no valor das posições.
- **ADR-0002 (provedor de LLM)**: usa os campos de custo de `messages`.
- **ADR-0006 (Telegram)**: se aceita, adiciona `alerts.delivered_at`.