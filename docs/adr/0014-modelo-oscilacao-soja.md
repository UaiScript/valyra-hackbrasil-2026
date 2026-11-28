# ADR-0014 — Modelo verificável de oscilação na cadeia da soja (M0 vs. M1)

## Contexto

A proposta central do **Alternative Alpha** no Valyra é combinar dados tradicionais de
mercado com dados alternativos para investigar riscos econômicos na cadeia da soja em
Mato Grosso e traduzi-los em contexto compreensível junto ao orçamento pessoal.

Até a [ADR-0012](0012-fontes-alpha.md) e a [ADR-0013](0013-relatorio-semanal-noticias.md),
o módulo `alpha` implementou apenas leitura descritiva de séries e regras por limiar fixo
(mudança da Selic, comparação mensal do IPCA, estiagem/excesso de chuva e manchetes por
tema). Faltavam:

1. Um ativo listado representativo da cadeia da soja em Mato Grosso (hoje a coleta traz
   apenas `PETR4`, `VALE3`, `ITUB4` e `MGLU3`, com um único ponto sem histórico diário).
2. Uma estimativa quantitativa reproduzível que combine mercado e clima com pesos
   aprendidos nos dados, avaliada fora da amostra contra um baseline simples (`M0` vs.
   `M1`), sem violar as regras invioláveis do projeto.

Restrições técnicas e de governança:

- **Proibição de números ou probabilidades sem suporte verificável** ([AGENTS.md](../../AGENTS.md),
  [ADR-0011](0011-contrato-evidencias-ia.md), [ADR-0013](0013-relatorio-semanal-noticias.md)):
  pesos manuais arbitrários ou inferência de "probabilidade de subida/queda de preço" por
  analogia unitária ($N=1$) são inválidos estatisticamente e sugerem recomendação direcional.
  Já a **oscilação realizada (volatilidade / amplitude de variação)** mede dispersão e
  incerteza, possui persistência temporal conhecida e informa risco sem indicar compra ou venda.
- **Zero data leakage**: em um alvo de horizonte futuro de $H$ pregões, na data de corte
  `as_of` somente janelas cujos $H$ pregões seguintes já foram observados e publicados até
  `as_of` podem entrar no ajuste ou na avaliação (*purge gap* de $H$ pregões).
- **Infraestrutura gratuita e chave opcional no momento**:
  - A API roda no Render Free (512 MB RAM, somente leitura em `signals`), então o cálculo
    não deve introduzir bibliotecas pesadas (`numpy`, `scipy`, `scikit-learn`) na imagem de
    produção nem exigir nova migração de banco.
  - Na `brapi.dev`, `?range=3mo&interval=1d` entrega cerca de 61 pregões diários. Os quatro
    tickers atuais funcionam sem chave; `SLCE3` (SLC Agrícola, produtora de soja e milho com
    operações em Mato Grosso) exige `BRAPI_TOKEN` gratuito. Como a conferência operacional
    de chaves externas ficará para etapa separada, o código deve degradar de forma limpa e
    explícita quando `BRAPI_TOKEN` ou o histórico de `SLCE3` ainda não estiverem disponíveis.
  - Os feeds RSS de notícias trazem apenas dias recentes, sem anos de histórico consistente;
    incluí-los como regressor geraria distorção entre treino e leitura. Notícias permanecem
    como contexto qualitativo ao lado do estudo quantitativo.

## Decisão

Implementar no módulo `alpha`, integrado ao radar HTTP e à Valyra AI, o estudo preditivo
versionado **`soy_volatility_ridge_v1`**, comparando um baseline de mercado (`M0`) contra
um modelo com clima de Mato Grosso (`M1`) para a oscilação de 5 pregões de `SLCE3`:

### 1. Séries de entrada e coleta (`ingest_alpha.py` e `alpha/domain.py`)

1. Acrescentar `SLCE3` (`brapi:SLCE3:change_pct`, `metric_key="alpha.brapi.slce3.change_pct"`,
   `kind="price_move"`, `unit="%"`, `theme="acoes"`) ao catálogo de ações, marcado com
   `requires_token=True`.
2. **Coleta `brapi` com e sem `BRAPI_TOKEN`**:
   - Sem `BRAPI_TOKEN`, `ingest_alpha` ignora séries `requires_token=True` sem registrar
     erro nem emitir warning espúrio no GitHub Actions; os quatro tickers livres continuam
     sendo coletados normalmente.
   - Com `--backfill-days`, `fetch_brapi` consulta `?range=3mo&interval=1d` (`historicalDataPrice`),
     ordena os pregões por data em `America/Sao_Paulo` e calcula a variação diária em `%` a
     partir de `adjustedClose` (fallback `close`) em `Decimal`:
     `((close_t - close_{t-1}) / close_{t-1}) * 100`, quantizada em `0.0001` (`ROUND_HALF_EVEN`).
     Isso preserva a convenção de variação percentual sem abrir contrato de dinheiro Alpha (`BRL`).
   - Sem `--backfill-days` (execução horária no pregão), mantém `regularMarketChangePercent`.
