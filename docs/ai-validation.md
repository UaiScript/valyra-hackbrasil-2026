# Validação de explicações IA

`ai.domain.build_explain_response(context, payload)` é o ponto de validação e
montagem chamado pelo serviço IA antes de responder ao usuário.
É uma função pura: não acessa banco, provedor, relógio ou fontes externas.
Contratos na [ADR-0011](adr/0011-contrato-evidencias-ia.md).

## O que a função verifica

1. Revalida cópias do contexto e do payload. Isso inclui datas, origem tipada,
   corte, revisões únicas por sinal e dependências de cálculo sem ciclos. Não
   confia apenas na validação feita ao construir modelos com listas mutáveis.
2. Resolve os IDs citados contra o contexto original e inclui dependências de
   cálculos. O modelo não fornece objetos de evidência para substituir os originais.
3. Confere os literais de `answer` e das limitações geradas pelo modelo somente
   contra essas evidências citadas/resolvidas. Valores de outras evidências,
   perguntas e histórico não autorizam números na resposta.
4. Mantém a exigência de incerteza alta e limitação quando não há citações,
   inclusive se o contexto possuir dados que o modelo não citou. Dados ausentes
   não autorizam saldo zero, probabilidades ou fontes inventadas.
5. Preserva os dados, revisões e limitações originais do servidor, incluindo
   publicação estimada e ingestão posterior ao corte em reconstituições públicas.

A função não consulta o banco para comprovar que a evidência é verdadeira.
O [serviço IA](ai-service.md) autoriza a conta e monta o contexto pelos services
públicos de Finance e Alpha (incluindo indicadores do radar e manchetes da semana
publicados até o corte), selecionando evidências inteiras dentro de 64.000 bytes.

## Regra conservadora de números

Os valores financeiros e indicadores devem reproduzir `display_value`, que o
servidor acrescenta ao prompt a partir dos dados tipados, sem `float`:

| Evidência original | Aceito | Rejeitado |
| --- | --- | --- |
| `amount_cents: 500000` | `R$ 5.000,00` | `R$ 999,00`, `500000`, `US$ 5.000,00` |
| `amount_cents: -12990` | `R$ -129,90` | `R$ 129,90` |
| Decimal `12.500`, unidade `%` | `12,500 %` | `12,5 %`, `0,125 fraction`, `12,500 pp` |
| Inteiro `3`, unidade `count` | `3 count` ou `3` | `3%`, `R$ 3`, `.3`, `- 3` |

- Espaços, inclusive não separáveis, maiúsculas de unidades e formas Unicode
  compatíveis são normalizados. A representação numérica, o sinal, a precisão e
  a unidade devem continuar iguais; não são feitas contas, arredondamentos ou
  conversões automáticas. Uma alternativa matematicamente equivalente pode ser
  recusada por não reproduzir a apresentação fornecida.
- Datas devem usar ISO conforme os metadados citados e o corte. Não basta citar
  uma data de observação antiga se a publicação só ocorreu depois do corte.
- URLs explícitas no texto devem copiar uma URL das fontes citadas. O caminho
  preserva maiúsculas; números contidos em uma URL não se tornam métricas.
- Números de uma evidência `text` só são aceitos na reprodução da passagem
  original inteira; não viram números avulsos para outras afirmações.
- Há bloqueio parcial de quantidades por extenso, como zero, cinco, mil e dobro.
  Não é um analisador completo de português: `um`/`uma` também são artigos, e
  quantidades implícitas ou outras construções linguísticas exigem revisão.
  O prompt exige copiar os valores de apresentação, sem números por extenso ou
  listas numeradas.
- Limitações originais produzidas pelo servidor são preservadas. A checagem de
  literais se aplica ao texto gerado pelo LLM, não inventa evidências para justificar
  mensagens operacionais já fornecidas pelo servidor.

## Erros

Todos herdam de `ExplanationValidationError`, que herda de `ValueError`:

- `EvidenceContextError`: contexto original com estrutura/metadados inválidos.
- `EvidenceReferenceError`: citações inválidas ou ausência de evidências sem
  incerteza alta e limitação.
- `UnsupportedClaimError`: número, data, unidade ou URL sem suporte no recorte citado.

As mensagens não incluem valores, URLs ou conteúdo bruto do modelo. A revalidação
não imprime warnings de serialização com dados de modelos adulterados. O
router mapeia esses erros para o [contrato HTTP](ai-http.md), sem incluir o texto rejeitado.
Resposta rejeitada não deve ser exposta como aprovada nem corrigida silenciosamente.

## O que a checagem não demonstra

Consistência lexical não comprova causalidade, aconselhamento adequado, a verdade
externa de uma fonte, ou a associação semântica entre cada frase e a métrica citada.
Por exemplo, o modelo pode citar saldo de referência corretamente e chamá-lo de
lucro; ou repetir Micro/Macro corretamente e afirmar que um causou o outro.

O prompt proíbe esses comportamentos. Os casos sintéticos em
[explanation_evals.json](../services/api/tests/ai/fixtures/explanation_evals.json)
separam `automatic` de `human_review`: um caso lexicalmente aceito pode exigir
rejeição humana. Os testes não apresentam esses casos como respostas adequadas,
não chamam modelos reais e não comprovam a qualidade do provedor escolhido.

## Verificação

```bash
make test-ai
make lint
python infra/check_docs.py
```

Cobertura inclui valores inventados, troca de unidade/sinal, fonte inventada,
datas futuras, contexto/listas adulterados, cópia de evidência fabricada, ausência
de dados e os limites semânticos identificados nos exemplos.
