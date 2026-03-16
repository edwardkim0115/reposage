COMPOSE = docker compose

.PHONY: up down build logs api-test web-lint format migrate

up:
	$(COMPOSE) up --build

down:
	$(COMPOSE) down --volumes

build:
	$(COMPOSE) build

logs:
	$(COMPOSE) logs -f

migrate:
	$(COMPOSE) run --rm api alembic -c apps/api/alembic.ini upgrade head

api-test:
	$(COMPOSE) run --rm api pytest

web-lint:
	$(COMPOSE) run --rm web npm run lint --workspace @reposage/web

format:
	$(COMPOSE) run --rm api ruff format .

