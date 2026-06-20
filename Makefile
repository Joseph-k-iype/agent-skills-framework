PYTHON ?= python3
SDK := sdks/python

.PHONY: test test-py test-ts test-sdk test-cli test-skill test-harness lint install-ts

test: ## Run every suite (Python + TypeScript)
	bash scripts/run_tests.sh

test-py: test-sdk test-cli test-skill test-harness ## Run all Python suites

test-sdk:
	cd $(SDK) && $(PYTHON) -m pytest -q

test-cli:
	PYTHONPATH=$(SDK) $(PYTHON) -m pytest cli/tests -q

test-skill:
	cd skills/data-discovery && PYTHONPATH=$(CURDIR)/$(SDK) $(PYTHON) -m pytest -q

test-harness:
	cd testing && PYTHONPATH=$(CURDIR)/$(SDK) $(PYTHON) -m pytest -q

test-ts: ## Run the TypeScript suite
	cd sdks/typescript && npm test

install-ts:
	cd sdks/typescript && npm install

lint:
	cd $(SDK) && ruff check .
