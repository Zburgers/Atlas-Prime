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
		'  make worker-test Run media worker tests' \
		'  make lint       Run lightweight syntax/config checks' \
		'  make smoke      Run Sector H stack smoke check' \
		'  make analytics-rebuild DATE_FROM=YYYY-MM-DD DATE_TO=YYYY-MM-DD  Rebuild daily analytics' \
		'  make search-reindex  Enqueue a public-video search index rebuild' \
		'  make processing-recover-stale [ARGS="--apply"]  Inspect/fail abandoned processing jobs (dry run by default)' \
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
	$(COMPOSE) run --rm --build worker pytest tests
	$(COMPOSE) run --rm --build web-test npm --workspace apps/web test

.PHONY: worker-test
worker-test: env
	$(COMPOSE) run --rm --build worker pytest tests

.PHONY: lint
lint: env
	$(COMPOSE) config -q
	$(COMPOSE) run --rm --build api python -m compileall app tests
	$(COMPOSE) run --rm --build worker python -m compileall media_worker tests
	$(COMPOSE) run --rm --build web-test npm --workspace apps/web run lint

.PHONY: smoke
smoke:
	./scripts/smoke-devex.sh

.PHONY: fixture
fixture:
	./scripts/generate-sample-media.sh

.PHONY: analytics-rebuild
analytics-rebuild: env
	@test -n "$(DATE_FROM)" && test -n "$(DATE_TO)" || (echo "Set DATE_FROM and DATE_TO as YYYY-MM-DD"; exit 2)
	$(COMPOSE) run --rm --build api python -m app.commands.rebuild_analytics --date-from "$(DATE_FROM)" --date-to "$(DATE_TO)"

.PHONY: search-reindex
search-reindex: env
	$(COMPOSE) exec search-worker celery -A app.worker.search call search_worker.rebuild_public_video_index

.PHONY: processing-recover-stale
processing-recover-stale: env
	$(COMPOSE) run --rm --build api python -m app.commands.recover_stale_jobs $(ARGS)
