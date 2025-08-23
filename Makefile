.PHONY: format check lint test coverage before-commit clean install-deps install-dev setup-dev

PYTHON = python
PYTEST = pytest
BLACK = black
RUFF = ruff
ISORT = isort
COVERAGE = coverage
SRC_DIR = src
TEST_DIR = tests
PIP = pip

format:
	$(BLACK) $(SRC_DIR) $(TEST_DIR)
	$(ISORT) $(SRC_DIR) $(TEST_DIR)

check:
	$(BLACK) --check $(SRC_DIR) $(TEST_DIR)
	$(ISORT) --check $(SRC_DIR) $(TEST_DIR)
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
