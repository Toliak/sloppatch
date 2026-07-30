ARG BASE_IMAGE="debian:trixie-20260610"
FROM ${BASE_IMAGE} AS builder

ENV DEBIAN_FRONTEND=noninteractive

# Enable apt-get cache, see https://stackoverflow.com/a/79936062/14142236
RUN [ -f "/etc/apt/apt.conf.d/docker-clean" ] && \
    mv /etc/apt/apt.conf.d/docker-clean /etc/apt/apt.conf.d/docker-clean.disabled || \
    true

RUN --mount=type=cache,sharing=private,target=/var/cache/apt \
\
    apt-get update -y --allow-releaseinfo-change && \
    apt-get install -y --no-install-recommends \
        curl \
        ca-certificates \
        bash \
        python3 \
        python3-venv \
        python3-pip \
        make \
        binutils \
        libpython3-dev

COPY . /opt/workdir

RUN cd /opt/workdir && \
    make .venv

RUN cd /opt/workdir && \
    . ./.venv/bin/activate && \
    make build-whl-deps

RUN cd /opt/workdir && \
    . ./.venv/bin/activate && \
    make build-pyinstaller

RUN mkdir /opt/workdir/dist-only/ && \
    cp /opt/workdir/dist/sloppatch*.whl /opt/workdir/dist-only/

# ----------------------------------------
FROM scratch AS target

COPY --from=builder /opt/workdir/bin /opt/sloppatch/bin
COPY --from=builder /opt/workdir/dist /opt/sloppatch/dist-with-deps
COPY --from=builder /opt/workdir/dist-only /opt/sloppatch/dist-only
