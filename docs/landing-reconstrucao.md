# Reconstrução da landing da Valyra

Registro de implementação de 05/11/2026. A landing pública foi reconstruída no repositório conforme a sequência solicitada pelo usuário. A prévia principal inicia em **Pessoal**, escolha confirmada durante o trabalho. O veredito da revisão independente é **recapture**: há validação técnica, mas faltam as capturas e a revisão visual exigidas.

## Escopo e composição

A nova sequência apresenta:

1. Cabeçalho com marca, navegação para conteúdo real e acesso à demonstração.
2. Mensagem central com duas ações e indicação de dados demonstrativos.
3. Prévia panorâmica Pessoal, alinhada e composta em HTML.
4. Abas Para você e Para sua empresa, com conteúdo e dados correspondentes.
5. Exemplo Micro + Macro com premissa explícita e explicação do estágio da IA.
6. Recortes de Financeiro, Planejamento e Radar, com informações específicas da demonstração.
7. Estágio do projeto, dúvidas verificáveis e repositório.
8. Chamada final e rodapé compacto.

A identidade cromática, o nome Valyra e o símbolo existente foram preservados. A tipografia Segoe UI/system-ui continua em uso. O dashboard, seus componentes compartilhados, rotas, contratos, regras de negócio, estado e integrações ficaram fora da reconstrução. Os estilos novos são locais à landing.

Não foram adicionadas dependências, fontes externas ou imagens de IA/terceiros. As interfaces e barras das prévias são HTML/CSS alimentados pelos registros sintéticos existentes. Não há screenshots de produto ou imagens comerciais que exijam proveniência adicional.

## Arquivos principais

| Arquivo                                                                      | Responsabilidade                                                                                              |
| ---------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| `apps/web/src/features/landing/Landing.tsx`                                  | Sequência da página, cabeçalho/menu, exemplo Micro/Macro/IA, recortes, dúvidas, chamadas e rodapé.            |
| `apps/web/src/features/landing/AudienceSection.tsx`                          | Abas acessíveis, conteúdo por público, carregamento, erro e destinos de demonstração por perfil.              |
| `apps/web/src/features/landing/ProductPreviews.tsx`                          | Prévias panorâmica e compacta, Financeiro, Planejamento e Radar.                                              |
| `apps/web/src/features/landing/previewModel.ts`                              | Adaptação dos dados da demonstração e hipótese editorial de alimentação, reutilizando os cálculos existentes. |
| `apps/web/src/shared/styles/landing.css`                                     | Composição, estados e adaptação responsiva no escopo da landing.                                              |
| `apps/web/PRODUCT.md`                                                        | Contexto de produto e limites atuais, incluindo a escolha inicial de Pessoal.                                 |
| `apps/web/DESIGN.md`                                                         | Sistema existente do dashboard e extensão local observada da landing.                                         |
| `apps/web/.impeccable/surfaces/apps-web-src-features-landing-landing-tsx.md` | Contrato de direção desta superfície.                                                                         |

`DESIGN.md` recebeu uma extensão local e a correção da frase antiga que dizia que a composição da landing estava preservada. O sistema do dashboard foi mantido. Não foi criada uma nova família visual global, nem regenerado o sidecar do sistema ou reparado drift fora do escopo.

## Dados, cálculos e limites de produto

A prévia inicial usa `landingExample`, cópia do conjunto Pessoal de `demoRepository`. O modelo reutiliza `summarize`, `expenseCategories` e `projectCommitments`; as abas leem o mesmo repositório de demonstração. Não há uma coleção paralela de indicadores comerciais. Os dados são os registros efetivos da demonstração, e todos são **sintéticos**, sem informações financeiras reais do usuário.

As prévias mostram saldo inicial e resultado do período separadamente, percentuais sobre o total informado de despesas, compromissos e os três lançamentos mais recentes em ordem decrescente de data. Os dois cenários abaixo têm fórmulas e finalidades distintas:

| Exemplo                | Fórmula em centavos                                          | Apresentação em reais                                                                    |
| ---------------------- | ------------------------------------------------------------ | ---------------------------------------------------------------------------------------- |
| Alimentação hipotética | `48590 + Math.round(48590 × 5 / 100) = 48590 + 2430 = 51020` | R$ 485,90 de referência + R$ 24,30 de diferença = R$ 510,20 para uma compra equivalente. |
| Planejamento Pessoal   | `555770 − 88490 = 467280`                                    | R$ 5.557,70 de saldo − R$ 884,90 de compromissos = R$ 4.672,80 de saldo resultante.      |

O aumento de 5% é uma hipótese editorial da landing, arredondada uma vez em centavos. Não vem de notícia, cotação ou fonte econômica verificada e não altera saldo, registros ou compromissos. O Planejamento apenas subtrai os compromissos listados; não aplica essa hipótese nem prevê novas receitas.

A demonstração permite explorar Visão geral, Financeiro, Planejamento e Radar nos perfis Pessoal e Empresa, sem cadastro. Conexão bancária, notícias em tempo real, IA operacional e cálculo automático de impacto econômico não estão disponíveis. As explicações atuais são editoriais; as integrações e a IA são evolução planejada.

## Estados e navegação implementados

