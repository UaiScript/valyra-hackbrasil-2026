# GitHub — CI e revisão

## Workflows integrados

- [CI](../.github/workflows/ci.yml): push em branches e pull_request para main, sem filtro de caminhos que impeça checks obrigatórios. Pode gerar duas execuções para um push com PR aberto.
- Job postgres, nome real **PostgreSQL / Compose**: preserva configuração Compose e consulta autenticada em PostgreSQL 18.
- Job api, nome real **API**: substitui api-persistence; não duplica o pipeline do PR #17. Instala Python 3.12/uv 0.13.7 e dependências com uv.lock, executa make lint, 168 testes puros com destinos inacessíveis antes de iniciar o PostgreSQL, sobe somente postgres, verifica banco dedicado, executa make migrate/Alembic check, exige exatamente uma cabeça, roda a suíte completa e gera/compara OpenAPI. Detecta também saída não rastreada do exportador e confere links/contexto.
- [Landing](../.github/workflows/landing.yml): workflow independente preservado, check **Landing / build e navegador**, instalação npm ci pelo lockfile, auditoria, TypeScript/build e testes reais em desktop/celulares.

Os alvos Make e core HTTP mínimos ausentes das #8/#9 foram implementados nesta integração, dentro dos contratos existentes; nenhum endpoint Finance #14/#15 foi acrescentado. A API agora tem configuração oficial para validar a #13 sem arquivos temporários. Todos os bancos do CI pertencem ao runner efêmero; .env.example é apenas configuração demo, sem segredos de produção.

Actions estão fixadas por SHA. Novas revisões resolvidas em 08/11/2026: setup-uv v7 em 94527f2e458b27549849d47d273a16bec83a01e9 e Claude Code Action v1 em 074f3963a45f3e002e58c97dd0ddf472e0146bf5. Inputs version, python-version, enable-cache, claude_code_oauth_token, github_token, prompt, claude_args e include_fix_links foram conferidos no action.yml oficial fixado.

## Revisão Claude: limites e estado real

[Workflow](../.github/workflows/claude-review.yml) e [prompt](../.github/review-prompt.md) reaproveitam a intenção da branch de Breno (0965a0c), com controles atualizados. Disparam em PR opened/ready_for_review e issue_comment contendo @claude; não em todo synchronize. Comentários só disparam quando o workflow já existir na branch padrão.

O preflight exige permissão efetiva admin/maintain/write do solicitante e confirma PR interno, aberto e não draft, além da presença do contexto de revisão na base confiável. Apenas então verifica a presença do secret, sem revelar seu valor. Forks e usuários sem escrita não recebem execução privilegiada. Sem token, o resumo registra configuração pendente e o job **Review com Claude** fica ignorado; isso não é aprovação de review.

O job de revisão usa somente contexto da base confiável, nunca checkout/executa código do head com segredos. Não há pull_request_target, allowed_non_write_users=* ou contents:write. Ferramentas limitadas a leitura/busca e gh pr view/diff/comment; nenhum commit, aprovação ou merge é autorizado. O OAuth autentica Claude, enquanto github_token limitado permite leitura/comentário no PR, sem escrita no conteúdo. Essa restrição não transforma conteúdo de PR em instrução confiável: prompt e checklist explicitam a fronteira.

**Pendência:** na consulta de 08/11/2026 não havia secrets de repositório listados. A API de secrets da organização respondeu 403 por falta de admin:org; não se presume acesso aos seus valores/nem ausência de secrets herdados. A execução do preflight confirma a disponibilidade efetiva. A primeira revisão autenticada/comentário ainda precisa de validação e não deve ser anunciada como concluída sem evidência.

Se o secret existir mas o contexto confiável ainda não estiver em main, integrar primeiro o workflow/contexto autorizado e validar em novo PR interno pronto para revisão. Não fornecer tokens ao código deste PR para contornar essa dependência.

## Configuração externa — somente recomendação

Nada nesta entrega modifica proteção, secrets, labels, Project ou opções de merge.

Inspeção em 08/11/2026: main sem proteção (API retornou Branch not protected), nenhum ruleset, Actions habilitado com allowed_actions=all/sha_pinning_required=false; squash habilitado. O token atual tem administração do repositório, mas isso não autoriza mudar essas opções nesta etapa.

Recomendação concreta, após os checks reais passarem:

1. Proteção/ruleset main exige PR, uma aprovação humana, conversas resolvidas, rejeição de force push e exclusão. Exigir checks **PostgreSQL / Compose**, **API** e **Landing / build e navegador**, selecionando os nomes reais exibidos no GitHub. Landing precisa sempre produzir o check se for obrigatório para todos os PRs; seu filtro atual por caminhos pode deixá-lo pendente em PRs sem landing. Antes de torná-lo obrigatório globalmente, decidir entre remover o filtro e executar sempre ou adotar regra condicional apropriada. PostgreSQL/API não têm esse problema.
2. Checks desatualizados/ausentes ou aprovação faltante bloquearão merges; decidir se requer branch atualizada antes do merge. Não exigir Review com Claude enquanto credencial/cota/primeiro comentário estiverem pendentes.
3. Usar squash conforme fluxo do time. Neste PR agregado, não fazer squash automático sobre os anteriores: revisar a estratégia de integração descrita no registro.
4. Titular autorizado gera claude setup-token e administrador cadastra CLAUDE_CODE_OAUTH_TOKEN em Actions. Nunca colar valor em PR/Issue/log. Monitorar cota, limitar turnos/tempo e revogar ao fim do hackathon. Review não substitui aprovação humana.
5. As labels api, web, pipelines, infra, docs, P0 e P1 já existem na consulta atual; nenhuma foi criada nesta entrega. Dropdown dos forms não aplica labels dinamicamente; manter a atribuição na triagem. Project: auto-add, item added → Todo, issue closed/PR merged → Done, auto-archive; conferir opções antes de habilitar. Nenhuma automação foi alterada. A inspeção dos Projects foi bloqueada pela ausência de read:project no token; não foi solicitado escopo adicional.

## Fontes primárias e histórico

- [Claude inputs fixados](https://github.com/anthropics/claude-code-action/blob/074f3963a45f3e002e58c97dd0ddf472e0146bf5/action.yml).
- [Claude segurança](https://github.com/anthropics/claude-code-action/blob/074f3963a45f3e002e58c97dd0ddf472e0146bf5/docs/security.md).
- [setup-uv fixado](https://github.com/astral-sh/setup-uv/tree/94527f2e458b27549849d47d273a16bec83a01e9).
- [Eventos GitHub](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows).
- [Trabalho anterior de contexto/CI de Breno](https://github.com/UaiScript/valyra-hackbrasil-2026/tree/0965a0cd628682074c3d3954f9f37cc4ee7596d3). Resultados registrados ali são históricos, não verificações desta integração.
