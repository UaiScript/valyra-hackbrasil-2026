# ADR-0010 — Convenções de cálculo do Finance

## Contexto

As tarefas F4–F8 (Issues #43–#47) calculam o saldo realizado e o resumo mensal, a recorrência, o gasto atípico, a projeção de caixa e o alerta de pressão de caixa. A [modelagem](../modelagem-db.md#42-saldo-e-datas) só propunha o saldo de fechamento, e a [revisão](../revisao-modelagem.md) mantinha a escolha entre abertura e fechamento como pendente. A seção 4.3 deixava o limiar de anomalia e a precisão das estimativas em aberto. A Issue #40 (F1) pede que essas convenções sejam registradas antes de qualquer código.

Restrições que valem aqui: dinheiro em centavos inteiros e sem `float` ([ADR-0009](0009-dinheiro-em-centavos.md)); `anomaly_score NUMERIC(5,4)` com check entre 0 e 1; `is_recurring` e `recurrence_key` já existem em `transactions`; não há tabelas próprias para esses cálculos e o LLM não gera números.

O seed define a referência da conta demo como `500000` em `2026-11-01`, e o CSV de demonstração vai de `2026-08-01` a `2026-10-31`.

## Decisão

### 1. Saldo de referência = fechamento

`balance_cents` é o saldo de **fechamento** de `balance_as_of` e já inclui todas as movimentações dessa data. Para uma data `D >= balance_as_of`:

```text
saldo_realizado_cents(D) = balance_cents + soma(amount_cents onde balance_as_of < date <= D)
```

- Datas iguais ou anteriores à referência não entram de novo.
- Quando `D < balance_as_of`, o saldo fica **indisponível**: `realized_balance_cents: null` no resumo e `422 BALANCE_UNAVAILABLE` na projeção.
- Datas posteriores a `D` não entram no realizado.

Exemplo: referência `500000` em `2026-11-01` e saída `-12990` em `2026-11-02` dão realizado `487010` em `2026-11-07`. Uma saída em `2026-11-10` não participa.

### 2. Data de "hoje"

`core/clock.get_today()` é a única fonte de "hoje" para os cálculos:

- se `DEMO_TODAY` (data ISO, por variável de ambiente) estiver definida, devolve essa data;
- caso contrário, devolve a data corrente no calendário `America/Sao_Paulo`.

Timestamps continuam em UTC. O ambiente de demonstração usa `DEMO_TODAY=2026-11-07`. Os testes fixam a data e não dependem do relógio.

Consequência para o demo: como a referência (01/11) é posterior ao CSV (ago–out), o histórico alimenta a recorrência, o gasto atípico e a média variável, mas não altera o saldo realizado.

### 3. Recorrência

- **Chave da série:** `account_id` + `normalize_description(description)` (a mesma normalização do hash em `finance/domain.py`) + sinal do valor.
- Uma série é recorrente quando, ao mesmo tempo:
  - tem **pelo menos 3 ocorrências em meses distintos**;
  - **todos** os intervalos entre ocorrências consecutivas ficam entre **25 e 35 dias**, inclusive;
  - todo valor `v` respeita `|v − med| × 10 <= |med|` (±10%), em inteiros, sendo `med` a mediana dos valores da série.
- Mediana de quantidade par = média dos dois centrais, comparada sem `float` (multiplicando os dois lados por 2).
- `is_recurring` e `recurrence_key` são recalculados ao fim de cada importação sobre todas as transações da conta, de qualquer lote. Reimportar o mesmo CSV não muda os flags.

### 4. Gasto atípico

- Só **saídas**, agrupadas por conta + categoria atual (`category_id`). Entradas e grupos com **menos de 5 saídas** ficam com `anomaly_score = NULL`.
- Com `x` = magnitude da saída e `med` e `MAD` = mediana e desvio absoluto mediano das magnitudes do grupo (a própria transação incluída):

```text
z     = 0,6745 × max(0, x − med) / MAD
score = min(1, z / 4,375)
```

- **Unilateral:** só gastar mais que o normal pontua; uma saída menor que a mediana recebe score 0.
- `4,375 = 3,5 / 0,8`, ou seja, `score >= 0,8` equivale a `z >= 3,5`, o corte clássico de Iglewicz–Hoaglin. `is_anomaly = score >= 0,8`.
- **MAD = 0:** usar `z = max(0, x − med) / (1,2533 × desvio absoluto médio)`. Se o desvio médio também for zero (todos os valores iguais), o score é 0.
- Aritmética em `Decimal`, sem `float`; o score é quantizado em 4 casas com `ROUND_HALF_EVEN` e respeita o check do banco.
- Recalcular ao importar e ao corrigir a categoria, nos grupos de origem e de destino.

### 5. Projeção de caixa

- `days` de 1 a 90, padrão 30. O dia 1 é amanhã. O saldo inicial é o realizado de hoje (seção 1).
- **Recorrências:** cada série recorrente da conta é prevista na data `última + intervalo mediano`. Enquanto essa data for `<= hoje`, avança mais um intervalo mediano. O valor previsto é a mediana da série.
- **Variável diária:** soma das saídas **não recorrentes** de `[hoje − 89, hoje]` dividida por 90. A magnitude é arredondada **para cima**, o que é conservador e erra no máximo 1 centavo por dia.
- Entradas não recorrentes ficam fora da projeção.
- A projeção é calculada sob demanda e não grava nada. Valores previstos aparecem separados do realizado.

### 6. Pressão de caixa

- Cria um alerta `cash_pressure`, com severidade `warning`, quando a projeção de **30 dias** tem `min_balance_cents < 0`.
- A deduplicação usa `cash:<account_id>:<AAAA-MM>`, com o mês de hoje: no máximo um alerta por conta por mês.
- Saldo indisponível (referência futura) não gera alerta.
- Título e mensagem vêm de template com os números calculados, sem LLM.

## Alternativas consideradas

- **Saldo de abertura:** descartado; alteraria o limite inferior da soma e o exemplo já registrado na modelagem.
- **Só o relógio real para "hoje":** descartado; a demo dependeria do dia da apresentação. **Mover a referência do seed para antes do CSV:** adiado; exige mudar o seed e não é necessário para os cálculos.
- **Próxima recorrência no mesmo dia do mês, com o último valor:** mais intuitivo para salário e aluguel, mas a mediana é mais estável e tolera variações de calendário.
- **Score por saturação `1 − e^(−z/k)` ou por percentil na categoria:** o primeiro é mais difícil de explicar e exige exponencial em `Decimal`; o segundo perde a relação com MAD pedida na F6.
- **MAD = 0 → score 1 para qualquer desvio, ou `NULL`:** o primeiro gera falsos positivos em categorias constantes; o segundo esconde aumentos reais.
- **Desvio bilateral:** gastos abaixo do normal não representam risco de caixa e tornariam o sinal ruidoso.
- **Arredondamento half-even da média variável:** neutro, mas pode subestimar o gasto; preferimos o viés conservador.
- **Margem de segurança no gatilho (por exemplo, abaixo de R$ 100):** avisa mais cedo, mas acrescenta um parâmetro sem calibração. Pode entrar depois.

## Consequências

- F4–F8 têm valores fechados e testáveis; os testes de domínio cobrem cada regra sem PostgreSQL.
- Todos os limiares são constantes do domínio. Mudá-los exige atualizar esta ADR, os testes e o contrato, se a resposta mudar.
- Os cálculos dependem de todo o histórico da conta. Para volumes grandes, recalcular a cada importação pode precisar de janela ou de processamento incremental; isso não se aplica ao MVP.
- O score é heurístico, não uma probabilidade. A interface e o Valyra AI devem tratá-lo como indicador, sem atribuir causa.
- Para reverter, basta uma nova ADR que substitua esta; nenhuma migração depende destas escolhas.

## Status

**Proposta — 2026-11-13.** Valores debatidos com Samuel na preparação da Issue #40. A ADR fica aceita só depois que o time confirmar ou ajustar os limiares no PR (critério 3 da Issue #40): 25–35 dias, ±10%, ≥ 3 meses, ≥ 5 saídas, `0,8` (z = 3,5), janela de 90 dias e gatilho `< 0`.
