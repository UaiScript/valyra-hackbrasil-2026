UV ?= uv
ENV_FILE ?= $(abspath $(if $(wildcard .env),.env,.env.example))
RUN = "$(UV)" run --locked --env-file "$(ENV_FILE)" --directory services/api

.PHONY: sync dev test test-domain lint migrate seed openapi
sync:
	"$(UV)" sync --project services/api --locked
dev:
	docker compose --env-file "$(ENV_FILE)" up -d --wait postgres
	$(RUN) uvicorn valyra.main:create_app --factory --reload
test:
	$(RUN) pytest
test-domain:
	$(RUN) pytest tests/finance/test_domain.py
lint:
	$(RUN) ruff check .
	$(RUN) ruff format --check .
	$(RUN) lint-imports
migrate:
	$(RUN) alembic upgrade head
seed:
	$(RUN) python -m valyra.seed
openapi:
	$(RUN) python -m valyra.scripts.export_openapi
