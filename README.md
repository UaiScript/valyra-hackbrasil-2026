# Valyra

**Inteligência financeira para planejar o orçamento e compreender o contexto dos investimentos.**

O Valyra é uma plataforma de inteligência financeira pessoal em desenvolvimento pela equipe **UaiScript** para o **Hack Brasil 2026**. A proposta é ajudar pessoas a antecipar possíveis dificuldades de orçamento e compreender riscos econômicos relevantes para os ativos que acompanham.

Seu motor de análise econômica, o **Alternative Alpha**, combina dados financeiros tradicionais, dados alternativos e notícias para investigar tendências e produzir sinais fundamentados. O **Valyra AI** explica esses sinais junto ao contexto financeiro pessoal, com fontes, datas, premissas e incertezas explícitas.

## Problema e público-alvo

Controlar os gastos do mês e acompanhar investimentos exige interpretar informações dispersas: transações, contas futuras, cotações, notícias e indicadores econômicos. Consultar esses dados separadamente pode dificultar tanto a percepção de uma pressão futura no caixa quanto a compreensão de riscos associados aos investimentos.

O público inicial são **pessoas físicas que organizam o próprio orçamento e acompanham uma pequena lista de ativos**. O Valyra busca tornar análises e evidências mais acessíveis a esse público, reunindo projeções financeiras e contexto econômico em uma experiência compreensível, inclusive para quem não tem formação em finanças ou estatística.

## Solução proposta

A plataforma reúne três módulos em uma aplicação web responsiva:

| Módulo | Papel na experiência |
| --- | --- |
| **Valyra Finance** | Organizar transações de demonstração por categoria, destacar gastos atípicos e projetar despesas e saldo futuro com premissas visíveis. |
| **Alternative Alpha** | Apresentar sinais econômicos com fontes e datas, combinando cotações, notícias e dados alternativos. O recorte inicial de pesquisa é a cadeia da soja em Mato Grosso. |
| **Valyra AI** | Explicar o contexto pessoal (**Micro**) e o econômico (**Macro**) em linguagem acessível, distinguindo dados observados, projeções e hipóteses. |

O objetivo é permitir uma jornada de **planejar → monitorar → compreender**: visualizar o orçamento, acompanhar sinais relevantes e consultar as evidências por trás de cada análise.

### Exemplo de uso

Uma pessoa consulta a projeção de saldo e identifica uma possível concentração de despesas nas próximas semanas. No radar econômico, encontra um sinal sobre a cadeia agrícola relacionado ao setor de um ativo que acompanha. Ao abrir a explicação, vê a origem das informações, suas datas e as limitações da análise.

Os dois contextos podem coexistir sem relação causal. A explicação deve ajudar a pessoa a investigar e decidir com autonomia, sem concluir automaticamente que um evento econômico altera seu orçamento ou exige a venda de um ativo.

## Escopo do MVP

As quatro entregas prioritárias para o hackathon são:

1. **Dashboard financeiro:** transações e categorias de demonstração, com resumo do orçamento.
2. **Projeção de despesas e saldo:** cálculos reproduzíveis, começando por regras simples e transparentes, com valores conhecidos e previstos identificados.
3. **Radar econômico:** sinais com fonte, data, região e relação fundamentada com um setor ou ativo acompanhado.
4. **Explicação Micro + Macro:** interpretação dos dois contextos com evidências, premissas e incerteza.

O replay histórico é uma entrega adicional, condicionada à conclusão das prioridades e à disponibilidade de registros que permitam reconstruir o que era conhecido em cada data.

## Dados e uso de inteligência artificial

A demonstração usa transações sintéticas e dados econômicos públicos, com identificação das informações simuladas. Os coletores implementados consultam SGS/BCB, brapi e Open-Meteo; notícias vêm de feeds da Agência Brasil, BCB e IBGE, conforme as fontes e condições registradas nas ADRs [0012](docs/adr/0012-fontes-alpha.md) e [0013](docs/adr/0013-relatorio-semanal-noticias.md). A disponibilidade no ambiente publicado depende da configuração e execução das coletas. INMET, CONAB, MDIC/Comex Stat e integração direta com a B3 continuam candidatos futuros.

As projeções numéricas são produzidas por cálculos determinísticos do Finance. A IA explica as evidências, preservando sua origem e suas limitações; a resposta passa por validação de citações e números no servidor. Indicadores e manchetes não demonstram causalidade nem sustentam probabilidades de queda de uma ação. O uso de dados alternativos para melhorar previsões continua uma hipótese de pesquisa; ainda não há ganho preditivo comprovado.

O MVP não inclui integração bancária real, execução de operações ou recomendações personalizadas de compra e venda. Análises históricas deverão respeitar as datas de publicação e as versões dos dados disponíveis no período simulado.

## Landing page

A página de apresentação e a aplicação ficam em [`apps/web/`](apps/web/README.md). A landing (`/`) usa exemplos visuais sintéticos e não depende da API. A aplicação (`#/app`) integra Finance, Alerts, radar Alpha, notícias da semana e explicações da IA com evidências. O [roteiro da demonstração](docs/demo.md) descreve preparação, perguntas e alternativas quando fontes ou provedor estiverem indisponíveis.

Com Node.js 22.12 ou superior, execute `npm --prefix apps/web ci --ignore-scripts` e `npm --prefix apps/web run dev`. Com `make dev` rodando, abra <http://127.0.0.1:3000/#/app>. Validação, destino dos links e hospedagem estão no README de apps/web.

## Base técnica e estágio do projeto

A arquitetura é um **monorepo com frontend React e TypeScript e backend único FastAPI**, organizado nos domínios Finance, Alerts, Alpha e AI, com PostgreSQL e migrações Alembic. DuckDB/Parquet continuam planejados. A [arquitetura atual](docs/architecture.md) distingue a implementação das propostas da [fundação técnica](docs/spec-tecnica.md).

Implementado no MVP:

- Finance: importação CSV com rejeições e duplicatas, categorias, resumo, recorrências, gastos atípicos, orçamento por categoria, limite diário, projeção e alertas de caixa.
- Alpha: radar de indicadores, cotações em variação percentual, clima por região e relatório semanal de notícias com fonte e publicação.
- IA: `POST /api/v1/ai/explain`, contexto obtido no servidor, cliente Gemini/OpenAI, seleção dentro do limite do prompt e resposta com evidências originais. Ausência de dados é declarada; a explicação exige provedor configurado.
- Validação: testes de integração PostgreSQL, jornadas HTTP com LLM simulado, testes de navegador e CI no GitHub Actions. Execuções automáticas não fazem chamadas pagas ao LLM.

Continuam pendentes login, conexão bancária, histórico persistido de conversas, previsão de retorno/probabilidades e replay completo de Finance. Execução local em [CONTRIBUTING.md](CONTRIBUTING.md), contrato em [api-design.md](docs/api-design.md) e limites da IA em [ai-validation.md](docs/ai-validation.md).
