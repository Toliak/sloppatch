.PHONY: test mypy ruff ruff-format docker-dev-up docker-dev-build .venv

.venv:
	python3 -m venv .venv
	.venv/bin/pip install -e .[dev]

COV_ENABLED = $(and $(COV),$(filter-out 0,$(COV)))
COV_ARGS = $(if $(filter 1,$(COV)),--cov-report html:.pytest_htmlcov --cov=src,)

test:
	pytest $(COV_ARGS) tests

test-e2e:
	bash tests/test_sloppatch_cli/e2e.sh

mypy:
	mypy . --check-untyped-defs

ruff:
	ruff check .

ruff-format:
	ruff format .
