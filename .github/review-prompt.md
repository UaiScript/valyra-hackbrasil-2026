# Review do Valyra

Faça uma revisão objetiva do diff do PR e da base de destino. Leia `AGENTS.md` e os arquivos de camada existentes, especialmente `services/api/AGENTS.md`. Consulte os documentos indicados ali somente quando pertinentes. Não execute código, migrations ou scripts do PR; analise as alterações e verificações informadas. A publicação do comentário é a única escrita autorizada.

## Checklist

1. **Regras invioláveis:** sem vazamento temporal (`published_at`, `as_of`, revisão conhecida), números inventados pelo LLM, dados pessoais/segredos ou edição manual de arquivos gerados. Dinheiro Finance em centavos inteiros, sem float. Preserve pendências da modelagem, não as transforme em regras aceitas.
2. **Dependências:** router → service → domain/repository; domínio sem banco/HTTP/LLM; core sem importar domínios; entre módulos, usar service público. No frontend integrado, respeitar convenções de features e acesso aos dados existentes.
3. **Testes:** lógica nova precisa de teste relevante de comportamento e erro/limite pertinente. Documentação pura não exige teste de aplicação. Identifique verificações ausentes sem inventar que os testes falharam ou passaram.
4. **Contexto e contratos:** mudança de convenção atualiza o AGENTS correspondente; mudança de API regenera `packages/contracts/openapi.json` quando o exportador existir e avisa o time. Confirme schemas/operationIds e unidade dos valores. Arquivo gerado ainda ausente não autoriza criar JSON manual.
5. **Migrations:** nova alteração de schema traz migração revisada à mão; não editar migração já presente na base do PR. Conferir tipos, defaults, constraints, FKs, índices, integridade e segurança do downgrade. Cabeça única e model/schema coerentes. Não declarar CI de Alembic aprovada sem resultado.
6. **Testes e dados:** banco de testes distinto e explícito, sem fallback de limpeza para aplicação; seed idempotente e sem reset. Limites CSV e rejeições seguem o contrato registrado.
7. **Escopo:** diferencie implementado, planejado e hipótese. Não exija módulos futuros ou toda a visão do produto num incremento Finance. Considere a ausência real de dependências das Issues #8–#10; um job ignorado não prova cobertura.

## Formato da resposta

Publique um comentário em português, sem elogios genéricos ou resumo promocional. Para cada achado, informe **gravidade, arquivo/linha, cenário que dispara o problema, impacto e correção sugerida**. Priorize defeitos concretos no diff:

- **Crítica:** perda/exposição de dados ou violação grave comprovável.
- **Alta:** comportamento essencial incorreto ou bloqueio da entrega.
- **Média:** erro relevante em cenário limitado ou lacuna de validação.
- **Baixa:** manutenção com consequência concreta; evite preferências cosméticas.

Separe dúvidas de alinhamento e verificações não executadas dos defeitos confirmados. Não repita problemas históricos sem relação com o diff. Se não houver achados, escreva “Nenhum problema identificado nesta revisão” e declare o limite da análise estática. Review não é aprovação humana, não comprova ausência de falhas e não autoriza merge.
