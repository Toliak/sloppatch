.PHONY: .env

DOCKER_ENV := BUILDKIT_PROGRESS=plain
DOCKER_DIR := .
DOCKER_COMPOSE_FILE := $(DOCKER_DIR)/docker-compose.yaml

$(DOCKER_DIR)/.env:
	@test -f $(DOCKER_DIR)/.env || (echo "Error: File '$(DOCKER_DIR)/.env' does not exist" && exit 1)

docker-up: $(DOCKER_DIR)/.env
	$(DOCKER_ENV) docker compose -f $(DOCKER_COMPOSE_FILE) \
					   up \
					   --build \
					   --abort-on-container-failure \
					   --force-recreate

docker-build: $(DOCKER_DIR)/.env
	$(DOCKER_ENV) docker compose -f $(DOCKER_COMPOSE_FILE) \
					   build
