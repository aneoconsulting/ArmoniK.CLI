# ─── Stage 1: Build ───────────────────────────────────────────────────────────
# uv's official image already has uv + a managed Python — no extra install step.
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS builder

WORKDIR /build

# Optional: bake CLI extension packages into the image at build time.
# Pass a space-separated list via --build-arg, e.g.:
#   docker build --build-arg ARMONIK_EXTRA_PACKAGES="my-ext==1.0 another-ext" .
# Leave blank (default) for a vanilla image.
ARG ARMONIK_EXTRA_PACKAGES=""

# Copy dependency manifests first — maximises Docker layer caching.
COPY pyproject.toml ./
COPY packages/armonik_cli_core/pyproject.toml ./packages/armonik_cli_core/

# UV_SYSTEM_PYTHON=1 makes uv target the image's managed interpreter directly.
ENV UV_SYSTEM_PYTHON=1

COPY . .
RUN uv pip install --no-cache . \
    && if [ -n "$ARMONIK_EXTRA_PACKAGES" ]; then \
         echo "[armonik] Baking in extra packages: $ARMONIK_EXTRA_PACKAGES" && \
         uv pip install --no-cache $ARMONIK_EXTRA_PACKAGES; \
       fi

# ─── Stage 2: Runtime ─────────────────────────────────────────────────────────
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS runtime

# OCI standard image metadata
LABEL org.opencontainers.image.title="ArmoniK CLI" \
      org.opencontainers.image.description="Command-line tool to monitor and manage ArmoniK clusters." \
      org.opencontainers.image.source="https://github.com/aneoconsulting/ArmoniK.CLI" \
      org.opencontainers.image.licenses="Apache-2.0"

# CA certificates are needed for TLS connections to ArmoniK clusters.
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

ENV UV_SYSTEM_PYTHON=1

# Copy installed Python packages and the CLI binary from the builder.
COPY --from=builder /usr/local/lib/python3.11 /usr/local/lib/python3.11
COPY --from=builder /usr/local/bin/armonik    /usr/local/bin/armonik

# ── Config ─────────────────────────────────────────────────────────────────────
# The CLI's default config path is ~/.config/armonik_cli/config.yml.
# In this container that resolves to /root/.config/armonik_cli/config.yml.
#
# Recommended approach — mount your config and point AKCONFIG at it:
#   docker run -v /host/config.yml:/config/armonik.yml \
#              -e AKCONFIG=/config/armonik.yml ...
#
# The entrypoint auto-exports AKCONFIG=/config/armonik.yml when a file is
# found there, so the -e flag is optional if you use that exact mount path.
RUN mkdir -p /root/.config/armonik_cli /config

# ── Runtime extension installs ─────────────────────────────────────────────────
# For *ephemeral* containers (K8s pods, CI runners, etc.) the strongly
# recommended approach is to bake extensions at build time via the build-arg
# above, or derive a custom image:
#
#   FROM dockerhubaneo/armonik-cli:latest
#   RUN uv pip install my-ext
#
# For persistent containers or local Docker usage, setting ARMONIK_EXTRA_PACKAGES
# at runtime is convenient — packages are installed on every cold start, which
# adds a few seconds but avoids a custom image build.
ENV ARMONIK_EXTRA_PACKAGES=""

COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["--help"]
