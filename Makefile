# Entry points for humans and agents alike. See AGENTS.md section 3.
#
# Everything here is stdlib Python; no runtime dependencies, so these work on
# the Pi as well as a dev box.

PYTHON ?= python

# PYTHONPATH separator differs by platform, and this repo is edited on Windows
# and run on the Pi. Getting it wrong fails with a confusing "No module named
# machinegen" rather than anything about paths.
ifeq ($(OS),Windows_NT)
PATHSEP := ;
else
PATHSEP := :
endif
export PYTHONPATH := tools$(PATHSEP)ui

.PHONY: all test check gen verify lint integration hardware clean help

help:
	@echo "make test        unit tests (fast, no hardware)"
	@echo "make check       validate machine/wen33013.toml against physical limits"
	@echo "make gen         regenerate every generated file"
	@echo "make verify      fail if a generated file is stale"
	@echo "make lint        ruff"
	@echo "make all         verify + lint + test   <- run before committing"
	@echo "make integration needs LinuxCNC (run on the Pi)"
	@echo "make hardware    needs the physical machine - never unattended"

all: verify lint test

test:
	$(PYTHON) -m pytest tests/unit

check:
	$(PYTHON) -m machinegen check

gen:
	$(PYTHON) -m machinegen generate

verify:
	$(PYTHON) -m machinegen verify

lint:
	-$(PYTHON) -m ruff check .

integration:
	$(PYTHON) -m pytest tests/integration -m integration

# Deliberately not part of `all`. Read docs/commissioning/ first.
hardware:
	$(PYTHON) -m pytest tests/hardware -m hardware

clean:
	find . -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache
