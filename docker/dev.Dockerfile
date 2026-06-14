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
    make

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
RUN git clone https://github.com/Toliak/MCE2 /tmp/mce2 && \
    cd /tmp/mce2/configapp && \
    make build && \
    mkdir -p "/usr/local/bin" && \
    mv /tmp/mce2/configapp/bin/mce "/usr/local/bin/mce" && \
    rm -rf /tmp/mce2

RUN /usr/local/bin/mce -y -ALL -no-ui && \
    rm -rf /tmp/mce2-*
    # su devuser -c '/usr/local/bin/mce -y -ALL -repo-update-enable=0 -repo-packages-enable=0 -no-ui' && \
    # rm -rf /tmp/mce2-*

# Expose SSH port
EXPOSE 22

CMD ["/usr/sbin/sshd", "-De", "-o", "LogLevel=VERBOSE"]
