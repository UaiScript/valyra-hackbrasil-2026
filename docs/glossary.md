# Glossário

| Termo | Significado no Valyra |
| --- | --- |
| Sinal | Registro econômico com fonte, observação, publicação e evidências; não é recomendação de investimento. |
| Revisão | Nova versão publicada de um sinal lógico. No desenho, gera outra linha em vez de sobrescrever o passado. |
| `signal_key` | Identidade lógica que agrupa as revisões de um sinal; não é o identificador da fonte (`source_id`). |
| `as_of` | Corte temporal: só pode usar informação publicada e na versão disponível até esse instante. |
| `observation_date` | Data a que o fenômeno observado se refere. Pode anteceder a publicação. |
| `published_at` | Instante em que a fonte tornou a informação pública; publicação estimada deve ser identificada. |
| `ingested_at` | Instante em que o Valyra coletou o registro; não substitui a data de publicação. |
| Lote de importação | Uma tentativa de importar CSV para uma conta, com estado e contadores; reenvio é outro lote. |
| Rejeição | Registro inválido do CSV com linha, motivo e texto de origem; não impede necessariamente importar as outras linhas. |
| `row_hash` | SHA-256 de conta, data, centavos, descrição normalizada e ocorrência no arquivo, para deduplicação. Não garante conciliação universal de CSVs sobrepostos. |
| Categoria prevista | Sugestão original da classificação, preservada quando o usuário corrige a categoria exibida. |
| Centavos / `*_cents` | Inteiros de BRL: `12990` representa R$ 129,90; negativo indica saída em uma transação. |
| P0 | Prioridade essencial à jornada principal ou entrega do MVP. |
| P1 | Extensão que não deve bloquear a entrega das prioridades essenciais. |

As regras completas ficam na [modelagem](modelagem-db.md) e no [contrato Finance](api-design.md).
