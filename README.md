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

### Exemplo de uso planejado

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

A demonstração utilizará transações sintéticas e dados econômicos públicos, com identificação clara de informações simuladas. INMET, CONAB, MDIC/Comex Stat e B3 são fontes candidatas; disponibilidade, cobertura histórica e condições de uso serão avaliadas antes da integração.

As projeções numéricas serão produzidas por cálculos e modelos verificáveis. A IA terá o papel de explicar as evidências, preservando sua origem e suas limitações. O uso de dados alternativos para melhorar previsões é uma hipótese de pesquisa a ser comparada com modelos de referência; ainda não há ganho preditivo comprovado.

O MVP não inclui integração bancária real, execução de operações ou recomendações personalizadas de compra e venda. Análises históricas deverão respeitar as datas de publicação e as versões dos dados disponíveis no período simulado.

## Landing page

A página de apresentação está isolada em [`apps/landing/`](apps/landing/README.md), com build estático próprio e exemplos visuais sintéticos. Os links de acesso levam inicialmente ao [repositório oficial](https://github.com/UaiScript/valyra-hackbrasil-2026). Ela não depende da API ou do banco e não ocupa o diretório `apps/web` previsto para a aplicação.

Com Node.js 22.12 ou superior, execute `npm --prefix apps/landing ci --ignore-scripts` e `npm --prefix apps/landing run dev`. As instruções de validação, troca futura do destino, hospedagem e remoção estão no README da landing.

## Base técnica e estágio do projeto

A arquitetura definida é um **monorepo com frontend React e TypeScript e backend único FastAPI, organizado nos domínios Finance, Alpha e AI**. Estão previstos PostgreSQL para os dados da aplicação e DuckDB/Parquet para séries históricas. A [spec de fundação técnica](docs/spec-tecnica.md) detalha a arquitetura e identifica as propostas técnicas ainda em discussão.

Este README apresenta a proposta e o escopo do rascunho. O projeto está em desenvolvimento; as funcionalidades descritas representam as entregas planejadas para o MVP.

A persistência inicial do Finance possui modelos SQLAlchemy, migração Alembic, seed e testes em `services/api/`. Comandos, dependências mínimas e limitações de validação estão no [registro da Issue #10](docs/revisao-modelagem.md); ainda não há endpoints ou importador CSV implementados.
