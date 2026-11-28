#!/bin/sh
# Inicialização em produção: migra, semeia e só então aceita tráfego.
set -eu

: "${DATABASE_URL:?defina DATABASE_URL com a connection string do PostgreSQL}"

# Neon e Render entregam postgresql:// ou postgres://; o SQLAlchemy precisa do driver psycopg explícito.
case "$DATABASE_URL" in
  postgres://*) DATABASE_URL="postgresql+psycopg://${DATABASE_URL#postgres://}" ;;
  postgresql://*) DATABASE_URL="postgresql+psycopg://${DATABASE_URL#postgresql://}" ;;
esac
export DATABASE_URL

# O plano gratuito do Render não executa pre-deploy; migrar aqui é idempotente (alembic) e o seed também.
alembic upgrade head
python -m valyra.seed
# Clientes fictícios dos perfis da demo: só importa extrato em conta vazia, então não desfaz
# o que foi alterado durante a demo. Falha aqui não impede a API de subir.
python -m valyra.scripts.seed_demo_profiles || echo "Aviso: perfis da demo não foram semeados" >&2

# --proxy-headers: o Render termina o HTTPS no proxy e repassa a requisição em HTTP.
# Aceitar X-Forwarded-* de qualquer IP é seguro aqui porque o contêiner só recebe tráfego pelo proxy do Render.
exec uvicorn valyra.main:create_app --factory \
  --host 0.0.0.0 --port "${PORT:-8000}" \
  --proxy-headers --forwarded-allow-ips='*'
