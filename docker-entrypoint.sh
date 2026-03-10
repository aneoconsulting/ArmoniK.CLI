#!/bin/sh
# docker-entrypoint.sh
set -e

# ── Config resolution ──────────────────────────────────────────────────────────
# If AKCONFIG is not already set but a config file has been mounted at the
# conventional container path, point the CLI at it automatically.
if [ -z "$AKCONFIG" ] && [ -f "/config/armonik.yml" ]; then
    export AKCONFIG="/config/armonik.yml"
    echo "[armonik] Using config from /config/armonik.yml"
fi

# ── Runtime extension installs ─────────────────────────────────────────────────
# NOTE: For ephemeral containers (Kubernetes, CI) prefer the build-time
# ARMONIK_EXTRA_PACKAGES build-arg so extensions are baked into the image layer
# and this startup cost is avoided entirely.
if [ -n "$ARMONIK_EXTRA_PACKAGES" ]; then
    echo "[armonik] Installing extra packages: $ARMONIK_EXTRA_PACKAGES"
    # shellcheck disable=SC2086  # intentional word-splitting on the package list
    uv pip install --system --no-cache $ARMONIK_EXTRA_PACKAGES
fi

exec armonik "$@"