3. **Coleta `Open-Meteo` com histórico de até 90 dias**:
   - Com `--backfill-days N`, `fetch_climate` reconstrói até `min(N, 90)` dias passados de
     `rain_30d` e `rain_30d_anomaly` combinando `past_days=92` do endpoint recente com a
     janela de 10 anos do `ARCHIVE_URL` (até `today - 2`), sem chamadas HTTP adicionais por
     dia. Datas anteriores a `today - 1` entram com `backfill=True` (`published_at_estimated = True`,
     publicação estimada ao meio-dia do dia seguinte).
4. Documentar `BRAPI_TOKEN=` vazio em `.env.example`.

### 2. Modelo determinístico `M0` vs. `M1` e anti-leakage (`alpha/domain.py`)

Função pura em `alpha/domain.py` (sem banco, rede, relógio ou dependências externas),
operando exclusivamente sobre observações já filtradas por `published_at <= as_of`:

1. **Alinhamento temporal no corte `as_of`**:
   - Retornos diários ordenados $(d_t, r_t)$ de `brapi:SLCE3:change_pct` visíveis em `as_of`.
   - Para cada pregão $d_t$, associa-se a última observação visível de
     `openmeteo:sorriso-mt:rain_30d_anomaly` com `observation_date <= d_t` e
     `published_at <= cutoff_feature(d_t)` (no histórico reconstituído, não usar anomalia
     de data futura em relação ao pregão $d_t$).
2. **Variáveis e alvo** (janela passada $W = 5$ pregões, horizonte futuro $H = 5$ pregões):
   - $x_{0,t} = 1$ (intercepto, sem penalização Ridge);
   - $x_{1,t} = \sqrt{\sum_{j=0}^{4} r_{t-j}^2}$: oscilação realizada recente de 5 pregões (`%`);
   - $x_{2,t} = |r_t|$: magnitude da variação do último pregão (`%`);
   - $x_{3,t} = |\text{anomalia}_{\text{Sorriso}, t}| / 100$: intensidade do desvio hídrico
     de 30 dias em Sorriso-MT (escala adimensional, ex.: `-34.9%` → `0.349`);
   - **Alvo**: $y_t = \sqrt{\sum_{j=1}^{5} r_{t+j}^2}$ — oscilação realizada acumulada nos
     próximos 5 pregões (`%`).
3. **Purge gap obrigatório e validação *walk-forward***:
   - Uma amostra $t$ só possui rótulo conhecido em `as_of` se $t + H \le T_{\text{last}}$.
   - Para avaliar fora da amostra (*expanding window* com `MIN_TRAIN = 15` janelas concluídas
     e `MIN_EVAL = 5` passos de teste): em cada passo $\tau$, ajustam-se `M0` (features
     $[1, x_1, x_2]$) e `M1` (features $[1, x_1, x_2, x_3]$) por regressão Ridge fechada
     ($(X^\top X + \lambda I_0)w = X^\top y$, $\lambda = 1$, eliminação gaussiana determinística)
     usando **apenas** $\{t \le \tau - H\}$. Predições negativas são truncadas em `0`.
   - Calculam-se `mae_m0` e `mae_m1` (média de $|y_\tau - \hat{y}_\tau|$, em pontos
     percentuais `pp`) sobre as $N_{\text{eval}}$ janelas avaliadas.
4. **Estimativa corrente, pesos/contribuições e regime**:
   - Ajuste final em todas as janelas concluídas $\{t \le T_{\text{last}} - H\}$ aplicado em
     $x_{T_{\text{last}}}$, produzindo `m0_forecast_pct`, `m1_forecast_pct` e as contribuições
     aditivas de `M1` (`intercept_pct`, `market_persistence_pct`, `daily_shock_pct` e
     `climate_component_pct`, além dos pesos `weights`).
   - Regime classificado contra o percentil 75 dos $y$ de treino: `"elevada"` se
     $\hat{y}^{(M1)} \ge P_{75}(y_{\text{train}})$, caso contrário `"normal"`.
   - Todos os valores públicos são quantizados e serializados como texto decimal (sem `float`).
5. **Estado de dados insuficientes (`status = "insufficient_data"`)**:
   - Na leitura (`alpha/service.py`), carregar até `MODEL_HISTORY_POINTS = 90` pontos visíveis
     para as séries do modelo (mantendo `HISTORY_POINTS = 30` para `IndicatorOut.history`).
   - Se `SLCE3` ou o clima de Sorriso-MT estiverem ausentes ou resultarem em menos de
     `MIN_TRAIN + MIN_EVAL` janelas concluídas, devolver `status = "insufficient_data"` com
     motivo explícito e contagens observadas, sem estimativas numéricas fabricadas.

### 3. Contratos HTTP, Interface Web e Integração com Valyra AI

