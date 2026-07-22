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

# -------

DOCKER_ENV := BUILDKIT_PROGRESS=plain
DOCKER_DIR := docker
DOCKER_COMPOSE_FILE := $(DOCKER_DIR)/dev.docker-compose.yaml

$(DOCKER_DIR)/.env:
	@test -f docker/.env || (echo "Error: File 'docker/.env' does not exist" && exit 1)

docker-dev-up: $(DOCKER_DIR)/.env
	$(DOCKER_ENV) docker compose -f $(DOCKER_COMPOSE_FILE) \
					   up \
					   --build \
					   --abort-on-container-failure \
					   --force-recreate

docker-dev-build: $(DOCKER_DIR)/.env
	$(DOCKER_ENV) docker compose -f $(DOCKER_COMPOSE_FILE) \
					   build