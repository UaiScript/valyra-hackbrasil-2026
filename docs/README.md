# Contexto do Valyra

Leia apenas as referências pertinentes à tarefa. A arquitetura é um monorepo com API modular única; documentos de design não comprovam que a aplicação foi implementada.

| Quando a tarefa envolver | Leia |
| --- | --- |
| Visão, público e escopo | [README do projeto](../README.md) |
| Instruções de trabalho | [AGENTS raiz](../AGENTS.md), [backend](../services/api/AGENTS.md) e [contribuição](../CONTRIBUTING.md) |
| Arquitetura e estado deste checkout | [architecture.md](architecture.md) |
| Decisões aceitas e novos registros | [ADR-0001](adr/0001-monolito-modular.md), [ADR-0008](adr/0008-review-por-agente.md), [ADR-0009](adr/0009-dinheiro-em-centavos.md), [template](adr/0000-template.md) |
| Vocabulário de dados e produto | [glossary.md](glossary.md) |
| Convenções e histórico da fundação | [spec-tecnica.md](spec-tecnica.md) |
| Schema e integridade dos dados | [modelagem-db.md](modelagem-db.md) |
| CSV, schemas e contratos HTTP Finance | [api-design.md](api-design.md) |
| Migração inicial, seed e decisões pendentes | [revisao-modelagem.md](revisao-modelagem.md) |
| CI, Claude e configuração manual do GitHub | [github-setup.md](github-setup.md) |

## Estado das referências

Os três specs de design — fundação, modelagem e API — registram decisões, contratos e propostas. Os itens explicitamente em revisão permanecem assim até decisão da equipe. A revisão de modelagem complementa esses specs para as Issues de Finance.

A aplicação web histórica segue fora deste checkout. A landing está integrada e isolada; veja seu [README](../apps/landing/README.md). Estado das entregas #11/#12, validações e pendências em [integracao-11-12.md](integracao-11-12.md). Não substituir registros históricos por resultados de hoje.
