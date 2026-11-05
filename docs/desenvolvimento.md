# Desenvolvimento

Execute os comandos na raiz do repositório. A stack, os scripts e as dependências estão em [package.json](../package.json) e [apps/web/package.json](../apps/web/package.json); versões resolvidas ficam no [lockfile](../package-lock.json).

## Requisitos e início

- Node.js `>=22.12.0` e npm `>=10`, declarados em `engines` na raiz.
- Ambiente usado nesta revisão: Node.js 24.19.0, npm 11.17.0 e Python 3.13.15.
- Python é necessário para `check:data`, `check` e a prévia Python. Os scripts usam somente a biblioteca padrão; não há `pip install`, ambiente virtual ou versão mínima Python declarada em configuração. A versão acima é a efetivamente verificada.
- Não são necessárias variáveis de ambiente, chaves ou arquivo `.env` na versão atual. Não introduza segredos nas fixtures.

```sh
npm ci
npm run dev
```

O Vite usa `http://127.0.0.1:5173` por padrão e informa outra porta se ela estiver ocupada. Use o endereço exibido no terminal. Landing: `/#/`; demonstração: `/#/demo/overview`; entrada em Empresa: `/#/demo/overview?profile=business`. Encerre seu servidor com `Ctrl+C`.

## Comandos disponíveis

| Objetivo            | Comando                                   | O que verifica/faz                                           |
| ------------------- | ----------------------------------------- | ------------------------------------------------------------ |
| Tipos               | `npm run typecheck`                       | TypeScript estrito, sem emitir arquivos                      |
| Testes              | `npm test`                                | Vitest: regras, repositório, rotas e interações em Happy DOM |
| Dados               | `npm run check:data`                      | Contratos das fixtures com Python                            |
| Build               | `npm run build`                           | Tipos + build em `apps/web/dist/`                            |
| Check principal     | `npm run check`                           | Tipos → testes → dados → build                               |
| Conferir formatação | `npm run format:check`                    | Prettier; não altera arquivos                                |
| Aplicar formatação  | `npm run format`                          | Prettier no escopo permitido pelo `.prettierignore`          |
| Prévia do build     | `npm run preview`                         | Vite, porta padrão 4173                                      |
| Prévia alternativa  | `python scripts/serve_web.py --port 4173` | Servidor estático local, após build; não é API               |

**Lint:** não existe script ou configuração de lint no projeto. Prettier verifica formatação, não substitui um linter. Não use `npm run lint` como check existente.

As duas prévias de build usam a mesma porta padrão: rode uma por vez e observe a porta informada. O servidor Python aceita `--port`; o Vite pode selecionar outra porta ocupada. O resultado é estático e usa rotas por hash, sem exigir fallback de servidor. HTTPS e hospedagem são pendências; não há URL pública confirmada.

Para executar um grupo relevante de testes:

```sh
npm run test --workspace @valyre/web -- src/app
npm run test --workspace @valyre/web -- src/features/finance
```

## Como fazer uma mudança

**Tela/navegação:** localize a funcionalidade em `apps/web/src/features/`. Para uma tela nova, atualize `ScreenId` em `shared/types/domain.ts`, o catálogo em `app/routes.ts` e a composição do `Workspace.tsx`. Use `demoHref` nos links para levar o perfil. Preserve seleção de tela, foco, estado vazio/erro e limpeza de filtros ao trocar de contexto. A lista atual de rotas está na [arquitetura](arquitetura-inicial.md).

**Dados:** altere somente os exemplos necessários em `src/data/demo/personal.json` ou `business.json`. Preserve IDs próprios do perfil, centavos inteiros e datas coerentes com a referência de novembro de 2026. Execute `npm run check:data` e os testes afetados. Atualizar o período exige revisar também rótulos fixos nas telas e `REFERENCE_DATE` em `scripts/check_demo_data.py`; não basta trocar uma data na fixture.

**Regras:** leia [regras-de-negocio.md](regras-de-negocio.md) e altere `features/finance/calculations.ts` com testes de comportamento. Geometria do gráfico fica no Planejamento; apresentação não deve introduzir outra regra de saldo.

**Estilos/componentes:** tokens em `src/shared/styles/tokens.css`; estilos gerais, landing e workspace em arquivos próprios da mesma pasta. Marca/ícones e componentes comuns ficam em `src/shared/components/`. Consulte [DESIGN.md](../apps/web/DESIGN.md); uma mudança na landing não deve atingir o dashboard por seletores globais. Faça inspeção visual quando alterar layout.

**API futura:** o ponto atual é `data/demoRepository.ts`, com contrato `DemoRepository` em `shared/types/domain.ts`. Hoje ele lê JSON local e retorna cópias. Antes de adicionar HTTP, defina e valide o contrato no adaptador; não espalhe `fetch` pelas telas nem declare uma API conectada antes de existir.

## Verificar e revisar

Use `npm run check` e `npm run format:check`; confira também `git diff --check` e `git status --short`. Teste as duas opções de perfil nos fluxos afetados. Ao mudar estrutura/rotas, confira imports e links com a capitalização exata dos arquivos para Linux. Atualize apenas os documentos relacionados à tarefa.

Happy DOM verifica comportamento React; não mede layout, contraste renderizado, responsividade ou erros do console de um navegador real. A pendência visual existente está em [estado-atual.md](estado-atual.md). Mudanças sem UI podem ser verificadas por testes, diffs e integridade dos estilos; não precisam inaugurar uma revisão de design.

## Problemas de ambiente conhecidos

- **Porta ocupada:** use a porta indicada pelo Vite ou escolha outra; não encerre o servidor de um colega.
- **`esbuild` com “Acesso negado” ao ler diretórios ancestrais:** ocorreu no sandbox Windows desta revisão. Repita no terminal autorizado do projeto ou solicite ao ambiente a permissão de execução necessária; não relaxe configurações de segurança da máquina nem altere código para esconder a falha.
- **Instalação sem acesso ao registro:** `npm ci --offline` só funciona com o cache completo. O fluxo normal para uma pessoa nova é `npm ci` com acesso ao registro npm.
- **Ferramenta de navegador sem acesso à URL/captura:** registre a limitação e não trate testes DOM ou HTTP 200 como inspeção visual concluída.

Convenções de revisão e comentários: [CONTRIBUTING.md](../CONTRIBUTING.md).
