# ADR-0002 — Provedor LLM

## Contexto

O módulo `ai/` explica evidências estruturadas de Finance e Alpha. O registro
inicial de 09/11/2026 escolheu Gemini 2.5 Flash como primário e GPT-4o-mini como
fallback condicionado a chave e orçamento diário. A revisão de 14/11 constatou que
o campo de orçamento só habilitava chamadas sem contabilizar nem bloquear gasto, e
decidiu bloquear o fallback até existir controle persistente. A revisão de 14/11
(segunda) reativou o fallback com controle de gasto delegado ao painel da OpenAI.

A estabilização inicial do cliente e seu contrato interno não incluiu domínio de
validação, serviço, router HTTP ou persistência de conversas. O estado atual das
entregas seguintes está em [HTTP IA](../ai-http.md); conversas seguem sem persistência.
O prazo registrado para o hackathon é 30/11, com apresentação prevista para 27/11.

## Decisão

- **Primário:** Gemini 2.5 Flash, pelo SDK `google-genai`, com `GEMINI_API_KEY`.
  Sem a chave primária, tenta OpenAI se sua chave estiver presente; sem ambas,
  gera `LLMUnavailableError` sem chamar a rede.
- **Fallback:** GPT-4o-mini, pelo SDK `openai`, ativado quando `OPENAI_API_KEY`
  estiver presente. Controle de gasto é responsabilidade do **hard spend limit**
  configurado no projeto da OpenAI — não há contador interno na aplicação.
  Antes da apresentação, configurar "Enforce a hard limit" no painel:
  https://platform.openai.com/settings/organization/limits
- Com Gemini configurado, o fallback é acionado apenas por `LLMUnavailableError`
  do Gemini (indisponibilidade ou cota esgotada). `LLMParseError` e `LLMConfigurationError` não o acionam.

### Limites de execução

| Configuração | Padrão | Faixa |
| --- | --- | --- |
| `LLM_TIMEOUT_SECONDS` | 30 | 1–120 segundos por operação HTTP |
| `LLM_MAX_ATTEMPTS` | 2 | 1–3 tentativas totais |
| `LLM_MAX_OUTPUT_TOKENS` | 2048 | 128–8192 tokens |

O prompt serializado tem teto de 64.000 bytes UTF-8, incluindo pergunta, contexto
e histórico. JSON não serializável ou não finito é recusado antes da rede.
Os limites são operacionais e configuráveis; não definem limiares financeiros.
Timeout HTTP não é um prazo global de toda a chamada: fases de rede e novas
tentativas podem aumentar o tempo total. Entre tentativas há espera curta limitada.

O SDK não repete por conta própria. A aplicação repete apenas falhas de transporte,
HTTP 408/409/429 e 5xx. Erros permanentes, como 400/401/403, geram
`LLMConfigurationError` sem repetição. Na OpenAI, HTTP 429 por falta de crédito
ou limite financeiro/uso atingido gera `LLMUnavailableError` sem repetição;
429 por limite transitório de requisições segue o teto de tentativas.

Ambos os provedores recebem JSON Schema derivado do Pydantic; OpenAI usa
`json_schema` com `strict: true`. Resposta vazia, recusada,
truncada ou fora do schema gera `LLMParseError` sem nova tentativa. Os clientes
HTTP são fechados ao terminar. Chaves usam `SecretStr`; logs da aplicação não
incluem prompts, respostas brutas nem mensagens de erro vindas do SDK.

### Fronteiras de confiança

- Só `ai/` chama o LLM. Metadados de provedor/modelo vêm da aplicação.
- O LLM explica números previamente calculados; não inventa números, fontes,
  probabilidades ou causalidade. Pergunta e histórico não são evidências.
- **Schema válido não é evidência verdadeira.** Conferência dos números e fontes
  contra o contexto original e do corte `published_at/as_of` ocorre no domínio
  descrito na [validação IA](../ai-validation.md). A checagem lexical não certifica
  causalidade, associação semântica das métricas ou veracidade externa.
- A [ADR-0011](0011-contrato-evidencias-ia.md), aprovada em 17/11/2026, define
  o contexto tipado e a resposta do modelo por IDs de evidências. O modelo não
  devolve cópias dos valores/fontes. Valores monetários Finance usam centavos;
  preços monetários Alpha e frações de centavo continuam fora do recorte.
  Schemas públicos e a rota `POST /api/v1/ai/explain` estão registrados no OpenAPI;
  contrato e verificação em [HTTP IA](../ai-http.md).

## Alternativas consideradas

- **Contador diário em memória:** não protege contra reinícios ou múltiplos processos.
- **Contador persistente no PostgreSQL:** não autorizado neste recorte por custo de
  implementação incompatível com o prazo; registrado como possível evolução futura.
- **Fallback permanentemente bloqueado:** descartado; o objetivo do fallback é
  exatamente cobrir indisponibilidade ou esgotamento de cota do Gemini.
- **Outro provedor ou execução local:** adiados para manter o escopo do hackathon.

## Consequências

- Indisponibilidade simultânea de Gemini e OpenAI gera `LLMUnavailableError`; o
  consumidor deve mostrar erro controlado.
- Configurar hard spend limit na OpenAI é **pré-requisito de ambiente** antes da
  apresentação, não uma garantia implementada no código.
- API, banco e CI continuam utilizáveis sem chave de LLM. Testes usam SDK real com
  transporte HTTP simulado e não fazem chamadas externas ou pagas.
- Referências: [Google Gen AI SDK](https://github.com/googleapis/python-genai),
  [OpenAI spend limits](https://developers.openai.com/api/docs/guides/spend-limits).

## Status

**Aceita em 14/11/2026 (segunda revisão).** Gemini como primário; GPT-4o-mini como
fallback ativo por presença de chave, com controle de gasto pelo painel da OpenAI.
Não aprova precisão monetária Alpha/IA, persistência de conversas nem as demais
propostas dos specs.
