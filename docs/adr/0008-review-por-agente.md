# ADR-0008 — Review com Claude Code Action

## Contexto

A equipe definiu revisão por agente e uma aprovação humana no fluxo de PR. O review deve aplicar regras versionadas e preservar a cota disponível para o hackathon.

## Decisão

Usar Claude Code Action v1, fixada por SHA de commit, autenticada pelo secret `CLAUDE_CODE_OAUTH_TOKEN`, gerado por `claude setup-token`. O revisor lê o contexto raiz/por camada e o prompt versionado em [.github/review-prompt.md](../../.github/review-prompt.md).

Revisar PR aberto pronto para revisão, transição ready_for_review e menção `@claude` em comentário de PR por integrante autorizado. Não revisar automaticamente a cada push. O bot comenta problemas por gravidade; não implementa correções, aprova ou faz merge.

## Alternativas consideradas

- Revisão apenas humana: não satisfaz o fluxo combinado.
- Review em todo push: aumenta consumo e repetição de comentários.
- Outra integração/provedor: adiada para não introduzir mais ferramentas nesta etapa.

## Consequências

O administrador precisa cadastrar o secret e validar o primeiro comentário. Usar permissões limitadas, sem expor credenciais a forks ou comentários de pessoas sem acesso de escrita. Rever consumo, limitar turnos/tempo e revogar o token ao fim do hackathon. A conta titular deve autorizar o uso da assinatura; nunca versionar ou compartilhar o valor do token em texto.

Review do agente não substitui uma aprovação humana. O gatilho issue_comment requer o workflow na branch padrão. Pode ser necessário reduzir diff ou ajustar limite de turnos; ausência de comentário não significa ausência de problemas. Para substituir a integração, alterar esta ADR e revogar as credenciais antigas.

## Status

**Aceita no escopo explícito da Issue #11, solicitada nesta integração.** A aceitação desta decisão específica não significa aprovação de todas as propostas dos specs nem comprova configuração remota ou execução de revisão por agente. Texto reaproveitado da branch de Breno, commit 0965a0c; histórico anterior permanece no Git.
