# HTTP IA e jornada de validação

Contrato gerado em [openapi.json](../packages/contracts/openapi.json), operação
`ai_explain`, integrada ao frontend em `#/app/valyra-ai` e no resumo semanal. O
serviço inclui cálculos do Finance, indicadores do radar Alpha e manchetes da
semana publicados até o corte, respeitando o limite de 64.000 bytes do prompt.
Configuração e fallback em [ai-client.md](ai-client.md), montagem em
[ai-service.md](ai-service.md) e limites da conferência em [ai-validation.md](ai-validation.md).

## Requisição

`POST /api/v1/ai/explain`, `Content-Type: application/json`:

```json
{
  "question": "Qual é meu saldo de referência e quais são as limitações?",
  "account_id": "00000000-0000-0000-0000-000000000101"
}
```

- `question`: texto não vazio após remover espaços das extremidades, até 2.000
  caracteres. `account_id`: UUID da conta pertencente ao usuário demo configurado.
- Campos extras são rejeitados, inclusive `context_data`, `user_id`, `as_of`,
  `history`, `evidence_ids` e `model`. Usuário e corte vêm do servidor.
- O contexto inclui apenas dados obtidos pelos services públicos; pergunta não
  fornece valores verificáveis. Não há histórico persistido ou streaming.
- A identidade demo usa `DEMO_USER_ID`; isso não implementa login/autenticação.
  CORS aceita a origem configurada em `CORS_ORIGIN`.

## Resposta de sucesso

HTTP `200`, schema `ExplainResponse`:

| Campo | Conteúdo |
| --- | --- |
| `answer` | Texto em português, após validação do domínio |
| `as_of` | Corte do servidor em ISO 8601 UTC |
| `evidences` | Evidências originais citadas e suas dependências, com origem, valor, unidade e período |
| `uncertainty` | `baixa`, `média` ou `alta` |
| `limitations` | Limitações originais do servidor e do modelo |

O frontend deve exibir limitações e incerteza junto da explicação, incluindo
quando o status for `200`. Não deve inferir saldo realizado/projeção a partir de
saldo de referência. Em `evidences`, dinheiro Finance usa
`value.kind="money"`, `amount_cents` inteiro seguro e `currency="BRL"`, sem
alterar o contrato dos endpoints Finance. O schema gerado descreve as variantes
de origem e valor (`finance_record`, `calculation` e `alpha_signal`), exibidas com
procedência e datas no frontend.

Sem evidências elegíveis, há `200` com mensagem determinística de insuficiência,
`evidences: []`, `uncertainty: "alta"` e limitações. Nesse caso não há chamada ao
provedor nem conversão de ausência em zero. Metadados de provedor/modelo,
`display_value` e o contexto completo não são campos da resposta.

## Falhas

O OpenAPI desta operação declara o envelope real, inclusive no `422`:

```json
{
  "error": {
    "code": "AI_INVALID_RESPONSE",
    "message": "Não foi possível validar a explicação",
    "details": {}
  }
}
```

| HTTP | Código | Tratamento |
| --- | --- | --- |
| 404 | `ACCOUNT_NOT_FOUND` | Conta inexistente ou alheia, antes de buscar contexto/chamar provedor |
| 422 | `VALIDATION_ERROR` | Corrigir o corpo; `details.errors` segue o envelope de validação existente |
| 500 | `AI_CONFIGURATION_ERROR` | Provedor recusou a configuração; corrigir o ambiente |
| 500 | `AI_CONTEXT_INVALID` | Contexto inválido ou prompt fora dos limites; corrigir a preparação no servidor |
| 502 | `AI_INVALID_RESPONSE` | Saída recusada, truncada, fora do schema ou rejeitada pelo domínio; não exibir como explicação |
| 503 | `AI_UNAVAILABLE` | Sem chaves, cota/crédito ou indisponibilidade após tentativas/fallback |

Erros IA retornam mensagens fixas, sem texto bruto do provedor, chaves, valores ou
IDs inventados. A rota não repete chamadas: tentativas limitadas e fallback
pertencem ao cliente. Evite repetição automática no frontend, pois uma nova
requisição pode consumir cota. A checagem lexical não comprova causalidade ou a
associação semântica entre uma frase e sua métrica.

## Jornada automática, sem chamadas pagas

```bash
make test-ai
# Com TEST_DATABASE_URL dedicado configurado:
make test
make lint
make openapi
python infra/check_docs.py
```

- `tests/ai/test_http.py`: pergunta HTTP → autorização Finance simulada → contexto
  sintético montado pelo serviço → cliente → domínio → serialização HTTP. Um dos
  testes usa SDK Gemini real com `httpx.MockTransport`, incluindo construção do
  prompt, parsing e validação, sem acessar a rede. Os demais substituem o cliente.
- Casos de rejeição cobrem número, data e fonte inventados, corpo com contexto
  forjado, contexto vazio, chaves ausentes e erros sanitizados. O contrato público
  e os schemas de erros são conferidos no OpenAPI.
- `tests/db/test_ai_http.py`: mesma entrada HTTP com PostgreSQL dedicado, conta e
  transação sintéticas, Finance real e cliente simulado. Confere origem dos
  registros/lotes e isolamento entre usuários.

`make test-ai` continua sem banco. Não há chave real nem modo de simulação
ativável pelo corpo HTTP. O teste com transporte simulado verifica a integração
técnica, sem atestar a qualidade das respostas de um modelo real.

## Verificação manual com provedor real

Esta etapa depende de chave configurada localmente e consome cota. Ela permanece
pendente enquanto o ambiente não tiver provedor configurado; os testes automáticos
não a substituem. Use somente a conta/dados sintéticos da demonstração.

1. Configure `.env` local conforme `.env.example`, com `GEMINI_API_KEY` e, se
   desejar reserva gratuita, `GROQ_API_KEY` e `OPENROUTER_API_KEY`; para fallback pago, `OPENAI_API_KEY`.
   Configure o limite de gasto externo antes de habilitar OpenAI, conforme ADR-0002.
   Não compartilhe as chaves.
2. Prepare o banco e a conta sintética, sem reset de dados:

   ```bash
   make sync
   docker compose up -d --wait postgres
   make migrate
   make seed
   make dev
   ```

3. Em outro terminal, execute a pergunta pelo HTTP. O seed cria a conta de ID
   abaixo, com saldo de referência sintético; não altera saldos já existentes:

   ```bash
   curl --silent --show-error --include \
     -X POST http://127.0.0.1:8000/api/v1/ai/explain \
     -H 'Content-Type: application/json' \
     --data '{"question":"Qual é meu saldo de referência e quais são as limitações?","account_id":"00000000-0000-0000-0000-000000000101"}'
   ```

4. Confira `200`, o corte UTC, o valor e a data originais da conta, a evidência
   citada, as limitações de resumo/projeções/Alpha e a distinção entre referência
   e saldo realizado. A resposta deve explicar somente dados presentes, sem
   números novos ou causalidade. Uma resposta rejeitada deve chegar como erro
   controlado; não afrouxe o domínio para fazer o smoke passar.
5. Opcionalmente importe `datasets/samples/transactions_demo.csv` pela rota
   Finance existente e repita. A explicação não deve tratar o recorte de
   movimentações como resumo completo nem gerar totais por conta própria.

Registre data, provedor habilitado, status HTTP e observações de qualidade no PR,
sem chaves ou conteúdo pessoal. Ter uma chave configurada não comprova execução
deste roteiro. Não há verificação manual com provedor real registrada nesta entrega.
