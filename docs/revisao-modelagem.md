# Implementação da migração e seed — Issue #10

Registro da [Issue #10](https://github.com/UaiScript/valyra-hackbrasil-2026/issues/10), implementada em 07/11 e validada em PostgreSQL em **08/11/2026**, após a revisão documental da #7. A equipe autorizou implementar os refinamentos de persistência abaixo. Regras das tabelas ficam na [modelagem, seção 4](modelagem-db.md#4-finance); este registro reúne integração, seed, comandos e limites da validação.

## Estado conferido

- Branch `willian/banco-finance`, checkout inicialmente limpo em `1ff2ea6`, que contém a revisão documental integrada no PR #16. Não foram encontrados `AGENTS.md` aplicáveis nem código prévio de backend para reutilizar.
- Existem agora `services/api/pyproject.toml`, `uv.lock`, persistência mínima em `core`, cinco modelos em `finance/models.py`, Alembic, seed e testes. O Compose preserva PostgreSQL 18, porta, volume e healthcheck; ganhou somente o mount de init do banco dedicado de testes. A configuração foi acrescentada a `.env.example`; nenhum `.env` foi substituído.
- Não existem core HTTP, endpoints, parser, categorização, Makefile ou OpenAPI gerado. `docs/plano-1-implementacao.md` e `plano-fundacao-importacao-csv.md` não estão disponíveis no checkout.
- As Issues #8/#9/#10 foram consultadas novamente; as descrições e comentários de #7–#10 e #13–#15 foram lidos na revisão anterior. As decisões documentais de Alpha/IA/alertas continuam com seu status anterior; não foram implementadas.
- A retomada de 08/11 preservou todas as alterações locais e os dois stashes. Docker Desktop foi iniciado no contexto local `desktop-linux`; somente o serviço `postgres` do projeto `valyra` foi iniciado. Não havia volume anterior do projeto. O `.env` foi criado do exemplo por estar ausente e continua ignorado pelo Git, sem exibição de credenciais.
- Confirmados PostgreSQL **18.6**, publicação exclusiva em `127.0.0.1:5432` e bancos distintos `valyra` / `valyra_test`, ambos vazios antes da validação. O volume `valyra_postgres_data` foi criado pelo Compose; nenhum volume foi removido.

## Integração mínima com #8/#9

- **#8:** variáveis de conexão/demo no exemplo, script idempotente que cria `valyra_test` se ausente e mount de init. Em volume existente, o init precisa de execução explícita com `psql`; não remover volumes para reaplicá-lo. Makefile e demais componentes da #8 não foram antecipados.
- **#9:** uma única `Base`/metadata e `User` em `core/db.py`; `Settings`/`get_settings()` com `database_url`, `cors_origin`, `demo_user_id`; engine, fábrica de sessões e `get_session()`. A URL é obrigatória, sem destino implícito. O chamador da sessão controla a transação; fechar uma sessão não confirma escritas.
- **Composição:** `alembic/env.py` carrega os modelos Finance, sem import de Finance por core. `import-linter` verifica essa fronteira. Nenhum componente HTTP, `client` ou `get_current_user_id()` foi criado.
- **#10:** modelos, migração inicial e testes usam a mesma metadata. A migração foi escrita/revisada manualmente, com criação em ordem de dependências e remoção inversa. Não se usa `create_all()`. O `alembic check` online passou no desenvolvimento e nos schemas descartáveis do banco de testes, sem diferenças entre ORM e migração.

## Decisões pendentes

| Decisão | Efeito na implementação | Etapa dependente |
|---|---|---|
| Saldo de abertura ou fechamento; proposta de fechamento na seção 4.2 da modelagem | Determina limite inferior da soma e interpretação da referência; as tarefas não fecharam essa convenção | Semântica da conta (#10/#15) e cálculo futuro de saldo |
| Persistir tentativas fracassadas após rollback | A transação única da #14 pode apagar o lote; definir se haverá registro em outra transação/mecanismo, sem prometer `failed` persistido | Importação (#14); não bloqueia a definição dos seis modelos |
| Limites monetários de entrada, armazenamento e resposta | Evitar overflow de `BIGINT` e perda de precisão de inteiros JSON no JavaScript; tarefas não fixam teto nem erro para valor fora da faixa | Domínio (#13), HTTP (#14/#15) e eventual check (#10) |
| Completar schemas HTTP e semântica de consulta | #14 remete a spec ausente para campos completos dos lotes; fechar também resposta do PATCH, `null` no update, confiança preenchida, limites de datas e desempate da ordenação, conforme lacunas do contrato | Schemas/consultas (#14/#15) |
| Casos CSV não detalhados | Confirmar cabeçalho reordenado/colunas extras, sintaxe CSV malformada e numeração/texto de registros multilinha; não criar razões de erro adicionais sem alinhamento | Parser (#13) e tradução de erros (#14) |

**Resolvido nas fontes:** #13 define UTF-8/BOM, separador, datas, precisão CSV, linhas vazias, limites de arquivo/linhas, normalização, SHA-256, ocorrência inicial e fallback. #14 define valores iniciais da classificação e transação única. #15 define rotas de consulta, filtros, ordenação e saldo estritamente inteiro. Esses contratos têm fonte principal em [api-design.md](api-design.md); saem da lista de pendências. Preços médios e evidências monetárias de Alpha/IA continuam nas seções 5.4, 6 e 7 da modelagem.

**Autorizado e validado nesta implementação:** nulabilidade/defaults, exclusões/cascatas, FK composta, checks de contadores/scores/timestamps e proteção contra conflitos no seed deixaram de ser pendências para a Issue #10. A revisão de Samuel e Breno permanece como próximo passo.

## Seed da Issue #10

Interface implementada: `valyra.seed.run(session: Session) -> None`; execução por `python -m valyra.seed`.

| Registro | Valores registrados |
|---|---|
| Usuário demo | `id = settings.demo_user_id`, configurável por `DEMO_USER_ID`; `name = "Usuário demo"`. Exemplo de ID da Issue #8: `00000000-0000-0000-0000-000000000001` |
| Conta principal | `id = 00000000-0000-0000-0000-000000000101`; `user_id` do demo; `name = "Conta principal"`; `balance_cents = 500000`; `balance_as_of = 2026-11-01` |

As 12 categorias registradas:

| slug | nome | kind |
|---|---|---|
| `mercado` | Mercado | `expense` |
| `restaurantes` | Restaurantes | `expense` |
| `transporte` | Transporte | `expense` |
| `moradia` | Moradia | `expense` |
| `contas-e-servicos` | Contas e serviços | `expense` |
| `saude` | Saúde | `expense` |
| `educacao` | Educação | `expense` |
| `lazer` | Lazer | `expense` |
| `assinaturas` | Assinaturas | `expense` |
| `outros` | Outros | `expense` |
| `salario` | Salário | `income` |
| `outras-receitas` | Outras receitas | `income` |

**[Registrado]** Usar `INSERT … ON CONFLICT DO NOTHING`, com conflito pelo ID do usuário, ID da conta e `slug` das categorias. Reexecução não duplica nem atualiza nome, saldo, data, categoria ou dados já alterados. Categorias existentes conservam seus UUIDs; resolver referências por `slug`. Não importar transações nem executar reset de dados no seed inicial.

**Conflitos autorizados e implementados:** conta fixa pertencente a outro usuário ou categoria com `kind` incompatível gera `SeedConflictError`, sem reatribuir ou sobrescrever. As referências existentes são consultadas por ID/slug, com lock durante a validação.

**Transação:** `run(session)` abre um SAVEPOINT e não chama `commit()` da transação externa. Se falhar, desfaz todas as suas inserções, mesmo se o chamador capturar a exceção e confirmar trabalho anterior. O chamador deve usar um contexto de transação e decidir commit/rollback; `python -m valyra.seed` usa `get_session_factory().begin()`, confirmando no sucesso e revertendo na falha. Como `Session.begin_nested()` pode fazer autoflush prévio, o chamador deve entregar uma sessão com seu trabalho anterior já consistente.

## Testes e validação

Resultado de **08/11/2026: 77 testes passaram, sem testes ignorados**, em PostgreSQL 18.6. A primeira execução teve somente um aviso de permissão no cache antigo do pytest; a repetição com `-p no:cacheprovider` passou sem avisos. Foram usados os URLs locais conferidos contra o Compose e exportados explicitamente ao processo de teste, sem imprimir credenciais.

- `upgrade head` aplicado no banco local `valyra`, previamente vazio; `alembic check` online sem novas operações. O round-trip upgrade/downgrade/upgrade ocorreu somente em schema descartável de `valyra_test`.
- Seed executado duas vezes no desenvolvimento: **1 usuário, 1 conta, 12 categorias e nenhuma transação/lote/rejeição**. Comparação de todas as linhas confirmou igualdade completa após a segunda execução, incluindo UUIDs, nomes, saldo, datas e timestamps.
- O script de init criou `valyra_test` no volume novo; sua reexecução idempotente também foi conferida, sem alterar linhas em nenhum dos dois bancos.
- A comparação de todas as linhas e de `alembic_version` antes/depois de cada execução da suíte confirmou que os testes não alteraram o desenvolvimento. Não houve limpeza no banco `valyra`.
- Ruff, formatação e fronteira de imports passaram. O job de CI `Finance / PostgreSQL 18` não foi disparado nesta entrega; a validação descrita é local. A geração SQL offline anterior não foi usada como substituta da integração.

A suíte executou os critérios abaixo:

| Cenário | Resultado esperado |
|---|---|
| Migração em banco de testes vazio | `upgrade head` cria as seis tabelas; uma única cabeça, com a revisão inicial presente no histórico sem fixá-la como cabeça permanente |
| ORM versus migração | `alembic check` sem diferença; tipos, defaults, FKs, checks e índices revisados |
| Valores inválidos | Banco rejeita `amount_cents = 0`, enums inválidos, campos obrigatórios nulos e FKs inexistentes |
| Unicidade do hash | Mesma conta e hash são bloqueados, inclusive em lotes diferentes; outra conta pode usar o mesmo hash |
| Conta versus lote | Transação com conta diferente da conta do lote é rejeitada pela FK composta |
| Lote | Rejeitar contador negativo, soma acima do total, conclusão sem conciliação e combinação inválida de status/término |
| Scores e timestamps | Aceitar scores nulos ou nos limites 0 e 1; rejeitar fora do intervalo; rejeitar atualização/término anterior à criação |
| Exclusões | Bloquear remoção de referências em uso; remover rejeições só com lote cuja exclusão seja permitida |
| Seed em banco vazio | Usuário configurado, conta com ID/saldo/data esperados e exatamente 12 categorias |
| Seed repetido e dados existentes | Duas execuções mantêm quantidades e UUIDs; mudanças prévias em nome/saldo/data/categorias não são sobrescritas; registros ausentes são acrescentados |
| Conflitos do seed | Conta ligada a outro demo ou categoria com `kind` incompatível gera diagnóstico sem reatribuição/sobrescrita e sem inserções parciais |
| Limpeza restrita a testes | Fixture exige `TEST_DATABASE_URL` explícita e destino de teste autorizado; nunca recorre a `DATABASE_URL` para limpar dados |

**Fixtures validadas:** exigem `TEST_DATABASE_URL` explícita com driver `postgresql+psycopg` e nome terminado em `_test`. Antes de criar/limpar schemas, conferem `current_database()`, endereço/porta efetivos e, se configurado, comparam com a conexão real da aplicação; aliases de URL não bastam para declarar bancos distintos. Cada execução usa schemas aleatórios isolados; a limpeza entre testes limita `TRUNCATE` às seis tabelas e preserva `alembic_version`. As remoções de estruturas ocorreram exclusivamente nesses schemas de teste, nunca no desenvolvimento.

As Issues #13–#15 ainda exigem parser, hash, categorização e services/HTTP. O teste de alteração da categoria atual verifica que o ORM não muda a prevista automaticamente; não cria uma regra de imutabilidade para SQL direto. Conciliação com linhas persistidas e cálculo de saldo continuam fora do escopo.

## Comandos disponíveis

Na raiz, com Docker Desktop iniciado e `.env` próprio preservado. Se estiver ausente, crie-o de `.env.example`. As URLs precisam corresponder à porta, usuário e senha do Compose, apontando a bancos locais distintos; não exiba esses valores. O `--env-file` exporta também `TEST_DATABASE_URL` para o processo do pytest, que não a lê diretamente do arquivo.

```powershell
$uvFinance = ".\.tools\bootstrap\Scripts\uv.exe"
$envFinance = (Resolve-Path .env).Path.Replace('\', '/')
docker --context desktop-linux compose up -d --wait postgres
& $uvFinance run --locked --env-file $envFinance --directory services/api alembic upgrade head
& $uvFinance run --locked --env-file $envFinance --directory services/api alembic check
& $uvFinance run --locked --env-file $envFinance --directory services/api python -m valyra.seed
& $uvFinance run --locked --env-file $envFinance --directory services/api python -m valyra.seed
& $uvFinance run --locked --env-file $envFinance --directory services/api pytest -p no:cacheprovider
& $uvFinance run --locked --directory services/api ruff check .
& $uvFinance run --locked --directory services/api ruff format --check .
& $uvFinance run --locked --directory services/api lint-imports
```

O caminho do `.env` usa barras `/` porque o `uv` local interpretou as barras invertidas do caminho absoluto como escapes. O cache do pytest foi desabilitado somente para evitar a permissão do cache antigo no Windows; isso não ignora testes. Em outra instalação de `uv`, ajuste apenas `$uvFinance` para o executável disponível. `uv sync --project services/api --locked` prepara as dependências quando necessário.

Em volume existente, o script de criação do teste pode ser reaplicado sem apagar dados. O comando abaixo usa usuário e banco da configuração do container, respeitando `POSTGRES_DB`:

```powershell
docker --context desktop-linux compose exec -T postgres sh -c 'exec psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 -f /docker-entrypoint-initdb.d/01-create-test-db.sql'
```

Migração e seed usam `DATABASE_URL`; executar em desenvolvimento apenas após comprovar que o destino é local ao projeto. Testes não usam essa URL como fallback para limpeza. `alembic upgrade head --sql` serve apenas para inspeção offline e não substitui a suíte PostgreSQL.

Nesta execução, Python 3.13 foi usado; o pacote aceita 3.12 ou superior e o job de CI foi configurado para 3.12. O `uv` foi instalado isoladamente em `.tools/bootstrap/Scripts/uv.exe`, pois não estava no PATH. Esse bootstrap e os ambientes/cache não são versionados; `uv.lock` é versionável. Não foi criado Makefile.

## Próximo passo

Submeter o diff local à revisão de Samuel e Breno, com atenção à migração, à fronteira transacional do seed e às interfaces mínimas adicionadas às dependências #8/#9. A validação local PostgreSQL da Issue #10 foi concluída sem necessidade de alterar o código de persistência. O core HTTP e o contrato gerado permanecem responsabilidade das próximas tarefas; as decisões de produto listadas acima não foram antecipadas.
