.PHONY: setup-env up up-prod down logs build frontend-dev frontend-build frontend-test test-backend test-backend-e2e test-frontend lint typecheck validate smoke eval eval-strict eval-scale shell-app shell-db migrate reset-dev

## Create .env from .env.sample if it does not already exist
setup-env:
	@if [ -f .env ]; then \
		echo ".env already exists; leaving it unchanged"; \
	else \
		cp .env.sample .env; \
		echo "Created .env from .env.sample; edit it before production use"; \
	fi

## Start all services (development mode with hot-reload)
up:
	docker compose up

## Start in production mode (no override file)
up-prod:
	docker compose -f docker-compose.yml up -d

## Stop services (data is preserved — bind mounts on host)
down:
	docker compose down
	@echo "Data preserved at ./data/postgres and ./backups"

## View logs
logs:
	docker compose logs -f

## Build images
build:
	docker compose build

## Start the Vite frontend dev server
frontend-dev:
	cd frontend && pnpm dev

## Build the frontend production assets
frontend-build:
	cd frontend && pnpm install && pnpm build

## Run frontend unit/component tests
frontend-test:
	cd frontend && pnpm test

## Run backend tests
test-backend:
	cd backend && pytest

## Run live-stack backend E2E tests; requires docker compose up
test-backend-e2e:
	cd backend && pytest tests/e2e

## Alias for frontend tests
test-frontend: frontend-test

## Type-check frontend and lint backend if configured
lint:
	cd frontend && pnpm lint
	cd backend && uv run ruff check app tests

## Type-check frontend build boundary
typecheck:
	cd frontend && pnpm build

## Run evaluation suite against live stack; requires docker compose up
eval:
	cd backend && uv run --project . python ../evals/runner.py --base-url http://localhost:8000 --output-dir ../evals/results

## Release eval gate: fails on ANY skipped or errored check (GPT5.6 #3)
eval-strict:
	cd backend && uv run --project . python ../evals/runner.py --base-url http://localhost:8000 --output-dir ../evals/results --strict

## Scale/concurrency eval: ingests a volume corpus, measures latency + concurrency (GPT5.6 #20)
eval-scale:
	cd backend && uv run --project . python ../evals/runner.py --base-url http://localhost:8000 --output-dir ../evals/results --scale --scale-size 150

## Smoke-check local API; requires docker compose up
smoke:
	curl -fsS http://localhost:$${APP_PORT:-8000}/api/health >/dev/null
	@echo "Recalium API health check passed"

## Local validation bundle excluding UI E2E until Playwright is added
validate: test-backend frontend-build frontend-test

## Open shell in app container
shell-app:
	docker compose exec recalium-app bash

## Open psql in postgres container
shell-db:
	docker compose exec recalium-postgres psql -U $${POSTGRES_USER:-recalium} -d $${POSTGRES_DB:-recalium}

## Run alembic migrations manually
migrate:
	docker compose exec recalium-app alembic -c backend/alembic.ini upgrade head

## Reset dev environment (PRESERVES DATA — only removes containers)
## If you want to also wipe the DB: manually delete ./data/postgres/
reset-dev:
	@echo "Stopping containers (data preserved at ./data/postgres)..."
	docker compose down
	docker compose build --no-cache
	docker compose up
