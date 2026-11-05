# Valyra

Aplicação web de demonstração financeira para pessoas e empresas. React, TypeScript e Vite; Python apoia validação de dados e prévia estática. Não há API, autenticação, banco de dados ou IA operacional.

- Comece por [docs/README.md](docs/README.md) e siga apenas o caminho da tarefa; não é necessário ler toda a documentação.
- Confira branch e `git status` antes de editar. Preserve mudanças locais, arquivos dos colegas e instruções aplicáveis. Trabalhe fora da principal e não faça merge ou push sem solicitação.
- Instalação: `npm ci`. Desenvolvimento: `npm run dev`. Verificação: `npm run check` e `npm run format:check`. Os comandos completos e os limites do ambiente estão em [docs/desenvolvimento.md](docs/desenvolvimento.md).
- Mantenha as funcionalidades em `apps/web/src/features/`. Rotas e destinos ficam em `apps/web/src/app/routes.ts`; contratos em `shared/types/domain.ts`; dados em `data/demo/` e leitura em `data/demoRepository.ts`, sob `apps/web/src/`.
- Preserve regras, contratos, rotas e isolamento dos perfis. Dinheiro usa centavos inteiros; o Radar não modifica lançamentos. Consulte [regras-de-negocio.md](docs/regras-de-negocio.md) antes de alterar cálculos.
- Use Valyra em textos públicos; preserve os nomes técnicos `valyre` e `@valyre/web` e o nome do repositório.
- Comente em português o motivo das regras e decisões não evidentes. Evite comentários linha a linha, abstrações sem uso atual e dependências para operações simples.
- Não trate dados sintéticos, explicações editoriais ou propostas de integração como recursos reais. Não inclua segredos ou dados financeiros pessoais nos exemplos.
- Atualize a documentação diretamente afetada e execute checks proporcionais. Não altere registros históricos para fazê-los parecer verificações atuais.
- Diretórios de skills e configurações de ferramentas já instalados não são código da aplicação. Preserve-os; não crie instruções duplicadas para outros assistentes.
