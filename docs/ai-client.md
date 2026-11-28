# Cliente IA — fundação

O cliente implementa Gemini como primário e OpenAI como fallback
([ADR-0002](adr/0002-provedor-llm.md)). A
[ADR-0011](adr/0011-contrato-evidencias-ia.md), aprovada em 17/11/2026, define os
contratos tipados e a resolução de citações implementados neste incremento.
O [serviço IA](ai-service.md) já consulta Finance, executa o cliente e valida a
resposta. A [rota HTTP](ai-http.md) já está disponível, integrada ao Finance,
radar Alpha e manchetes da semana; conversa persistida continua pendente.
O domínio confere citações, metadados temporais e reprodução lexical de números.
Ele não comprova semântica, causalidade ou veracidade externa; regras e limites em
[ai-validation.md](ai-validation.md). O cliente isolado retorna payload bruto do
modelo: use o serviço para obter uma resposta validada pelo domínio.

## Configuração

Execute `make sync` na raiz. Configure `GEMINI_API_KEY` em seu `.env` local.
O `.env.example` deixa as chaves vazias para a API e o CI funcionarem sem provedor.
Com `OPENAI_API_KEY`, há fallback em caso de indisponibilidade/cota do Gemini;
sem chave Gemini, OpenAI pode atender diretamente. Nunca versione as chaves.

O modelo Gemini vem de `GEMINI_MODEL` (padrão `gemini-3.8-flash`). O Google
desativa versões antigas; em novembro de 2026 havia relatos no fórum do Google
de 404 para `gemini-2.5-flash`, sintoma que aparece como `AI_CONFIGURATION_ERROR`.
Trocar a variável basta para seguir outro modelo. Na família 2.5 o cliente
desliga o raciocínio (`thinking_budget=0`); na 2.0 não envia configuração de
raciocínio; da família 3 em diante usa `thinking_level` baixo, porque esses
modelos não oferecem desligamento. Use uma chave do Google AI Studio (Gemini
Developer API); chaves criadas no Google Cloud dependem da Generative Language
API ativada no projeto.

