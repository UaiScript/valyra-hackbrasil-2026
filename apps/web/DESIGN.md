# Sistema visual da Valyra

Refinamento da implementação existente. A superfície da demonstração opera em modo **Operate**: consultar registros, entender o saldo e relacionar compromissos e contexto. A composição da landing foi reconstruída como superfície de apresentação, preservando a identidade global. Este documento registra decisões do frontend; não aprova o escopo do produto em nome da equipe.

## Identidade e prioridades

O nome público é **Valyra** e o símbolo vetorial existente permanece. `valyre` e `@valyre/web` são identificadores técnicos preservados. A navegação continua Visão geral, Financeiro, Planejamento e Radar, com Pessoal/Empresa no mesmo shell.

O caminho de leitura é saldo → entradas/saídas → compromissos → lançamentos → contexto econômico. A composição diferencia números registrados, simulação e interpretação. Não usa índices de risco, precisão ou resultados inventados.

## Tokens e papéis

Fonte: `src/shared/styles/tokens.css`. Estilos operacionais: `src/shared/styles/workspace.css`. A família Segoe UI/system-ui existente foi mantida, sem fontes externas.

| Papel              | Regra                                                                       |
| ------------------ | --------------------------------------------------------------------------- |
| Fundo e leitura    | `#F6F5FA` e `#FFFFFF`                                                       |
| Estrutura e texto  | `#171B3B`; sidebar e síntese de compromissos em azul profundo               |
| Ação/seleção       | `#6B4EFF`; variante `--violet-ink` para texto com contraste                 |
| Acento             | `#F57963`, pontual no símbolo; sem ponto redundante na seleção              |
| Texto principal    | 14–16 px, conforme a função                                                 |
| Metadados          | 12–13 px, com contraste suficiente                                          |
| Título da página   | 28 px em desktop; 26 px em celular                                          |
| Título de seção    | 16–18 px                                                                    |
| Valores principais | 28–32 px; secundários 22–28 px; algarismos tabulares                        |
| Espaçamento        | Base de 4 px; grupos 8–12 px, conteúdo 16–24 px, margens principais 32 px   |
| Bordas e raios     | Borda de 1 px; controles 6 px e painéis 8 px                                |
| Profundidade       | Sombra somente no detalhe sobreposto da demonstração                        |
| Estados            | Tokens para hover, foco, seleção, desabilitado e erro; transições de 150 ms |

## Componentes e interações

- **Shell:** seleção violeta e nomes visíveis; marca, seletor e navegação alinhados. Sem mensagem promocional na sidebar. O topo mostra período e um disclosure de demonstração, sem repetir seção/perfil em vários cabeçalhos.
- **Resumo:** saldo principal e entradas/saídas de apoio; saldo inicial e resultado do período ficam explícitos. No Financeiro, o resultado da seleção lidera e continua acompanhando os filtros.
- **Categorias:** barras com uma cor principal, rótulos/valores alinhados e percentuais calculados sobre o total informado.
- **Tabela:** descrição com direção em texto, valores com sinal, datas sem quebra e números alinhados à direita. Categorias usam texto discreto. Ordenação é somente a efetiva: data decrescente.
- **Planejamento:** degraus horizontais até o vencimento e verticais na saída; datas com distâncias proporcionais. Escala em reais, valores exatos por foco/ponteiro/toque e memória de cálculo. O realizado é o ponto inicial; os demais pontos são simulados.
- **Radar:** tema, região/origem ilustrativa, título, resumo e relação possível com o perfil. Detalhes separam contexto, hipótese e limites. Nenhuma hipótese altera o financeiro.
- **Estados:** carregamento sem reutilizar dados do outro perfil, erro com nova tentativa, vazio com recuperação e limpeza de filtros desabilitada quando não há filtros.

## Adaptação e acessibilidade

Até 800 px, a sidebar passa a uma navegação superior. Até 420 px, os quatro destinos ficam em duas colunas para preservar os nomes completos. Em telas estreitas, valores longos deixam a composição em duas colunas; a hierarquia é preservada por linhas de comparação.

**Decisão expressa do usuário:** tabelas mantêm rolagem horizontal no celular. A região tem nome, foco por teclado e indicação visível. Descrição, categoria, data e valor continuam disponíveis.

No gráfico móvel, alvos de 24 px evitam sobreposição e um seletor de data com altura de controle fornece uma alternativa de toque. Rótulos dos eixos são HTML, com tamanho independente da escala do SVG. A tabela de memória de cálculo contém os valores completos; o link a reabre antes de transferir o foco.

Foco visível, labels, controles nativos e nomes acessíveis acompanham os componentes. A preferência de movimento reduzido continua respeitada. Contraste calculado em tokens não substitui a conferência de contraste renderizado.

## Estado de verificação

O refinamento foi verificado por tipos, testes de domínio/DOM e build. **A revisão renderizada em desktop e celular permanece pendente:** a ferramenta de computador encerrou o acesso por não conseguir verificar a URL atual do navegador. Não há capturas validadas desta versão. Veja `../../docs/refinamento-interface.md` para o registro e as verificações restantes.

## Landing pública — extensão local

### Overview

A landing opera em modo **Persuade**, com prévia inicial **Pessoal** confirmada pelo usuário. A composição agora apresenta mensagem central, prévia panorâmica alinhada, públicos, exemplo Micro/Macro/IA, recortes de funcionalidades, estágio do projeto e encerramento. Esse arranjo é local à landing; não redefine a densidade nem o sistema operacional do dashboard descrito acima.

