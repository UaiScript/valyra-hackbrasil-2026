# Como contribuir com o Valyra

Leia [AGENTS.md](AGENTS.md), [arquitetura](docs/architecture.md) e o [índice](docs/README.md). Preserve trabalho local, stashes, segredos e registros históricos.

## Ambiente reproduzível

Requer Python >=3.12, uv, GNU Make, Docker Desktop com motor Linux ativo e Compose; para a landing, Node >=22.12 e npm. Na raiz, copie .env.example para .env somente se não existir. Nunca sobrescreva um .env existente. Ajuste POSTGRES_PORT e as duas URLs conforme porta e credenciais locais; DATABASE_URL e TEST_DATABASE_URL devem ser bancos distintos.

```sh
make sync
# Inspecione a configuração antes de iniciar; não remova volumes.
docker compose config --quiet
docker compose up -d --wait postgres
make migrate
make seed
make test
make lint
make openapi
python infra/check_docs.py
```

Make usa .env existente, ou .env.example se ausente. Passa esse arquivo ao processo uv, inclusive TEST_DATABASE_URL; ler somente o .env no teste não basta. Substituições: make UV=/caminho/uv ENV_FILE=/caminho/ambiente test. Windows: GNU Make precisa estar disponível; informe o caminho do make.exe e de UV quando não estiverem no PATH. Não é necessário WSL para Python/Make; Docker Desktop requer o motor Linux funcionando. No Windows, prefira 127.0.0.1 nas URLs se localhost tentar IPv6 antes do bind IPv4. Em worktrees com banco próprio, defina COMPOSE_PROJECT_NAME no arquivo de ambiente e uma porta livre para não reutilizar o projeto Docker de outro checkout.

make dev sobe somente postgres e inicia uvicorn em reload. make test-domain executa a suíte pura sem precisar de PostgreSQL, mesmo que TEST_DATABASE_URL esteja ausente. A suíte completa exige banco dedicado; sem TEST_DATABASE_URL, testes de banco são explicitamente ignorados, não validados. Não use SQLite para substituir a validação PostgreSQL.

Para trabalhar por grupo, `make test-unit` executa todos os testes sem PostgreSQL
(`pytest -m "not postgres"`) e `make test-integration` só os que usam banco
(`pytest -m postgres`). A coleta marca automaticamente os testes que dependem de
`test_destination`, inclusive por fixtures como `client` e `db_session`; a marcação
explícita `@pytest.mark.postgres` também é respeitada. Novas fixtures de banco devem
usar essa mesma barreira de segurança. O CI roda esses grupos separados, sem repetir
os testes de domínio e IA na etapa de integração. `make test` continua disponível
para rodar tudo; `test-domain` e `test-ai` são recortes locais.

A suíte prioriza jornadas HTTP/persistência. Mantenha unitários para regras que
essas jornadas não exercitam, como limites e arredondamento financeiro, recuperação
de CSV malformado, corte temporal, evidências adulteradas e falhas/custos do LLM.
Getters, detalhes privados e validações do framework já exercitadas pela API não
precisam de uma segunda bateria unitária. Ao reduzir testes, preserve os cenários
de integração e explicite quais regras de borda continuam verificadas; menos casos
significa menos cenários exercitados, não uma garantia de cobertura equivalente.

O init roda em volume novo. Em volume existente, preserve os dados e execute apenas o [script idempotente](infra/postgres/init/01-create-test-db.sql) via psql conforme [registro](docs/revisao-modelagem.md); respeite POSTGRES_DB e não apague volumes. Fixtures criam schemas aleatórios no banco de testes validado; nunca limpam desenvolvimento.

## Landing

```sh
npm --prefix apps/web ci --ignore-scripts
npm --prefix apps/web run dev
npm --prefix apps/web run check
npm --prefix apps/web test
npm --prefix apps/web run build
```

Para navegador, na pasta apps/web: npx --no-install playwright install chromium e npm run test:e2e. No Windows com Chrome instalado, defina PLAYWRIGHT_CHANNEL=chrome no processo. Veja [README de apps/web](apps/web/README.md). Após mudar o contrato da API, rode make openapi e npm --prefix apps/web run gen:api; o check falha se os tipos do front estiverem desatualizados.

## Fluxo e revisão

Branch tipo/escopo-descricao, Conventional Commits com escopos api/web/pipelines/contracts/infra/docs/experiments. Use Closes #N quando concluir ou Refs #N enquanto houver pendências. Solicitação explícita prevalece; não altere status de Issues/PRs ou configurações externas sem autorização. Identifique assistência por ferramentas e dê crédito ao trabalho reaproveitado.

Atualize AGENTS quando mudar convenções. Se mexeu no contrato, avise o time. Gere OpenAPI por make openapi; nunca edite o JSON manualmente. Migração nova precisa revisão; não edite migração já mergeada. Teste lógica e erros relevantes, com dados sintéticos/públicos e centavos inteiros.

PR informa problema/resultado, validações reais e pendências; UI alterada pede screenshot. Uma aprovação humana e checks aplicáveis precedem merge por squash. Claude é apoio de review, não substitui aprovação humana. Configuração e restrições externas: [guia GitHub](docs/github-setup.md).
