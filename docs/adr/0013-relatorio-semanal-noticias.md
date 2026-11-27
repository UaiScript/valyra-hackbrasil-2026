# ADR-0013 — Relatório semanal de notícias no Alternative Alpha

## Contexto

A [ADR-0012](0012-fontes-alpha.md) deixou notícias de portais fora do MVP por licença e
procedência incertas. Em 27/11/2026 o time pediu para avaliar, como bônus, um relatório
semanal com as notícias que podem impactar as decisões financeiras da persona, para
reforçar a Valyra como central de inteligência financeira.

Fontes avaliadas em 27/11/2026, pelas páginas públicas dos provedores. As URLs dos feeds
não puderam ser chamadas do ambiente de nuvem usado na análise:

| Fonte | Acesso | Uso permitido | Observação |
| --- | --- | --- | --- |
| Agência Brasil (EBC), feed `rss/economia/feed.xml` | RSS público | "Reprodução autorizada para veículos de comunicação com fins jornalísticos, mediante indicação da fonte"; uso comercial pede contato com o licenciamento da EBC | Não é Creative Commons; conteúdo de agências parceiras pode ter reprodução proibida |
| Banco Central, `api/feed/sitebcb/sitefeeds/notasImprensa` | RSS público | Conteúdo institucional público, citando a fonte | Endereço visto em agregador de feeds, não confirmado no site do BCB |
| Agência de Notícias do IBGE, `servicodados.ibge.gov.br/api/v3/noticias/` | API JSON sem chave | Conteúdo institucional público, citando a fonte | Campos `titulo`, `introducao`, `link`, `data_publicacao` conforme clientes públicos da API |
| GDELT | API sem chave | Metadados abertos | Descartada: aponta para portais de licença variada e não tem foco no Brasil |

## Decisão

Proposta para o time aprovar:

1. Guardar cada manchete como sinal `news_event` (o `kind` já existe na migração
   `0004_alpha`), sem valor numérico, com título, trecho de até 240 caracteres, link da
   matéria e fonte. Nenhuma matéria é copiada inteira; a tela sempre leva ao original.
2. Regras temporais: `published_at` é a data da fonte limitada ao instante da coleta
   (nunca depois dela; sem data, a própria coleta), `ingested_at` é a coleta e a data da
   fonte fica no `payload`. O relatório da semana mostra só o publicado até o corte.
3. Ligação com o orçamento por regra determinística e versionada (`news_theme_v2`):
   palavras-chave inteiras levam a manchete a um tema e o tema aponta categorias Finance.
   É um "pode mexer em", nunca causa nem previsão. Os temas são calculados na leitura,
   então trocar a regra não reescreve linhas somente inserção.
   A versão 2 acrescenta "Ações que você acompanha" (nome da empresa → ticker do radar)
   e "Agro e cadeia da soja", e cada tema aponta o tema do radar Alpha cujo dado observado
   (variação do dia, Selic, IPCA, chuva) aparece ao lado das manchetes. Nenhum percentual
   de "possibilidade de alta ou queda" é exibido: sem modelo validado, seria número sem
   suporte verificável.
4. A Valyra AI recebe até 8 manchetes da semana como evidência textual `alpha_signal`,
   com fonte e data, e só pode reproduzi-las literalmente (contrato da ADR-0011).
5. Coleta por workflow agendado três vezes ao dia, com o mesmo interruptor e secret da
   coleta Alpha. Sem migração nova.

## Alternativas consideradas

- Portais comerciais por RSS: licença de reprodução fechada ou desconhecida.
- GDELT: procedência variada e pouca cobertura brasileira.
- Pedir ao LLM para classificar e ligar notícias ao orçamento: a ligação viraria uma
  afirmação do modelo sem suporte verificável.
- Deixar de fora: a promessa de "eventos com origem e data" fica só com sinais macro.

## Consequências

- O Alpha ganha um relatório legível pela persona, com fonte e data em cada item.
- Custos: três fontes externas sem SLA e regras de palavras-chave que erram (falso
  positivo ou manchete sem tema); o relatório mostra quantas ficaram fora.
- Uso comercial do conteúdo da Agência Brasil exige contato com a EBC antes de qualquer
  versão paga; até lá, só título, trecho e link.
- Reverter: desligar o workflow e esconder a rota; as linhas podem ficar.

## Status

Proposta em 27/11/2026, com protótipo em PR para avaliação do time. Não aceita.
Ainda não verificados: os três endereços de feed a partir de uma rede com acesso.
