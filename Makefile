.PHONY: format check lint test coverage before-commit clean install-deps install-dev setup-dev

PYTHON = python
PYTEST = pytest
BLACK = black
RUFF = ruff
COVERAGE = coverage
SRC_DIR = lambdas
TEST_DIR = tests
PIP = pip

format:
	$(BLACK) $(SRC_DIR) $(TEST_DIR)
	$(RUFF) check --fix $(SRC_DIR) $(TEST_DIR)

check:
	$(BLACK) --check $(SRC_DIR) $(TEST_DIR)
	$(RUFF) check $(SRC_DIR) $(TEST_DIR)

lint:
	$(RUFF) check $(SRC_DIR) $(TEST_DIR)

lint-fix:
	$(RUFF) check --fix $(SRC_DIR) $(TEST_DIR)

test:
	$(PYTEST) -xvs

coverage:
	$(PYTEST) --cov=$(SRC_DIR) --cov-report=term --cov-report=html

before-commit: format lint test

testchanged:
	$(PYTEST) -xvs `git diff --name-only | grep -E 'test_.*\.py$$' | xargs`

clean:
	rm -rf __pycache__
	rm -rf .pytest_cache
	rm -rf .coverage
	rm -rf htmlcov
	rm -rf .ruff_cache
	rm -rf dist
	rm -rf build
	rm -rf *.egg-info

ci: check test coverage

install-deps:
	$(PIP) install -r requirements.txt

install-dev:
	$(PIP) install -r requirements-dev.txt

setup-dev: install-dev

install-shared:
	@echo "Instalando shared-libs..."
	cd shared-libs && $(PIP) install -e .
	python -c "from fruit_detection_shared.domain.entities import CombinedResult; print('✅ Funcionou!')"

build:
	@echo "Construindo todos os pacotes..."
	@for lambda_dir in lambda-*; do \
		if [ -d "$$lambda_dir" ]; then \
			echo "Construindo $$lambda_dir..."; \
			$(MAKE) build-lambda LAMBDA=$$(echo $$lambda_dir | sed 's/lambda-//'); \
		fi \
	done

build-lambda:
	@if [ -z "$(LAMBDA)" ]; then \
		echo "Use: make build-lambda LAMBDA=nome-da-lambda"; \
		exit 1; \
	fi
	@echo "Construindo lambda-$(LAMBDA)..."
	@cd lambda-$(LAMBDA) && \
		mkdir -p deployment/src && \
		cp -r src/* deployment/src/ && \
		$(PIP) install -r requirements.txt -t deployment/ && \
		cd ../shared-libs && $(PIP) install . -t ../lambda-$(LAMBDA)/deployment/ && \
		cd ../lambda-$(LAMBDA)/deployment && \
		zip -r ../lambda-$(LAMBDA).zip . && \
		cd .. && \
		echo "Pacote criado: lambda-$(LAMBDA).zip ($(shell du -h lambda-$(LAMBDA)/lambda-$(LAMBDA).zip 2>/dev/null | cut -f1))"