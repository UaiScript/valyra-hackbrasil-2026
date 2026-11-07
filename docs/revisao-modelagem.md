# Preparação da migração e seed — Issue #10

Registro de 07/11/2026 para a parte de dados da [Issue #7](https://github.com/UaiScript/valyra-hackbrasil-2026/issues/7) e preparação da [Issue #10](https://github.com/UaiScript/valyra-hackbrasil-2026/issues/10). Regras das tabelas ficam exclusivamente na [modelagem, seção 4](modelagem-db.md#4-finance); este documento não implementa banco ou API.

## Estado conferido

- Branch `willian/modelagem-de-dados`; a continuação preserva as alterações locais dos quatro documentos da revisão inicial. HEAD `2f61788` contém o merge do PR de modelagem (#6).
- Existem README, dois specs originais, `.env.example`, `.gitignore`, Compose com PostgreSQL 18 e CI de validação do PostgreSQL.
- Não foram encontrados `AGENTS.md` aplicáveis, `services/api/`, ORM, Alembic, seed, Makefile, contrato gerado ou verificadores documentais. `docs/api-design.md` foi criado nesta revisão; `docs/plano-1-implementacao.md`, citado nas Issues, não está disponível no checkout.
- Descrições e comentários das Issues #7–#10 e #13–#15 foram consultados; todas estavam acessíveis e sem comentários adicionais. O PR #6 está integrado e também não tem comentários adicionais; sua descrição mantém o design em revisão. Referências à base antiga de frontend não orientam esta entrega, que permanece documental.

## Dependências para implementar

1. **[Registrado, Issue #8]** Preparar `DATABASE_URL`, `TEST_DATABASE_URL`, `DEMO_USER_ID` e banco de testes separado. Nada disso está ainda em `.env.example`, exceto as variáveis atuais do serviço PostgreSQL. Não remover volumes ou dados para inicializar o ambiente.
2. **[Registrado, Issue #9]** Entregar `core.db.Base` com naming convention da modelagem; configuração `Settings`/`get_settings()`; `get_session()`; identificação do demo por `get_current_user_id()`; fixtures `client` e `db_session` usando `TEST_DATABASE_URL`.
3. **[Pendente de alinhamento]** Resolver as decisões da tabela abaixo que afetarem a migração. Elas complementam as regras explícitas da Issue #10 e não devem entrar como decisões tácitas no DDL. Fallback, hash e rejeição de precisão CSV já estão definidos nas Issues #13/#14.
4. **[Registrado, Issue #10]** Criar `User` em `core/db.py` e os cinco modelos Finance em `finance/models.py`; configurar Alembic e a migração inicial `0001_finance_inicial`. Usar a mesma metadata e importar todos os modelos no ambiente Alembic; revisar o autogenerate à mão. Não incluir Alpha, IA, login ou sessão de usuário.

## Decisões pendentes

| Decisão | Efeito na implementação | Etapa dependente |
|---|---|---|
| Saldo de abertura ou fechamento; proposta de fechamento na seção 4.2 da modelagem | Determina limite inferior da soma e interpretação da referência; as tarefas não fecharam essa convenção | Semântica da conta (#10/#15) e cálculo futuro de saldo |
| Persistir tentativas fracassadas após rollback | A transação única da #14 pode apagar o lote; definir se haverá registro em outra transação/mecanismo, sem prometer `failed` persistido | Importação (#14); não bloqueia a definição dos seis modelos |
| Exclusões e cascatas propostas | Confirmar `RESTRICT` das referências e cascata de rejeições; preservar contadores e histórico | Migração (#10) |
| FK composta entre transação e lote por conta | Confirmar `UNIQUE (id, account_id)` no lote e FK composta; impede relacionamentos entre contas diferentes | ORM/migração (#10) |
| Limites monetários de entrada, armazenamento e resposta | Evitar overflow de `BIGINT` e perda de precisão de inteiros JSON no JavaScript; tarefas não fixam teto nem erro para valor fora da faixa | Domínio (#13), HTTP (#14/#15) e eventual check (#10) |
| Demais refinamentos de integridade e conflitos de seed | Confirmar propostas de nulabilidade/defaults, checks de contadores/scores/timestamps, semântica de `completed_at` para `failed` e conflitos do seed; detalhes na modelagem e seção de seed abaixo | ORM, migração e seed (#10) |
| Completar schemas HTTP e semântica de consulta | #14 remete a spec ausente para campos completos dos lotes; fechar também resposta do PATCH, `null` no update, confiança preenchida, limites de datas e desempate da ordenação, conforme lacunas do contrato | Schemas/consultas (#14/#15) |
| Casos CSV não detalhados | Confirmar cabeçalho reordenado/colunas extras, sintaxe CSV malformada e numeração/texto de registros multilinha; não criar razões de erro adicionais sem alinhamento | Parser (#13) e tradução de erros (#14) |

**Resolvido nas fontes:** #13 define UTF-8/BOM, separador, datas, precisão CSV, linhas vazias, limites de arquivo/linhas, normalização, SHA-256, ocorrência inicial e fallback. #14 define valores iniciais da classificação e transação única. #15 define rotas de consulta, filtros, ordenação e saldo estritamente inteiro. Esses contratos têm fonte principal em [api-design.md](api-design.md); saem da lista de pendências. Preços médios e evidências monetárias de Alpha/IA continuam nas seções 5.4, 6 e 7 da modelagem.

## Seed previsto na Issue #10

Interface: `valyra.seed.run(session: Session) -> None`, com execução futura por `make seed`.

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

**[Proposta]** Se a conta de ID fixo já pertencer a outro usuário (por exemplo após mudança de `DEMO_USER_ID`), interromper com diagnóstico claro; não reatribuir a conta ou sobrescrever seu conteúdo. Se uma categoria existente tiver `kind` incompatível, sinalizar o conflito para alinhamento, preservando os dados.

## Aceite da implementação futura

Os itens abaixo são testes a implementar, **não verificações executadas nesta revisão**:

| Cenário | Resultado esperado |
|---|---|
| Migração em banco de testes vazio | `upgrade head` cria as seis tabelas; uma única cabeça |
| ORM versus migração | `alembic check` sem diferença; tipos, defaults, FKs, checks e índices revisados |
| Valores inválidos | Banco rejeita `amount_cents = 0`, enums inválidos, campos obrigatórios nulos e FKs inexistentes |
| Unicidade do hash | Mesma conta e hash são bloqueados, inclusive em lotes diferentes; outra conta pode usar o mesmo hash |
| Conta versus lote **[Proposta]** | Transação com conta diferente da conta do lote é rejeitada pela FK composta |
| Lote **[Proposta]** | Rejeitar contador negativo, soma acima do total, conclusão sem conciliação e combinação inválida de status/término |
| Scores e timestamps **[Proposta]** | Aceitar scores nulos ou nos limites 0 e 1; rejeitar fora do intervalo; rejeitar atualização/término anterior à criação |
| Exclusões **[Proposta]** | Bloquear remoção de referências em uso; remover rejeições só com lote cuja exclusão seja permitida |
| Seed em banco vazio | Usuário configurado, conta com ID/saldo/data esperados e exatamente 12 categorias |
| Seed repetido e dados existentes | Duas execuções mantêm quantidades e UUIDs; mudanças prévias em nome/saldo/data/categorias não são sobrescritas; registros ausentes são acrescentados |
| Conflitos do seed **[Proposta]** | Conta ligada a outro demo ou categoria com `kind` incompatível gera diagnóstico sem reatribuição/sobrescrita |
| Limpeza restrita a testes | Fixture exige `TEST_DATABASE_URL` explícita e destino de teste autorizado; nunca recorre a `DATABASE_URL` para limpar dados |

**[Proposta de proteção das fixtures]** Antes de qualquer `TRUNCATE` previsto na Issue #10, validar a identidade efetiva do banco e a configuração dedicada de testes; recusar destino compartilhado com a aplicação ou não autorizado. Usar somente as tabelas de dados do schema de testes, preservando o controle do Alembic. URL diferente por si só não prova que os bancos são distintos. Nenhuma limpeza é executada nesta etapa.

As Issues #13–#15 já especificam testes futuros de parser, hash, regras, reenvio, rejeições e operações HTTP. Conciliação com linhas persistidas, correção de categoria e cálculo de saldo também dependem dos respectivos services. O aceite da migração não comprova comportamentos de aplicação; nenhum desses testes foi executado nesta revisão documental.

## Próximo passo

Alinhar as propostas da seção 4 com o backend, aguardar as interfaces das Issues #8/#9 e então implementar somente os seis modelos, migração inicial, seed e testes da Issue #10. O exportador OpenAPI é responsabilidade da API; não gerar contrato manual nesta etapa.
