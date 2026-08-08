IMAGE_NAME := sloppatch_build
PODMAN_BIN := podman
PODMAN_JOBS := $(shell nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 1)

PROJECT_DIR := ..

# buildah's `userns-uid-map` does not recognize /etc/subuid and /etc/subgid uid mapping,
# so it does not automatically split the uids (if I specify 1:1:10000, it will try to allocate
# 10000 contiguous uids even if there are multiple entries in /etc/subuid).
# Therefore, only necessary UIDs are specified here.
# This looks like an issue, but I am a bit too busy to reproduce it on the latest podman and report it.
# https://chatgpt.com/s/t_6a771f6240648191abc735edfff8b467
USERNS_ARGS = \
  --userns-uid-map=0:0:1 \
  --userns-uid-map=1:1:50 \
  --userns-uid-map=1000:51:1 \
  --userns-uid-map=65534:52:2

USERNS_RUN_ARGS = \
  --uidmap=0:0:1001 \
  --uidmap=65534:1001:1

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
