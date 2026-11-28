# Contexto de backend

Leia o [contexto raiz](../../AGENTS.md). Esta pasta contém core HTTP (/health), oito modelos, Alembic, seed, domínio CSV, importação, consultas, correção de categoria, resumo mensal, recorrência, gastos atípicos e projeção de caixa e orçamento por categoria Finance via HTTP (#14/#15/#42/#43/#44/#45/#46), alertas de pressão de caixa (#47) e testes. IA tem cliente Gemini/Groq/OpenAI, contratos tipados, resolução de citações, validação lexical de números/metadados, serviço integrado ao Finance público e POST /api/v1/ai/explain; veja [ADR-0002](../../docs/adr/0002-provedor-llm.md), [ADR-0011](../../docs/adr/0011-contrato-evidencias-ia.md), [cliente](../../docs/ai-client.md), [serviço](../../docs/ai-service.md) e [HTTP](../../docs/ai-http.md). Alpha ([ADR-0012](../../docs/adr/0012-fontes-alpha.md)) tem `sources`/`signals` (migração `0004_alpha`, trigger somente inserção), GET /api/v1/alpha/radar, GET /api/v1/alpha/forecasts (previsões por perfil calculadas em código, [ADR-0016](../../docs/adr/0016-previsoes-por-perfil.md)) e o script `valyra.scripts.ingest_alpha`, executado pelo workflow agendado; alertas `market_signal` continuam planejados.

## Estrutura e dependências

O backend é um único FastAPI, com `core` compartilhado e módulos por domínio sob `src/valyra/`: `finance`, `alpha`, `alerts` e `ai`. `alerts` existe só para `cash_pressure` (#47): Finance chama `alerts.service` dentro da transação da importação, e Alerts não importa Finance (contratos import-linter). `alerts.service.create_cash_pressure` não faz commit.

Cada módulo separa `router.py` (HTTP), `schemas.py` (entrada/saída Pydantic), `service.py` (casos de uso), `domain.py` (regras puras), `repository.py` (I/O) e `models.py` (ORM), criando apenas o que o incremento utilizar.

- Dependência: `router → service → domain | repository`. Não importar no sentido inverso.
- `domain.py` não importa banco, HTTP, LLM ou configurações de infraestrutura. `finance/analytics.py` segue a mesma regra e também não lê o relógio: "hoje" vem de `core/clock.get_today()` no service e chega como parâmetro.
- Entre domínios, use o `service` público, nunca `repository` ou `models` do outro módulo para executar casos de uso.
- IA autoriza a conta antes de obter contexto/chamar LLM; contexto e cliente substituíveis são dependências internas do servidor. Valide a resposta pelo domínio contra um snapshot separado do enviado ao cliente. Consulta IA só lê, sem commit/rollback da sessão recebida; ausência de evidências retorna insuficiência sem provedor. Histórico não é evidência; contexto padrão corrente tem saldo de referência, recorte explícito de movimentações e, com lote concluído até o corte, resumo, orçamento e projeção calculados pelos services Finance como evidências `calculation`; o LLM nunca resume ou projeta.
- Contexto IA respeita quantidade e os 64.000 bytes do prompt serializado. Remova somente evidências/mensagens inteiras, preserve dependências e avisos temporais, declare omissões e valide contra o snapshot efetivamente enviado. O limite diário é referência calculada pelo Finance para esta conta, não saldo nem gasto diário da projeção; ausência vira limitação, zero permanece evidência.
- `core` não importa domínios. FKs entre módulos são permitidas no banco; não autorizam acesso cruzado indiscriminado no código.
- API lê sinais; os únicos escritores são `scripts/ingest_alpha.py` e `scripts/ingest_news.py` (GitHub Actions; notícias são `news_event` sem valor, conforme a [ADR-0013](../../docs/adr/0013-relatorio-semanal-noticias.md)). O trigger `signals_insert_only` bloqueia UPDATE/DELETE; papéis de banco da modelagem continuam desenho. Valores Alpha são `Decimal` e saem como texto decimal; cotações ficam em % até haver contrato de dinheiro Alpha. Previsões (`alpha/forecast.py`, domínio puro) usam float internamente por serem indicadores, saem como texto decimal, nunca vêm do LLM e marcam séries de reserva sintéticas (`data_origin`), que não vão à IA; a IA recebe as demais como `calculation` Alpha projetada.

## Convenções da API

Fontes: [contrato Finance](../../docs/api-design.md), [modelagem](../../docs/modelagem-db.md) e [preparação da migração](../../docs/revisao-modelagem.md).

- Rotas versionadas `/api/v1/`; `name="<módulo>_<ação>"` estável por operação, por exemplo `finance_list_accounts`. Não presumir que `name` vira `operationId` sem a configuração correspondente da API; verificar o OpenAPI exportado.
- Dinheiro Finance: `BIGINT` em centavos e inteiro JSON estrito, nomes `balance_cents`/`amount_cents`, sem conversão por `float`. UUIDs são strings no JSON.
- `DATE`/`YYYY-MM-DD` para datas de negócio; instantes timezone-aware normalizados para UTC. Sinal de transação: entrada positiva, saída negativa, zero proibido.
- Configuração por ambiente; usuário demo configurável, sem login. Validar propriedade da conta no service; existência de FK não comprova essa propriedade.
- Erros no envelope `{"error":{"code":"...","message":"...","details":{}}}`. Use os códigos registrados no contrato; não invente schema HTTP a partir de todas as colunas do banco. No OpenAPI, o router Finance declara 422 com `error_responses(422)` e cada rota acrescenta seus outros 4xx com `error_responses(...)` (core/errors.py); `tests/core/test_openapi_errors.py` exige a tabela por operação.
- HTTP IA aceita somente pergunta/conta, usa identidade demo (padrão ou do perfil em `X-Valyra-Profile`) e contexto do servidor; respostas 404/422/500/502/503 declaradas com ErrorResponse no OpenAPI. Mapear erros IA conhecidos no router; não retornar payload rejeitado, prompt ou mensagem bruta do SDK. Falhas internas de contexto não são erros 422 do usuário. Jornada sintética com transporte simulado em tests/ai; integração Finance HTTP em tests/db.
- Listagens usam `Page[T]` (`items`, `total`, `limit`, `offset`); `limit` padrão 50, entre 1 e 200; `offset` não negativo. Sessão de banco de `get_session()` não é sessão de usuário; `get_current_user_id()` retorna o demo configurado, ou o usuário fictício do perfil da demo indicado em `X-Valyra-Profile` (seletor de demonstração, não autenticação).
- CSV: UTF-8/BOM, contrato de cabeçalho/data/precisão/limites e hash conforme api-design. Preserve descrição original; normalização é cópia para regras/hash.
- Preserve categoria prevista ao corrigir categoria exibida. Respeite transação única da importação; rollback não garante lote `failed` persistido.
- O service controla commit/rollback do caso de uso; repository nunca faz commit. Rotas usam `def` síncrono porque a sessão SQLAlchemy é bloqueante. Erros de arquivo CSV viram `AppError` 422 no service. Filtro ou PATCH em conta de outro usuário responde 404 `ACCOUNT_NOT_FOUND`, como conta inexistente.
- Corpos de atualização usam `extra="forbid"` e recusam `null` explícito em colunas NOT NULL; dinheiro de entrada é `StrictInt` dentro da faixa BIGINT (validador, não `ge`/`le`, para não gerar float no OpenAPI).
- Preserve as pendências da modelagem e os refinamentos já implementados/autorizados na #10. Domínio valida BIGINT; limite seguro JSON no frontend e contratos incompletos continuam pendentes.

## Migrações e testes

- Um histórico Alembic em `services/api/alembic/`, usando a mesma metadata dos models.
- Autogenerate é rascunho: revisar tipos, defaults, checks, índices, FKs, operações de dados e downgrade à mão.
- Nunca edite migração já integrada na `main`; crie uma nova. Resolva múltiplas cabeças antes do merge, preservando a história integrada.
- Banco de testes separado e explícito por `TEST_DATABASE_URL`; nunca recorrer ao banco da aplicação para limpar dados. Verifique o destino efetivo antes de operações destrutivas.
- Seed idempotente, sem reset nem importação automática de transações para o usuário demo padrão. Exceção: `valyra.scripts.seed_demo_profiles` (start.sh) importa um extrato sintético pela importação CSV só nos usuários fictícios dos perfis da demo (`core/demo_profiles.py`, cabeçalho `X-Valyra-Profile`, fora do OpenAPI) e apenas em conta vazia; `--reset` recria só esses perfis. A primeira migração cobre somente User e as cinco tabelas Finance da revisão; `0002_alerts` cria `alerts`; `0003_budgets` cria `budgets`; `0004_alpha` cria `sources` e `signals`.
- Testes de regras, HTTP e persistência conforme o incremento; testes de `as_of` precisam excluir publicações/revisões futuras. Não gerar contratos manuais para passar CI.
- Priorize jornadas de integração. Unitários ficam nas bordas sem cobertura equivalente por HTTP: precisão/limites financeiros, CSV malformado, corte temporal, adulteração de evidências e falhas/custos do LLM. Evite repetir getters, detalhes privados e validações do framework; redução de cenários não comprova equivalência de cobertura.

## Ordem para criar um endpoint

1. Acordar schema de entrada/saída e exemplos.
2. Implementar service usando domínio/repository apropriados.
3. Registrar router com `name="<módulo>_<ação>"`.
4. Adicionar teste de comportamento, incluindo erro relevante.
5. Executar `make openapi`, revisar o contrato gerado e avisar os consumidores.

Comandos disponíveis na raiz: `make dev`, `make lint`, `make migrate`, `make seed`, `make test`, `make openapi`. A configuração oficial é services/api/pyproject.toml com uv.lock. make test-ai valida o cliente com transporte HTTP simulado, sem banco ou chamadas pagas. Reserva gratuita Groq com GROQ_API_KEY e fallback GPT-4o-mini com OPENAI_API_KEY ([ADR-0014](../../docs/adr/0014-reserva-groq.md)); controle de gasto pelo painel da OpenAI. Contexto é montado no servidor e o LLM devolve apenas IDs; o domínio confere literais em answer e limitações contra as citações, sem certificar semântica ou causalidade. Regras em [validação IA](../../docs/ai-validation.md); schemas não comprovam autorização nem veracidade externa. make test-unit roda todos os testes sem banco; make test-integration seleciona postgres. A coleta deriva a marca postgres da dependência de test_destination, inclusive indireta; o CI executa os grupos sem repetição. make test-domain é um recorte local de regras puras (CSV, analytics, clock, alertas, Alpha, notícias e previsões); pytest completo usa banco exclusivo para persistência, health, Finance, Alerts e Alpha HTTP (fixtures `client` e `db_session` em `tests/conftest.py`; `seed` e `importar` em `tests/finance/conftest.py`). A dependência de fixtures de banco é explícita, não autouse; a única autouse limpa o cache em memória das previsões, sem banco.

No CSV, line_number é a primeira linha física; raw_line preserva quebras internas. Registros malformados e estouro de csv.field_size_limit são wrong_column_count; o limite do processo (normalmente 131072 caracteres) não é alterado. O enquadramento lógico impede importar fragmentos após erro. O router de importação lê no máximo `MAX_FILE_BYTES + 1` bytes e responde 413 acima de 1 MiB; o servidor ainda recebe o corpo inteiro antes, então um limite de requisição precisa vir do servidor/proxy.

O exportador gera JSON com indentação 2, chaves ordenadas e LF explícito em todas as plataformas; regenere, não normalize o contrato à mão.
