# ADR-0014 — Groq como reserva gratuita do Gemini

## Contexto

A [ADR-0002](0002-provedor-llm.md) definiu Gemini como primário e GPT-4o-mini como
fallback pago, e adiou outros provedores. Em 28/11/2026 a produção respondia
`AI_UNAVAILABLE` com `GEMINI_API_KEY` configurada, sintoma compatível com cota esgotada
do plano gratuito do Gemini. O fallback OpenAI exige crédito e limite de gasto, que o
time não tem configurados para a apresentação.

O Groq oferece plano gratuito sem cartão e uma API compatível com Chat Completions da
OpenAI em `https://api.groq.com/openai/v1`. Pela página de Structured Outputs do Groq,
consultada em 28/11/2026, `openai/gpt-oss-20b` e `openai/gpt-oss-120b` aceitam
`response_format` do tipo `json_schema`; os demais modelos têm só JSON Object Mode.
O plano gratuito tem limites por minuto e por dia, que mudam sem aviso; um prompt maior
que o limite de tokens por minuto recebe HTTP 413.

## Decisão

1. Ordem de provedores: Gemini → Groq → OpenAI, cada um habilitado pela própria chave
   (`GEMINI_API_KEY`, `GROQ_API_KEY`, `OPENAI_API_KEY`). Sem nenhuma chave, nenhuma rede
   é chamada.
2. O Groq usa o SDK `openai` já instalado, apontando a base para `GROQ_BASE_URL`
   (padrão `https://api.groq.com/openai/v1`), com o modelo de `GROQ_MODEL`
   (padrão `openai/gpt-oss-120b`).
3. O Groq recebe o mesmo JSON Schema e as mesmas instruções de sistema, em modo
   best-effort (`strict: false`), porque o strict mode depende do modelo escolhido.
   A resposta passa pela mesma validação Pydantic e pelo domínio da
   [ADR-0011](0011-contrato-evidencias-ia.md); nada muda nas regras de evidência.
4. Nos modelos `openai/gpt-oss*`, o cliente pede `reasoning_effort: low`, pelo mesmo
   motivo do nível baixo no Gemini: o raciocínio consome o teto de saída.
5. Indisponibilidade (rede, 429, 5xx, cota) passa ao próximo provedor habilitado.
   HTTP 413 do Groq passa ao próximo sem repetir.
6. Erro de configuração do Gemini (chave inválida, acesso negado, modelo desativado)
   passa ao Groq, que é gratuito, mas continua sem acionar a OpenAI paga, como na
   ADR-0002. Erro de configuração do próprio Groq (chave dele inválida) não bloqueia a
   OpenAI. Se nenhum provedor atender, um erro de configuração prevalece sobre
   indisponibilidade, para apontar o que precisa ser corrigido no ambiente.
7. `LLMParseError` (resposta truncada, recusada ou fora do schema) do Gemini não aciona
   reserva. Do Groq, que usa modo best-effort, passa à OpenAI se configurada.
8. Só dados sintéticos da demonstração vão ao Groq, como já vão ao Gemini. Antes de
   enviar dados reais, revisar a política de retenção e uso de dados do plano gratuito.

## Alternativas consideradas

- **DeepSeek:** bom em português e barato, mas pago; repetiria o problema de crédito.
- **OpenRouter:** porta para vários modelos, com modelos gratuitos de disponibilidade
  variável; útil como último recurso, mas adiciona um intermediário.
- **Só ativar a OpenAI:** exige crédito e limite de gasto antes da apresentação.
- **Strict mode no Groq:** restringe a troca de modelo por variável; a validação local
  já recusa saída fora do schema.

## Consequências

- Basta `GROQ_API_KEY` no Render para a Valyra AI continuar respondendo quando a cota
  do Gemini acabar. Trocar `GROQ_MODEL` segue o catálogo do Groq sem novo deploy.
- Os metadados internos de `LLMResponse.provider` passam a aceitar `groq`; a resposta
  HTTP pública não muda e não expõe provedor ou modelo.
- Contextos grandes podem passar do limite por minuto do plano gratuito; nesse caso a
  chamada cai para a OpenAI, se configurada, ou retorna `AI_UNAVAILABLE`.
- O Groq não oferece garantia de serviço no plano gratuito. Para reverter, basta remover
  `GROQ_API_KEY`; o comportamento volta ao da ADR-0002.

## Status

Aceita em 28/11/2026 por Willian, que pediu no chat do projeto o Groq como reserva
automática do Gemini.
