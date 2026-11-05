# Verificação da primeira entrega

Entrega local verificada em **05/11/2026**, na branch `willian/base-do-projeto`. O nome público foi atualizado para **Valyre** conforme orientação posterior. O endereço do repositório e o arquivo histórico vazio de produto foram preservados.

## Verificações executadas

| Verificação                                                            | Resultado                                                                                                                                     |
| ---------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| `npm run typecheck`                                                    | Passou, TypeScript em modo estrito                                                                                                            |
| `npm test`                                                             | Passou: 15 testes em 3 arquivos                                                                                                               |
| `npm run check:data`                                                   | Passou para os dois perfis: centavos, IDs, datas e temas                                                                                      |
| `npm run build`                                                        | Passou: build estático em `apps/web/dist/`                                                                                                    |
| `npm run format:check`                                                 | Passou: padrão Prettier                                                                                                                       |
| `python -m py_compile scripts/check_demo_data.py scripts/serve_web.py` | Passou                                                                                                                                        |
| `git diff --check`                                                     | Passou, sem erros de whitespace                                                                                                               |
| Prévia Python em `http://127.0.0.1:4173/`                              | HTTP 200 para HTML, JavaScript, CSS e favicon; título Valyre                                                                                  |
| Contraste das combinações principais de texto                          | Cálculo das combinações principais acima de 4,5:1; não equivale a auditoria completa                                                          |
| Conferência do nome                                                    | Workspace e lockfile usam `valyre` / `@valyre/web`; referências anteriores permanecem somente no histórico e no caminho do documento original |

Ambiente utilizado: Node.js 24.19.0, npm 11.17.0 e Python 3.13.15. A sequência `npm run check` passou após a renomeação. O esbuild precisou executar fora da restrição de leitura do sandbox Windows para resolver diretórios ancestrais; não foi necessário alterar as regras da aplicação.

## O que os testes protegem

- Conciliação dos dados Pessoal/Empresa, centavos exatos, resultado negativo e listas vazias.
- Filtros combinados, categorias e soma de saídas, sem mutação das fixtures.
- Ordenação e subtração de compromissos, sem inferir receitas ou efeitos macro.
- Leituras independentes, listas aninhadas e dados próprios de cada perfil.
- Em DOM simulado: entrada Empresa pela landing, navegação pelas quatro seções e preservação do contexto no hash.
- Filtros da interface, total da seleção, estado vazio e limpeza; reinicialização ao trocar perfil.
- Temas separados por perfil, abertura dos detalhes do Radar, limpeza de detalhes, foco no título e acesso direto ao conteúdo.

## Limitação da conferência visual

A ferramenta de navegador não expôs uma conexão utilizável. Após recuperar o acesso ao computador, foi tentada uma revisão no Brave, mas a automação encerrou o acesso porque não conseguiu determinar a URL atual com confiança suficiente para aplicar sua política. Nenhum bloqueio de segurança foi contornado.

**Não houve inspeção visual concluída em desktop ou celular.** O DOM simulado valida comportamento, mas não mede layout, cortes ou sobreposições. Os estilos incluem breakpoints, tabelas com rolagem horizontal, foco visível e redução de movimento; precisam de conferência manual em navegador real, inclusive a 320 px de largura e com zoom de 200%.

## Pendências externas

Publicação HTTPS e URL pública, envio ao remoto/PR, inscrição, confirmação de participação, créditos, vídeo e aprovação coletiva permanecem pendentes. O documento completo de produto continua vazio. A prévia local de verificação foi encerrada; use os comandos do README para executá-la novamente.
