UV ?= uv
ENV_FILE ?= $(abspath $(if $(wildcard .env),.env,.env.example))
RUN = "$(UV)" run --locked --env-file "$(ENV_FILE)" --directory services/api

.PHONY: sync dev test test-unit test-integration test-domain test-ai lint migrate seed openapi
sync:
	"$(UV)" sync --project services/api --locked
dev:
	docker compose --env-file "$(ENV_FILE)" up -d --wait postgres
	$(RUN) uvicorn valyra.main:create_app --factory --reload
test:
	$(RUN) pytest
test-unit:
	$(RUN) pytest -m "not postgres"
test-integration:
	$(RUN) pytest -m postgres
test-domain:
	$(RUN) pytest tests/finance/test_domain.py tests/finance/test_analytics.py tests/core/test_clock.py \
		tests/alerts/test_alerts_domain.py tests/alpha/test_domain.py tests/alpha/test_news_domain.py
test-ai:
	$(RUN) pytest tests/ai
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
