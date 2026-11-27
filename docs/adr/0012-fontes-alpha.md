# ADR-0012 — Fontes públicas e ingestão do Alternative Alpha

## Contexto

O Alternative Alpha promete na landing monitorar indicadores, mostrar eventos com
origem e data e gerar sinais com premissas explícitas. Hoje ele existe só como
vitrine sintética: não há módulo `alpha` no backend nem fonte externa. A
[modelagem](../modelagem-db.md) já desenha `sources` e `signals` (somente inserção,
revisões como linhas novas, `published_at`, `published_at_estimated` e corte
`as_of`), e a [ADR-0011](0011-contrato-evidencias-ia.md) aceita evidências
`alpha_signal` que a IA recusa quando publicadas depois do corte.

Restrições do hackathon: dados públicos com uso permitido, custo zero e
hospedagem gratuita (API no Render Free, que dorme sem tráfego; banco no Neon Free).

Fontes avaliadas em 27/11/2026, pelas páginas dos provedores e por relatos de uso.
Não foi possível chamar as APIs do ambiente de nuvem usado na análise:

| Fonte | Acesso | Limites do plano gratuito | Uso proposto |
| --- | --- | --- | --- |
| [SGS do Banco Central](https://www.tabnews.com.br/SidneyBissoli/series-do-banco-central-como-consultar-o-sgs-a-focus-e-a-ptax-sem-cair-nas-armadilhas) (`api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados`) | Sem chave, licença ODbL com atribuição | Série diária limitada a janelas de 10 anos; `ultimos/N` até 20 pontos; sem paginação nem metadados; 503 em manutenção noturna | Selic meta (432), Selic diária (11), CDI diário (12), IPCA mensal (433) |
| [brapi.dev](https://brapi.dev/pricing) | Token gratuito, um por conta | 15.000 requisições/mês, um ticker por requisição, uma simultânea, cotação com cerca de 30 min de atraso, histórico de 3 meses só diário; macro do BCB só nos planos pagos | Cotações de ações (PETR4, MGLU3, VALE3 e ITUB4 funcionam sem token) |

Ainda não se sabe: se `^BVSP` está no plano gratuito da brapi e qual código SGS
corresponde ao IPCA acumulado em 12 meses (13522 aparece com outro significado
em uma das fontes). Os dois precisam de teste antes de entrar no código.

## Decisão

Proposta para o time aprovar:

1. Criar o módulo `alpha` no backend com `models`, `repository`, `service` e
   `router` de leitura, seguindo a [ADR-0001](0001-monolito-modular.md). A API só
   lê sinais; quem escreve é o pipeline, como a modelagem já prevê.
2. Usar o SGS para indicadores macro e a brapi para cotações, com no máximo
   cinco tickers no MVP. Cinco tickers de hora em hora no pregão consomem perto
   de 900 requisições por mês, cerca de 6% da cota.
3. Ingerir por um workflow agendado do GitHub Actions que grava no Neon. O Render
   Free dorme e não serve para coleta periódica. O token da brapi fica como
   secret do repositório, nunca em arquivo versionado.
4. Regras temporais, porque o SGS devolve só `data` e `valor`, sem publicação:
   - `observation_date` recebe a data de referência da fonte.
   - `published_at` recebe o instante da primeira coleta que viu o valor, com
     `published_at_estimated = false`. É conservador: o sistema nunca afirma que
     algo era conhecido antes de ter sido coletado.
   - Na carga histórica, `published_at` vem do calendário oficial de divulgação,
     com `published_at_estimated = true`, e a interface exibe "reconstituição
     ilustrativa".
   - Valor diferente para a mesma data em coleta futura vira nova linha com
     `revision_id` maior; nada é sobrescrito.
   - Na brapi, `published_at` é o instante da coleta, por causa do atraso.
5. Sinais por regras determinísticas e versionadas (por exemplo, mudança da
   Selic meta entre reuniões), com as séries de entrada como evidência. Nenhum
   sinal atribui causa a gasto pessoal nem probabilidade.
6. Notícias de portais ficam fora do MVP por licença e procedência incertas;
   eventos oficiais com data (Copom, divulgação do IPCA) cobrem a promessa.

## Alternativas consideradas

- Indicadores macro pela brapi: exigem plano pago.
- Coleta dentro da API no Render: perde execuções enquanto o serviço dorme e
  mistura leitura com escrita.
- `published_at` igual à data de referência do SGS: anteciparia dados, como o
  IPCA de um mês divulgado só no mês seguinte, e violaria a regra de data leakage.
- Manter o Alpha sintético: não cumpre a promessa da landing.

## Consequências

- O radar passa a mostrar dados reais com fonte, data de referência e instante
  de coleta, e a IA pode citar sinais Alpha respeitando o corte.
- Um replay por `as_of` fica possível, porque cada revisão guarda a publicação.
- Custos: dependência de duas fontes externas sem SLA, um secret no GitHub e uma
  migração nova. Falha de coleta deixa o radar desatualizado, nunca com dado
  inventado; a interface mostra o instante da última coleta.
- Reverter: desligar o workflow e esconder o radar; as tabelas são somente
  inserção e podem ficar.
- Dinheiro Alpha (cotações) continua fora do contrato da ADR-0011: cotação entra
  como `DecimalValue` com unidade registrada, ou espera uma decisão própria.

## Status

Proposta, 27/11/2026, a pedido de Willian. Aguarda aprovação do time antes de
qualquer código do módulo `alpha` ou do pipeline.
