# ADR-0016 — Previsões por perfil calculadas em código

## Contexto

Em 28/11/2026 Willian pediu que a Valyra ofereça previsões para cada perfil da demo
(orçamento apertado, começando a investir, investidor), mostrando os dados, a estatística e
a "probabilidade", e também a visão da Valyra, para o cliente decidir. As previsões de soja e
café da brapi estão só no plano pago, e fazer a conta pelo LLM gastaria tokens e geraria
números sem suporte verificável, o que a regra do projeto proíbe.

Fontes avaliadas em 28/11/2026. Nenhuma pôde ser chamada do ambiente de nuvem da análise:

| Fonte | Acesso | Uso |
| --- | --- | --- |
| SGS do Banco Central | Sem chave, já usado (ADR-0012) | Selic, CDI e IPCA; novos: dólar de venda (código 1) e IC-Br Agropecuária (27575) |
| brapi.dev, plano gratuito | Token gratuito, já usado | Variação diária; com `range=3mo&interval=1d`, até 3 meses de fechamentos para a carga histórica |
| CEPEA/Esalq | Sem API aberta; uso dos indicadores pede citação e tem termos próprios | Descartada no MVP; o IC-Br Agropecuária cobre soja, milho, café e boi em reais |
| Ipeadata | API OData sem chave | Alternativa futura; as séries usadas já estão no SGS |

## Decisão

Proposta, com implementação pedida por Willian no thread do projeto:

1. Previsões são calculadas no back end, em código puro (`alpha/forecast.py`, sem banco,
   rede ou relógio). A analogia é a calculadora e o narrador: o código calcula e o texto só
   lê o resultado pronto. O LLM nunca calcula previsão.
2. Modelos simples e explicáveis, versão `forecast_v1`:
   - séries com inércia (IPCA, Selic, CDI anualizado, IC-Br Agropecuária): suavização
     exponencial com tendência amortecida (Holt), com parâmetros escolhidos pelo menor erro
     de um passo no próprio histórico;
   - preços de mercado (cesta de PETR4, VALE3, ITUB4 e MGLU3; dólar): passeio aleatório sem
     tendência. A tela diz que a faixa mede risco, não direção.
3. Probabilidade com suporte verificável: 1.000 cenários com semente fixa, sorteando os
   erros do próprio passado. A tela mostra o cenário central, a faixa de 80% e de 95% e a
   "chance" de um evento como a fração de cenários em que ele acontece. Cada previsão traz
   um teste com o passado (quantas vezes a faixa de 80% teria acertado) e, quando faz
   sentido, o erro médio contra repetir o último valor. A regra da ADR-0013 (sem % de
   possibilidade nas notícias) continua valendo para notícias, onde não há modelo.
4. Cada perfil recebe as previsões ligadas à sua decisão (`PROFILE_SPECS`): inflação, agro e
   juros para o orçamento apertado; juro real, renda fixa, Selic e IPCA para quem começa a
   investir; bolsa, dólar, Selic e agro para o investidor.
5. A "visão da Valyra" é uma regra fixa e versionada (`forecast_view_v1`) sobre esses
   números, exibida separada dos dados e marcada como opinião, não recomendação.
6. Sem data leakage: a rota `GET /api/v1/alpha/forecasts` aceita `as_of` e só usa revisões
   publicadas até o corte, como o radar.
7. Reserva: série sem histórico suficiente usa uma série sintética gerada em código com
   semente fixa, nunca gravada no banco, marcada na tela e na API (`data_origin`) e nunca
   enviada à Valyra AI. O resultado fica em memória por 10 minutos.
8. A Valyra AI recebe as previsões feitas com dados coletados como evidências `calculation`
   do módulo Alpha (`basis = projected`), com cenário central, faixa, chance e o título da
   visão, e só pode citá-las (ADR-0011).

## Alternativas consideradas

- Plano pago da brapi: custo fora do hackathon.
- Pedir a previsão ao LLM: número sem suporte e gasto de tokens a cada pergunta.
- Modelos mais pesados (ARIMA, Prophet, redes): dependências grandes e explicação mais
  difícil para a persona, com pouco ganho em séries curtas.
- Exibir só faixas, sem chance: atende a regra, mas não responde ao pedido de probabilidade;
  a chance calculada sobre cenários e testada no passado tem suporte verificável.

## Consequências

- Previsões grátis, instantâneas e reproduzíveis; nenhuma chamada paga.
- Os modelos olham só o passado da própria série: choques novos ficam de fora, e a
  combinação CDI x IPCA supõe independência. Os limites aparecem em cada previsão.
- Para usar dados reais é preciso rodar a coleta com `backfill_days` (SGS até 10 anos e
  brapi até 3 meses). Os códigos SGS 1 e 27575 precisam ser conferidos na primeira coleta.
- A conta interna usa `float`, porque são indicadores e não dinheiro; a saída é texto
  decimal arredondado. Dinheiro Alpha continua fora do contrato.
- Reverter: esconder a rota e a tela; nada é gravado além das novas séries coletadas.

## Status

Proposta em 28/11/2026, implementada a pedido de Willian no thread do projeto. Aguarda a
aceitação do time na revisão do PR. Ainda não verificados: os códigos SGS 1 e 27575 e o
histórico de 3 meses da brapi no plano gratuito.
