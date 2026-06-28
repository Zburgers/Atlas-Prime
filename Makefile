COMPOSE := docker compose

.PHONY: help
help:
	@printf '%s\n' \
		'Atlas Prime Sector H commands:' \
		'  make env        Create .env from .env.example if missing' \
		'  make up         Build and start the full local stack' \
		'  make down       Stop the local stack' \
		'  make logs       Follow service logs' \
		'  make ps         Show compose service status' \
		'  make db-upgrade Run API Alembic migrations' \
		'  make test       Run API and web tests' \
		'  make lint       Run lightweight syntax/config checks' \
		'  make smoke      Run Sector H stack smoke check' \
		'  make fixture    Generate a tiny legal MP4 fixture with ffmpeg'

.PHONY: env
env:
	@test -f .env || cp .env.example .env

.PHONY: up
up: env
	$(COMPOSE) up --build -d

.PHONY: down
down:
	$(COMPOSE) down

.PHONY: logs
logs:
	$(COMPOSE) logs -f

.PHONY: ps
ps:
	$(COMPOSE) ps

.PHONY: db-upgrade
db-upgrade: env
	$(COMPOSE) run --rm --build api alembic upgrade head

.PHONY: test
test: env
	$(COMPOSE) run --rm --build api pytest
	$(COMPOSE) run --rm --build web-test npm --workspace apps/web test

.PHONY: lint
lint: env
	$(COMPOSE) config -q
	$(COMPOSE) run --rm --build api python -m compileall app tests
	$(COMPOSE) run --rm --build web-test npm --workspace apps/web run lint

.PHONY: smoke
smoke:
	./scripts/smoke-devex.sh

.PHONY: fixture
fixture:
	./scripts/generate-sample-media.sh
