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
