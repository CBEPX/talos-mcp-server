FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

ARG TARGETARCH
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

COPY .talosctl-version talosctl-checksums.txt /tmp/
RUN set -eu; \
    version="$(cat /tmp/.talosctl-version)"; \
    asset="talosctl-linux-${TARGETARCH}"; \
    digest="$(awk -v v="$version" -v a="$asset" '$2 == v && $3 == a { print $1 }' /tmp/talosctl-checksums.txt)"; \
    test -n "$digest"; \
    curl -fsSL --retry 3 "https://github.com/siderolabs/talos/releases/download/${version}/${asset}" -o /usr/local/bin/talosctl; \
    echo "$digest  /usr/local/bin/talosctl" | sha256sum -c -; \
    chmod 0755 /usr/local/bin/talosctl; \
    rm /tmp/.talosctl-version /tmp/talosctl-checksums.txt

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
RUN uv sync --locked --no-dev
ENV PATH="/app/.venv/bin:$PATH"
ENTRYPOINT ["talos-mcp-server"]
