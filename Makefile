# Use bash as shell
SHELL := /bin/bash

# Phony targets
.PHONY: install run deps

# Default: install deps
all: install

# Install dependencies
install:
	@pip install -r requirements.txt

# Lint code
lint:
	@echo "Linting src/"
	@ruff check src --fix

# Type check code
types:
	@mypy src/main.py --check-untyped-defs

# Format code
format:
	@echo "Formatting src/"
	@ruff format src

# Run process
run:
	@python3.11 src/main.py
