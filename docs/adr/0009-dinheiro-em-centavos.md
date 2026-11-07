# ADR-0009 — Dinheiro em centavos inteiros

## Contexto

O frontend existente utiliza centavos inteiros. As Issues #7/#10 e a revisão de Finance alinharam banco e contratos para evitar divergência de unidade e cálculos com ponto flutuante.

## Decisão

Representar dinheiro em centavos inteiros de BRL no banco, API e frontend. No Finance, usar `BIGINT` no PostgreSQL e inteiro JSON com sufixo `*_cents`: `balance_cents` e `amount_cents`. Transação positiva é entrada, negativa é saída, zero é rejeitado. Formatar reais apenas na apresentação.

No CSV, valores chegam como texto decimal em reais, são validados e convertidos de forma exata para centavos; não usar `float` nem truncar precisão adicional. Datas, quantidades, scores e indicadores não são campos monetários.

Preços médios com frações de centavo e evidências monetárias genéricas de Alpha/IA têm pendências explícitas na modelagem: não arredondar, renomear ou implementar esses campos silenciosamente. Essa pendência não altera a escolha de centavos para os campos Finance já definidos.

## Alternativas consideradas

- String decimal na API: descartada para os campos Finance; diverge do contrato inteiro do frontend e exige conversões em cada consumidor.
- Float para dinheiro: não adotado por não preservar aritmética decimal exata.
- NUMERIC(14,2) no Finance: desenho anterior substituído pelo alinhamento em BIGINT/centavos.

## Consequências

Unidade consistente entre camadas e testes. Limites de entrada/armazenamento e faixa segura dos números JSON no JavaScript precisam ser acordados e validados antes de suportar valores fora da faixa definida. Não confundir limite BIGINT com precisão garantida no frontend. Alterar unidade/serialização no futuro exige nova ADR, migração e alinhamento dos consumidores.

## Status

**Aceita.** Contrato Finance registrado nas Issues #7/#10 e tarefa de contexto autorizada pelo usuário em 07/11/2026. Não comprova schema implementado.
