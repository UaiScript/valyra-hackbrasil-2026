# Trabalhando na Valyra

1. Comece pelo [README](README.md); use [docs/README.md](docs/README.md) para selecionar o contexto da tarefa.
2. Confira branch e alterações locais. Trabalhe em branch de desenvolvimento, preserve mudanças dos colegas e não faça merge direto na principal.
3. Siga o [guia de desenvolvimento](docs/desenvolvimento.md) para instalar, executar e verificar. Antes da revisão, use `npm run check`, `npm run format:check` e `git diff --check`.
4. Descreva o comportamento alterado, o motivo e as verificações executadas. Atualize a documentação afetada; mudanças de negócio devem ser alinhadas com a equipe.

## Convenções

Textos públicos usam **Valyra**; nomes técnicos e do repositório permanecem. Código novo deve respeitar as regras de origem do hackathon, ainda pendentes de conferência pela equipe.

Use nomes que indiquem responsabilidade. Regras ficam em `apps/web/src/features/finance/calculations.ts`; contratos em `shared/types/domain.ts`; dados e acesso em `data/`, sob `apps/web/src/`. Rotas e destinos compartilhados ficam em `apps/web/src/app/routes.ts`. Evite abstrações sem consumidor atual, arquivos de reexportação e dependências para operações simples.

Comentários em português explicam o porquê e o contrato a preservar: sinal/centavos, perfis, datas, respostas tardias e limites das simulações. Não narre linha por linha. TODOs precisam descrever trabalho concreto que ainda não existe.

Testes devem proteger comportamento e regras, não nomes de pastas ou a forma dos componentes. Atualizações de dependências precisam incluir o lockfile e a justificativa. Não inclua segredos nem dados financeiros reais nos exemplos. Mudanças de layout exigem conferência em desktop e celular; limitações devem ser relatadas.

Agentes devem seguir [AGENTS.md](AGENTS.md). As cópias instaladas de skills/configurações de ferramentas não são material para reorganizar ou duplicar nesta contribuição.
