# Imagem de produção da API para hospedagem gratuita (Render); o desenvolvimento local segue com make dev.
FROM python:3.12-slim

# uv via PyPI: mesma ferramenta e mesmo uv.lock do desenvolvimento local.
RUN pip install --no-cache-dir uv==0.8.17

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

# Mantém a profundidade services/api/src/... porque config.py localiza a raiz por parents[5].
WORKDIR /app/services/api

# Dependências antes do código, para o cache de camadas sobreviver a mudanças em src/.
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project

COPY alembic.ini ./
COPY alembic ./alembic
COPY src ./src
COPY deploy ./deploy
RUN uv sync --locked --no-dev && chmod +x deploy/start.sh \
    && useradd --create-home --uid 10001 valyra
USER valyra

EXPOSE 8000
CMD ["./deploy/start.sh"]
