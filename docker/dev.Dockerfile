FROM debian:trixie-20260610

# Avoid interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Enable apt-get cache, see https://stackoverflow.com/a/79936062/14142236
RUN mv /etc/apt/apt.conf.d/docker-clean /etc/apt/apt.conf.d/docker-clean.disabled

RUN --mount=type=cache,target=/var/cache/apt \
\
    apt-get update -y --allow-releaseinfo-change && \
    apt-get install -y \
        openssh-server \
        sudo \
        curl \
        vim \
        git \
        golang \
        python3 \
        python3-venv \
        less \
        golang \
        make \
        locales-all \
        curl \
        jq

ARG USERNAME=devuser
ARG PASSWORD=123456
ARG USER_UID=1000
ARG USER_GID=$USER_UID

RUN groupadd --gid "$USER_GID" "$USERNAME" && \
    useradd --uid "$USER_UID" --gid "$USER_GID" -m "$USERNAME" && \
    echo "$USERNAME ALL=(ALL) ALL" > "/etc/sudoers.d/$USERNAME" && \
    echo "$USERNAME:$PASSWORD" | chpasswd

RUN mkdir -p /run/sshd && \
    ssh-keygen -A

# zsh, git, tmux, vim, ...
RUN mkdir -p /usr/local/bin && \
    curl -L https://github.com/Toliak/MCE2/releases/download/v1.0.1/mce-linux-amd64 --output /usr/local/bin/mce && \
    chmod +x /usr/local/bin/mce

RUN /usr/local/bin/mce -y -ALL -no-ui && \
    rm -rf /tmp/mce2-*

RUN su devuser -c '/usr/local/bin/mce -y -ALL -repo-update-enable=0 -repo-packages-enable=0 -no-ui' && \
    rm -rf /tmp/mce2-*

ARG VSCODE_VERSION=2ccd690cbff1569e4a83d7c43d45101f817401dc

COPY overlay/extensions.list "/home/$USERNAME/"
COPY overlay/install-vscode-server-with-extensions.sh "/home/$USERNAME/"

USER "$USERNAME"
RUN bash "/home/$USERNAME/install-vscode-server-with-extensions.sh" "$VSCODE_VERSION" "/home/$USERNAME/extensions.list"

# Expose SSH port
EXPOSE 22

USER root
CMD ["/usr/sbin/sshd", "-De", "-o", "LogLevel=VERBOSE"]
