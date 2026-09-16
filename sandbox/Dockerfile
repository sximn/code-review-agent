FROM ubuntu:24.04

# dont open dialogs, accept defaults automatically, etc.
ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash ca-certificates coreutils curl git jq nodejs npm \
    python3 python3-pip python3-venv ripgrep \
    && rm -rf /var/lib/apt/lists/*

# ubuntu 24.04 provides `ubuntu` user at UID 1000
# we use that for the non-root user. The controller always uses 1000:1000 to execute inside sandbox
RUN existing_user="$(getent passwd 1000 | cut -d: -f1 || true)" \
    && if [ -z "$existing_user" ]; then \
         useradd --create-home --uid 1000 --shell /bin/bash agent; \
       elif [ "$existing_user" != "agent" ]; then \
         usermod --login agent "$existing_user"; \
       fi \
    && mkdir -p /workspace \
    && chown 1000:1000 /workspace

USER 1000:1000

WORKDIR /workspace

CMD ["sleep", "infinity"]
