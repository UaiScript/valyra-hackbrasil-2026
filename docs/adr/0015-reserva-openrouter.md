# ADR-0015 — OpenRouter como reserva de emergência

## Contexto

A [ADR-0014](0014-reserva-groq.md) colocou o Groq como reserva gratuita entre Gemini e
OpenAI e citou o OpenRouter como possível último recurso. Os dois provedores gratuitos
ativos (Gemini e Groq) têm limites por minuto e por dia que mudam sem aviso; se ambos
esgotarem durante a apresentação, a Valyra AI responde `AI_UNAVAILABLE`, porque a OpenAI
não tem crédito configurado.

O OpenRouter expõe uma API compatível com Chat Completions da OpenAI em
`https://openrouter.ai/api/v1` e oferece modelos gratuitos (ids terminados em `:free`).
Pela documentação consultada em 28/11/2026:

- o roteador `openrouter/free` escolhe aleatoriamente um modelo gratuito disponível,
  filtrando os que suportam as capacidades pedidas, inclusive saída estruturada;
- modelos gratuitos têm limite de 20 requisições por minuto e 50 por dia em contas com
  menos de 10 créditos comprados (1000 por dia a partir disso);
- HTTP 402 indica saldo insuficiente e HTTP 429, limite de requisições;
- alguns modelos gratuitos podem registrar prompts e usá-los em treinamento.

## Decisão

1. Ordem de provedores: Gemini → Groq → OpenRouter → OpenAI, cada um habilitado pela
   própria chave (`GEMINI_API_KEY`, `GROQ_API_KEY`, `OPENROUTER_API_KEY`,
   `OPENAI_API_KEY`).
2. O OpenRouter usa o SDK `openai` já instalado, com base `OPENROUTER_BASE_URL`
   (padrão `https://openrouter.ai/api/v1`) e modelo `OPENROUTER_MODEL` (padrão
   `openrouter/free`). O roteador gratuito evita depender de um modelo específico que
   saia do catálogo; um modelo `:free` fixo pode ser configurado pela variável.
3. Mesmo JSON Schema e instruções de sistema, em modo best-effort (`strict: false`), com
   `provider.require_parameters: true` para o OpenRouter só usar provedores que aceitem
   `response_format`. A resposta passa pela mesma validação Pydantic e pelo domínio da
   [ADR-0011](0011-contrato-evidencias-ia.md); nada muda nas regras de evidência.
4. Indisponibilidade (rede, 429, 5xx) passa ao próximo provedor habilitado; HTTP 402
   passa ao próximo sem repetir.
5. Com modelo gratuito (`openrouter/free` ou id terminado em `:free`), o OpenRouter conta
   como reserva sem custo: recebe a chamada mesmo depois de erro de configuração do
   Gemini. Com qualquer outro modelo, é tratado como pago e segue a trava da ADR-0002.
   O hard spend limit da OpenAI não cobre o OpenRouter: quem configurar um modelo pago
   deve definir o limite de crédito da própria chave no painel do OpenRouter.
6. Erro de configuração ou resposta fora do schema do OpenRouter passa à OpenAI, se
   configurada, como no Groq.
7. Só dados sintéticos da demonstração vão ao OpenRouter. Antes de enviar dados reais,
   revisar a política de dados de cada modelo gratuito. O filtro
   `provider.data_collection: "deny"` não é usado porque excluiria a maior parte dos
   provedores gratuitos e deixaria o roteador sem modelo.

## Alternativas consideradas

- **Fixar um modelo `:free` como padrão:** previsível, mas o catálogo gratuito muda com
  frequência e o modelo pode sumir; continua possível pela variável.
- **OpenRouter antes do Groq:** o roteador escolhe modelos ao acaso, com qualidade
  variável; o Groq tem modelo fixo e testado com saída por JSON Schema.
- **Só aumentar limites pagando:** exige crédito antes da apresentação.

## Consequências

- Basta `OPENROUTER_API_KEY` no Render para haver uma terceira tentativa gratuita antes
  de `AI_UNAVAILABLE`.
- `LLMResponse.provider` passa a aceitar `openrouter`; a resposta HTTP pública não muda.
  O modelo registrado é o configurado, não o escolhido pelo roteador.
- A qualidade da resposta varia com o modelo sorteado; respostas fora do schema são
  recusadas pela validação, sem inventar dados.
- Sem créditos comprados, são 50 chamadas gratuitas por dia. Para reverter, basta remover
  `OPENROUTER_API_KEY`.

## Status

Aceita em 28/11/2026 por Willian, que pediu no chat do projeto o OpenRouter como reserva
de emergência depois do Groq.
