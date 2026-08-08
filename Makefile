.PHONY: test test-e2e mypy ruff ruff-format build-whl  build-whl-deps  build-pyinstaller

PYTHON_BIN := python3

# ---------------------------

all: prepare-dev

.venv:
	$(PYTHON_BIN) -m venv .venv

prepare-dev: .venv
	.venv/bin/pip install -e .[dev]

# ---------------------------

COV_ENABLED = $(and $(COV),$(filter-out 0,$(COV)))
COV_ARGS = $(if $(filter 1,$(COV_ENABLED)),--cov-report html:.pytest_htmlcov --cov=src,)

test:
	pytest $(COV_ARGS) tests

test-e2e:
	bash tests/test_sloppatch_cli/e2e.sh

mypy:
	mypy .

ruff:
	ruff check .

ruff-format:
	ruff format .

build-whl:
	python -m build

build-whl-deps:
	pip wheel . --wheel-dir=dist

build-pyinstaller:
	pyinstaller --onefile $$(which sloppatch) --distpath ./bin
