# ADR-0011 — Contexto e evidências da IA

## Contexto

A fundação IA já possui cliente Gemini/OpenAI e schemas internos, mas
`context_data: dict[str, Any]` não define procedência, unidade ou corte temporal.
O modelo atualmente devolve uma cópia dos valores e fontes; isso permite uma
resposta formalmente válida com metadados inventados.

A [ADR-0009](0009-dinheiro-em-centavos.md) define dinheiro Finance em centavos,
mas deixa evidências monetárias Alpha/IA pendentes. A
[modelagem](../modelagem-db.md) distingue publicação, observação e ingestão;
Finance não tem publicação pública nem histórico completo de alterações.
A proposta elaborada em 14/11 foi aprovada para implementação pelo responsável
em 17/11/2026. Essa aprovação inicial fechou o contrato em memória para o MVP,
sem criar HTTP ou tabelas. A publicação HTTP foi autorizada no incremento seguinte;
o estado atual está nas consequências e em [HTTP IA](../ai-http.md).

## Decisão

**Aceita para implementação em 17/11/2026, por solicitação explícita do responsável.**

### 1. Três fronteiras de dados

| Contrato | Quem produz | Conteúdo |
| --- | --- | --- |
| `ExplainRequest` | Futuro frontend | `question` e `account_id`; campos extras proibidos |
| `EvidenceContext` | Serviço IA no servidor | Conta autorizada, corte, instante de montagem, evidências e limitações |
| `LLMPayload` | Provedor LLM | `answer`, `evidence_ids`, `uncertainty`, `limitations` |
| `ExplainResponse` | Servidor, após validação | `answer`, `as_of`, evidências originais citadas, incerteza e limitações |

- Usuário demo vem da dependência da API, nunca do corpo. O service valida a
  propriedade da conta antes de obter qualquer contexto.
- O frontend não envia valores, fontes, contexto, IDs de evidências ou modelo.
  Pergunta/histórico não são evidências. `as_of` vem do servidor no primeiro
  recorte HTTP; aceitar corte histórico do cliente fica para a entrega de replay.
- `LLMRequest` continua interno: pergunta + `EvidenceContext` tipado + histórico
  limitado com papéis `user`/`assistant`. Só o servidor o monta.
- Contexto financeiro é obtido pelo service público de Finance; sinais pelo
  service público de Alpha, quando existir. Sem importar repositories cruzados
  nem buscar fontes externas durante a explicação.
- Os schemas não tornam o dado confiável sozinhos. A confiança depende dessa
  montagem no servidor, da autorização e da posterior validação de domínio.

### 2. Envelope de contexto

| Campo | Tipo/regra proposta |
| --- | --- |
| `account_id` | UUID da conta previamente autorizada |
| `as_of` | Instante ISO 8601 com fuso, normalizado para UTC; corte de conhecimento |
| `built_at` | Instante UTC em que o servidor montou o contexto; `as_of <= built_at` |
| `evidences` | Lista de `EvidenceItem` tipados; IDs únicos dentro do contexto |
| `limitations` | Limitações factuais produzidas pelo servidor; preservadas na saída |

Um contexto pode vir sem evidências. Isso permite declarar insuficiência de
informação, sem números ou fontes inventados. Ausência de módulo, resumo ou
projeção gera limitação explícita, nunca um zero sintético.

### 3. Evidência tipada

Campos comuns: `evidence_id` (identificador local ao contexto, como `e1`),
`metric_key` (chave técnica do dado), `label`, `basis`, `source`, `value`,
`period` e a propriedade interna `display_value` (calculada, não recebida).

- `basis`: `reference`, `observed` ou `projected`; saldo de referência nunca recebe
  o rótulo de saldo realizado. `projected` exige período futuro identificado e
  método de cálculo; não representa publicação de um fato futuro.
- `period`: `start`/`end`, datas de negócio `AAAA-MM-DD`, inclusivas e ordenadas.
  Uma observação de um dia usa as duas datas iguais.
- `display_value` é uma dica de apresentação interna do prompt, calculada no
  servidor a partir do valor tipado, sem `float`. Não substitui o dado monetário
  estruturado nem entra como campo financeiro na resposta pública. O LLM pode
  reproduzi-lo em `answer`, mas não calcular conversões ou percentuais adicionais.
- Apenas métricas realmente produzidas pelos módulos entram no contexto. O schema
  não implementa os cálculos propostos na ADR-0010 nem aprova seus limiares.

#### Valores e unidades

União discriminada por `kind`; sem campo genérico `value: Any`:

| Variante | Campos | Escopo |
| --- | --- | --- |
| `money` | `amount_cents: int`, `currency: "BRL"` | Valores financeiros Finance, já em centavos |
| `integer` | `value_int: int`, `unit: str` | Contagens; unidade explícita do service |
| `decimal` | `value_decimal: str`, `unit: str` | Indicadores não monetários, sem perda de precisão |
| `text` | `value_text: str` | Evidência textual sem valor quantitativo principal |

