.PHONY: install setup lint fmt test run verify check-deprecated

PYTHON = .venv/bin/python
PIP = .venv/bin/pip
RUFF = .venv/bin/ruff
MYPY = .venv/bin/mypy
BLACK = .venv/bin/black
VULTURE = .venv/bin/vulture
PROSPECTOR = .venv/bin/prospector
PYTEST = .venv/bin/pytest

# Talosctl version management
TALOSCTL_VERSION ?= $(shell cat .talosctl-version 2>/dev/null || echo "v1.12.0")

install:
	python3 -m venv .venv
	$(PIP) install -e ".[dev]"

setup: install
	$(PIP) install --upgrade pip

lint:
	$(RUFF) check src/ tests/
	$(MYPY) src/
	$(VULTURE) src/ --min-confidence 70 || true

fmt:
	$(BLACK) src/ tests/
	$(RUFF) check --fix src/ tests/

test:
	$(PYTEST) tests/

run-test-logging:
	.venv/bin/python tests/test_logging.py

verify:
	$(PYTHON) tests/verify_tools.py

run:
	$(PYTHON) src/talos_mcp/server.py

check-deprecated:
	$(PROSPECTOR) src/

# Integration Testing targets
CLUSTER_NAME ?= talos-mcp-test
LOCAL_CONFIG ?= $(PWD)/talosconfig

cluster-up:
	rm -f $(LOCAL_CONFIG)
	TALOSCONFIG=$(LOCAL_CONFIG) talosctl cluster create --name $(CLUSTER_NAME) --provisioner docker --workers 0 --talosconfig $(LOCAL_CONFIG)
	@echo "Cluster created. Waiting for API availability..."
	TALOSCONFIG=$(LOCAL_CONFIG) $(PYTHON) tests/wait_for_ready.py

cluster-down:
	talosctl cluster destroy --name $(CLUSTER_NAME) --provisioner docker
	rm -f $(LOCAL_CONFIG)

test-integration:
	@echo "Starting integration tests..."
	$(MAKE) cluster-up
	# Run Read-Only tests
	TALOS_MCP_READONLY=true TALOSCONFIG=$(LOCAL_CONFIG) $(PYTEST) tests/integration/test_ro.py
	# Run Read-Write tests
	TALOS_MCP_READONLY=false TALOSCONFIG=$(LOCAL_CONFIG) $(PYTEST) tests/integration/test_rw.py
	$(MAKE) cluster-down

# Version Management targets
show-version:
	@echo "Current talosctl version: $(TALOSCTL_VERSION)"
	@echo "Local talosctl version: $$(talosctl version --client --short 2>/dev/null || echo 'not installed')"

update-talosctl-version:
	@echo "Updating .talosctl-version to $(NEW_VERSION)"
	@if [ -z "$(NEW_VERSION)" ]; then echo "Usage: make update-talosctl-version NEW_VERSION=v1.13.0"; exit 1; fi
	@echo "$(NEW_VERSION)" > .talosctl-version
	@echo "Done. Run 'make docker-build' to rebuild the image."

check-talosctl-update:
	@echo "Checking for latest talosctl version..."
	@LATEST=$$(curl -s https://api.github.com/repos/siderolabs/talos/releases/latest | grep '"tag_name"' | cut -d'"' -f4); \
	CURRENT=$$(cat .talosctl-version | tr -d '[:space:]'); \
	echo "Current: $$CURRENT"; \
	echo "Latest:  $$LATEST"; \
	if [ "$$CURRENT" != "$$LATEST" ]; then \
		echo "Update available! Run: make update-talosctl-version NEW_VERSION=$$LATEST"; \
	else \
		echo "Already up to date."; \
	fi

# Docker targets
docker-build:
	docker build -t talos-mcp-server:$(TALOSCTL_VERSION) .
	docker tag talos-mcp-server:$(TALOSCTL_VERSION) talos-mcp-server:latest

docker-run:
	docker run --rm -it \
		-v $$HOME/.talos:/root/.talos:ro \
		-e TALOSCONFIG=/root/.talos/config \
		talos-mcp-server:latest
