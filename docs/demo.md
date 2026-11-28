# Roteiro da demonstração

Roteiro de 3 minutos para apresentar o Valyra Finance publicado (front na Vercel, API no Render, banco no Neon). Os dados são sintéticos: uma persona fictícia de Belo Horizonte, com salário mensal, contas fixas e dois gastos fora do padrão em novembro.

## Os arquivos

| Arquivo | Quando importar | O que contém |
| --- | --- | --- |
| `datasets/samples/demo_historico.csv` | Antes da apresentação | 129 lançamentos de agosto a outubro de 2026: salário, aluguel, condomínio, Cemig, Copasa, internet, celular, assinaturas, academia, curso, mercado, aplicativos de transporte, restaurantes, farmácia e um freela. |
| `datasets/samples/demo_novembro.csv` | Ao vivo, durante a demo | 43 lançamentos de 1º a 25 de novembro, incluindo um tratamento odontológico de R$ 1.280,00 e um jantar de R$ 486,50. |

O histórico dá ao Valyra três meses para reconhecer as recorrências e o padrão de gasto de cada categoria. Novembro traz a surpresa: os dois gastos atípicos e, com o aluguel vencendo antes do salário, o alerta de saldo negativo.

As contas de energia e água ficam na mesma categoria que internet e celular, com valores próximos; assim nenhuma conta comum aparece como atípica. Estes dois arquivos são o conjunto oficial da apresentação. O `transactions_demo.csv` continua disponível para desenvolvimento e testes, mas não deve ser misturado com eles na mesma conta.

## Preparação (uma vez, antes do dia)

