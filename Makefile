# =============================================================================
# MegaStore Makefile
# =============================================================================

.PHONY: help build up down restart logs shell migrate makemigrations superuser \
        seed test lint format clean celery beat frontend db-shell redis-cli \
        collectstatic backup restore

# Default target
help: ## Show this help message
	@echo "MegaStore - Available Commands:"
	@echo "================================"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# -----------------------------------------------------------------------------
# Docker Commands
# -----------------------------------------------------------------------------

build: ## Build all Docker containers
	docker compose build

up: ## Start all services in detached mode
	docker compose up -d

down: ## Stop all services
	docker compose down

restart: ## Restart all services
	docker compose down && docker compose up -d

logs: ## Tail logs from all services
	docker compose logs -f

logs-web: ## Tail logs from the web service
	docker compose logs -f web

logs-celery: ## Tail logs from the celery worker
	docker compose logs -f celery_worker

logs-beat: ## Tail logs from the celery beat scheduler
	docker compose logs -f celery_beat

ps: ## Show running containers
	docker compose ps

# -----------------------------------------------------------------------------
# Django Commands
# -----------------------------------------------------------------------------

shell: ## Open Django shell in the web container
	docker compose exec web python manage.py shell_plus

shell-bash: ## Open a bash shell in the web container
	docker compose exec web bash

migrate: ## Run database migrations
	docker compose exec web python manage.py migrate

makemigrations: ## Create new database migrations
	docker compose exec web python manage.py makemigrations

superuser: ## Create a Django superuser
	docker compose exec web python manage.py createsuperuser

collectstatic: ## Collect static files
	docker compose exec web python manage.py collectstatic --noinput

seed: ## Seed the database with sample data
	docker compose exec web python manage.py seed_data

# -----------------------------------------------------------------------------
# Testing & Quality
# -----------------------------------------------------------------------------

test: ## Run the test suite
	docker compose exec web python -m pytest --cov=apps --cov-report=term-missing -v

test-fast: ## Run tests without coverage
	docker compose exec web python -m pytest -x -v

lint: ## Run linting checks (flake8 + isort check + black check)
	docker compose exec web flake8 apps/ config/ utils/
	docker compose exec web isort --check-only apps/ config/ utils/
	docker compose exec web black --check apps/ config/ utils/

format: ## Auto-format code (isort + black)
	docker compose exec web isort apps/ config/ utils/
	docker compose exec web black apps/ config/ utils/

typecheck: ## Run mypy type checking
	docker compose exec web mypy apps/ config/ utils/

# -----------------------------------------------------------------------------
# Database
# -----------------------------------------------------------------------------

db-shell: ## Open PostgreSQL shell
	docker compose exec db psql -U $${POSTGRES_USER:-megastore_user} -d $${POSTGRES_DB:-megastore}

db-reset: ## Reset the database (WARNING: destroys all data)
	docker compose exec web python manage.py flush --no-input
	docker compose exec web python manage.py migrate

backup: ## Create a database backup
	@mkdir -p backups
	docker compose exec db pg_dump -U $${POSTGRES_USER:-megastore_user} \
		$${POSTGRES_DB:-megastore} > backups/backup_$$(date +%Y%m%d_%H%M%S).sql
	@echo "Backup created in backups/"

restore: ## Restore database from backup (usage: make restore FILE=backups/backup.sql)
	docker compose exec -T db psql -U $${POSTGRES_USER:-megastore_user} \
		$${POSTGRES_DB:-megastore} < $(FILE)

# -----------------------------------------------------------------------------
# Redis
# -----------------------------------------------------------------------------

redis-cli: ## Open Redis CLI
	docker compose exec redis redis-cli

redis-flush: ## Flush all Redis data
	docker compose exec redis redis-cli FLUSHALL

# -----------------------------------------------------------------------------
# Celery
# -----------------------------------------------------------------------------

celery: ## Start a Celery worker (for local development)
	cd backend && celery -A config worker -l info --concurrency=2

beat: ## Start the Celery beat scheduler (for local development)
	cd backend && celery -A config beat -l info

celery-inspect: ## Inspect active Celery tasks
	docker compose exec celery_worker celery -A config inspect active

# -----------------------------------------------------------------------------
# Frontend
# -----------------------------------------------------------------------------

frontend-install: ## Install frontend dependencies
	cd frontend && npm install

frontend-dev: ## Start frontend development server
	cd frontend && npm start

frontend-build: ## Build frontend for production
	cd frontend && npm run build

frontend-lint: ## Lint frontend code
	cd frontend && npm run lint

# -----------------------------------------------------------------------------
# Elasticsearch
# -----------------------------------------------------------------------------

es-reindex: ## Rebuild Elasticsearch indexes
	docker compose exec web python manage.py search_index --rebuild -f

es-health: ## Check Elasticsearch cluster health
	curl -s http://localhost:9200/_cluster/health | python -m json.tool

# -----------------------------------------------------------------------------
# Cleanup
# -----------------------------------------------------------------------------

clean: ## Remove all containers, volumes, and build cache
	docker compose down -v --remove-orphans
	docker system prune -f

clean-pyc: ## Remove Python bytecode files
	find backend -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find backend -name "*.pyc" -delete 2>/dev/null || true

clean-all: clean clean-pyc ## Full cleanup including volumes and bytecode
	rm -rf frontend/node_modules frontend/build
	rm -rf backend/staticfiles backend/media
