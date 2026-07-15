.PHONY: setup load-data dbt-run test lint run-api docker-up docker-down eval clean help

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

setup: ## Install dependencies and start services
	python3 -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -e ".[dev]"
	.venv/bin/pre-commit install
	docker-compose up -d postgres redis mlflow
	@echo "Waiting for PostgreSQL..."
	@sleep 5
	@echo "Setup complete! Activate venv: source .venv/bin/activate"

load-data: ## Download and load data into PostgreSQL
	.venv/bin/python scripts/load_data.py

dbt-run: ## Run dbt models and tests
	dbt run --profiles-dir .
	dbt test --profiles-dir .

test: ## Run all tests with coverage
	pytest src/ tests/ -v --cov=src --cov-report=html --cov-report=term-missing

test-fast: ## Run tests without coverage (faster)
	pytest src/ tests/ -v --no-cov

lint: ## Run all linters
	black src/ tests/ scripts/
	isort src/ tests/ scripts/
	ruff check src/ tests/ scripts/ --fix
	mypy src/

lint-check: ## Check linting without fixing
	black --check src/ tests/ scripts/
	isort --check src/ tests/ scripts/
	ruff check src/ tests/ scripts/
	mypy src/

run-api: ## Start FastAPI development server
	uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

docker-up: ## Start all Docker services
	docker-compose up -d

docker-down: ## Stop all Docker services
	docker-compose down

docker-logs: ## Show Docker logs
	docker-compose logs -f

eval: ## Run model evaluation
	.venv/bin/python src/ml/evaluate.py --output results/

db-revision: ## Create a new Alembic migration (usage: make db-revision m="add users table")
	.venv/bin/alembic revision --autogenerate -m "$(m)"

db-upgrade: ## Apply migrations up to head
	.venv/bin/alembic upgrade head

db-downgrade: ## Roll back one migration
	.venv/bin/alembic downgrade -1

clean: ## Remove all generated files
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache htmlcov .coverage mlruns target/ .mypy_cache .ruff_cache
	@echo "Cleaned!"
