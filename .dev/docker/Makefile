include .env

# Check .env
REQUIRED_VARS := BASE_IMAGE USERNAME PASSWORD USER_UID USER_GID SSH_ADDR
$(foreach var,$(REQUIRED_VARS),$(if $(value $(var)),,$(error $(var) is not set. Please set it in .env or export it)))

USER_UID_PLUS_1 := $(shell expr $(USER_UID) + 1)
USER_UID_MINUS_1 := $(shell expr $(USER_UID) - 1)
USER_GID_PLUS_1 := $(shell expr $(USER_GID) + 1)
USER_GID_MINUS_1 := $(shell expr $(USER_GID) - 1)

# For docker/podman build
BUILD_ARGS := \
	--build-arg BASE_IMAGE="$(BASE_IMAGE)" \
	--build-arg USERNAME="$(USERNAME)" \
	--build-arg PASSWORD="$(PASSWORD)" \
	--build-arg USER_UID="$(USER_UID)" \
	--build-arg USER_GID="$(USER_GID)" \
	--build-arg SSH_PUB_KEY="$(SSH_PUB_KEY)" \
	--build-arg MCE_VERSION="$(MCE_VERSION)" \
	--build-arg VSCODE_VERSION="$(VSCODE_VERSION)"

DOCKER_BIN := docker
DOCKER_ENV := BUILDKIT_PROGRESS=plain

PODMAN_BIN := podman
PODMAN_JOBS := $(shell nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 1)
PODMAN_ENV :=

IMAGE_NAME := $(PROJECT_NAME)_dev
CONTAINER_NAME := $(PROJECT_NAME)_dev-run

SHARED_RUN_OPTS :=    --rm \
						-it \
						--security-opt label=disable \
						--device /dev/fuse \
						-e TERM=xterm-256color \
						-p $(SSH_ADDR):22 \
						--name "$(CONTAINER_NAME)"

SHARED_BUILD_OPTS :=    $(BUILD_ARGS) \
						-t "$(IMAGE_NAME)" \
						-f ./Dockerfile

.PHONY: docker-up docker-stop docker-build podman-up podman-stop podman-build


# ----------------------------------------

all: podman-up

.env:
	@test -f .env || (echo "Error: File '.env' does not exist" && exit 1)

# ----------------------------------------

docker-up: .env docker-build
	@echo "Run (docker) dev container with:"
	@echo "  SSH_ADDR: $(SSH_ADDR)"

	$(DOCKER_ENV) "$(DOCKER_BIN)" \
				run \
				$(SHARED_RUN_OPTS) \
				-v ../..:/opt/workdir \
				"$(IMAGE_NAME)"

docker-stop: .env
	@echo "Stop (docker) dev container"
	$(DOCKER_ENV) "$(DOCKER_BIN)" \
				stop \
				$(CONTAINER_NAME)

docker-build: .env
	@echo "Building (docker) with:"
	@echo "  BASE_IMAGE: $(BASE_IMAGE)"
	@echo "  USERNAME:   $(USERNAME)"
	@echo "  USER_UID:   $(USER_UID)"
	@echo "  USER_GID:   $(USER_GID)"

	$(DOCKER_ENV) "$(DOCKER_BIN)" \
				build . \
				$(SHARED_BUILD_OPTS)

# ----------------------------------------

podman-up: .env podman-build
	@echo "Run (podman) dev container with:"
	@echo "  SSH_ADDR: $(SSH_ADDR)"

# 	--userns=keep-id \

	$(PODMAN_ENV) "$(PODMAN_BIN)" \
				run \
				$(SHARED_RUN_OPTS) \
				-v ../..:/opt/workdir \
				--uidmap $(USER_UID):0:1 \
				--uidmap 0:1:$(USER_UID_MINUS_1) \
				--uidmap 100000:$(USER_UID_PLUS_1):32768 \
				--uidmap 65534:65534:1 \
				--gidmap $(USER_GID):0:1 \
				--gidmap 0:1:$(USER_GID_MINUS_1) \
				--gidmap 100000:$(USER_GID_PLUS_1):32768 \
				--gidmap 65534:65534:1 \
				"$(IMAGE_NAME)"

podman-stop: .env
	@echo "Stop (podman) dev container"
	$(PODMAN_ENV) "$(PODMAN_BIN)" \
				stop \
				$(CONTAINER_NAME)

podman-build: .env
	@echo "Building (podman) with:"
	@echo "  BASE_IMAGE: $(BASE_IMAGE)"
	@echo "  USERNAME:   $(USERNAME)"
	@echo "  USER_UID:   $(USER_UID)"
	@echo "  USER_GID:   $(USER_GID)"

	$(PODMAN_ENV) "$(PODMAN_BIN)" \
				build . \
				--jobs="$(PODMAN_JOBS)" \
				$(SHARED_BUILD_OPTS)
