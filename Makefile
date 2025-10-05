.PHONY: install dev build test lint clean

install:
	uv sync

dev:
	uv run python -m stockbot

build:
	@echo "No build step for this project"

test:
	@echo "No tests defined"

lint:
	uv run ruff check

clean:
	rm -rf .venv