- `amount_cents` e `value_int` são inteiros estritos, sem aceitar bool, float ou
  string. **Escopo da IA:** limitar a `[-9007199254740991, 9007199254740991]`, garantindo
  representação exata no JSON consumido pelo frontend. Não altera BIGINT nem os
  endpoints Finance existentes. Valor fora dessa faixa não vira string, zero ou
  valor arredondado: é omitido com limitação explícita.
- Decimal não monetário é texto decimal finito, sem expoente, vírgula, NaN ou
  infinito, produzido a partir de Decimal/valor original exato, sem conversão por
  float e sem quantização silenciosa. Precisão publicada é preservada.
- Unidade não é inferida: `%` representa percentual, `pp` representa variação em
  pontos percentuais, e `fraction` representa fração. Exemplos: `12.5 %` e `0.125 fraction` não são
  trocados automaticamente. Unidade de produção/área vem da fonte validada.
- Scores continuam indicadores heurísticos, nunca probabilidades ou dinheiro.
- Preços monetários Alpha, moedas diferentes de BRL, preços médios com fração de
  centavo e conversões cambiais ficam fora deste recorte. Precisão e persistência
  desses dados exigem decisão posterior; não reaproveitar `decimal` para contornar
  a regra de dinheiro.

O recorte implementado usa `count` para contagens. Unidades decimais aceitas:
`%`, `pp`, `fraction`, `count`, `t`, `kg`, `ha`, `kg/ha`, `t/ha`, `mm`, `°C` e
`index`. Novas unidades exigem registro explícito no contrato, sem interpretação
livre ou monetária. Histórico limitado a dez mensagens de até 4.000 caracteres;
contexto limitado a cem evidências e vinte limitações, além do teto de bytes do
cliente. A data de negócio de projeções usa o calendário America/Sao_Paulo.

### 4. Procedência

`source` é outra união discriminada por `kind`:

| Origem | Campos obrigatórios | Observação |
| --- | --- | --- |
| `finance_record` | `record_type` (`account`/`transaction`), `record_id`, `recorded_at` | Registro interno identificado; transação inclui `import_batch_id` |
| `calculation` | `module`, `method_key`, `method_version`, `computed_at`, `input_scope` | Resultado determinístico; escopo de registros/lotes consultados |
| `alpha_signal` | `source_id`, `signal_id`, `signal_key`, `revision_id`, `source_url`, `observation_date`, `published_at`, `published_at_estimated`, `ingested_at` | Fonte pública permitida e revisão exata |

- Finance usa IDs reais de registros/lotes e `recorded_at` da versão consultada,
  nunca UUID de uma fonte pública inventada nem URL fictícia. `recorded_at` deve
  estar no corte (`<= as_of`); atualização posterior exige omissão/limitação. Não exige
  `published_at` em registros privados/sintéticos de Finance.
- Cálculo informa versão do método efetivamente usado e `input_scope` com conta,
  intervalo e referências de lotes/registros pertinentes. Se depender de outras
  métricas do contexto, registra também `input_evidence_ids`, sem ciclos ou IDs
  ausentes. Não é necessário enviar todas as transações ao LLM: a rastreabilidade
  detalhada fica no servidor e o contexto oferece os resultados já calculados.
- Em Alpha, `source_id` identifica a fonte; `signal_id` identifica a revisão
  persistida, não é intercambiável com `signal_key`. URL deve ser HTTP(S).
  Ingestão futura em relação a `built_at` é inválida.
- Licença/uso permitido é responsabilidade do cadastro/ingestão da fonte. Uma URL
  válida não demonstra essa permissão.

### 5. Corte temporal

1. Alpha: `published_at <= as_of`; para cada `signal_key`, usar a revisão mais
   recente por publicação e, em empate, `revision_id`, conforme a modelagem.
2. `observation_date` descreve o período observado; não substitui publicação.
   `ingested_at` descreve coleta e não é rebatizado como publicação.
3. Uma fonte pública ingerida depois do corte pode servir à reconstituição por
   publicação, como no desenho atual de replay, sem afirmar que o sistema já a
   possuía naquela data. Publicação estimada exige limitação de reconstituição
   ilustrativa; não apresentar horário estimado como comprovado.
4. No primeiro recorte, Finance só fornece snapshot corrente com `as_of` definido
   pelo servidor. Não basta filtrar transações por data para reconstruir saldo,
   categoria ou conta antes de alterações posteriores. Finance histórico fica
   indisponível até existir suporte de versionamento/snapshot apropriado.
5. No replay futuro, Finance não deve ser misturado ao corte histórico sem esse
   suporte: omitir as evidências Finance com limitação, sem usar o estado atual.
6. Cálculos podem ser executados depois do corte sobre entradas válidas no corte:
   `computed_at` não é `published_at`. A validade temporal vem das entradas. A
   projeção pode ter período posterior a `as_of`, marcada como `projected`, mas
   não pode usar informação publicada depois do corte.

### 6. Casos de aceite para os schemas

- Aceitar `amount_cents: 500000`; recusar `5000.0`, `"500000"`, `true` e inteiros
  fora da faixa aprovada. Nunca converter silenciosamente.
