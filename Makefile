PYTHON ?= python3

.PHONY: dev test lint

dev:
	uvicorn app.api:app --host 0.0.0.0 --port 8080 --reload

test:
	$(PYTHON) -m pytest

lint:
	ruff check .
	mypy app packs tests
