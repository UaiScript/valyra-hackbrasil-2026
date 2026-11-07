# GitHub — CI, templates e review por agente

Esta entrega adiciona os arquivos das tarefas de contexto e CI/review na branch de trabalho solicitada pelo usuário. Arquivos no Git não configuram automaticamente secrets, proteções de branch, labels ou o Project. Nenhum desses ajustes remotos foi realizado pelo agente.

## 1. O que cada workflow faz

### CI

O arquivo [ci.yml](../.github/workflows/ci.yml) mantém push em qualquer branch e acrescenta pull_request para `main`. Um push com PR aberto pode gerar duas execuções, uma por evento; isso é esperado nesta configuração explícita, sem filtros por caminho que ocultem checks obrigatórios.

- Job `postgres`, nome **PostgreSQL / Compose**: valida YAML/variáveis pelo Compose, sobe PostgreSQL e executa uma consulta autenticada. Continua independente da API.
- Job `api`, nome **API**: verifica os pré-requisitos, instala uv/Python e dependências congeladas pelo lockfile, executa lint, sobe PostgreSQL, verifica `valyra_test`, aplica migrations, confere schema/ORM, exige cabeça Alembic única, executa testes e compara contratos gerados com o Git.

`actions/checkout` e `astral-sh/setup-uv` estão fixadas por SHA de commit. A tag comentada facilita identificar a versão; não substitua o SHA por uma tag mutável. O ambiente usa dados e credenciais descartáveis próprios do runner.

**Dependência real:** neste checkout ainda faltam Makefile, implementação/pyproject/lockfile da API, Alembic, contrato gerado e script Compose que inicializa o banco de testes. São interfaces das Issues #8–#10. O job `api` falha explicitamente na conferência inicial, em vez de pular verificações e aparentar sucesso. Integrar essas entregas antes de exigir o check como proteção da `main` ou anunciar o aceite completo da tarefa.

O arquivo de lock esperado é `services/api/uv.lock`; Alembic usa `services/api/alembic.ini`; contrato gerado esperado em `packages/contracts/openapi.json`. `make` roda na raiz. O desenho de conexão da API neste job pressupõe SQLAlchemy síncrono com psycopg e URLs para bancos `valyra`/`valyra_test` distintos no PostgreSQL do runner; alinhar com a implementação da fundação antes do aceite. Não criar manualmente um contrato JSON ou banco fora do init para esconder dependências ausentes.

Além de `git diff --exit-code packages/contracts/`, o job detecta novos arquivos não versionados no diretório: só comparar diff de arquivos rastreados não detectaria uma nova saída esquecida do exportador.

Não há job web porque não existem manifestos/comandos npm neste checkout. Adicioná-lo quando a base estiver integrada, usando `npm ci`, `npm run check` e `npm run format:check` reais.

### Claude Review

O arquivo [claude-review.yml](../.github/workflows/claude-review.yml) usa Claude Code Action v1 fixada no commit resolvido da tag. Inputs `claude_code_oauth_token`, `github_token`, `prompt`, `claude_args` e `include_fix_links` foram conferidos no action.yml da revisão fixada.

Gatilhos:

- PR aberto pronto para revisão e evento `ready_for_review`.
- Comentário novo em PR contendo `@claude`, por integrante autorizado.
- Não dispara automaticamente em `synchronize`/cada push; PR draft, fechado ou vindo de fork não recebe revisão autenticada.

O filtro inicial exige associação OWNER/MEMBER/COLLABORATOR. A action também verifica permissão de escrita do solicitante. No caminho de comentário, uma consulta de metadados confirma que o PR é interno, aberto e não draft antes de fornecer o OAuth token à action. Não há `pull_request_target` nem liberação de usuários/bots arbitrários.

O bot lê [review-prompt.md](../.github/review-prompt.md), `AGENTS.md` e instruções de camada, analisa o diff e publica problemas por gravidade. A integração usa o `github.token` do job para ler/comentar, com permissões explícitas e sem permissão de escrita no conteúdo do repositório. O OAuth autentica o Claude; não é um token GitHub. Ao fornecer `github_token`, usamos o caminho de token explícito suportado pela action, sem depender da troca OIDC por token do GitHub App. Ferramentas do revisor ficam limitadas a leitura/busca e comandos de consulta/comentário de PR. Não há autorização para executar código do PR, implementar correções, aprovar ou fazer merge.

## 2. Configuração manual do administrador

