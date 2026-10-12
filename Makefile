PYTHON ?= python3
UV ?= uv

.PHONY: env up dev down config backend-check frontend-check check integration schema
env:
	$(PYTHON) scripts/bootstrap_env.py

up: env
	docker compose up --build

dev:
	$(PYTHON) scripts/dev.py

down:
	docker compose down

config: env
	docker compose config --quiet

backend-check:
	cd backend && $(UV) run ruff check .
	cd backend && $(UV) run ruff format --check .
	cd backend && $(UV) run mypy app
	cd backend && $(UV) run pytest -m 'not integration'

frontend-check:
	cd frontend && npm run lint
	cd frontend && npm run typecheck
	cd frontend && npm run test:proxy
	cd frontend && npm run build

ops-check:
	$(PYTHON) -m unittest discover -s tests -v
	docker compose --env-file deploy/production.env.example -f docker-compose.production.yml config --quiet

check: backend-check frontend-check ops-check

integration:
	cd backend && $(UV) run pytest -m integration

schema:
	cd backend && PYTHONPATH=. $(UV) run python scripts/export_openapi.py
	cd frontend && npm run generate:api
