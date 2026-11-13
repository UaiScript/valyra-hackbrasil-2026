# Contrato de dados — Finance

> **Issue #15 (10/11/2026):** consultas de contas (com PATCH), transações e categorias implementadas; o contrato soma 7 operações Finance e `system_health`. Decisões de consulta que a especificação deixava abertas estão marcadas como provisórias em [api-design](api-design.md#operações-http--issues-14-e-15).

> **Issue #14 (10/11/2026):** importação de CSV e consulta de lotes implementadas em `services/api/src/valyra/finance/` (router, service, repository, schemas), com OpenAPI regenerado. Consultas da #15 continuam planejadas. Estado atual em [arquitetura](architecture.md).

> **Integração #11/#12 (08/11/2026):** persistência/seed #17, domínio CSV #19 e core HTTP mínimo (/health, erros, paginação, OpenAPI) estão implementados nesta branch. Endpoints Finance #14/#15, projeções e módulos analíticos continuam planejados. A [arquitetura atual](architecture.md) e o [registro de integração](integracao-11-12.md) atualizam o estado; notas históricas anteriores abaixo descrevem suas respectivas etapas.

> **Atualização de 07/11/2026 — Issues #7/#10.** Contratos registrados nas Issues [#9](https://github.com/UaiScript/valyra-hackbrasil-2026/issues/9), [#10](https://github.com/UaiScript/valyra-hackbrasil-2026/issues/10), [#13](https://github.com/UaiScript/valyra-hackbrasil-2026/issues/13), [#14](https://github.com/UaiScript/valyra-hackbrasil-2026/issues/14) e [#15](https://github.com/UaiScript/valyra-hackbrasil-2026/issues/15). Persistência e seed foram implementados na etapa #10; endpoints, schemas HTTP e domínio CSV abaixo continuam previstos. O [registro de implementação](revisao-modelagem.md) informa a validação disponível.

## Representação dos dados