- **Menu:** até 900 px, o botão expõe `aria-expanded` e `aria-controls`, muda de nome e abre os links. A abertura foca o primeiro link; Escape fecha e devolve o foco ao botão. Selecionar uma seção fecha o menu, rola até ela e foca seu título. O acesso móvel à demonstração permanece no menu e na abertura.
- **Abas:** iniciam em Pessoal. Clique, ArrowLeft, ArrowRight, Home e End atualizam seleção e foco com `tabIndex` móvel. O painel identifica a aba ativa. Texto, benefícios, prévia e link acompanham Pessoal ou Empresa.
- **Dados por perfil:** durante a troca, há estado de carregamento com `aria-busy`/status. Erro apresenta alerta e nova tentativa. Respostas tardias são descartadas; a composição não reutiliza números Pessoais sob título Empresa.
- **Links:** as ações gerais abrem `#/demo/overview?profile=personal`; os destinos das abas e da navegação das prévias preservam o perfil correspondente. Financeiro, Planejamento e Radar têm links para suas rotas reais. “O projeto” aponta para conteúdo da página; o GitHub usa o repositório existente.
- **Foco e movimento:** há foco visível, controles nomeados e transições locais de 150 ms, desativadas com preferência de movimento reduzido. As dúvidas usam `details`/`summary` nativos.

Esses comportamentos foram inspecionados no código. A revisão de teclado e a confirmação visual no navegador continuam na lista manual abaixo.

## Referências e limites de acesso

As páginas [Conta Azul](https://contaazul.com/), [Koyfin](https://www.koyfin.com/) e [Koyfin Features](https://www.koyfin.com/features/) foram acessadas por ferramenta web. A direção aproveita clareza de comunicação por necessidades e demonstração de funcionalidades com contexto. Não foram copiados marcas, textos, screenshots ou números comerciais dessas empresas.

Não houve inspeção visual das referências nem do artefato no navegador. A ferramenta de computador informou `browser host unavailable`; a tentativa de selecionar o Edge encerrou a interação por não conseguir confirmar a URL atual. Assim, não há comparação capturada de antes/depois nem comprovação visual de proporções, primeira dobra, contraste ou ausência de overflow.

## Execução e verificação técnica

Na raiz do repositório, com as dependências instaladas:

```powershell
npm run dev --workspace @valyre/web -- --host 127.0.0.1 --port 5174
```

Abrir `http://127.0.0.1:5174/#/`. Os comandos de verificação existentes são:

```powershell
npm run check
npm run format:check
git diff --check
```

Resultados registrados nesta sessão:

| Evidência                        | Resultado                                                                                            |
| -------------------------------- | ---------------------------------------------------------------------------------------------------- |
| `npm run check`                  | Passou: typecheck, 38 testes em 6 arquivos, validação Python dos 2 perfis e build.                   |
| `npm run format:check`           | Passou.                                                                                              |
| `git diff --check`               | Passou.                                                                                              |
| Detector do Impeccable           | Uma execução em `apps/web/src`, resultado `[]`; não substitui revisão renderizada.                   |
| Servidor Vite temporário em 5174 | HTML e módulo `Landing.tsx` responderam HTTP 200; isso confirma serviço, sem confirmar renderização. |
| Comparação SHA256                | 28 arquivos ao todo: código fora da landing e seu CSS, manifestos e lockfile, sem alterações.        |

O servidor temporário da porta **5174 foi encerrado** ao final da verificação. O servidor preexistente na porta **5173 foi preservado**.

## Revisão visual pendente

**Veredito independente: `recapture`.** Não houve aprovação visual ou decisão de `ship`. Faltam as três capturas full-page, todas iniciando no perfil Pessoal:

| Largura | Captura exigida                            |
| ------- | ------------------------------------------ |
| 1440 px | `apps/web/.impeccable/review/desktop.png`  |
| 390 px  | `apps/web/.impeccable/review/mobile.png`   |
| 768 px  | `apps/web/.impeccable/review/user-768.png` |

Checklist para concluir a validação manual e reavaliar o veredito:

- [ ] Em **1440 px**, capturar a página inteira a partir de Pessoal e conferir título, início da prévia na primeira dobra, largura e leitura dos números, alinhamentos, espaçamento e contraste entre seções.
- [ ] Em **768 px**, capturar a página inteira a partir de Pessoal e conferir menu, navegação horizontal das prévias, organização do exemplo Micro/Macro/premissa, transições de coluna e valores sem corte.
- [ ] Em **390 px**, capturar a página inteira a partir de Pessoal e conferir menu, botões, rótulos completos, totais em linhas, categorias junto às descrições, ordem das etapas e compromissos sem sobreposição.
- [ ] Nas três larguras, conferir o documento inteiro para rolagem horizontal acidental, recortes, foco visível, contraste renderizado e conteúdo legível; não inferir esses resultados apenas do CSS.
- [ ] Operar o menu por teclado, conferir foco inicial, Escape, retorno ao botão e navegação/foco das seções.
- [ ] Operar as abas por clique, setas, Home e End; conferir seleção, painel, conteúdo, números e destinos dos dois perfis. Conferir carregamento e nova tentativa em uma falha controlada.
- [ ] Abrir os links das prévias e de Financeiro, Planejamento e Radar; conferir rotas e perfil correto. Abrir e fechar as dúvidas por teclado.
- [ ] Conferir o exemplo de alimentação e o Planejamento contra as fórmulas registradas, sem associação indevida entre os resultados.
- [ ] Conferir preferência de movimento reduzido e leitura das prévias sem dependência de hover. As prévias não usam arquivos de imagem; não há carregamento de imagem de produto para validar.
- [ ] Comparar as capturas e submeter a nova evidência à revisão independente antes de registrar aprovação visual.
