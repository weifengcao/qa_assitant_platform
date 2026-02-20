PYTHON ?= python3

.PHONY: dev test lint typecheck eval clean

dev:
	uvicorn app.api:app --host 0.0.0.0 --port 8080 --reload

test:
	$(PYTHON) -m pytest

lint:
	ruff check .

typecheck:
	mypy app packs tests

eval:
	$(PYTHON) -m eval.run

clean:
	find . -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .ruff_cache .mypy_cache
