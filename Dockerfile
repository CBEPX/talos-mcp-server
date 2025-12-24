# Use a Python image with uv pre-installed
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# Install talosctl - version is read from .talosctl-version file
# Override at build time with: docker build --build-arg TALOSCTL_VERSION=vX.Y.Z
ARG TALOSCTL_VERSION
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy version file and install talosctl
COPY .talosctl-version /tmp/.talosctl-version
RUN TALOSCTL_VERSION=${TALOSCTL_VERSION:-$(cat /tmp/.talosctl-version | tr -d '[:space:]')} \
    && echo "Installing talosctl ${TALOSCTL_VERSION}" \
    && curl -Lo /usr/local/bin/talosctl https://github.com/siderolabs/talos/releases/download/${TALOSCTL_VERSION}/talosctl-linux-amd64 \
    && chmod +x /usr/local/bin/talosctl \
    && rm /tmp/.talosctl-version

# Set up the application directory
WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy from the cache instead of linking since it's a mounted volume
ENV UV_LINK_MODE=copy

# Install the project's dependencies using the lockfile and settings
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

# Add the project sources
ADD . /app

# Install the project itself
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH"

# Default configuration
ENV TALOS_MCP_LOG_LEVEL=INFO
ENV TALOS_MCP_AUDIT_LOG_PATH=/app/logs/audit.log
VOLUME /app/logs
VOLUME /root/.talos

# Reset the entrypoint, don't invoke `uv`
ENTRYPOINT []

# Run the server
CMD ["python", "src/talos_mcp/server.py"]