1. Confirmar que Actions permite as actions oficiais usadas e o SHA de `anthropics/claude-code-action`, respeitando eventual política da organização.
2. Com autorização do titular da assinatura, gerar `claude setup-token` localmente e cadastrar **somente** no secret `CLAUDE_CODE_OAUTH_TOKEN` em Settings → Secrets and variables → Actions. Não colar o token em Issue, PR, arquivo ou log. Revogar ao final do hackathon e acompanhar cota/uso.
3. Configurar labels `api`, `web`, `pipelines`, `infra`, `docs`, `P0`, `P1`. Os dropdowns dos forms registram camada/prioridade no corpo; eles não aplicam labels dinamicamente. Atribuí-las no cadastro/triagem.
4. Após ambos os jobs realmente passarem, configurar ruleset/proteção para `main`: PR obrigatório, checks **PostgreSQL / Compose** e **API**, uma aprovação humana. Os IDs dos jobs são `postgres` e `api`; confirmar os nomes exibidos na primeira execução antes de selecionar checks obrigatórios.
5. Habilitar squash merge e adotar esse método para a equipe. Review do Claude não substitui aprovação humana e não deve bloquear PR só por cota/ausência de secret sem decisão do time.
6. No Project, configurar auto-add de Issues/PRs do repositório; item adicionado → Todo; Issue fechada → Done; PR integrado → Done; auto-archive de itens concluídos. Confirmar que as opções/colunas existem e testar com um item; automações não foram criadas por estes arquivos.

## 3. Verificar após publicar pelo fluxo autorizado

- Abrir PR e conferir ambos os gatilhos de CI na aba Checks/Actions. Esperado após integrar dependências: `postgres` e `api` verdes. Antes disso, `api` deve indicar os pré-requisitos ausentes.
- Com secret configurado, abrir PR interno não draft ou marcá-lo como ready_for_review; conferir **Review com Claude** e o comentário. Limite de tempo/turnos pode exigir reduzir o diff ou nova solicitação explícita.
- Para `@claude`, o workflow precisa primeiro existir na branch padrão: o GitHub executa issue_comment usando essa branch. Testar o comentário em um segundo PR após integrar o workflow, não exigir esse gatilho no primeiro PR que o cria.
- Forms também precisam estar na branch padrão para aparecerem em New issue. Testar tarefa com aceite obrigatório e bug com reprodução/esperado/obtido. Conferir o template de PR.
- Comentar em PR de fork ou com ator não autorizado não deve executar a action com secret. Não mudar para `pull_request_target` para contornar essa restrição.

## 4. Validação local e limites

Antes do PR, validar YAML/workflows com actionlint, links locais e comandos de infraestrutura contra ambiente descartável. Checar `AGENTS.md` raiz com menos de 150 linhas e os dois arquivos CLAUDE contendo somente `@AGENTS.md`.

Os comandos da CI são executados pelo runner, não por um commit local. Resultados de lint estático, SQL e shell locais não comprovam execução remota ou comentário do Claude. Não incluir tokens no ambiente de testes locais destes arquivos. A ausência das entregas da API impede executar `make lint/test/migrate/openapi` de verdade nesta branch; registrar essa limitação no PR.

Verificações desta implementação, em 07/11/2026:

- Actionlint sem erros nos dois workflows; inputs conferidos no action.yml dos commits fixados; sintaxe dos blocos Bash validada.
- Contexto raiz com 57 linhas, seis seções solicitadas; ponteiros CLAUDE, campos obrigatórios dos forms e links locais conferidos.
- Check PostgreSQL executado contra Docker real em projeto descartável: healthy e SELECT autenticado. Conferência de `valyra_test` falhou como esperado sem o banco e passou após criá-lo exclusivamente no ambiente de teste; essa criação não altera o Compose nem substitui a entrega da Issue #8.
- Pré-requisitos ausentes da API produziram erro explícito. Controle de cabeça única verificado com saídas simuladas de zero, uma e duas revisões; não é execução real do Alembic.
- Comparação Git do contrato verificada em repositório temporário: arquivo limpo passou, alteração rastreada e novo arquivo não versionado falharam. Exportador simulado; OpenAPI real ainda depende da API.
- Recursos de teste removidos; sem execução remota, comentário do Claude ou alteração de configuração do GitHub pelo agente.

## Referências primárias

- [GitHub: eventos de workflow](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows).
- [GitHub: sintaxe e permissões](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax).
- [Claude Code Action: inputs no commit utilizado](https://github.com/anthropics/claude-code-action/blob/61a9c274fa7110a66dfafc1bbbced03833eb25fe/action.yml).
- [Claude Code Action: exemplos de review](https://github.com/anthropics/claude-code-action/blob/61a9c274fa7110a66dfafc1bbbced03833eb25fe/docs/solutions.md).
- [setup-uv: configuração](https://github.com/astral-sh/setup-uv/tree/eb1897b8dc4b5d5bfe39a428a8f2304605e0983c).
