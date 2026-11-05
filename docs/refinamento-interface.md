# Refinamento da interface da Valyra

Registro de 05/11/2026, na branch `willian/base-do-projeto`. A implementação anterior foi refinada sobre React/TypeScript/Vite, preservando dados, cálculos, contratos, perfis e rotas. O nome público passou a **Valyra**; os identificadores técnicos `valyre` e `@valyre/web` permanecem. Não houve novas dependências.

## Diagnóstico antes da implementação

Foram examinados componentes, tokens, estilos, rotas, testes e documentação. Duas avaliações independentes de fonte apoiaram o trabalho: uma de design e outra do detector Impeccable. Nenhuma delas foi apresentada como inspeção visual renderizada.

1. Escala operacional de 10–13 px, com títulos promocionais de peso excessivo.
2. Seção, marca, perfil, período e aviso demonstrativo repetidos antes dos dados.
3. Painel de planejamento com título promocional e ornamento competindo com o saldo.
4. Tabela com categorias etiquetadas, dados pequenos e alinhamento frágil de descrição/direção.
5. Gráfico sem escala monetária e com diagonais/intervalos iguais entre datas, sugerindo continuidade.
6. Radar com numeração/ícone repetidos, grandes intervalos e leitura lenta.
7. Atalhos da Visão geral que não levavam o perfil na URL.

## Mudanças implementadas

- Sidebar azul profunda com alinhamento, seleção violeta e links úteis; removidos ponto coral redundante e cartão promocional inferior.
- Topo compacto: período e acesso à explicação completa do modo demonstração. Cabeçalhos diretos nas quatro telas.
- Tipografia operacional de 14–16 px, secundária de 12–13 px e títulos de página de 26–28 px. Tokens para controles, bordas, estados e transições.
- Visão geral com saldo inicial/resultado explícitos, percentuais conciliados com o total e síntese de compromissos sem arcos decorativos.
- Financeiro com busca mais larga, filtros próximos dos resultados, valores tabulares à direita, categorias discretas, ordenação real indicada e ação de limpar desabilitada sem filtros.
- Planejamento em degraus, com intervalo temporal real, escala em reais, valores por interação e memória textual. Consulta adicional de datas no celular; não é previsão.
- Radar mais compacto, com tema/origem ilustrativa, relação possível com o perfil e detalhes de contexto, hipótese e limitações.
- Carregamento, erro com nova tentativa, vazio com recuperação e estados de foco/seleção/hover/desabilitado.
- Tabela com rolagem horizontal em celular, conforme escolha expressa do usuário. Não foram ocultadas colunas.
- Navegação estreita em duas colunas e composições que dão espaço a valores empresariais longos.

O sistema foi registrado em [DESIGN.md](../apps/web/DESIGN.md). Não foram criadas funcionalidades de negócio, persistência ou integrações para preencher a interface.

## Uso das referências

`impeccable context` foi executado uma vez sobre `Workspace.tsx`. O resultado autorizou o refinamento da implementação existente sem bloquear em um novo documento de produto. Foram consultados os playbooks de avaliação, operação, polimento, layout, tipografia e a qualidade mínima antes da edição.

O detector estático inicial e a varredura posterior retornaram **um warning `side-tab`**, em `landing.css`, na sequência explicativa da landing. Sem achados adicionais nas telas operacionais. A borda foi mantida como exceção contextual: a detecção identifica o padrão, mas não demonstra um problema de uso nessa sequência. O detector não certifica layout ou acessibilidade.

[Uncodixfy](https://github.com/cyxzdev/Uncodixfy/blob/main/Uncodixfy.md) foi consultado como referência crítica, subordinada ao briefing. Mantivemos a sidebar, o resumo financeiro, o violeta e componentes úteis; suas funções não foram removidas por coincidirem com padrões comuns.

## Verificação funcional

Os testes cobrem as quatro seções em Pessoal e Empresa, filtros/totais, preferências separadas, recuperação de vazio/erro, carregamento ao mudar perfil, foco e atalhos que preservam o perfil. O gráfico é verificado quanto a datas proporcionais, degraus, escala com zero/negativo e lista vazia; no DOM, foco/seleção atualizam o valor e o link abre a memória de cálculo.

| Verificação executada                           | Resultado                                                                            |
| ----------------------------------------------- | ------------------------------------------------------------------------------------ |
| `npm run check`                                 | Passou: typecheck, 26 testes em 4 arquivos, validação Python dos dois perfis e build |
| `npm run format:check`                          | Passou                                                                               |
| `git diff --check`                              | Passou, sem erros de whitespace                                                      |
| Prévia local na porta 5174                      | HTML e módulo do gráfico responderam HTTP 200; título Valyra                         |
| Contraste das combinações principais dos tokens | Texto entre 5,05:1 e 16,71:1; borda dos controles 3,46:1 sobre branco                |
| Detector Impeccable                             | Um warning contextual na landing; nenhum achado nas telas operacionais               |

Os testes DOM não são testes de responsividade renderizada. A última alteração de CSS apenas reaplica os tokens de espaçamento e ajusta o resumo em larguras intermediárias; o build foi refeito. O servidor temporário de revisão na porta 5174 foi encerrado; o servidor existente na porta 5173 foi preservado.

## Limitação que impede encerrar a revisão visual

A ferramenta informou que o host de navegador estava indisponível. Ao selecionar o Brave, encerrou a interação por não conseguir determinar a URL atual com confiança suficiente para aplicar sua política. A automação foi interrompida, sem contornar o bloqueio e sem usar outro caminho para controlar aquela janela.

**Não foram obtidas capturas nem concluída a inspeção renderizada.** A implementação está disponível para revisão, mas o aceite visual permanece aberto. Não se declara ausência de cortes, sobreposições, erros de console ou rolagem acidental em navegador real.

Para concluir a revisão: executar `npm run dev` e conferir Visão geral, Financeiro, Planejamento e Radar nos dois perfis em desktop (1440 px), intermediário (768–1024 px) e celular (320, 375 e 390 px), incluindo zoom de 200%, Tab/Shift+Tab, filtros, leitura e seleção do gráfico, detalhes e os estados vazios. Somente as regiões de tabela devem exigir rolagem horizontal.

O arquivo histórico `verificacao-inicial.md` registra a entrega anterior e o nome usado naquela etapa; não substitui esta verificação. Publicação HTTPS, envio ao remoto, inscrição, créditos e aprovação coletiva continuam sem confirmação.
