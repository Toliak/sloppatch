IMAGE_NAME := sloppatch_build
PODMAN_BIN := podman
PODMAN_JOBS := $(shell nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 1)

PROJECT_DIR := ..

USERNS_ARGS = \
  --userns-uid-map=0:0:1 \
  --userns-uid-map=1:1:1999 \
  --userns-uid-map=65534:2000:2

USERNS_RUN_ARGS = \
  --uidmap=0:0:1 \
  --uidmap=1:1:1999 \
  --uidmap=65534:2000:2

BUILD_SHARED_CMD := $(PODMAN_BIN) build \
					$(USERNS_ARGS) \
					--jobs=$(PODMAN_JOBS) \
					--file ./build.Containerfile \
					$(PROJECT_DIR)

BUILD_RELEASE_CMD :=    $(BUILD_SHARED_CMD) \
						--target target \
						--tag "$(IMAGE_NAME)_target"

.PHONY: build-preparer build-release

build-preparer:
	$(BUILD_SHARED_CMD) \
		--target preparer \
		--tag "$(IMAGE_NAME)_preparer"

build-release:
	$(BUILD_RELEASE_CMD)

ci:	build-preparer
	$(PODMAN_BIN) run --rm \
		$(USERNS_RUN_ARGS) \
		"$(IMAGE_NAME)_preparer" \
		sh -c "cd /opt/workdir && . ./.venv/bin/activate && make $(CMD)"

RELEASE_RAW_DIR := $(PROJECT_DIR)/dist/release-raw
RELEASE_DIR := $(PROJECT_DIR)/dist/release

release:
	mkdir -p $(RELEASE_RAW_DIR) $(RELEASE_DIR)
	$(BUILD_RELEASE_CMD) \
		--output type=local,dest=$(RELEASE_RAW_DIR)
	find $(RELEASE_RAW_DIR)/opt/sloppatch/dist-only -type f -name "sloppatch*.whl" -exec cp {} $(RELEASE_DIR)/. \;
	cp $(RELEASE_RAW_DIR)/opt/sloppatch/bin/sloppatch $(RELEASE_DIR)/sloppatch-linux-libc-amd64
	ls -R $(RELEASE_DIR)