Configure o hard spend limit no projeto da chave OpenAI antes da apresentação.
Esse limite é externo à aplicação, mensal e sujeito a pequeno excedente durante
sua propagação. Guia: [OpenAI spend limits](https://developers.openai.com/api/docs/guides/spend-limits).
Não há contador de gasto diário interno.

Os padrões são 30 segundos por operação HTTP, duas tentativas totais por provedor
e 4.096 tokens de saída, incluindo o raciocínio do modelo.
Variáveis: `LLM_TIMEOUT_SECONDS`, `LLM_MAX_ATTEMPTS`,
`LLM_MAX_OUTPUT_TOKENS` (revise valores antigos de 2048 já definidos no
ambiente, que deixam pouco espaço ao JSON). Não são um prazo global para todas as tentativas.
O prompt aceita até 64.000 bytes UTF-8. O serviço seleciona evidências inteiras
com limitação explícita antes de chamar o cliente; chamadas diretas ao cliente
com contexto ainda grande falham antes da rede. A medida inclui a serialização
real de pergunta, contexto, histórico e dicas de apresentação.

## Contratos e confiança

| Modelo | Uso |
| --- | --- |
| `ExplainRequest` | Entrada HTTP: somente pergunta e conta, sem valores/contexto/usuário |
| `EvidenceContext` | Contexto interno montado pelo servidor após autorizar a conta |
| `LLMRequest` | Pergunta, contexto tipado obrigatório e histórico com papéis user/assistant |
| `LLMPayload` / `LLMResponse` | Texto, IDs citados, incerteza e limitações; metadados do provedor são internos |
| `ExplainResponse` | Resposta do serviço com evidências originais recuperadas pelo servidor |

- Dinheiro Finance usa inteiro `amount_cents`, BRL e faixa exata do JavaScript.
  O schema recusa excedentes; o service omite a métrica com limitação,
  sem arredondar ou alterar os endpoints Finance existentes.
- Decimais não monetários usam texto exato, unidade registrada e sem `float`.
  Preços monetários Alpha e frações de centavo ficam fora do recorte.
- Procedência é registro Finance, cálculo com método/entradas ou sinal Alpha com
  fonte/revisão/publicação identificadas. Não há publicação fictícia no Finance.
- Contexto recusa datas contraditórias, registros/sinais posteriores ao corte,
  IDs repetidos, dependências ausentes/cíclicas e múltiplas revisões do mesmo sinal.
  Selecionar a revisão correta no banco continua responsabilidade do futuro Alpha.
- Histórico: até dez mensagens de 4.000 caracteres. Contexto: até cem evidências e
  vinte limitações, respeitando também o teto de bytes. Nunca truncar silenciosamente.
- O servidor fornece `display_value` calculado apenas no prompt. O modelo cita IDs;
  não devolve ou altera valores, datas ou URLs. A resposta pública não contém essa
  dica interna nem os metadados de provedor/modelo.
- `ai.domain.build_explain_response(context, payload)` rejeita citações desconhecidas,
  preserva limitações do servidor, inclui entradas dos cálculos e confere literais
  do texto com unidade contra essas evidências. Schemas não comprovam propriedade da conta,
  licenciamento da fonte nem ausência de afirmações causais indevidas.
- Finance histórico permanece indisponível até existir suporte a versões/snapshots.

## Testes sem chamadas externas

```bash
make sync
make lint
make test-ai
```

Os testes isolados usam SDKs reais com transporte HTTP simulado ou cliente injetado,
sem chaves reais ou banco.
Cobrem schema enviado, citações, unidades, precisão, corte temporal, conexões,
falhas permanentes/transitórias e respostas incompletas/recusadas. Falta de crédito
ou limite financeiro OpenAI não é repetido. Suíte integrada exige banco dedicado,
conforme [CONTRIBUTING.md](../CONTRIBUTING.md); não apague volumes para validá-la.

## Verificação manual opcional

Este exemplo de baixo nível faz uma chamada externa e pode consumir a cota da conta. Usa contexto
vazio, sintético, sem consulta ao banco; não comprova autorização de uma conta real.
Execute só com uma chave configurada localmente:

```bash
uv run --locked --env-file "$PWD/.env" --directory services/api python - <<'PY'
from datetime import UTC, datetime
from valyra.ai.llm_client import call_llm
from valyra.ai.schemas import EvidenceContext, LLMRequest

now = datetime.now(UTC)
context = EvidenceContext(
    account_id="00000000-0000-0000-0000-000000000101",
    as_of=now,
    built_at=now,
    limitations=["Não há dados financeiros neste exemplo sintético."],
)
result = call_llm(LLMRequest(
    question="Quais limitações existem sem dados financeiros?",
    context_data=context,
))
print(result.model_dump_json(indent=2))
PY
```

A configuração do projeto continua exigindo `DATABASE_URL`, embora o cliente não
abra conexão. Saída esperada: insuficiência de dados, incerteza alta, sem citações.
Esta documentação não afirma que o comando foi executado com chave real. O
serviço, ao contrário desta chamada direta ao cliente, responde a contexto vazio
sem usar o provedor; veja o [exemplo sem chamada externa](ai-service.md).

## Falhas e próximas entregas

- `LLMUnavailableError`: chaves ausentes, tentativas transitórias esgotadas ou
  crédito/limite financeiro OpenAI atingido.
- `LLMConfigurationError`: configuração recusada; não repetir automaticamente.
- `LLMParseError`: saída inválida, truncada ou recusada; não apresentar como válida.
- `ValidationError`: entrada/contexto incompatível com o contrato aprovado.
- `EvidenceContextError`: snapshot original inválido ou incompatível com o corte.
- `EvidenceReferenceError`: citações inválidas ou ausência de citações sem limitação/incerteza alta.
- `UnsupportedClaimError`: número, unidade, data ou URL sem suporte nas evidências citadas.
- `LLMPromptError` (`ValueError`) antes da rede: serialização ou tamanho do prompt inválido.

Próximos passos: integrar os services de
resumo, projeções e Alpha quando disponíveis com seleção de revisões,
e validar a qualidade com o provedor real configurado. O [contrato HTTP](ai-http.md)
já está no OpenAPI. A checagem lexical não equivale a validação semântica completa.
