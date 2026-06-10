check:
	@command -v docker >/dev/null 2>&1 || (echo "Docker not found" && exit 1)
	@docker compose version >/dev/null 2>&1 || (echo "Docker Compose plugin not found" && exit 1)
	@test -f .env || (echo ".env missing — run: cp .env.example .env" && exit 1)
	@echo "Environment ready."

setup: check
	docker compose build

migrate:
	docker compose run --rm web python manage.py migrate

seed:
	docker compose run --rm web python manage.py seed

up:
	docker compose up

test:
	docker compose run --rm web pytest

coverage:
	docker compose run --rm web pytest --cov=. --cov-report=term-missing
