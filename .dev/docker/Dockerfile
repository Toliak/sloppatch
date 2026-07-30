ARG BASE_IMAGE="nothing.local/check_your_env"
FROM ${BASE_IMAGE} AS vscode-server

ENV DEBIAN_FRONTEND=noninteractive

# Enable apt-get cache, see https://stackoverflow.com/a/79936062/14142236
RUN [ -f "/etc/apt/apt.conf.d/docker-clean" ] && \
    mv /etc/apt/apt.conf.d/docker-clean /etc/apt/apt.conf.d/docker-clean.disabled || \
    true

# TODO: check
RUN --mount=type=cache,sharing=private,target=/var/cache/apt \
\
    apt-get update -y --allow-releaseinfo-change && \
    apt-get install -y --no-install-recommends \
        curl \
        ca-certificates \
        bash

RUN U_NAME=$(uname -m) && \
    if [ "${U_NAME}" = "aarch64" ]; then \
        ARCH="arm64"; \
    elif [ "${U_NAME}" = "x86_64" ]; then \
        ARCH="x64"; \
    elif [ "${U_NAME}" = "armv7l" ]; then \
        ARCH="armhf"; \
    else \
        echo "Unable to detect ARCH=$ARCH" && \
        exit 1; \
    fi && \
    echo "$ARCH" > /tmp/arch

ARG VSCODE_VERSION

COPY ./overlay/vscode/cli.sh ./overlay/vscode/server.sh     /opt/vscode/
RUN if [ -n "${VSCODE_VERSION}" ]; then \
        bash /opt/vscode/cli.sh "${VSCODE_VERSION}" "$(cat /tmp/arch)" && \
        bash /opt/vscode/server.sh "${VSCODE_VERSION}" "$(cat /tmp/arch)"; \
    fi

COPY ./overlay/vscode/extensions.sh ./overlay/vscode/extensions.list     /opt/vscode/

RUN if [ -n "${VSCODE_VERSION}" ]; then \
        bash /opt/vscode/extensions.sh "${VSCODE_VERSION}" /opt/vscode/extensions.list; \
    fi

# ----------------------------------------

# See https://github.com/Toliak/MCE2
FROM ${BASE_IMAGE} AS mce-configs

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
        ca-certificates

ARG MCE_VERSION

RUN if [ -n "${MCE_VERSION}" ]; then \
        curl -L "https://github.com/Toliak/MCE2/releases/download/v${MCE_VERSION}/mce-linux-amd64" --output /tmp/mce && \
        chmod +x /tmp/mce && \
        mkdir -p /opt/mce-install && \
        /tmp/mce -ALL -y -no-ui --home-dir=/etc/skel; \
    fi

# ----------------------------------------

FROM ${BASE_IMAGE} AS target

ENV DEBIAN_FRONTEND=noninteractive

# Enable apt-get cache, see https://stackoverflow.com/a/79936062/14142236
RUN [ -f "/etc/apt/apt.conf.d/docker-clean" ] && \
    mv /etc/apt/apt.conf.d/docker-clean /etc/apt/apt.conf.d/docker-clean.disabled || \
    true

RUN --mount=type=cache,sharing=private,target=/var/cache/apt \
\
    apt-get update -y --allow-releaseinfo-change && \
    apt-get install -y --no-install-recommends \
        openssh-server \
        sudo \
        curl \
        vim \
        git \
        golang \
        python3 \
        python3-venv \
        python3-pip \
        less \
        make \
        locales \
        curl \
        jq \
        zsh \
        tmux \
        git \
        procps

RUN sed -i -e 's/# en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen && \
    locale-gen

COPY --from=mce-configs /etc/skel /etc/skel

ARG USERNAME
ARG PASSWORD
ARG USER_UID
ARG USER_GID

# WARN: no sudo, `echo "$USERNAME ALL=(ALL) ALL" > "/etc/sudoers.d/$USERNAME" && \`
RUN CURRENT_SHELL=$(getent passwd $(whoami) | cut -d: -f7) && \
    if [ -f /etc/skel/.zshrc ]; then CURRENT_SHELL=$(which zsh); fi; \
    groupadd --gid "${USER_GID}" "${USERNAME}" && \
    useradd --uid "${USER_UID}" --gid "${USER_GID}" -m "${USERNAME}" -s "$CURRENT_SHELL" && \
    echo "${USERNAME}:${PASSWORD}" | chpasswd

RUN mkdir -p /run/sshd && \
    ssh-keygen -A

COPY --from=vscode-server /root/.vscode-server /home/"${USERNAME}"/.vscode-server
RUN chown "${USER_UID}:${USER_GID}" -R /home/"${USERNAME}"/.vscode-server

# Initialize the shell (if base_image has something to initialize)
USER "${USER_NAME}"
RUN CURRENT_SHELL=$(getent passwd $(whoami) | cut -d: -f7) && \
    "$CURRENT_SHELL" -i -c 'echo'

# Expose SSH port
EXPOSE 22

USER root
CMD ["/usr/sbin/sshd", "-De", "-o", "LogLevel=VERBOSE"]
