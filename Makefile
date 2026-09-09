.PHONY: up down logs migrate test shell

up:            ## Build and start the whole stack (api on :8080)
	docker compose up -d --build

down:          ## Stop the stack and drop volumes
	docker compose down -v

logs:
	docker compose logs -f api worker

migrate:       ## Apply migrations against the local DB
	alembic upgrade head

test:          ## Run the test suite (needs db + redis running: `make up`)
	pytest

shell:         ## psql into the running database
	docker compose exec db psql -U marketplace -d marketplace_db
