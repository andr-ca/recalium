.PHONY: up down logs build shell-app shell-db migrate reset-dev

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
