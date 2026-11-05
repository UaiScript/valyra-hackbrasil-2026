# Estado atual

Revisão de manutenção em 05/11/2026, branch `willian/base-do-projeto`. Este é o resumo atual; relatórios de etapas anteriores mantêm suas próprias datas, nomes e contagens de testes.

## Implementado

- Landing com prévias em HTML, menu, abas Pessoal/Empresa, exemplos e acesso à demonstração.
- Um app com Visão geral, Financeiro, Planejamento e Radar; contexto e preferências separados por perfil.
- Consulta com filtros, totais em centavos e compromissos com memória de cálculo/gráfico em degraus.
- Estados de carregamento, erro, vazio e foco cobertos pelos testes pertinentes.
- Leitura local de JSON sintético; scripts Python de validação e prévia estática.

## Demonstrativo ou planejado

Todos os registros são fictícios. O planejamento é uma subtração de compromissos e a hipótese de alimentação da landing é editorial. O Radar não entrega notícias reais nem aplica impacto econômico ao financeiro.

API/FastAPI, persistência, autenticação, conexão bancária, importação, cenários editáveis e IA com fontes não estão implementados. Prioridades e decisões coletivas estão em [escopo-mvp.md](escopo-mvp.md); participação e publicação, em [hackathon-checklist.md](hackathon-checklist.md).

## Pontos de atenção

- Revisão visual de landing e app continua pendente. Os registros de [landing](landing-reconstrucao.md) e [refinamento](refinamento-interface.md) descrevem o bloqueio de acesso à URL do navegador; não há capturas aprovadas.
- A base usa datas fixas de novembro de 2026. Alterar o período exige alinhar fixtures, labels e validação; consulte [desenvolvimento.md](desenvolvimento.md).
- Os nomes técnicos `valyre` / `@valyre/web` são intencionais; textos públicos usam Valyra.
- O arquivo legado de produto `FARO_BASE_PRODUTO_NEGOCIO_E_IMPLEMENTACAO_v1.md` permanece vazio. O [PRODUCT.md](../apps/web/PRODUCT.md) captura contexto confirmado, não uma aprovação coletiva do documento completo de negócio.
- Configurações instaladas em `.agents/`, `.agent/`, `.codex/` e `.gemini/` foram preservadas. O [AGENTS.md](../AGENTS.md) centraliza orientações do projeto; não há novas cópias por assistente.

## Verificação desta revisão

| Check                             | Resultado                                                                                                                                                               |
| --------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Baseline antes das alterações     | `npm run check` passou: 38 testes em 6 arquivos                                                                                                                         |
| Após centralizar as rotas         | `npm run check` passou: tipos, 56 testes em 7 arquivos, validação Python e build                                                                                        |
| Instalação limpa                  | `npm ci --offline --no-audit --no-fund` e `npm run build` passaram em diretório temporário com cópia da aplicação e lockfile; o `node_modules` principal foi preservado |
| Execução local                    | Vite iniciado na porta temporária 5180; página, módulo App e módulo de rotas responderam HTTP 200                                                                       |
| Formatação e whitespace           | `npm run format:check` e `git diff --check` passaram                                                                                                                    |
| Links e imports                   | 94 links Markdown locais e 95 imports relativos resolvidos, com capitalização exata verificada                                                                          |
| Integridade de apresentação/dados | SHA256 preservado em 13 arquivos: todos os estilos, fixtures, favicon, componentes comuns, HTML e manifestos/lockfile                                                   |
| Credenciais/exemplos              | Fixtures inspecionadas e busca por padrões comuns de credenciais sem achados nos arquivos da aplicação, scripts e documentação                                          |

Não existe script de lint; nenhum foi inventado ou adicionado. A instalação isolada usou o cache npm completo deste ambiente, não confirma disponibilidade de rede em outra máquina. O build foi feito também no checkout principal.

## Mudanças de manutenção

O catálogo de telas, a interpretação do hash e a construção de links agora ficam em `apps/web/src/app/routes.ts`, reutilizados no App, shell, atalhos e prévias. O contrato dos URLs foi preservado e ganhou testes específicos. Não houve movimentação de pastas, nova dependência, funcionalidade de negócio ou alteração de CSS.

Foram revisados comentários de centavos, filtros, compromissos, geometria de datas e contrato da leitura local. O README e AGENTS encaminham ao índice seletivo, que distingue documentos atuais de registros históricos. A arquitetura existente foi atualizada no mesmo caminho, sem duplicação. `PRODUCT.md` perdeu uma restrição transitória da tarefa anterior; o registro do sistema visual foi corrigido para não afirmar a existência de um sidecar ausente.

As verificações ocorreram no Windows. Não foi executado um build em Linux nem inspeção visual de navegador; as verificações de capitalização, testes de fluxos e integridade dos estilos reduzem esses riscos sem substituir esses ambientes.
