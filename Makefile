# =====================================
# 🌱 Project & Environment Configuration
# =====================================
# Read from pyproject.toml using grep (works on all platforms)
PROJECT_NAME = $(shell python3 -c "import re; print(re.search('name = \"(.*)\"', open('pyproject.toml').read()).group(1))")
VERSION = $(shell python3 -c "import re; print(re.search('version = \"(.*)\"', open('pyproject.toml').read()).group(1))")
-include .env
export

# Docker configuration
DOCKER_IMAGE = $(DOCKER_USERNAME)/$(PROJECT_NAME)
CONTAINER_NAME = $(PROJECT_NAME)-app
APP_PORT = 7860

# =====================================
# 🐋 Docker Commands (Development)
# =====================================
dev: ## Build and run development container with hot reload
	docker build --no-cache -t $(DOCKER_IMAGE):dev .
	docker run -d \
		--name $(CONTAINER_NAME)-dev \
		-p $(APP_PORT):$(APP_PORT) \
		-v $(PWD)/src:/app/src \
		-v $(PWD)/logs:/app/logs \
		-v $(PWD)/.env:/app/.env:ro \
		$(DOCKER_IMAGE):dev
	@echo "🎯 PRISM running at http://localhost:$(APP_PORT)"
	@echo "📊 Dashboard available"
	@echo "🤖 AI agents ready"

ls: ## List files inside the container
	docker run --rm $(DOCKER_IMAGE):dev ls -la /app

stop: ## Stop dev container
	docker stop $(CONTAINER_NAME)-dev || true

clean: stop ## Stop and remove dev container and image
	docker rm $(CONTAINER_NAME)-dev || true
	docker rmi $(DOCKER_IMAGE):dev || true

restart: clean dev ## Restart dev container

# =======================
# 🪝 Hooks
# =======================

hooks:	## Install pre-commit on local machine
	pip install pre-commit && pre-commit install && pre-commit install --hook-type commit-msg

# Pre-commit ensures code quality before commits.
# Installing globally lets you use it across all projects.
# Check if pre-commit command exists : pre-commit --version


# =====================================
# ✨ Code Quality
# =====================================

lint:	## Run code linting and formatting
	uvx ruff check .
	uvx ruff format .

fix:	## Fix code issues and format
	uvx ruff check --fix .
	uvx ruff format .


# =======================
# 🔍 Security Scanning
# =======================
security-scan:		## Run all security checks
	gitleaks detect --source . --verbose && \
	uv export --no-dev -o requirements.txt && \
	uvx pip-audit -r requirements.txt && \
	python3 -c "import os; os.remove('requirements.txt') if os.path.exists('requirements.txt') else None" && \
	uvx bandit -r . --exclude ./.venv,./node_modules,./.git


# =======================
# 🧪 Testing Commands
# =======================

test: ## Run all tests in the tests/ directory
	uv run --isolated --extra dev pytest tests/

test-file: ## Run specific test file
	uv run --isolated --extra dev pytest tests/test_crew.py

test-func: ## Run specific test function by name
	uv run --isolated --extra dev pytest -k test_crew_initialization

test-cov: ## Run tests with coverage
	uv run --isolated --extra dev --with pytest-cov pytest --cov=src/prism tests/

test-cov-html: ## Run tests with coverage and generate HTML report
	uv run --isolated --extra dev --with pytest-cov pytest --cov=src/prism --cov-report=html tests/

open-cov: ## Open HTML coverage report in browser
	@echo "To open the HTML coverage report, run:"
	@echo "  start htmlcov\\index.html        (Windows)"
	@echo "  open htmlcov/index.html          (macOS)"
	@echo "  xdg-open htmlcov/index.html      (Linux)"


# =====================================
# 📚 Documentation & Help
# =====================================

help: ## Show this help message
	@echo "Available commands:"
	@echo ""
	@python3 -c "import re; lines=open('Makefile', encoding='utf-8').readlines(); targets=[re.match(r'^([a-zA-Z_-]+):.*?## (.*)$$',l) for l in lines]; [print(f'  make {m.group(1):<20} {m.group(2)}') for m in targets if m]"


# =======================
# 🎯 PHONY Targets
# =======================

# Auto-generate PHONY targets (cross-platform)
.PHONY: $(shell python3 -c "import re; print(' '.join(re.findall(r'^([a-zA-Z_-]+):\s*.*?##', open('Makefile', encoding='utf-8').read(), re.MULTILINE)))")

# Test the PHONY generation
# test-phony:
# 	@echo "$(shell python3 -c "import re; print(' '.join(sorted(set(re.findall(r'^([a-zA-Z0-9_-]+):', open('Makefile', encoding='utf-8').read(), re.MULTILINE)))))")"
