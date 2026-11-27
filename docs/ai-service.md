# Serviço de explicações IA

`ai/service.py` liga contexto, cliente LLM e validação de domínio. A rota
`POST /api/v1/ai/explain` publica essa operação; veja o [contrato HTTP](ai-http.md).
Não há persistência de conversas. Contrato na
[ADR-0011](adr/0011-contrato-evidencias-ia.md), configuração do provedor no
[guia do cliente](ai-client.md) e regras na [validação IA](ai-validation.md).

## Fluxo

1. `explain_for_account(session, user_id, request)` autoriza a conta com
   `finance.service.get_account_for_user`. Conta inexistente ou alheia gera o
   mesmo `ACCOUNT_NOT_FOUND`, antes de consultar contexto ou chamar o LLM.
2. Define `as_of` pelo relógio do servidor, em UTC, e monta o contexto usando
   somente o service público de Finance. Não importa models/repository de Finance.
3. `explain_with_context(request, context)` revalida o contexto e confere a conta.
   Monta `LLMRequest` com pergunta, contexto tipado e histórico opcional.
4. Executa o cliente uma vez. Timeout, tentativas e fallback pertencem ao cliente;
   o serviço não repete uma resposta inválida nem tenta corrigi-la.
5. `build_explain_response` valida a saída contra um snapshot original separado
   daquele enviado ao cliente. A resposta inclui evidências originais citadas e
   limitações do servidor; não inclui provedor/modelo.

`explain_with_context` recebe contexto **já autorizado pelo chamador** e não
consulta o banco. É a entrada para testes sintéticos e integração interna. O
router usa `explain_for_account`, obtém `user_id` da dependência da
API e aceita apenas `ExplainRequest`, nunca contexto ou produtor do navegador.

O serviço só lê e não faz commit/rollback da sessão recebida. O chamador controla
o ciclo da sessão. Erros do cliente e do domínio propagam sem expor uma resposta
rejeitada; seu mapeamento para HTTP está no router IA e no [contrato](ai-http.md).

## Contexto Finance disponível

- Saldo de referência: valor, data e identificação real da conta, com
  `basis="reference"`. Não é saldo realizado, lucro ou projeção.
- Até vinte movimentações recentes, na ordenação do service Finance, até a data
  de negócio do corte em `America/Sao_Paulo`. O contexto identifica transação,
  lote, valor com sinal, data e instante da versão consultada.
- O recorte registra limitação quando não contém todas as movimentações. Não é
  um resumo do período nem base para o modelo calcular totais ou percentuais.
- Nomes da conta e descrições livres do extrato não entram nesse contexto. O
  rótulo de cada movimentação traz só a categoria e os sinais recorrente/atípica.
- Valores incompatíveis com os inteiros seguros da IA são omitidos com limitação,
  sem arredondamento, conversão para string ou substituição por zero.
- Versões atualizadas depois do corte e datas de negócio futuras são omitidas
  com limitação. A consulta é do estado corrente; não implementa replay histórico.

### Cálculos Finance como evidência

Quando a conta tem lote de importação concluído até o corte, o serviço anexa
resultados já calculados pelos services públicos do Finance. O LLM só cita os
IDs; nenhum total, diferença ou percentual é produzido por ele. Cada item usa
`source.kind="calculation"`, `module="finance"`, `method_version="adr-0010"` e
aponta os lotes concluídos em `input_scope.import_batch_ids`.

| Evidência | `basis` | Origem |
| --- | --- | --- |
| `finance_realized_balance` | observed | `get_summary` da conta |
| `month_income`, `month_expenses`, `month_net` | observed | Resumo do mês corrente até hoje |
| `month_cat_<categoria>` (até 8) | observed | Totais por categoria do mês corrente |
| `prev_month_expenses`, `prev_cat_<categoria>` (até 8) | observed | Mês anterior fechado, para comparação |
| `budget_limit_`, `budget_spent_`, `budget_status_<categoria>` | reference / observed | `get_account_budget_report`, consumo desta conta |
| `projection_end_balance`, `projection_min_balance` | projected | `get_projection` de 30 dias, dia único futuro |
| `projection_variable_daily` | projected | Premissa de gasto variável da projeção |

Regras de corte:

- Lotes concluídos depois do corte não entram no escopo; sem lote concluído, os
  cálculos são omitidos com limitação.
- Se a data de negócio do Finance (`DEMO_TODAY` ou relógio) for posterior à
  data do corte, todos os cálculos são omitidos: seria antecipar dados.
- Com `DEMO_TODAY` anterior ao corte, só dias da projeção posteriores à data do
  corte entram como `projected`, porque o contrato exige período futuro.

Alpha ainda não tem integração e aparece sempre como limitação. Saldo zero
informado é evidência válida; ausência de dados não significa zero. Sem nenhuma
evidência elegível, o serviço retorna uma mensagem determinística de
insuficiência, com incerteza alta e limitações, sem chamar o provedor.

## Substituição nos testes e evolução

As dependências são funções internas, passadas por argumento:

| Argumento | Contrato |
| --- | --- |
| `client` | Recebe `LLMRequest` e retorna `LLMPayload` ou seu subtipo `LLMResponse` |
| `context_provider` | Recebe o `as_of` do servidor e retorna `EvidenceContext` tipado |
| `clock` | Retorna um instante com fuso; padrão é o relógio UTC |

`context_provider` substitui a montagem padrão, sem contornar a autorização. Deve
respeitar a conta, o corte recebido e um `built_at` já alcançado pelo relógio do
servidor. Pode capturar dependências em uma função/closure; não é um parâmetro
HTTP. Novos produtores deverão consultar os services públicos de resumo,
projeções ou Alpha quando existirem, preservar a procedência e atualizar as
limitações. Aceitar um contexto sintético Alpha não comprova integração real.

Um exemplo sem banco, chave ou chamada externa:

```python
from datetime import UTC, datetime

from valyra.ai.schemas import EvidenceContext, ExplainRequest
from valyra.ai.service import explain_with_context

now = datetime.now(UTC)
request = ExplainRequest(
    question="Quais informações estão disponíveis?",
    account_id="00000000-0000-0000-0000-000000000101",
)
context = EvidenceContext(
    account_id=request.account_id,
    as_of=now,
    built_at=now,
    limitations=["Exemplo sintético sem dados financeiros."],
)
response = explain_with_context(request, context)
assert response.evidences == []
assert response.uncertainty == "alta"
```

`tests/ai/test_service.py` usa contexto sintético e cliente simulado, sem banco.
`tests/db/test_ai_service.py` verifica a ligação ao Finance real e autorização em
PostgreSQL dedicado, com LLM simulado. Execute `make test-ai` para testes isolados
ou `make test` com `TEST_DATABASE_URL` dedicado para incluir a integração.

A validação lexical não comprova causalidade ou associação semântica entre frase
e métrica. Os limites e exemplos de avaliação permanecem em
[ai-validation.md](ai-validation.md).
