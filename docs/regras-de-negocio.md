# Regras implementadas

Estas regras descrevem o código atual. Direção de produto e propostas futuras ficam em [escopo-mvp.md](escopo-mvp.md); estrutura e integração, em [arquitetura-inicial.md](arquitetura-inicial.md).

## Perfis e origem dos dados

Pessoal e Empresa compartilham as quatro seções. `personal` usa receitas/despesas e temas de interesse; `business` usa entradas/saídas, caixa e exposições operacionais. Rótulos: [profiles.ts](../apps/web/src/features/workspace/profiles.ts). Registros: [personal.json](../apps/web/src/data/demo/personal.json) e [business.json](../apps/web/src/data/demo/business.json).

Todos os valores, compromissos e eventos são sintéticos. O período realizado é 1–5/11/2026; compromissos de exemplo vencem depois de 5/11/2026. É uma referência fixa da demonstração, não a data corrente nem um calendário atualizado automaticamente.

O [repositório local](../apps/web/src/data/demoRepository.ts) devolve cópias independentes. Preferências do Radar ficam separadas por perfil enquanto o Workspace está montado. Trocar perfil ou seção reinicia filtros e detalhes da tela; recarregar ou voltar à landing encerra essas preferências. O perfil do hash acompanha a navegação e a recarga. A escolha de aba da landing é local àquela seção.

## Dinheiro e conciliação

Fonte: [calculations.ts](../apps/web/src/features/finance/calculations.ts). Valores monetários usam centavos inteiros, sem arredondar números em reais dentro das regras.

| Conceito                  | Regra                                                                             |
| ------------------------- | --------------------------------------------------------------------------------- |
| Entrada/receita           | `Transaction.amountCents > 0`                                                     |
| Saída/despesa             | `Transaction.amountCents < 0`; total de despesas é apresentado em módulo positivo |
| Resultado do período      | Soma de entradas menos o módulo das saídas                                        |
| Saldo disponível/em caixa | Saldo inicial + resultado do período                                              |
| Total de categoria        | Soma apenas das saídas daquela categoria                                          |
| Percentual de categoria   | Saídas da categoria / total de saídas informado na mesma visualização             |

O Financeiro calcula os totais **da seleção filtrada**, sem adicionar saldo inicial. A Visão geral usa todos os registros do perfil e inclui saldo inicial no saldo principal. Por isso resultado e saldo não são números intercambiáveis. Formatação em reais e datas: [format.ts](../apps/web/src/shared/format.ts).

## Filtros e consulta

Direção, categoria e busca são combinadas com **E**. Categoria compara o nome exato. A busca consulta descrição e categoria, ignora maiúsculas e espaços externos, mas preserva acentos: `cafe` não equivale a `café`. `all` desativa somente o filtro correspondente.

Os resultados são exibidos por data decrescente; não há ordenação acionada por coluna. Limpar filtros restaura a lista completa e fica desabilitado sem filtros ativos. Consulta não cria, edita ou importa lançamentos.

## Realizado, previsto e simulado

- **Realizado:** transações do período demonstrativo. A palavra não significa dado de uma conta real.
- **Previsto:** compromissos sintéticos futuros, com `amountCents` positivo. Eles ainda não compõem as saídas realizadas.
- **Simulado:** saldo atual menos esses compromissos, ordenados por data ISO crescente. O cálculo não altera transações nem infere renda, juros, recorrência ou efeitos econômicos.

O gráfico usa os saldos já calculados. [chartGeometry.ts](../apps/web/src/features/planning/chartGeometry.ts) calcula apenas escala e posições: intervalos entre datas em dias civis UTC; degrau vertical no vencimento; escala que inclui zero. Foco, seletor de datas e memória de cálculo estão em [BalanceChart.tsx](../apps/web/src/features/planning/BalanceChart.tsx). O gráfico não é motor de previsão ou saldo diário observado.

## Radar e hipóteses

Os eventos são fictícios, com tema, região, contexto, premissa e limitação. Os temas selecionados filtram a lista; desmarcar todos apresenta o estado vazio. As explicações são editoriais, sem consulta a fontes em tempo real ou modelo de IA. Um evento **não altera automaticamente** qualquer despesa, saldo ou compromisso.

A landing reutiliza os cálculos e dados da demonstração em [previewModel.ts](../apps/web/src/features/landing/previewModel.ts). A hipótese de alimentação é outra conta: `48590 + Math.round(48590 × 5 / 100) = 51020` centavos. O acréscimo de R$ 24,30 é arredondado uma vez e não entra no planejamento. O planejamento Pessoal continua `555770 − 88490 = 467280` centavos.

## Validação e limites

[check_demo_data.py](../scripts/check_demo_data.py) verifica centavos inteiros, datas do período, IDs, temas e compromissos futuros. TypeScript valida contratos do código e das fixtures importadas; não valida uma futura resposta HTTP em tempo de execução. Esse adaptador ainda não existe.

Não há autenticação, autorização de dados reais, persistência, conexão bancária, importação, IA operacional ou notícias verificadas. O seletor de perfil é um contexto de demonstração, não uma fronteira de autorização. Propostas de evolução não devem ser tratadas como regras já implementadas.
