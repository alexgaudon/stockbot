.PHONY: install dev build test lint clean

install:
	uv sync

dev:
	uv run python -m stockbot

run:
	docker run --env-file .env stocky:latest
	
build:
	docker build . -t stocky:latest

test:
	@echo "No tests defined"

lint:
	uv run ruff check

clean:
	rm -rf .venv