1. **HTTP (`GET /api/v1/alpha/radar`)**:
   - Adicionar `soy_volatility: SoyVolatilityOut` em `RadarOut` (`alpha/schemas.py`),
     discriminando `status: Literal["ready", "insufficient_data"]`, metadados do método
     (`rule="soy_volatility_ridge_v1"`, ativo `"SLCE3"`, região `"sorriso-mt"`, `horizon_days=5`),
     observações/entradas, estimativas `M1`/`M0`, decomposição de contribuições/pesos,
     métricas walk-forward (`eval_windows`, `mae_m0_pp`, `mae_m1_pp`) e `limitations`.
   - Regenerar `packages/contracts/openapi.json` e `apps/web/src/lib/api/schema.ts`.
2. **Valyra AI (`ai/service.py`)**:
   - Quando `soy_volatility.status == "ready"` e `cutoff_day` permitir período projetado
     futuro (`start = cutoff_day + 1 dia`), anexar evidências `CalculationSource` com
     `module="alpha"`, `method_key="alpha.soy_volatility_ridge"`, `method_version="adr-0014-v1"`
     e `input_scope={"account_id": None, "period": ..., "record_ids": ...}` (UUIDs dos sinais
     de entrada visíveis):
     - `alpha.volatility.slce3.m1_5d` (`basis="projected"`, `DecimalValue` em `%`),
     - `alpha.volatility.slce3.m0_5d` (`basis="projected"`, `DecimalValue` em `%`),
     - `alpha.volatility.slce3.mae_m1` e `alpha.volatility.slce3.mae_m0` (`basis="observed"`,
       `DecimalValue` em `pp`).
   - Quando `status == "insufficient_data"`, registrar limitação explícita sem emitir zero.
   - Reforçar nas limitações e instruções que oscilação estimada **não** representa direção
     de alta/queda do preço nem recomendação de compra ou venda.
3. **Frontend (`apps/web/src/app/pages/Alpha.tsx`)**:
   - Exibir painel **"Oscilação Estimada · Cadeia da Soja (`SLCE3` × Clima MT)"** com
     comparação `M1` vs. baseline `M0`, selo de regime (`normal` / `elevada`), barras de
     contribuição dos fatores (mercado vs. anomalia de chuva em Sorriso-MT), erro walk-forward
     (`MAE M1` vs. `MAE M0` em `N` janelas), limitações e atalho para explicar na Valyra AI.
   - Em `status === "insufficient_data"`, exibir estado informativo claro (indicando a
     dependência da carga histórica de `SLCE3` / clima) sem quebrar o radar.

## Alternativas consideradas

- **Pesos heurísticos manuais ou "probabilidade de subida da ação X%" pela última notícia**:
  descartados; violam `AGENTS.md` e `ADR-0013`, confundem ruído ($N=1$) com causalidade,
  não possuem calibração probabilística e sugerem recomendação direcional de ativo.
- **Incluir manchetes RSS como feature numérica da regressão**: descartado neste recorte; os
  feeds públicos entregam apenas janela curta recente, inviabilizando treino histórico sem
  viés. Manchetes entram como contexto qualitativo ao lado do sinal.
- **Treinar com `scikit-learn`/`XGBoost` dentro da API em produção**: descartado; inflaria a
  imagem Docker e o consumo de memória no Render Free para um problema de 4 variáveis que
  possui solução analítica exata em poucas linhas de Python.
- **Usar um ticker não agrícola (como `PETR4` ou `VALE3`) como substituto silencioso de
  `SLCE3`**: descartado; enfraqueceria a coerência econômica com a chuva em Sorriso-MT e
  poderia induzir correlação espúria. Sem `SLCE3`, declara-se `insufficient_data`.

## Consequências

- Entrega no produto a hipótese central do Alternative Alpha (dados alternativos climáticos
  aplicados à oscilação de um ativo da cadeia da soja, comparados *walk-forward* contra um
  baseline de mercado), com pesos auditáveis e zero vazamento temporal.
- Caso na janela curta de 3 meses da `brapi` gratuita o `M1` apresente `MAE` próximo ou
  superior ao `M0`, a interface e a IA exibem esse resultado de forma transparente como
  evidência empírica, sem ocultar desempenho negativo.
- A funcionalidade inteira opera em código, testes e frontend antes mesmo de `BRAPI_TOKEN`
  ser cadastrado; em produção, passa de `insufficient_data` para `ready` automaticamente
  assim que `BRAPI_TOKEN` for configurado no GitHub Actions e `ingest_alpha --backfill-days 90`
  for executado.
- **Reversão**: remover `soy_volatility` de `RadarOut` e das evidências da IA, retirar
  `SLCE3` de `STOCK_SERIES` e regenerar OpenAPI/tipos web; nenhuma tabela ou migração muda.

## Status

**Aceita em 28/11/2026**, por solicitação explícita do usuário para implementação pelo agente
de desenvolvimento, mantendo a configuração externa de chaves de API (`BRAPI_TOKEN`) para
verificação posterior da equipe.
