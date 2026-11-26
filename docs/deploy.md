# Publicação gratuita da API

Configuração para o hackathon: API no [Render](https://render.com/docs/free) (plano Free, Docker) e PostgreSQL no [Neon](https://neon.com/docs/introduction/free-tier) (plano Free). O front continua na Vercel e aponta para a API por `VITE_API_URL`.

## Por que essa combinação

| Peça | Serviço | Limites do plano gratuito |
| --- | --- | --- |
| API FastAPI | Render Free | Dorme após 15 minutos sem requisições; acordar leva cerca de 1 minuto. 750 horas por mês, suficiente para um serviço ligado o mês todo. Sem shell e sem disco persistente. |
| PostgreSQL | Neon Free | 1 GB por projeto; o compute suspende após 5 minutos parado e volta em segundos na próxima consulta. Não expira. |

O PostgreSQL gratuito do próprio Render foi descartado porque expira 30 dias após a criação e é apagado depois de 14 dias de carência.

## O que o repositório já faz

- `services/api/Dockerfile` instala as dependências pelo `uv.lock`, sem as de desenvolvimento, e roda como usuário sem privilégios.
- `services/api/deploy/start.sh` converte `postgresql://` em `postgresql+psycopg://`, executa `alembic upgrade head` e o seed idempotente, e só então inicia o uvicorn na porta `PORT` do Render. Migrar na inicialização substitui o pre-deploy, indisponível no plano gratuito; se a migração falhar, a API não sobe e o deploy aparece como falho no painel.
- `render.yaml` descreve o serviço, o health check em `/health` e as variáveis.

## Passo a passo

1. **Banco no Neon.** Crie a conta em neon.com, crie um projeto na região AWS US East (N. Virginia) e copie a connection string em *Connect*, com *Connection pooling* desligado. Ela começa com `postgresql://` e termina com `?sslmode=require`.
2. **API no Render.** Crie a conta em render.com entrando com o GitHub e autorize o repositório. Em *New* → *Blueprint*, escolha o repositório; o Render lê o `render.yaml` e pede os valores marcados como secretos:
   - `DATABASE_URL`: a connection string do Neon.
   - `CORS_ORIGIN`: o endereço do front na Vercel, por exemplo `https://valyra.vercel.app`, sem barra no final.
3. **Confira.** Quando o deploy terminar, abra `https://<nome>.onrender.com/health`. A resposta esperada é `{"status":"ok","postgres":"ok"}`.
4. **Front na Vercel.** Em *Settings* → *Environment Variables* do projeto, defina `VITE_API_URL` com o endereço do Render, sem barra no final, e faça *Redeploy*. A variável entra no build, então só vale depois de um novo deploy.

## Cuidados

- `CORS_ORIGIN` aceita uma única origem. Deploys de preview da Vercel têm outro endereço e serão recusados pelo navegador; teste pelo domínio de produção.
- Antes de apresentar, abra `/health` uma vez para acordar a API. Um monitor gratuito chamando `/health` a cada 10 minutos mantém o serviço acordado dentro das 750 horas.
- O Neon guarda dados de demonstração; use apenas os CSVs sintéticos de `datasets/samples/`.