A implementação usa `src/features/landing/` e `src/shared/styles/landing.css`. As regras visuais ficam sob a superfície da landing e reutilizam marca, símbolo, fonte e tokens globais existentes. Não há nova família visual global ou alteração de autoridade do sistema; nenhum sidecar foi criado ou regenerado nesta extensão.

### Colors

Branco e fundo claro sustentam a leitura. Azul profundo estrutura as prévias e a seção de Planejamento; violeta identifica ações, seleção e barras de categorias. O coral permanece no símbolo e no foco da seção escura. As cores vêm de `tokens.css`; a landing não substitui a paleta global.

### Typography

A família Segoe UI/system-ui é preservada. O título principal usa peso 600, `clamp(2.125rem, 4vw + 1rem, 3.75rem)` e entrelinha 1,08; até 600 px, usa `clamp(2rem, 8.8vw, 2.625rem)` e entrelinha 1,12. Os títulos de seção usam peso 600 e `clamp(1.875rem, 3.1vw, 2.625rem)`, passando a 30 px nas seções em telas estreitas. Valores financeiros usam algarismos tabulares.

Os tokens abaixo são observados no escopo local de `landing.css`; esse arquivo continua sendo sua fonte de implementação.

| Token local           | Valor observado                              |
| --------------------- | -------------------------------------------- |
| `--lp-body`           | `1.0625rem`; `1rem` até 600 px               |
| `--lp-support`        | `0.875rem`                                   |
| `--lp-section-gap`    | `5rem`; `4rem` até 900 px; `3rem` até 600 px |
| `--lp-control-radius` | `0.375rem`                                   |
| `--lp-preview-radius` | `0.75rem`                                    |
| `--lp-preview-shadow` | `0 18px 48px -30px #171b3b45`                |
| `--lp-transition`     | `150ms var(--ease-state)`                    |

### Layout

O contêiner de leitura tem limite de 1240 px e margens totais de 80 px; a prévia ampla tem limite de 1320 px e margens totais de 64 px. Até 900 px, ambos usam margens totais de 48 px; até 600 px, de 32 px. O cabeçalho tem altura mínima de 76 px no desktop. A abertura é centralizada e seguida imediatamente pela prévia.

A apresentação varia entre colunas, faixas de fundo e divisórias. Em 900 px, a navegação das prévias passa de lateral para uma linha de quatro destinos, e as seções de funcionalidades passam a uma coluna. Em 600 px, os totais, o exemplo de contexto e os compromissos passam a uma sequência vertical. A categoria da tabela reaparece junto à descrição quando sua coluna é ocultada. Esses comportamentos estão implementados e ainda exigem conferência renderizada em 390, 768 e 1440 px.

### Elevation & Depth

A prévia panorâmica usa a sombra local suave e uma borda discreta. A versão compacta das abas não usa sombra; as demais seções dependem de superfícies, contraste e divisórias. Essa diferença pertence à apresentação pública e não altera a regra de profundidade do dashboard.

### Shapes

Controles locais usam o raio de 6 px; as superfícies de prévia usam 12 px. As prévias ficam alinhadas, sem inclinação ou perspectiva. O conteúdo explicativo é organizado também por linhas e espaço, sem exigir um cartão para cada bloco.

### Components

- **Ações:** altura mínima de 48 px, ou 44 px no cabeçalho; preenchimento violeta, hover em `--violet-ink`, estado pressionado e foco visível. A ação secundária usa borda. As transições respeitam movimento reduzido.
- **Menu móvel:** disponível até 900 px; nome e `aria-expanded` acompanham o estado. Ao abrir, move o foco ao primeiro link; Escape fecha e devolve o foco ao botão. Os links locais rolam e focam o título da seção sem alterar o hash do roteador. Até 600 px, o acesso à demonstração fica no menu e na abertura.
- **Abas de público:** Pessoal inicia selecionado. Clique, setas, Home e End alteram seleção e foco. Título, descrição, três benefícios, prévia e destino da demonstração acompanham o perfil. Carregamento e erro com nova tentativa não exibem números do outro perfil; respostas tardias são descartadas.
- **Prévias:** são apresentações em HTML dos registros sintéticos da demonstração, com links reais para as seções correspondentes. Totais, categorias, compromissos e lançamentos recentes reutilizam os cálculos existentes. Não representam um segundo dashboard com regras próprias.
- **Dúvidas:** disclosures nativos com respostas sobre dados sintéticos, perfis e integrações indisponíveis.

### Do's and Don'ts

- **Do** manter a composição da landing local e preservar o sistema operacional do dashboard.
- **Do** identificar dados demonstrativos e separar registros, hipótese econômica e planejamento aritmético.
- **Do** manter nomes visíveis, foco e destinos reais nas ações e prévias.
- **Don't** tratar as relações editoriais do exemplo como IA operacional ou impacto econômico calculado pelo produto.
- **Don't** converter a ausência de captura em aprovação visual: o veredito independente desta entrega é **recapture**. As capturas full-page de 390, 768 e 1440 px permanecem pendentes; legibilidade renderizada, contraste e ausência de overflow não foram confirmados. Registro: `../../docs/landing-reconstrucao.md`.
