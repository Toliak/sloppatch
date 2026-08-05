include .env

# Check .env
REQUIRED_VARS := BASE_IMAGE USER_NAME USER_PASS SSH_ADDR PROJECT_NAME
$(foreach var,$(REQUIRED_VARS),$(if $(value $(var)),,$(error $(var) is not set. Please set it in .env or export it)))

USER_UID := $(shell id -u)
USER_GID := $(shell id -g)

# For docker/podman build
BUILD_ARGS := \
	--build-arg BASE_IMAGE="$(BASE_IMAGE)" \
	--build-arg USER_NAME="$(USER_NAME)" \
	--build-arg USER_PASS="$(USER_PASS)" \
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

SHARED_RUN_OPTS := 		--rm \
						-it \
						--security-opt label=disable \
						--device /dev/fuse \
						-e TERM=xterm-256color \
						-p "$(SSH_ADDR):22" \
						-v "$$PWD/../..:/opt/workdir" \
						-v "$$HOME/.local/share/containers/storage:/var/lib/shared" \
						--name "$(CONTAINER_NAME)"

SHARED_BUILD_OPTS :=    $(BUILD_ARGS) \
						-t "$(IMAGE_NAME)" \
						-f ./Dockerfile

# WARN: do not unify uidmap and gidmap, because UID and GID may differ
PODMAN_RUN_MAP :=   --uidmap $(USER_UID):0:1 \
					--uidmap 0:1:$(shell expr $(USER_UID)) \
					--uidmap 100000:$(shell expr $(USER_UID) + 1):$(shell expr 65536 - $(USER_UID) - 2 - 1) \
					--uidmap 65534:65534:2 \
					\
					--gidmap $(USER_GID):0:1 \
					--gidmap 0:1:$(shell expr $(USER_GID)) \
					--gidmap 100000:$(shell expr $(USER_GID) + 1):$(shell expr 65536 - $(USER_GID) - 2 - 1) \
					--gidmap 65534:65534:2

.PHONY: docker-up docker-stop docker-build podman-up podman-stop podman-build

# ----------------------------------------

all: podman-up

.env:
	@test -f .env || (echo "Not found, '.env' file. Copy default")
	cp .env.template .env

# Or
# @test -f .env || (echo "ERROR: $@ file is missing. Manual configuration required" && exit 1)

# ----------------------------------------

docker-up: .env docker-build
	@echo "Run (docker) dev container with:"
	@echo "  SSH_ADDR: $(SSH_ADDR)"

	$(DOCKER_ENV) "$(DOCKER_BIN)" \
				run \
				$(SHARED_RUN_OPTS) \
				"$(IMAGE_NAME)"

docker-stop: .env
	@echo "Stop (docker) dev container"
	$(DOCKER_ENV) "$(DOCKER_BIN)" \
				stop \
				$(CONTAINER_NAME)

docker-build: .env
	@echo "Building (docker) with:"
	@echo "  BASE_IMAGE: $(BASE_IMAGE)"
	@echo "  USER_NAME:   $(USER_NAME)"
	@echo "  USER_UID:   $(USER_UID)"
	@echo "  USER_GID:   $(USER_GID)"

	$(DOCKER_ENV) "$(DOCKER_BIN)" \
				build . \
				$(SHARED_BUILD_OPTS)

# ----------------------------------------

podman-up: .env podman-build
	@echo "Run (podman) dev container with:"
	@echo "  SSH_ADDR: $(SSH_ADDR)"

	$(PODMAN_ENV) "$(PODMAN_BIN)" \
				run \
				$(SHARED_RUN_OPTS) \
				$(PODMAN_RUN_MAP)\
				"$(IMAGE_NAME)"

podman-stop: .env
	@echo "Stop (podman) dev container"
	$(PODMAN_ENV) "$(PODMAN_BIN)" \
				stop \
				$(CONTAINER_NAME)

podman-build: .env
	@echo "Building (podman) with:"
	@echo "  BASE_IMAGE: $(BASE_IMAGE)"
	@echo "  USER_NAME:   $(USER_NAME)"
	@echo "  USER_UID:   $(USER_UID)"
	@echo "  USER_GID:   $(USER_GID)"

	$(PODMAN_ENV) "$(PODMAN_BIN)" \
				build . \
				--jobs="$(PODMAN_JOBS)" \
				$(SHARED_BUILD_OPTS)
