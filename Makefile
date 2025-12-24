.PHONY: install setup lint fmt test run verify check-deprecated

PYTHON = .venv/bin/python
PIP = .venv/bin/pip
RUFF = .venv/bin/ruff
MYPY = .venv/bin/mypy
BLACK = .venv/bin/black
VULTURE = .venv/bin/vulture
PROSPECTOR = .venv/bin/prospector
PYTEST = .venv/bin/pytest

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

