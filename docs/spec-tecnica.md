# Fundação técnica do Valyra — Design

> **Integração #11/#12 (08/11/2026):** persistência/seed #17, domínio CSV #19 e core HTTP mínimo (/health, erros, paginação, OpenAPI) estão implementados nesta branch. Endpoints Finance #14/#15, projeções e módulos analíticos continuam planejados. A [arquitetura atual](architecture.md) e o [registro de integração](integracao-11-12.md) atualizam o estado; notas históricas anteriores abaixo descrevem suas respectivas etapas.

| Campo | Valor |
|---|---|
| Status | Em revisão pelo time |
| Data | 06/11/2026 |
| Base | Documento de Alinhamento Estratégico v0.3 (03/11/2026) |
| Escopo | Arquitetura (aplicação, backend, frontend), contexto para agentes, fluxo de trabalho, skills e estrutura de pastas |
| Fora de escopo | Funcionalidades de produto, modelos preditivos, design visual detalhado |

## Como ler este documento

Cada decisão está marcada com a origem, para o time debater só o que é novo:

- **[Doc v0.3]**: já estava no documento de alinhamento.
- **[Decisão do time]**: fechada durante o brainstorming de 06/11.
- **[Proposta]**: sugestão adicionada neste spec; precisa ser discutida e aceita.

A seção 11 lista todas as propostas em um só lugar.

