# Como contribuir com o Valyra

Comece pelo [AGENTS.md](AGENTS.md) e use o [índice de contexto](docs/README.md) para ler apenas os documentos da sua tarefa. Preserve alterações locais, trabalho dos colegas e registros históricos.

## Issue, branch e commit

Use uma Issue com camada, prioridade, descrição e critérios de aceite; converta drafts do Project antes de começar. Assuma o card, confira dependências e mova para In Progress.

Trabalhe em branch curta `tipo/escopo-descricao`, fora da `main`, salvo instrução explícita para usar a branch atual. Exemplo: `ci/infra-pipeline-e-templates`. Não faça merge ou push sem autorização.

Commits seguem `tipo(escopo): descrição`, com tipos `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `ci`, `perf`; escopos `api`, `web`, `pipelines`, `contracts`, `infra`, `docs`, `experiments`. Exemplo: `ci(infra): adiciona revisão de PR com Claude`. Registre coautoria da ferramenta quando o commit for produzido por agente.

## Ambiente e comandos

Pré-requisitos atuais: Git, Docker e Docker Compose. Na raiz:

```bash
cp -n .env.example .env
docker compose config --quiet
docker compose up -d --wait --wait-timeout 60 postgres
```

O `cp -n` preserva configuração existente. No Windows, copie pelo editor se necessário. Valores do modelo são exclusivos de desenvolvimento. O Compose atual sobe apenas PostgreSQL; um volume existente não é reinicializado ao mudar `.env`. `docker compose down` preserva dados; `down --volumes` apaga o volume e exige revisão do destino antes de uso.

| Parte | Comandos previstos | Disponibilidade |
| --- | --- | --- |
| Backend | `make dev`, `make lint`, `make test`, `make migrate`, `make seed`, `make openapi` | Dependem da fundação/API/migrations das Issues #8–#10; ainda ausentes |
| Frontend | `npm ci`, `npm run dev`, `npm run check`, `npm run format:check` | Da base web em outra branch, ainda não integrada |

Não acrescente um Makefile ou scaffold concorrente para satisfazer essas referências. Integre as entregas responsáveis e atualize esta tabela. Preserve `valyre`/`@valyre/web` como nomes técnicos ao incorporar a base do frontend; textos públicos usam Valyra.

## Validação e PR

Execute verificações proporcionais e informe comandos/resultados reais. Para o banco: validar Compose, iniciar e consultar; `healthy` não comprova migrations. A CI e suas dependências estão descritas no [guia GitHub](docs/github-setup.md).

Abra PR com objetivo, Issue relacionada (`Closes #N` quando concluir), mudanças, validação e pendências. Inclua screenshot se houver UI. Preserve testes existentes e teste lógica nova com cenários relevantes, sem testes que apenas reproduzam a implementação.

Se mexeu no contrato, avise o time. Quando o exportador existir, execute `make openapi` e revise o contrato gerado; não edite os arquivos gerados manualmente. Mudança de schema traz migração nova revisada à mão; nunca altere uma migração integrada na `main`.

Atualize documentação e `AGENTS.md` da área no mesmo PR se uma convenção mudar. Comentários em português devem explicar decisões e regras não evidentes, sem narrar cada linha. Mudanças arquiteturais precisam de ADR aceita ou alinhamento explícito com a equipe.

Mova para In Review quando estiver pronto. O merge por squash exige checks aplicáveis, revisão por agente e uma aprovação humana de outro integrante; o bot não substitui o humano. Proteção de branch e labels não são configuradas pelo simples cadastro destes arquivos.

## Dados e segurança

Somente dados sintéticos/públicos permitidos. Dinheiro Finance usa centavos inteiros; não converter via float. Não versione `.env`, tokens, dados pessoais ou dumps privados. Preserve datas de publicação/revisões e não anuncie simulação ou proposta como integração real. O Radar não altera transações por inferência econômica.
