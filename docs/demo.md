# Roteiro da demonstração

Roteiro de 3 minutos para apresentar o Valyra Finance publicado (front na Vercel, API no Render, banco no Neon). Os dados são sintéticos: uma persona fictícia de Belo Horizonte, com salário mensal, contas fixas e dois gastos fora do padrão em novembro.

## Os arquivos

| Arquivo | Quando importar | O que contém |
| --- | --- | --- |
| `datasets/samples/demo_historico.csv` | Antes da apresentação | 129 lançamentos de agosto a outubro de 2026: salário, aluguel, condomínio, Cemig, Copasa, internet, celular, assinaturas, academia, curso, mercado, aplicativos de transporte, restaurantes, farmácia e um freela. |
| `datasets/samples/demo_novembro.csv` | Ao vivo, durante a demo | 43 lançamentos de 1º a 25 de novembro, incluindo um tratamento odontológico de R$ 1.280,00 e um jantar de R$ 486,50. |

O histórico dá ao Valyra três meses para reconhecer as recorrências e o padrão de gasto de cada categoria. Novembro traz a surpresa: os dois gastos atípicos e, com o aluguel vencendo antes do salário, o alerta de saldo negativo.

As contas de energia e água ficam na mesma categoria que internet e celular, com valores próximos; assim nenhuma conta comum aparece como atípica. O arquivo antigo `transactions_demo.csv` continua disponível para testes, mas não deve ser misturado com estes dois na mesma conta.

## Preparação (uma vez, antes do dia)

1. **Banco limpo.** Se a conta demo já tiver transações de testes anteriores, volte ao estado inicial como descrito em [deploy.md](deploy.md#cuidados). Dados antigos entram nos mesmos cálculos e mudam os números do roteiro.
2. **Data fixa.** No Render, em *Environment*, crie `DEMO_TODAY=2026-11-26` e faça o redeploy. Sem ela, "hoje" é o dia real e, a partir de dezembro, o aluguel previsto já terá passado e o alerta deixa de aparecer.
3. **Histórico.** Em `/#/app/importar`, importe `demo_historico.csv`. Resultado esperado: 129 importadas, 0 duplicadas, 0 rejeitadas, nenhum alerta.
4. **Saldo de referência.** Em *Visão geral*, clique em *Editar* na conta e informe R$ 1.150,00 em 01/11/2026 (saldo depois de pagar aluguel e condomínio de novembro).
5. **Ensaio opcional.** Para ensaiar sem gastar o momento ao vivo, use um banco de branch do Neon ou a API local. Se `demo_novembro.csv` já tiver sido importado na produção, a reimportação mostra 43 duplicadas e nenhum alerta novo; o alerta continua na tela de alertas.

## Checklist dos 10 minutos antes

- Abra `https://valyra-api.onrender.com/health` e espere `{"status":"ok","postgres":"ok"}`. A API gratuita dorme após 15 minutos parada e leva cerca de 1 minuto para acordar.
- Abra `https://valyra-landing.vercel.app` em uma aba e confira, dentro do app, o indicador "API conectada".
- Deixe `demo_novembro.csv` em uma pasta fácil de achar, como a Área de Trabalho.
- Zoom do navegador em 110% a 125%, notificações desligadas e só as abas da demo abertas.
- Não deixe a API parada por mais de 15 minutos entre o checklist e a apresentação; recarregue `/health` se houver espera.

## Roteiro (3 minutos)

Números abaixo conferidos com `DEMO_TODAY=2026-11-26`, banco limpo e a preparação acima.

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