- Dinheiro: PostgreSQL `BIGINT`, nome `*_cents`; na API, número inteiro JSON em centavos de BRL. `accounts.balance_cents` e `transactions.amount_cents` são os campos registrados. Entrada positiva, saída negativa, zero proibido em transação. Conversão e cálculo sem `float`.
- Identificadores: `UUID` no backend e strings UUID no JSON, inclusive FKs. IDs de usuário e conta demo são fornecidos pelo seed; não são IDs de sessão.
- Datas de negócio (`date`, `balance_as_of`): `DATE`, JSON `YYYY-MM-DD`, sem fuso. Instantes (`created_at`, `updated_at`, `completed_at` quando presentes): `TIMESTAMPTZ`, ISO 8601 com fuso, normalizados para UTC, por exemplo `2026-11-07T17:00:00Z`.
- **Banco/ORM:** tipos, nulabilidade, defaults e constraints têm fonte única na [modelagem, seção 4](modelagem-db.md#4-finance); os refinamentos autorizados para a #10 estão no código. **CSV:** contrato de entrada textual abaixo. **HTTP:** somente os campos explicitados nos schemas desta página são previstos como públicos; uma coluna do banco não implica exposição na API. Propostas de comportamento ainda identificadas na modelagem continuam sujeitas a alinhamento.

Exemplos isolados de campos, **não payloads de endpoint**:

```json
{"balance_cents": 500000, "balance_as_of": "2026-11-01"}
```

```json
{"amount_cents": -12990, "date": "2026-11-02"}
```

São R$ 5.000,00 de referência e saída de R$ 129,90. Formatação em reais pertence à apresentação.

A busca por strings sugerida na Issue #7 também captura `balance_as_of`, campo de data cuja serialização é string ISO. A validação deve distinguir datas de campos monetários.

## Interfaces internas e estado atual

Implementados: configuração, `Base`/`User`, engine/sessão, modelos Finance e seed. Demais interfaces do core HTTP e do domínio CSV seguem previstas, sem implementação nesta etapa.

| Origem | Interface | Campos / tipos registrados |
|---|---|---|
| Issue #9 | `Settings` / `get_settings()` | `database_url: str`, `cors_origin: str`, `demo_user_id: UUID`; configuração de ambiente da Issue #8 |
| Issue #9 | `get_current_user_id() -> UUID` | Retorna o usuário demo configurado, sem autenticação ou isolamento por sessão |
| Issue #9 | `get_session() -> Iterator[Session]` | Sessão de banco; não representa sessão de usuário |
| Mínimo da #9 para #10 | `Base`, `get_engine()`, `get_session_factory()` | Uma metadata e uma infraestrutura de conexão/sessão; sem camada HTTP |
| Issue #9 | `Page[T]` | `items: list[T]`, `total: int`, `limit: int`, `offset: int` |
| Issue #9 | `PageParams` | `limit: int = 50`, entre 1 e 200; `offset: int = 0`, não negativo |
| Issue #9 | `AppError` | `code: str`, `message: str`, `status_code: int`, `details: dict \| None = None`; resposta `{"error":{"code":"NOT_FOUND","message":"Recurso não encontrado","details":{}}}` no exemplo da tarefa |
| Issue #10 | ORM | `User`, `Account`, `ImportBatch`, `ImportRejection`, `Category`, `Transaction`; não define por si só schemas HTTP |
| Issue #10 | `seed.run(session: Session) -> None` | Seed idempotente; dados e aceite em [revisao-modelagem.md](revisao-modelagem.md) |

## Entrada CSV e domínio — Issue #13

| Item | Contrato registrado |
|---|---|
| Arquivo | UTF-8 com ou sem BOM (`utf-8-sig`); separador vírgula; leitura com `csv.reader`; LF e CRLF aceitos |
| Cabeçalho | `date,description,amount`; comparar nomes após `strip().lower()`, aceitando espaços e maiúsculas |
| `date` | Data de negócio `YYYY-MM-DD`; `03/11/2026` é rejeitada |
| `description` | Texto original, obrigatório; somente espaços gera `empty_description`. A versão normalizada serve ao hash e às regras, sem substituir a original |
| `amount` | Texto em reais decimais com sinal; padrão `^-?\d+(\.\d{1,2})?$`. Ex.: `-89.90` → `-8990` centavos; `1500` → `150000`; `0.5` → `50` |
| Conversão | `int(Decimal(texto) * 100)`, sem `float`; rejeitar vírgula decimal, mais de duas casas e valor zero, sem arredondamento |
| Limites | `MAX_FILE_BYTES = 1_048_576` (1 MiB), verificado pelo router; `MAX_ROWS = 5000` registros de dados, verificado pelo domínio |
| Contagem | Cabeçalho não conta; linhas totalmente vazias são ignoradas; arquivo só com cabeçalho tem `total = 0`. `total` conta registros válidos e rejeitados |
| Rejeição | `line_number` é a linha física do arquivo, com cabeçalho na linha 1; `raw_line` mantém o texto rejeitado, sem a quebra final no exemplo da Issue #14 |

Exemplo de arquivo:

```csv
date,description,amount
2026-11-03,Supermercado BH,-89.90
2026-11-05,Salario ACME,6000.00
```

Motivos de rejeição de **linha**: `invalid_date`, `invalid_amount`, `zero_amount`, `empty_description`, `wrong_column_count`. Ex.: `2026-11-03,Mercado,-89,90` tem colunas demais (`wrong_column_count`); o valor `"-89,90"` entre aspas mantém três colunas, mas gera `invalid_amount`.

Interfaces puras previstas em `finance/domain.py`:

| Interface | Campos / resultado |
|---|---|
| `ParsedRow` (dataclass imutável) | `line_number: int`, `date: date`, `description: str`, `amount_cents: int` |
| `RejectedRow` (dataclass imutável) | `line_number: int`, `reason: str`, `raw_line: str` |
| `ParseResult` (dataclass imutável) | `rows: list[ParsedRow]`, `rejected: list[RejectedRow]`, `total: int` |
| `parse_csv(content: bytes) -> ParseResult` | Leitura, validação e conversão; erros de arquivo usam `CsvFormatError.code` |
| `normalize_description(text: str) -> str` | NFKD para remover acentos, minúsculas, espaços colapsados e `strip`; `"  Café  da  MANHÃ "` → `"cafe da manha"` |
| `compute_row_hashes(account_id: UUID, rows: list[ParsedRow]) -> list[str]` | SHA-256 hexadecimal, conforme expressão abaixo |
| `categorize(description: str, amount_cents: int) -> str` | Slug da primeira regra correspondente, ou fallback por sinal |

Entrada exata do hash registrada na tarefa:

```text
f"{account_id}|{date.isoformat()}|{amount_cents}|{normalize_description(description)}|{ocorrencia}"
```

A ocorrência começa em **1**, por combinação de data, valor e descrição normalizada dentro do arquivo. A [modelagem, seção 4.3](modelagem-db.md#43-categorização-deduplicação-e-cálculos) registra o alcance e a limitação dessa deduplicação.

`CATEGORY_RULES` é uma lista ordenada, com correspondência por **palavra inteira** na descrição normalizada (`99` não casa com `1999`). Regras de despesa valem somente para valor negativo; `salario`, somente para positivo. Ordem e palavras-chave mínimas da Issue #13:

| slug | palavras-chave |
|---|---|
| `mercado` | `supermercado`, `mercado`, `atacadao`, `hortifruti` |
| `restaurantes` | `restaurante`, `ifood`, `lanchonete`, `padaria` |
| `transporte` | `uber`, `99`, `combustivel`, `posto`, `estacionamento` |
| `moradia` | `aluguel`, `condominio` |
| `contas-e-servicos` | `energia`, `cemig`, `agua`, `copasa`, `internet`, `telefone` |
| `saude` | `farmacia`, `drogaria`, `hospital`, `clinica` |
| `educacao` | `escola`, `faculdade`, `curso`, `livraria` |
| `lazer` | `cinema`, `show`, `ingresso` |
| `assinaturas` | `netflix`, `spotify`, `prime`, `disney` |
| `salario` | `salario`, `folha` |

Sem correspondência: saída usa `outros`; entrada usa `outras-receitas`. A Issue #14 fixa, para toda transação importada, `category_id = predicted_category_id`, `category_source = 'rule'`, `category_confidence = NULL`, `is_recurring = false` e `anomaly_score = NULL`.

## Operações HTTP — Issues #14 e #15

IDs de caminho e filtros de identificação usam UUID. Upload usa `multipart/form-data`, campo `file`, exemplificado como `text/csv`; nome e conteúdo chegam ao service. Não foi especificada validação adicional por extensão ou MIME.

| Método e caminho | operationId | Entrada / saída registrada |
|---|---|---|
| `POST /api/v1/finance/accounts/{account_id}/import-batches` | `finance_create_import_batch` | Arquivo `file`; **201**, `ImportBatchOut`, com `rejections`, sem `alerts_created` |
| `GET /api/v1/finance/import-batches` | `finance_list_import_batches` | `Page[ImportBatchSummaryOut]`; `created_at` decrescente; itens sem `rejections` |
| `GET /api/v1/finance/import-batches/{id}` | `finance_get_import_batch` | `ImportBatchOut`, incluindo rejeições; lote ausente gera 404 |
| `GET /api/v1/finance/accounts` | `finance_list_accounts` | `Page[AccountOut]`, contas do usuário demo |
| `PATCH /api/v1/finance/accounts/{id}` | `finance_update_account` | `AccountUpdate`; **200**, teste confirma `balance_cents` na resposta; schema completo da resposta não explicitado |
| `GET /api/v1/finance/transactions` | `finance_list_transactions` | `Page[TransactionOut]`; data decrescente; filtros abaixo |
| `GET /api/v1/finance/categories` | `finance_list_categories` | `Page[CategoryOut]`; ordem por `kind` e `name` |

Todas as listagens usam `Page[T]`/`PageParams` da Issue #9: `items`, `total`, `limit` (default 50, de 1 a 200), `offset` (default 0, não negativo). Filtros registrados para transações: `account_id`, `date_from`, `date_to`, `category_id`. Sem `account_id`, consultar todas as contas do usuário demo. Datas de filtro seguem `YYYY-MM-DD`; inclusão dos limites, tratamento de intervalo invertido e desempate de ordenação não foram explicitados. Não há filtro de lote adicional registrado na Issue #14.

### Schemas públicos confirmados

| Schema | Campos confirmados e tipos |
|---|---|
| `AccountOut` | `id: UUID`, `name: str`, `balance_cents: int`, `balance_as_of: date` |
| `AccountUpdate` | `name: str`, `balance_cents: StrictInt`, `balance_as_of: date`, todos **omitíveis**. `10.5` e `"1000"` para saldo geram 422, sem coerção. Omissão não define aceitação de `null`; isso permanece pendente |
| `CategoryOut` | `id: UUID`, `slug: str`, `name: str`, `kind: expense \| income` |
| `TransactionOut` | `id: UUID`, `date: date`, `description: str`, `amount_cents: int`, `category: {id: UUID, slug: str, name: str}`, `category_source: rule \| model \| user`, `category_confidence` (nulo na importação), `predicted_category_id: UUID` |
| `ImportRejectionOut` | `line_number: int`, `reason: str`, `raw_line: str`; sem ID interno no exemplo testado |
| `ImportBatchOut` | Confirmados: `id: UUID`, `status: processing \| completed \| failed`, `rows_total: int`, `rows_imported: int`, `rows_duplicated: int`, `rows_rejected: int`, `rejections: list[ImportRejectionOut]`; `alerts_created` excluído |
| `ImportBatchSummaryOut` | Resumo sem `rejections`; implementado na #14 com `id`, `status` e os quatro contadores, sujeito à lacuna abaixo |

**Lacuna da fonte:** a Issue #14 remete à seção 3.1 de um spec de API que não estava disponível no checkout antes desta revisão. A lista completa de campos de lote, a presença/nulabilidade de seus timestamps no HTTP e o schema completo do resumo não são recuperáveis dessa referência. Não se presume expor `account_id`, `file_name`, timestamps ou todas as colunas do ORM. **[Implementado, #14]** Os schemas de lote expõem somente os campos confirmados; ampliar exige alinhar com o frontend e regenerar o contrato. Para `category_confidence` preenchida, o intervalo de domínio está na modelagem; a representação JSON ainda não está explicitada nas tarefas.

**[Provisório, implementado na #15 — confirmar com o time]** Lacunas acima resolvidas pela implementação, sem decisão formal: resposta do PATCH é `AccountOut`; `null` explícito no `AccountUpdate` e campos desconhecidos geram 422 `VALIDATION_ERROR`; `balance_cents` fora da faixa BIGINT gera 422; `balance_as_of` só aceita texto `AAAA-MM-DD`; filtros de data são inclusivos e intervalo invertido devolve lista vazia; transações empatadas na data ordenam por `created_at` e `id` decrescentes; filtro `account_id` de outro usuário responde 404 `ACCOUNT_NOT_FOUND`; `category_confidence` preenchida sai como string decimal (sempre nula na importação por regras).

`TransactionOut` não expõe `account_id`, `import_batch_id`, `row_hash`, `created_at`, `updated_at`, `is_recurring`, `recurrence_key` ou `anomaly_score`; `is_anomaly` também não integra o schema, conforme o teste da Issue #15. Não há operação de correção de categoria ou resumo/projeção de saldo nas tarefas consultadas.

Exemplo de item `TransactionOut` para a primeira linha do CSV acima; UUIDs ilustrativos, sem definir IDs do seed de categorias:

```json
{
  "id": "00000000-0000-0000-0000-000000000201",
  "date": "2026-11-03",
  "description": "Supermercado BH",
  "amount_cents": -8990,
  "category": {"id": "00000000-0000-0000-0000-000000000301", "slug": "mercado", "name": "Mercado"},
  "category_source": "rule",
  "category_confidence": null,
  "predicted_category_id": "00000000-0000-0000-0000-000000000301"
}
```

Exemplo de corpo `AccountUpdate` da Issue #15:

```json
{"balance_cents": 421050, "balance_as_of": "2026-11-07"}
```

### Erros registrados

Envelope da Issue #9: `{"error":{"code":"...","message":"...","details":{}}}`. Mensagens textuais não fixadas nas tarefas não são definidas aqui.

| HTTP | Código | Situação / origem |
|---|---|---|
| 413 | `FILE_TOO_LARGE` | Upload acima de 1 MiB; router lê no máximo `MAX_FILE_BYTES + 1` bytes (#14) |
| 422 | `CSV_ENCODING` | Falha de decodificação UTF-8 (#13/#14) |
| 422 | `CSV_MISSING_COLUMNS` | Cabeçalho sem as colunas necessárias (#13/#14) |
| 422 | `CSV_TOO_MANY_ROWS` | Mais de 5000 registros de dados (#13/#14) |
| 404 | `ACCOUNT_NOT_FOUND` | Conta inexistente ou fora do usuário demo via `get_account_for_user` (#14); PATCH ausente tem 404 testado na #15 |
| 404 | `IMPORT_BATCH_NOT_FOUND` | Consulta de lote ausente (#14) |
| 422 | `VALIDATION_ERROR` | Validação HTTP/Pydantic: paginação inválida e `balance_cents` não inteiro (#9/#15); `details.errors` contém os erros |

Rejeições de linha são dados de uma importação concluída, sem promover cada rejeição a erro HTTP. **[Lacuna do contrato gerado]** O OpenAPI ainda não declara as respostas 404/413 nem o envelope de erro; o 422 aparece com o schema padrão do FastAPI, diferente do envelope real. Falhas técnicas e persistência de tentativas estão na [modelagem, seção 4.5](modelagem-db.md#45-transação-e-falhas-da-importação).

## Caminho dos dados

| Origem | Transformação registrada | Persistência | Saída HTTP prevista |
|---|---|---|---|
| CSV `amount` em reais decimais | Conversão decimal exata (#13) | `transactions.amount_cents BIGINT` | `TransactionOut.amount_cents`, inteiro JSON |
| CSV `date` | Validar data ISO (#13) | `transactions.date DATE` | `TransactionOut.date`, string ISO |
| CSV `description` | Conservar original; normalizar cópia para regras/hash (#13) | `transactions.description TEXT`; sem coluna de descrição normalizada | `TransactionOut.description` original |
| Conta da rota + data/valor/descrição normalizada + ocorrência | SHA-256 (#13) | `transactions.row_hash`, UNIQUE por conta | Hash e ocorrência não expostos; sem coluna nova para ocorrência |
| Regra ou fallback por sinal | Slug → categoria existente do seed (#13/#14) | FKs atual/prevista iguais, fonte `rule`, confiança nula | `category`, `predicted_category_id`, `category_source`, `category_confidence` |
| Nome/conteúdo do upload e conta da rota | Service cria lote e associa transações (#14) | `import_batches`; `transactions.import_batch_id` | Lote nas rotas de importação/consulta; FK de origem não exposta em `TransactionOut` |
| Registro CSV inválido | Motivo, linha física e texto original (#13/#14) | `import_rejections`, ligado ao lote | `ImportRejectionOut` em `ImportBatchOut.rejections`; ausente no resumo |
| `ParseResult.total`, válidas e inseridas | Contar rejeições, inseridas e duplicadas (#14) | Quatro contadores do lote | Contadores confirmados em `ImportBatchOut` |
| Criação/conclusão do lote | Preencher estado e término (#14) | `status`, `created_at`, `completed_at` | `status` confirmado; timestamps HTTP aguardam contrato completo |
| Seed ou `AccountUpdate` | Seed idempotente (#10); PATCH valida inteiro estrito (#15) | `accounts.balance_cents`, `balance_as_of` | Referência em `AccountOut`; não representa saldo realizado calculado |
| Metadados de recorrência/anomalia | Inicialização da importação (#14); cálculos posteriores fora destas tarefas | `is_recurring = false`, `anomaly_score = NULL`; `recurrence_key` permanece opcional no desenho | Campos não expostos em `TransactionOut` |

Pendências restantes e suas etapas dependentes têm registro único em [revisao-modelagem.md](revisao-modelagem.md#decisões-pendentes). Preços médios e evidências Alpha/IA continuam nas seções 5.4, 6 e 7 da modelagem. A Issue #9 prevê gerar `packages/contracts/openapi.json` pela API; não editar ou criar esse contrato manualmente.