**Atualização de 08/11/2026 (Issues #7/#10).** O Finance usa centavos; veja [modelagem](modelagem-db.md), [contrato de dados](api-design.md) e [registro da migração/seed](revisao-modelagem.md). A persistência mínima foi implementada em `services/api/`: configuração, Base/engine/sessão, seis modelos, Alembic, seed e testes. A validação local em PostgreSQL 18.6 foi concluída, conforme o registro. HTTP, parser, Alpha, IA, alertas, Makefile e contrato gerado continuam planejados; as representações seguintes descrevem também essa arquitetura futura. Frontend e sua stack foram preservados, sem recuperar a base antiga citada na Issue #7.

---

## 1. Contexto e objetivos

**Produto [Doc v0.3].** Três módulos dentro de um mesmo app:

- **Valyra Finance**: transações de demonstração, categorização, gastos atípicos e projeção de caixa.
- **Alternative Alpha**: análise preditiva do mercado financeiro utilizando cotações, notícias e dados alternativos para identificar tendências e riscos, com foco inicial na cadeia da soja em Mato Grosso.
- **Valyra AI**: explica os dois contextos com fonte, data, premissas e incerteza.

**Restrições [Doc v0.3].**

- 4 semanas (04–30/11), com jornada P0 demonstrável até 13/11.
- Repositório público, demo em HTTPS, vídeo de até 3 minutos.
- Somente dados sintéticos ou públicos.
- Sem data leakage: observação, publicação e ingestão são instantes distintos.
- O LLM interpreta evidências; números vêm de estatística, nunca do LLM.
- **[Escopo atual do MVP]** Um usuário demo, pessoa física, sem login ou isolamento por sessão; o identificador do demo será configurável.

**Contexto de desenvolvimento [Decisão do time].**

- 4 pessoas, divisão de trabalho **por camada**: front, back, dados/ML e infra.
- Agentes usados: **Claude Code, Codex e Cursor**.
- Todo o contexto do projeto fica **dentro do repositório**.

**Critérios de sucesso desta fundação.**

1. Qualquer pessoa (ou agente) consegue trabalhar na sua camada lendo apenas o `AGENTS.md` raiz e o da sua pasta.
2. Uma mudança em uma camada não quebra outra sem que o CI acuse.
3. A estrutura de pastas não precisa mudar até a submissão.

---

## 2. Arquitetura da aplicação

```
                ┌──────────────────────────┐
                │ apps/web (React)         │
                │ cliente TS gerado do     │
                │ OpenAPI                  │
                └────────────┬─────────────┘
                             │ HTTPS /api/v1
                ┌────────────▼─────────────┐
                │ services/api (FastAPI)   │
                │ finance · alpha · ai     │
                │ alerts (PR #6)           │
                └──┬───────────┬────────┬──┘
     lê/escreve    │  só lê    │        │ chamadas LLM
        ┌──────────▼──┐  ┌─────▼─────┐ ┌▼─────────────┐
        │ PostgreSQL  │  │ DuckDB +  │ │ Provedor LLM │
        │ (app)       │  │ Parquet   │ │ (ADR-0002)   │
        └──────▲──────┘  └─────▲─────┘ └──────────────┘
               │ publica sinais│ escreve séries
           ┌───┴───────────────┴───┐
           │ pipelines/ (ETL, jobs)│ ← INMET, CONAB, MDIC, B3
           └───────────────────────┘
```

- **Monorepo, backend único em FastAPI, módulos por domínio** [Doc v0.3].
- **PostgreSQL para dados do app; DuckDB + Parquet para histórico** [Doc v0.3].

### 2.1 Responsabilidade sobre os dados [Proposta]

| Componente | Escreve | Lê |
|---|---|---|
| `pipelines/` | Parquet/DuckDB (séries históricas); `signals` e `signal_sectors` no Postgres (desenho do PR #6) | Fontes externas |
| `services/api` | Postgres: transações-demo, watchlist, alertas, conversas | Postgres (somente leitura em `signals`/`signal_sectors`) e DuckDB (somente leitura) |
| `apps/web` | — | API |

- `pipelines/` é o **único** componente que acessa fontes externas.
- A API **nunca** chama fonte externa durante uma requisição. Isso protege a demo contra queda de APIs de terceiros.

**[Desenho registrado no PR #6, em revisão]** Pipelines também escrevem `signal_sectors`; a API deverá apenas ler sinais e suas relações. O desenho prevê triggers de imutabilidade e papéis de banco para aplicar essa fronteira, conforme a [modelagem, seções 5.2 e 8.3](modelagem-db.md#83-papéis-do-banco-previstos). Essas garantias ainda não estão implementadas.

### 2.2 Campos temporais dos sinais [Doc v0.3]

Todo sinal tem: `observation_date`, `published_at`, `ingested_at`, `source_url`, `source_id`, `revision_id` e `confidence` (quando aplicável).

**[Desenho registrado no PR #6, em revisão]** `source_id` é UUID e FK para `sources(id)`, identificando a fonte; `signal_key` é a identidade lógica do sinal, compartilhada pelas revisões. A unicidade prevista é `(signal_key, revision_id)`. Uma nova revisão é outra linha, sem atualizar a anterior.

### 2.3 Corte temporal `as_of` [Proposta]

- Toda consulta de sinais aceita o parâmetro `as_of` e aplica `published_at <= as_of`; para cada `signal_key`, seleciona a revisão mais recente dentro do corte, conforme o desenho do PR #6. A consulta prevista está na [modelagem, seção 5.2](modelagem-db.md#52-regras-dos-sinais).
- O **Replay Histórico é a mesma API chamada com `as_of` no passado**; não existe caminho de código paralelo.
- O filtro está previsto para implementação em uma única função em `alpha/domain.py`, com teste obrigatório de "não vazamento".

### 2.4 Fronteira do LLM [Doc v0.3 + Proposta]

- Somente o módulo `ai` fala com o LLM [Proposta].
- `ai` recebe evidências estruturadas dos services de `finance` e `alpha` (valores já calculados, fonte, data) e devolve uma resposta validada por schema [Doc v0.3: saídas estruturadas e validação de schema].
- Schema mínimo de resposta [Proposta]:

```json
{
  "answer": "texto em linguagem acessível",
  "evidences": [
    { "source_id": "...", "source_url": "...", "published_at": "...", "value": "..." }
  ],
  "uncertainty": "baixa | média | alta",
  "limitations": ["..."]
}
```

- Validação adicional [Proposta]: todo número citado em `answer` precisa aparecer em `evidences`; caso contrário, a resposta é rejeitada.

O exemplo genérico acima não define valores monetários: quando uma evidência contiver dinheiro, a API deve usar inteiros em centavos com sufixo `_cents`. O formato tipado e a persistência dessas evidências ainda precisam de alinhamento, conforme as seções 6 e 7 da [modelagem](modelagem-db.md); valores textuais genéricos não autorizam serializar dinheiro como string.

### 2.5 Execução e deploy

- **Docker, GitHub Actions** [Doc v0.3].
- Dois artefatos [Proposta]: imagem Docker da API e build estático do front.
- `docker-compose.yml` sobe localmente: `api`, `web`, `postgres` e um job de pipeline com dados de amostra [Proposta].
- O arquivo DuckDB/Parquet usado em produção precisa ir junto da imagem ou em volume; a forma depende da hospedagem (ADR-0005).

---

## 3. Arquitetura de backend

### 3.1 Organização interna: monólito modular por domínio [Decisão do time]

Alternativas avaliadas: camadas globais (`routers/`, `services/`…) e Clean/Hexagonal por módulo. A escolhida isola cada domínio com custo baixo de boilerplate. Registro em ADR-0001.

```
services/api/
├── pyproject.toml
├── alembic/                    # migrações; única fonte de schema do Postgres
├── src/valyra/
│   ├── main.py                 # cria o app e registra os routers
│   ├── core/                   # config, db, logging, errors, deps
│   ├── finance/
│   │   ├── router.py           # HTTP: valida entrada e chama o service
│   │   ├── schemas.py          # Pydantic de entrada/saída (gera o OpenAPI)
│   │   ├── service.py          # orquestra casos de uso
│   │   ├── domain.py           # regras puras, sem I/O
│   │   ├── repository.py       # acesso a Postgres/DuckDB
│   │   └── models.py           # ORM (SQLAlchemy)
│   ├── alpha/                  # mesma forma; as_of em domain.py
│   ├── alerts/                 # desenho do PR #6; chamado via service
│   └── ai/                     # mesma forma + llm_client.py e prompts/
└── tests/
    ├── finance/
    ├── alpha/
    └── ai/
```

### 3.2 Regras de dependência [Proposta]

Regras de arquitetura, com implementação gradual da verificação por `import-linter`:

1. Dentro de um módulo: `router → service → domain | repository`. Nunca no sentido inverso.
2. `domain.py` não importa banco, HTTP nem LLM.
3. Um módulo só usa outro pelo `service` (ex.: `ai` chama `alpha.service`). Nunca pelo `repository` ou `models` do outro.
4. `core` não importa nenhum módulo de domínio.

Na etapa #10, a fronteira `core` → `finance` já tem contrato verificado; as demais regras aguardam os componentes correspondentes. O job de CI de persistência executará lint e testes com PostgreSQL 18, sem substituir o job existente de Compose.

### 3.3 Convenções [Proposta, exceto onde indicado]

- **Stack** [Doc v0.3]: Python, FastAPI, Pydantic, SQLAlchemy + Alembic, Pytest, Ruff.
- **Versões e ferramentas**: Python 3.12 e `uv` para dependências.
- **Rotas**: `/api/v1/{finance|alpha|ai}/...`.
- **Formato único de erro**, tratado em `core/errors.py`:
  ```json
  { "error": { "code": "SIGNAL_NOT_FOUND", "message": "...", "details": {} } }
  ```
- **Configuração** somente por variáveis de ambiente (`pydantic-settings`), com `.env.example` versionado. Secrets fora do Git [Doc v0.3].
- **Datas**: instantes em UTC e timezone-aware; datas de negócio do Finance são `DATE`, sem fuso, serializadas como `YYYY-MM-DD`.
- **Dinheiro [Registrado, Issues #7/#10]**: `BIGINT` em centavos de BRL no Finance (`balance_cents`, `amount_cents`); inteiros JSON na API; cálculo e conversão sem `float`. Detalhes e pendências de precisão ficam na [modelagem](modelagem-db.md#33-tipos).
- **Contrato [Proposta de fluxo; exportador previsto na Issue #9]**: `make openapi` deverá exportar `openapi.json` para `packages/contracts/`, com verificação de atualização no CI. Esses arquivos/comandos ainda não existem. O [contrato inicial de dados](api-design.md) registra apenas interfaces explícitas das tarefas; o OpenAPI será gerado pela implementação da API.

### 3.4 Testes [Proposta]

| Tipo | Alvo | Ferramenta |
|---|---|---|
| Unitário (maioria) | `domain.py` | Pytest |
| Integração | routers com Postgres em container | Pytest + `TestClient` |
| Obrigatório | "não vazamento" do `as_of` | Pytest |

---

## 4. Arquitetura de frontend

### 4.1 Organização por feature [Proposta]

```
apps/web/
├── src/
│   ├── app/                    # rotas, providers, layout
│   ├── features/
│   │   ├── finance/            # dashboard, projeção, alertas de caixa
│   │   ├── alpha/              # radar, watchlist, replay
│   │   └── ai/                 # assistente
│   │       # cada feature: components/, hooks/, pages/, index.ts
│   ├── components/ui/          # design system
│   ├── lib/
│   │   ├── api/                # cliente GERADO; não editar à mão
│   │   └── utils/              # moeda, datas
│   └── styles/tokens.css       # cores, tipografia, espaçamento
├── e2e/                        # Playwright
└── vite.config.ts
```

### 4.2 Decisões

- **Stack** [Doc v0.3]: React, TypeScript, Vite, Tailwind CSS, Recharts, TanStack Query, Vitest, Playwright.
- **Cliente de API gerado com `orval`** [Proposta]: gera hooks do TanStack Query a partir do `openapi.json`. Mudança de contrato quebra o build do front no lugar certo.
- **Estado** [Proposta]: estado de servidor no TanStack Query; estado local mínimo com `useState`. Sem Redux/Zustand até haver necessidade real.
- **Roteamento** [Proposta]: React Router.
- **Design system** [Proposta]:
  - Tokens em CSS variables, consumidos pelo tema do Tailwind, seguindo a identidade do documento v0.3 (fundo navy, acento verde-água).
  - Componentes base com **shadcn/ui** (copiados para o repo e editáveis).
  - Proibido criar cor ou espaçamento fora dos tokens.
- **Componente `<Evidence>`** [Proposta]: mostra fonte, data e nível de confiança; reutilizado em todo alerta e toda resposta da IA.
- **Regras de import** [Proposta]:
  - Uma feature não importa outra feature.
  - Código compartilhado vai para `components/` ou `lib/`.
  - Cada feature expõe somente seu `index.ts`.
- **Gerenciador de pacotes** [Proposta]: `pnpm`, Node 22 LTS.

### 4.3 Testes [Proposta]

- Vitest + Testing Library para componentes e hooks com lógica.
- Playwright apenas para o smoke da jornada **Planejar → Monitorar → Compreender** [jornada do Doc v0.3], contra o `docker-compose` no CI.

---

## 5. Contexto no repositório para agentes [Proposta]

### 5.1 Arquivos

```
valyra/
├── AGENTS.md                   # fonte única de contexto
├── CLAUDE.md                   # contém apenas: @AGENTS.md
├── services/api/AGENTS.md      # + CLAUDE.md apontando para ele
├── apps/web/AGENTS.md          # + CLAUDE.md apontando para ele
├── pipelines/AGENTS.md         # + CLAUDE.md apontando para ele
└── docs/
    ├── product/                # documento de alinhamento, jornada, escopo P0/P1
    ├── architecture.md         # seções 2–4 deste spec, mantidas atualizadas
    ├── adr/                    # decisões numeradas
    ├── data-sources.md         # INMET, CONAB, MDIC, B3: licença, defasagem, riscos
    ├── glossary.md             # sinal, as_of, published_at, P0...
    ├── playbooks/              # procedimentos (seção 7)
    └── specs/                  # specs e planos de features
```

- **`AGENTS.md` é a fonte única.** Codex e Cursor leem esse arquivo nativamente; Claude Code lê `CLAUDE.md`, que só importa o `AGENTS.md`. Não se duplica conteúdo entre os dois.
- **Arquivos por camada**, porque cada pessoa trabalha em uma camada: o agente carrega o `AGENTS.md` raiz e o da pasta em que está.
- `.cursor/rules/` é opcional e só para casos específicos do Cursor, sem repetir o `AGENTS.md`.

### 5.2 Conteúdo do `AGENTS.md` raiz (menos de 150 linhas)

1. O produto em uma frase.
2. **Regras invioláveis**:
   - Sem data leakage: respeitar `published_at` e `as_of`.
   - O LLM nunca gera números; números vêm de código estatístico.
   - Somente dados sintéticos ou públicos; nada de dados pessoais reais.
   - Não editar código gerado (`packages/contracts/`, `apps/web/src/lib/api/`).
   - Se uma decisão não tem ADR aceita, perguntar ao humano em vez de decidir.
3. Comandos (`make dev`, `make test`, `make lint`, `make openapi`, `make seed`).
4. Mapa de pastas, com um link para cada `AGENTS.md` de camada.
5. Ponteiros para `docs/` (arquitetura, ADRs, fontes, glossário, playbooks).

### 5.3 Regra de manutenção

O PR que muda uma convenção atualiza o `AGENTS.md` correspondente **no mesmo PR**. O review por agente verifica isso.

---

## 6. Fluxo de trabalho

### 6.1 Organização das tarefas [Decisão do time + Proposta]

- **GitHub Projects + Issues** [Decisão do time].
- Toda tarefa é uma **issue**. Card criado como draft no Project é convertido em issue antes de começar [Proposta].
- **Issue forms** em `.github/ISSUE_TEMPLATE/` [Proposta]:
  - `task.yml`: camada, prioridade, descrição, critério de aceite, contexto/links.
  - `bug.yml`: camada, passos para reproduzir, resultado esperado e obtido.
- **Labels fixas** [Proposta]: camada (`api`, `web`, `pipelines`, `infra`, `docs`) e prioridade (`P0`, `P1`).
- **Automações nativas do Project** [Proposta], sem GitHub Actions customizadas:
  - Auto-add: issue nova do repositório entra no quadro.
  - Item added → Todo.
  - Item closed → Done; Pull request merged → Done.
  - Auto-archive de itens concluídos.
- "In Progress" é movido manualmente.

### 6.2 Branches [Proposta]

- Trunk-based: `main` sempre deployável.
- Branches curtas (até 1–2 dias): `tipo/escopo-descricao`, ex.: `feat/api-projecao-gastos`.
- Merge por **squash**.

### 6.3 Commits: Conventional Commits [Proposta]

- Formato: `tipo(escopo): descrição`.
- Tipos: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `ci`, `perf`.
- Escopos fixos: `api`, `web`, `pipelines`, `contracts`, `infra`, `docs`, `experiments`.
- Exemplos:
  - `feat(api): endpoint de projeção de 30 dias`
  - `fix(pipelines): corrige published_at da CONAB`
- Commits feitos por agente levam o trailer `Co-authored-by` da ferramenta.

### 6.4 Pull requests [Decisão do time + Proposta]

- **Aprovação**: CI verde + review por agente + **1 aprovação humana de qualquer integrante** [Decisão do time]. Sem `CODEOWNERS` [Decisão do time].
- Branch protection na `main` exige CI verde e 1 aprovação [Proposta].
- Todo PR referencia uma issue (`Closes #N`) [Proposta].
- Tamanho-alvo: menos de ~400 linhas alteradas, sem contar código gerado [Proposta].
- **Template de PR** (`.github/pull_request_template.md`) [Proposta]:
  - [ ] Issue referenciada
  - [ ] Testes adicionados/atualizados e passando
  - [ ] `AGENTS.md` atualizado, se alguma convenção mudou
  - [ ] Se mexeu no contrato: `make openapi` rodado e time avisado
  - [ ] Sem secrets e sem dados reais
  - [ ] Screenshot, se mudou UI

### 6.5 Review por agente [Decisão do time]

- **Claude Code GitHub Action**, autenticado com o token da assinatura do Samuel (`CLAUDE_CODE_OAUTH_TOKEN`, gerado com `claude setup-token`). Registro em ADR-0008.
- Cuidados [Proposta]:
  - Disparar apenas em PR aberto, PR marcado como "ready for review" e menção `@claude`, não a cada push, para poupar a cota da assinatura.
  - Revogar o token ao fim do hackathon.
  - PRs vindos de forks não recebem secrets; o time trabalha com branches no próprio repositório.
- Prompt do revisor versionado em `.github/review-prompt.md` [Proposta], verificando:
  - Regras invioláveis do `AGENTS.md`.
  - Regras de dependência (backend e frontend).
  - Testes presentes para lógica nova.
  - `AGENTS.md` e `openapi.json` atualizados quando aplicável.

### 6.6 CI [Doc v0.3 + Proposta]

`.github/workflows/ci.yml`, com jobs [Proposta]:

| Job | Etapas |
|---|---|
| `api` | `ruff check`, `ruff format --check`, `import-linter`, `pytest` |
| `web` | lint, typecheck, `vitest`, build |
| `contracts` | regenera `openapi.json` e falha se houver diferença |
| `e2e` | sobe `docker-compose` e roda o smoke Playwright |

---

## 7. Skills e agentes [Proposta]

### 7.1 Recomendação

- **Não criar skills nem subagentes no início.** Os `AGENTS.md` cobrem o contexto (regras e convenções).
- Skills servem para **procedimentos repetidos com vários passos** em que agentes costumam pular etapas.
- Subagentes especializados não compensam: cada pessoa já cuida de uma camada.
- Regra: **só criar um playbook quando um procedimento já deu errado duas vezes.**

### 7.2 Formato compatível com as três ferramentas

- Cada procedimento é escrito uma vez, em Markdown comum, em `docs/playbooks/<nome>.md`.
- O `AGENTS.md` raiz lista os playbooks; Codex e Cursor os leem por esse caminho.
- Para Claude Code, `.claude/skills/<nome>/SKILL.md` é um invólucro de poucas linhas que manda ler o playbook.

### 7.3 Candidatos prováveis

| Playbook | Passos que não podem ser esquecidos |
|---|---|
| `add-endpoint` | schema → service → router → teste → `make openapi` → regenerar cliente |
| `add-data-source` | pipeline com campos temporais → entrada em `data-sources.md` → teste de `as_of` |
| `new-adr` | template, numeração e status |

---

## 8. Estrutura final de pastas

Base do Doc v0.3 (`apps/web`, `services/api`, `pipelines`, `experiments`, `datasets/samples`, `infra`, `docs`), com adições marcadas como [Proposta]:

```
valyra/
├── AGENTS.md                         # [Proposta]
├── CLAUDE.md                         # [Proposta]
├── README.md
├── LICENSE                           # Apache 2.0 planejada [Doc v0.3]
├── Makefile                          # [Proposta] interface única de comandos
├── docker-compose.yml                # [Proposta]
├── .env.example                      # [Proposta]
├── .github/                          # [Proposta]
│   ├── workflows/                    # ci.yml, claude-review.yml
│   ├── ISSUE_TEMPLATE/               # task.yml, bug.yml
│   ├── pull_request_template.md
│   └── review-prompt.md
├── .claude/skills/                   # [Proposta] invólucros → docs/playbooks/
├── apps/web/                         # seção 4 (+ AGENTS.md, CLAUDE.md)
├── services/api/                     # seção 3 (+ AGENTS.md, CLAUDE.md)
├── packages/contracts/               # [Proposta] openapi.json gerado e versionado
├── pipelines/                        # ETL por fonte (+ AGENTS.md, CLAUDE.md)
│   ├── inmet/
│   ├── conab/
│   ├── mdic/
│   └── b3/
├── experiments/                      # EXP-001: notebooks, baselines, relatório
├── datasets/samples/                 # somente dados sintéticos/públicos
├── infra/                            # Dockerfiles, deploy
└── docs/                             # seção 5.1
```

- Dados gerados localmente pelos pipelines (Parquet, arquivo DuckDB) ficam em `data/`, no `.gitignore` [Proposta]. Só `datasets/samples/` é versionado.
- O `Makefile` [Proposta] expõe: `make dev`, `make test`, `make lint`, `make openapi`, `make seed`. Pessoas e agentes usam os mesmos comandos.

---

## 9. ADRs iniciais

| ADR | Tema | Status | Origem |
|---|---|---|---|
| 0001 | Monólito modular por domínio no backend | Aceita | Decisão do time |
| 0002 | Provedor de LLM e orçamento | Aberta | Doc v0.3 |
| 0003 | Fonte licenciada de preços | Aberta | Doc v0.3 |
| 0004 | Data/evento para o Replay | Aberta | Doc v0.3 |
| 0005 | Hospedagem HTTPS (inclui como servir o DuckDB) | Aberta | Doc v0.3 |
| 0006 | Manter ou adiar Telegram | Aberta | Doc v0.3 |
| 0007 | Consentimento, segurança e limites regulatórios | Aberta | Doc v0.3 |
| 0008 | Review por agente com Claude Code GitHub Action | Aceita | Decisão do time |

Formato sugerido de ADR [Proposta]: Contexto, Decisão, Alternativas consideradas, Consequências, Status.

---

## 10. Fora de escopo deste spec

- Modelos preditivos, features e métricas do EXP-001 (H1–H4).
- Telas, fluxos e design visual detalhado.
- Escolhas das ADRs abertas (0002–0007).
- Telegram e qualquer item P1.

---

## 11. Propostas para debate

Resumo de tudo marcado como [Proposta]:

**Alinhamento com o desenho do [PR #6](https://github.com/UaiScript/valyra-hackbrasil-2026/pull/6), em revisão**

- Backend inclui `alerts/`, chamado por Finance e Alpha via `service`.
- `source_id` referencia a fonte; `signal_key` identifica o sinal lógico e agrupa suas revisões.
- Pipelines escrevem `signals`/`signal_sectors`; API só lê essas tabelas. Triggers e papéis são garantias planejadas na modelagem, sem implementação neste checkout.

**Arquitetura**
1. `pipelines/` como único componente que acessa fontes externas; API só lê DuckDB.
2. `as_of` como mecanismo único de corte temporal e do Replay.
3. Só o módulo `ai` fala com o LLM; schema de resposta com `evidences` e validação de números.
4. Dois artefatos de deploy + `docker-compose` local.

**Backend**
5. Regras de dependência verificadas com `import-linter`.
6. Python 3.12 + `uv`; rotas `/api/v1/...`; formato único de erro; datas em UTC.
7. `packages/contracts/openapi.json` versionado e checado no CI.

**Frontend**
8. Organização por feature com regras de import.
9. `orval` para gerar o cliente; React Router; sem lib de estado global.
10. Design system com tokens + shadcn/ui; componente `<Evidence>`.
11. `pnpm` + Node 22 LTS.

**Contexto e fluxo**
12. `AGENTS.md` como fonte única, com arquivos por camada e `CLAUDE.md` como ponteiro.
13. Issue forms, labels fixas e automações nativas do Project.
14. Trunk-based, squash merge, Conventional Commits com escopos fixos, trailer de coautoria de agente.
15. Template de PR com checklist; tamanho-alvo de ~400 linhas.
16. Gatilhos do review por agente e `.github/review-prompt.md`.
17. Jobs de CI (`api`, `web`, `contracts`, `e2e`).

**Skills e estrutura**
18. Playbooks em `docs/playbooks/` com invólucros em `.claude/skills/`, criados sob demanda.
19. `Makefile` como interface única; `data/` fora do Git.
