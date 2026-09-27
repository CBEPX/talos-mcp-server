.PHONY: install lint fmt test test-integration run show-version docker-build docker-run

PYTHON = .venv/bin/python
RUFF = .venv/bin/ruff
MYPY = .venv/bin/mypy
BLACK = .venv/bin/black
PYTEST = .venv/bin/pytest

# Talosctl version management
TALOSCTL_VERSION = $(shell cat .talosctl-version)

install:
	uv sync --locked --group dev

lint:
	uv lock --check
	$(RUFF) check src/ tests/ scripts/
	$(MYPY) src/
	$(BLACK) --check src/ tests/ scripts/

fmt:
	$(RUFF) check --fix src/ tests/ scripts/
	$(BLACK) src/ tests/ scripts/

test:
	$(PYTEST)

run:
	.venv/bin/talos-mcp-server

test-integration:
	@test -n "$(LAB_MANIFEST)" && test -n "$(LAB_NODE)" || { echo "Set LAB_MANIFEST and LAB_NODE for a disposable node" >&2; exit 2; }
	$(PYTHON) scripts/lab_smoke.py --manifest "$(LAB_MANIFEST)" --confirm-disposable "$(LAB_NODE)"

# Version Management targets
show-version:
	@echo "Current talosctl version: $(TALOSCTL_VERSION)"

# Docker targets
docker-build:
	docker build -t talos-mcp-server:$(TALOSCTL_VERSION) .

docker-run:
	docker run --rm -it \
		-v $$HOME/.talos:/root/.talos:ro \
		-e TALOS_MCP_TALOSCONFIG=/root/.talos/config \
		talos-mcp-server:$(TALOSCTL_VERSION)