1. **Banco limpo.** Se a conta demo já tiver transações de testes anteriores, volte ao estado inicial como descrito em [deploy.md](deploy.md#cuidados), de preferência criando um branch novo no Neon. Antes de apagar qualquer tabela, confirme no painel que é o banco da demo e que ele é descartável. Dados antigos entram nos mesmos cálculos e mudam os números do roteiro.
2. **Data fixa.** No Render, em *Environment*, crie `DEMO_TODAY=2026-11-26` e faça o redeploy. Sem ela, "hoje" é o dia real e, a partir de dezembro, o aluguel previsto já terá passado e o alerta deixa de aparecer.
3. **Histórico.** Em `/#/app/importar`, importe `demo_historico.csv`. Resultado esperado: 129 importadas, 0 duplicadas, 0 rejeitadas, nenhum alerta.
4. **Saldo de referência.** Em *Visão geral*, clique em *Editar* na conta e informe R$ 1.150,00 em 01/11/2026 (saldo depois de pagar aluguel e condomínio de novembro).
5. **Ensaio opcional.** Para ensaiar sem gastar o momento ao vivo, use um banco de branch do Neon ou a API local. Se `demo_novembro.csv` já tiver sido importado na produção, a reimportação mostra 43 duplicadas e nenhum alerta novo; o alerta continua na tela de alertas.

## Checklist dos 10 minutos antes

- Abra `https://valyra-api.onrender.com/health` (endereços atuais da publicação; se o serviço for recriado, confira no painel do Render e da Vercel) e espere `{"status":"ok","postgres":"ok"}`. A API gratuita dorme após 15 minutos parada e leva cerca de 1 minuto para acordar.
- Abra `https://valyra-landing.vercel.app` em uma aba e confira, dentro do app, o indicador "API conectada".
- Deixe `demo_novembro.csv` em uma pasta fácil de achar, como a Área de Trabalho.
- Zoom do navegador em 110% a 125%, notificações desligadas e só as abas da demo abertas.
- Não deixe a API parada por mais de 15 minutos entre o checklist e a apresentação; recarregue `/health` se houver espera.

## Roteiro (3 minutos)

Números conferidos manualmente em 26/11/2026, na API local da `main` no commit `d98c6be`, com `DEMO_TODAY=2026-11-26`, banco limpo e a preparação acima. Mudanças nos cálculos podem alterá-los; repita a conferência depois delas.

A projeção não usa o dia do mês: cada recorrência é prevista a partir da última ocorrência mais a mediana dos intervalos (ADR-0010, seção 5). Como os intervalos de agosto a novembro são 31, 30 e 31 dias, a mediana é 31, e por isso o aluguel de 01/11 aparece em 02/12 e o salário de 05/11 em 06/12.

**0:00 a 0:20, landing.** "Todo mês a gente descobre tarde demais que o dinheiro não fecha. O Valyra lê o seu extrato e avisa antes." Clique em *Abrir demonstração*.

**0:20 a 0:50, importar o extrato.** Em *Importar CSV*, envie `demo_novembro.csv`. Mostre o resultado: 43 lançamentos importados, nenhum rejeitado e 1 alerta criado. "Cada linha já entra categorizada. Se eu enviar o mesmo arquivo de novo, o Valyra reconhece as duplicatas e não conta nada duas vezes."

**0:50 a 1:30, resumo do mês.** Em *Resumo do mês*: entradas de R$ 4.300,00, saídas de R$ 6.010,80 e resultado de −R$ 1.710,80. Moradia lidera com R$ 1.830,00, seguida de Saúde com R$ 1.430,29. Em *Transações*, filtre os atípicos: a clínica odontológica de R$ 1.280,00 e o restaurante de R$ 486,50. "Ele compara cada gasto com o padrão da própria categoria. Farmácia de R$ 50 é normal; dentista de R$ 1.280 salta aos olhos."

**1:30 a 2:20, projeção de caixa.** Em *Projeção de caixa*: saldo de hoje R$ 1.269,20. O Valyra reconheceu sozinho as contas que se repetem, como salário, aluguel, condomínio, energia e assinaturas, e projeta os próximos 30 dias. O aluguel e o condomínio caem em 02/12, antes do salário previsto para 06/12, e o saldo chega a −R$ 1.314,10 em 05/12. "É como a previsão do tempo do seu bolso: não é chute, é o seu próprio histórico projetado para frente."

**2:20 a 2:50, alerta.** Em *Alertas*: "Saldo previsto negativo. A projeção dos próximos 30 dias indica saldo mínimo de −R$ 1.314,10 em 05/12/2026." "Todo número vem de um cálculo que dá para auditar. A IA entra para explicar essas evidências em linguagem simples, nunca para inventar números."

**2:50 a 3:00, fechamento.** "O Valyra transforma o extrato em decisão: o que aconteceu, o que é fora do padrão e o que vem pela frente."

## Plano B

- **API dormindo ou lenta:** abra `/health` em outra aba e continue falando pela landing; o app tenta de novo sozinho.
- **Importação ao vivo falhou:** importe `demo_novembro.csv` assim que a API responder, ou siga pelas telas se ele já tiver sido importado. O resumo, a projeção e o alerta continuam iguais.
- **Números diferentes do roteiro:** quase sempre é dado de teste antigo na conta ou `DEMO_TODAY` ausente; confira os dois itens da preparação.

## Jornada completa: Finance, Alpha e IA

Extensão sugerida para uma apresentação de até 5 minutos. O roteiro Finance e
seus números históricos acima foram preservados; esta extensão exige um novo
ensaio no ambiente que será apresentado, sem presumir os valores atuais das fontes.

### Preparação adicional

- Depois de importar os dois CSVs, abra **Orçamento**, escolha uma categoria de
  saída e defina um teto acima do gasto exibido. Confirme que salvar e remover
  um teto funcionam no site publicado, onde navegador e API usam origens diferentes.
  Deixe o orçamento preparado e confira o limite diário mostrado pelo Finance.
- Confira **Alternative Alpha** e **Notícias da semana**: devem existir dados
  coletados, com fonte e publicação. Verifique o horário da última coleta e as
  limitações de cobertura. O radar pode ficar vazio se a coleta não tiver ocorrido;
  isso não demonstra ausência de eventos no mercado.
- Configure a chave do provedor somente no ambiente do backend. Antes do evento,
  faça uma pergunta de ensaio na tela **Valyra AI** e confira resposta, evidências
  citadas e limitações. A chamada real consome cota; os testes automáticos usam
  transporte simulado e não comprovam a qualidade da resposta do provedor real.
- `DEMO_TODAY` fixa os cálculos Finance; o corte de conhecimento da IA continua
  sendo o instante real do servidor. O radar também tem seu próprio corte explícito.
  Não apresente a combinação como replay histórico completo da conta.

### Sequência sugerida

1. **Finance — 2min30.** Siga importação, resumo e projeção do roteiro. Mostre o
   alerta e um orçamento configurado. Explique: o limite diário vem do teto
   restante dividido pelos dias do mês pelo Finance; não é saldo disponível nem
   a estimativa de gasto diário usada na projeção. Os tetos são do usuário e o
   painel agrega suas contas; a explicação da IA usa o consumo da conta consultada.
2. **Alpha — 1min.** Abra o radar, escolha clima em uma região produtora e mostre
   observação, publicação e fonte. Na semana, abra uma manchete sobre agro/soja
   ou um ativo acompanhado, conforme o que realmente estiver coletado. Diga:
   “Isso oferece contexto para acompanhar; não é uma probabilidade de queda nem
   prova que a notícia causou uma mudança no preço.”
3. **IA — 1min.** Pergunte “Qual é meu limite diário de orçamento e de onde vem
   esse valor?”. Confira o valor com o Finance. Depois use **Gerar resumo** na
   semana ou pergunte sobre as notícias e indicadores disponíveis. Abra uma fonte
   citada e mostre sua publicação. Diferencie registros, cálculos e fontes públicas;
   indique quando a publicação for estimada. O modelo explica resultados que o
   servidor já calculou, e não precisa citar todas as evidências disponíveis.
4. **Fechamento — 30s.** Retome o alerta de caixa, o contexto econômico e a
   explicação com evidências. Declare as limitações: conta sintética, cobertura
   parcial das fontes e ausência de previsão probabilística de retorno.

### Verificação de aceite antes de apresentar

- [ ] Salvar e excluir orçamento funcionam no navegador publicado.
- [ ] O limite diário aparece na resposta com origem Finance; zero e ausência de
      teto não são tratados como o mesmo caso.
- [ ] Uma conta com mais categorias/indicadores ainda recebe explicação, com aviso
      quando parte do contexto precisar ser omitida pelo limite do prompt.
- [ ] Fontes HTTP(S) abrem em nova aba e a publicação é visível nas evidências Alpha.
- [ ] A pergunta de ensaio funciona com o provedor configurado, sem expor chave ou
      resposta descartada. Se a validação rejeitar a resposta, registre a falha;
      não apresente o texto rejeitado como explicação validada.

Sem Alpha/notícias, mostre a limitação de cobertura e siga com Finance. Sem
provedor, siga com os números e as fontes das telas e declare que a explicação
está indisponível. Não substitua uma falha por resposta pré-escrita apresentada
como chamada ao vivo. Os itens acima são verificações pendentes de ensaio, não
um registro de validação em produção.
