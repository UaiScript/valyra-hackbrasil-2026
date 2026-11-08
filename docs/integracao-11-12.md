# Integração das Issues #11/#12

Branch integ/issues-11-12, criada de origin/main 1ff2ea6 em worktree isolado. Incorporados por merge os PRs #17 (13fd842), #18 (097f25b) e #19 (e31ddba), todos ainda abertos na consulta inicial. Nenhuma branch publicada foi reescrita; PRs anteriores, .env local, .vscode e dois stashes são preservados.

## Acréscimos próprios

- #11: contexto raiz/API, ponteiros CLAUDE, arquitetura, glossário, ADRs, índice e contribuição. Reaproveitados os arquivos de Breno na branch breno/evolucao-arquitetura, commit 0965a0c, com atualização do estado integrado e crédito de autoria.
- Fundação necessária das #8/#9: Makefile, dependências oficiais FastAPI/uvicorn/httpx, core HTTP mínimo, /health, erros, demo, paginação, operationIds e exportador. O histórico remoto não continha essa implementação apesar das issues fechadas; não foi encontrado código equivalente em outra branch. Sem endpoints #14/#15.
- #12: um job API consolidado, mantendo postgres e landing; regras oficiais de imports, testes e contrato gerado; templates e review Claude com controles de elegibilidade.

## Decisões e pendências

ADRs 0001/0008/0009 são aceitas no escopo explícito da #11. Outras propostas dos specs não foram aprovadas por consequência. Permanecem abertas decisões de precisão JavaScript/Alpha/IA, significado do saldo em projeções e persistência de tentativas failed fora do rollback.

[Guia GitHub](github-setup.md) registra ausência de proteção/rulesets e visibilidade limitada dos secrets organizacionais. Token Claude, primeiro review real e configuração externa não são substituídos por YAML válido. Não alteramos essas configurações nem encerramos issues.

## Revisar sem duplicar entregas

O PR de integração contém as entregas anteriores por ancestralidade, não por cópias refeitas. Compare os commits próprios após os três merges para revisar apenas o incremento #11/#12. Recomenda-se revisar #17/#18/#19 como blocos de origem, depois o delta próprio desta integração. Para incorporação definitiva, escolher uma única rota: integrar os anteriores preservando seus commits e atualizar/revisar esta integração, ou usar o PR agregado e reconciliar manualmente os anteriores. Não fazer squash dos anteriores e depois merge cego deste agregado: os SHAs originais deixariam de ser ancestrais e o diff poderia repetir conteúdo.

Os PRs #17/#18/#19 não são fechados, substituídos ou marcados ready automaticamente. A ordem funcional é banco #17, landing #18 independente e domínio #19; contexto/CI integrado fecha a lacuna de validação do #19 quando a equipe aprovar a integração. Nenhum merge em main é feito nesta etapa.

## Validação desta integração

Resultados locais em 08/11/2026, com Python 3.13.15, uv 0.13.7, GNU Make 4.4.1, PostgreSQL 18 e Node 24.19.0:

- make lint: Ruff e formatação (31 arquivos) e dois contratos import-linter aprovados.
- make test-domain: 168 testes com URLs inacessíveis na porta 1, sem conexão PostgreSQL.
- make test: 257 aprovados (77 persistência + 168 domínio + 12 core), zero ignorados. Um aviso de depreciação Starlette TestClient/httpx foi mantido visível; não foi desativado.
- make migrate, Alembic check online e exatamente uma cabeça aprovados. Seed duas vezes preservou integralmente as linhas na segunda execução; comparação antes/depois da suíte confirmou desenvolvimento inalterado.
- make openapi gerou somente /health e duas execuções produziram bytes idênticos; JSON não editado à mão. O CI compara esse contrato versionado.
- Landing: npm ci pelo lockfile sem scripts, TypeScript/build, 10 testes de configuração e 18 testes Chromium/Chrome em desktop e duas larguras móveis aprovados; auditoria sem vulnerabilidades conhecidas.
- Actionlint 1.7.12 sem erros; checagem de contexto/CLAUDE/links locais e git diff --check aprovados. O checker de documentação é infra/check_docs.py.

Resultados remotos e comentário Claude devem ser consultados nos checks do PR de integração; validação local não substitui esses checks. Arquivos locais de ferramentas não integram o commit. As tentativas locais de diagnóstico de conexão localhost e codificação de logs não foram contabilizadas como testes aprovados; configuração isolada passou a usar IPv4 explícito.

Banco local separado: projeto Docker valyra-integ1112, loopback 55432, volume novo próprio. O banco original de desenvolvimento e seus volumes não são usados para limpeza. Não remover volumes existentes.
