# Contexto do Valyra

Leia apenas as referências pertinentes à tarefa. A arquitetura é um monorepo com API modular única; documentos de design não comprovam que a aplicação foi implementada.

| Quando a tarefa envolver | Leia |
| --- | --- |
| Visão, público e escopo | [README do projeto](../README.md) |
| Instruções de trabalho | [AGENTS raiz](../AGENTS.md), [backend](../services/api/AGENTS.md) e [contribuição](../CONTRIBUTING.md) |
| Arquitetura e estado deste checkout | [architecture.md](architecture.md) |
| Decisões aceitas e novos registros | [ADR-0001](adr/0001-monolito-modular.md), [ADR-0002](adr/0002-provedor-llm.md), [ADR-0008](adr/0008-review-por-agente.md), [ADR-0009](adr/0009-dinheiro-em-centavos.md), [ADR-0010](adr/0010-calculos-finance.md), [ADR-0011](adr/0011-contrato-evidencias-ia.md), [ADR-0012](adr/0012-fontes-alpha.md), [ADR-0013](adr/0013-relatorio-semanal-noticias.md), [ADR-0014](adr/0014-reserva-groq.md), [ADR-0015](adr/0015-reserva-openrouter.md), [template](adr/0000-template.md) |
| Vocabulário de dados e produto | [glossary.md](glossary.md) |
| Convenções e histórico da fundação | [spec-tecnica.md](spec-tecnica.md) |
| Schema e integridade dos dados | [modelagem-db.md](modelagem-db.md) |
| CSV, schemas e contratos HTTP Finance | [api-design.md](api-design.md) |
| Migração inicial, seed e decisões pendentes | [revisao-modelagem.md](revisao-modelagem.md) |
| Cliente IA, configuração e testes sem provedor | [ai-client.md](ai-client.md), [ADR-0002](adr/0002-provedor-llm.md) |
| Serviço IA, contexto substituível e integração Finance | [ai-service.md](ai-service.md) |
| Contrato HTTP IA, jornada automática e smoke manual | [ai-http.md](ai-http.md) |
| Validação lexical IA e casos de avaliação | [ai-validation.md](ai-validation.md) |
| Contrato de contexto/evidências IA aprovado | [ADR-0011](adr/0011-contrato-evidencias-ia.md) |
| CI, Claude e configuração manual do GitHub | [github-setup.md](github-setup.md) |
| Publicação gratuita da API (Render e Neon) | [deploy.md](deploy.md) |
| Dados sintéticos e roteiro da apresentação | [demo.md](demo.md) |

## Estado das referências

Os três specs de design — fundação, modelagem e API — registram decisões, contratos e propostas. Os itens explicitamente em revisão permanecem assim até decisão da equipe. A revisão de modelagem complementa esses specs para as Issues de Finance.

A aplicação web histórica segue fora deste checkout. A landing e a aplicação Finance ficam em apps/web; veja seu [README](../apps/web/README.md). Estado das entregas #11/#12, validações e pendências em [integracao-11-12.md](integracao-11-12.md). Não substituir registros históricos por resultados de hoje.