- Preservar `value_decimal: "12.500"` e sua unidade; recusar float, expoente,
  vírgula, NaN e infinito. Uma unidade vazia não autoriza inferência.
- Recusar instantes sem fuso e períodos invertidos. Normalizar instantes para UTC,
  mantendo datas de negócio como datas.
- Recusar campo de valor ou contexto no `ExplainRequest`, inclusive se
  vier com um ID de conta válido.
- Recusar IDs duplicados no contexto e datas contraditórias. Seleção de revisão,
  origem autorizada, correspondência dos números e citações ficam para o domínio.
- Permitir projeção futura com entradas elegíveis; recusar um sinal publicado
  depois do corte mesmo se sua observação for anterior.
- Não incluir evidência monetária Alpha com fração de centavo sob outro tipo.

### 7. Saída e validação

- LLM devolve somente `evidence_ids`; não pode devolver ou alterar valores, URLs,
  datas ou metadados de fonte. Provedor/modelo são atribuídos pela aplicação.
- Servidor rejeita IDs desconhecidos ou repetidos. Na resposta final, monta os
  itens citados a partir do contexto original, sem a dica interna `display_value`,
  e inclui as dependências necessárias
  para rastrear cálculos. A ordem de citação é preservada.
- `answer` deve ser não vazio; incerteza mantém `baixa`/`média`/`alta`. Limitações
  do servidor são preservadas junto das limitações produzidas pelo modelo.
- O domínio em `ai/domain.py` revalida o contexto e confere referências, metadados
  temporais e literais numéricos contra as evidências citadas/resolvidas. Valores
  com unidade reproduzem `display_value`; não se aceitam conversões ou arredondamentos.
  Regras e limites em [validação IA](../ai-validation.md). Formato e números corretos
  não certificam semântica, causalidade ou adequação de conselho.
- Contexto vazio só permite explicação de insuficiência, sem referências. Incerteza
  deve ser alta e a limitação deve estar presente.
- Limites de contexto/saída do cliente continuam valendo. Não truncar uma lista
  sem registrar que o contexto ficou parcial.

Exemplo de evidência monetária original do contexto. Ao montar o prompt, o
servidor acrescenta `display_value: "R$ 5.000,00"`; esse campo não é aceito como
entrada nem serializado na resposta pública:

```json
{
  "evidence_id": "e1",
  "metric_key": "finance.account.reference_balance",
  "label": "Saldo de referência informado",
  "basis": "reference",
  "source": {
    "kind": "finance_record",
    "record_type": "account",
    "record_id": "00000000-0000-0000-0000-000000000101",
    "recorded_at": "2026-11-14T12:00:00Z"
  },
  "value": {"kind": "money", "amount_cents": 500000, "currency": "BRL"},
  "period": {"start": "2026-11-01", "end": "2026-11-01"}
}
```

Exemplo da saída do modelo, antes da validação factual:

```json
{
  "answer": "O saldo de referência informado é R$ 5.000,00. Ele não representa uma projeção.",
  "evidence_ids": ["e1"],
  "uncertainty": "alta",
  "limitations": ["Projeção ainda indisponível."]
}
```

## Alternativas consideradas

- Modelo copiando objetos completos: descartado; duplicação permite
  alterar metadados, unidades e valores que já existem no servidor.
- Dinheiro textual genérico: descartado para Finance por contrariar ADR-0009.
- Float/quantização universal: descartados por perda de precisão e regras monetárias
  ainda não definidas em Alpha.
- Aceitar contexto do navegador: descartado por confundir dados fornecidos pelo
  usuário com evidência autorizada pelo servidor.
- Implementar todas as moedas/preços e persistência agora: adiado para limitar o
  escopo sem fechar silenciosamente as pendências da modelagem.

## Consequências

- Implementados `ai/schemas.py`, payload de citações, prompts e testes.
  `ai/domain.py` resolve IDs, revalida o contexto e confere a reprodução lexical
  dos números com unidade, sem certificar semântica ou causalidade.
- `ai/service.py` autoriza a conta e monta contexto corrente pelo service público
  de Finance, com contexto/cliente substituíveis para testes. Sem evidências,
  responde insuficiência sem chamar o LLM; dados ausentes geram limitações.
  O router expõe `POST /api/v1/ai/explain`, com contrato gerado e erros no envelope
  existente; roteiro e jornada sintética em [HTTP IA](../ai-http.md).
  Seleção de dados reais Alpha continua entrega seguinte.
  Schemas não garantem procedência ou seleção correta de revisões.
- Contrato novo é incompatível com `context_data` livre e com evidências copiadas
  pelo LLM. O frontend deve consumir os schemas públicos gerados, sem enviar contexto.
- Sem mudança de tabelas ou migração. Persistência futura de evidências monetárias
  exige desenho próprio; esta decisão não cria colunas nem usa JSONB para isso.

## Status

**Aceita — 17/11/2026.** Aprovação explícita no pedido “Beleza implemente ambas”,
referente às ADRs 0002 e 0011. Elaborada em 14/11/2026. Assistência de elaboração,
implementação e testes: OpenAI Codex. Não aprova cálculos da ADR-0010 nem a
persistência futura de evidências.
