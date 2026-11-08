# Contexto de backend

Leia o [contexto raiz](../../AGENTS.md). Esta pasta contém core HTTP mínimo (/health), seis modelos, Alembic, seed, domínio CSV e testes. Finance HTTP (#14/#15), projeções, Alpha, alertas e IA continuam planejados.

## Estrutura e dependências

O backend é um único FastAPI, com `core` compartilhado e módulos por domínio sob `src/valyra/`: `finance`, `alpha`, `alerts` e `ai`. `alerts` integra o desenho da modelagem; sua implementação é posterior ao Finance inicial.

Cada módulo separa `router.py` (HTTP), `schemas.py` (entrada/saída Pydantic), `service.py` (casos de uso), `domain.py` (regras puras), `repository.py` (I/O) e `models.py` (ORM), criando apenas o que o incremento utilizar.

- Dependência: `router → service → domain | repository`. Não importar no sentido inverso.
- `domain.py` não importa banco, HTTP, LLM ou configurações de infraestrutura.
- Entre domínios, use o `service` público, nunca `repository` ou `models` do outro módulo para executar casos de uso.
- `core` não importa domínios. FKs entre módulos são permitidas no banco; não autorizam acesso cruzado indiscriminado no código.
- API lê sinais; pipelines serão os escritores. Papéis/triggers da modelagem são desenho, não garantia já implementada.

## Convenções da API

Fontes: [contrato Finance](../../docs/api-design.md), [modelagem](../../docs/modelagem-db.md) e [preparação da migração](../../docs/revisao-modelagem.md).

- Rotas versionadas `/api/v1/`; `name="<módulo>_<ação>"` estável por operação, por exemplo `finance_list_accounts`. Não presumir que `name` vira `operationId` sem a configuração correspondente da API; verificar o OpenAPI exportado.
- Dinheiro Finance: `BIGINT` em centavos e inteiro JSON estrito, nomes `balance_cents`/`amount_cents`, sem conversão por `float`. UUIDs são strings no JSON.
- `DATE`/`YYYY-MM-DD` para datas de negócio; instantes timezone-aware normalizados para UTC. Sinal de transação: entrada positiva, saída negativa, zero proibido.
- Configuração por ambiente; usuário demo configurável, sem login. Validar propriedade da conta no service; existência de FK não comprova essa propriedade.
- Erros no envelope `{"error":{"code":"...","message":"...","details":{}}}`. Use os códigos registrados no contrato; não invente schema HTTP a partir de todas as colunas do banco.
- Listagens usam `Page[T]` (`items`, `total`, `limit`, `offset`); `limit` padrão 50, entre 1 e 200; `offset` não negativo. Sessão de banco de `get_session()` não é sessão de usuário; `get_current_user_id()` retorna o demo configurado.
- CSV: UTF-8/BOM, contrato de cabeçalho/data/precisão/limites e hash conforme api-design. Preserve descrição original; normalização é cópia para regras/hash.
- Preserve categoria prevista ao corrigir categoria exibida. Respeite transação única da importação; rollback não garante lote `failed` persistido.
- Preserve as pendências da modelagem e os refinamentos já implementados/autorizados na #10. Domínio valida BIGINT; limite seguro JSON no frontend e contratos incompletos continuam pendentes.

## Migrações e testes

- Um histórico Alembic em `services/api/alembic/`, usando a mesma metadata dos models.
- Autogenerate é rascunho: revisar tipos, defaults, checks, índices, FKs, operações de dados e downgrade à mão.
- Nunca edite migração já integrada na `main`; crie uma nova. Resolva múltiplas cabeças antes do merge, preservando a história integrada.
- Banco de testes separado e explícito por `TEST_DATABASE_URL`; nunca recorrer ao banco da aplicação para limpar dados. Verifique o destino efetivo antes de operações destrutivas.
- Seed idempotente, sem reset nem importação automática de transações. A primeira migração cobre somente User e as cinco tabelas Finance da revisão.
- Testes de regras, HTTP e persistência conforme o incremento; testes de `as_of` precisam excluir publicações/revisões futuras. Não gerar contratos manuais para passar CI.

## Ordem para criar um endpoint

1. Acordar schema de entrada/saída e exemplos.
2. Implementar service usando domínio/repository apropriados.
3. Registrar router com `name="<módulo>_<ação>"`.
4. Adicionar teste de comportamento, incluindo erro relevante.
5. Executar `make openapi`, revisar o contrato gerado e avisar os consumidores.

Comandos disponíveis na raiz: `make dev`, `make lint`, `make migrate`, `make seed`, `make test`, `make openapi`. A configuração oficial é services/api/pyproject.toml com uv.lock. make test-domain roda os 168 casos puros sem conexão PostgreSQL; pytest completo usa banco exclusivo para persistência/health. A dependência de fixtures de banco é explícita, não autouse.

No CSV, line_number é a primeira linha física; raw_line preserva quebras internas. Registros malformados e estouro de csv.field_size_limit são wrong_column_count; o limite do processo (normalmente 131072 caracteres) não é alterado. O enquadramento lógico impede importar fragmentos após erro. Arquivo acima de 1 MiB é responsabilidade do router futuro.

O exportador gera JSON com indentação 2, chaves ordenadas e LF explícito em todas as plataformas; regenere, não normalize o contrato à mão.
