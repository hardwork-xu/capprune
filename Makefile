export VECLIB_MAXIMUM_THREADS = 1
export OPENBLAS_NUM_THREADS = 1
export OMP_NUM_THREADS = 1

UV ?= uv
PY ?= .venv/bin/python

.PHONY: install demo test check benchmark analyze build docs-check
install:
	$(UV) sync --frozen
demo:
	$(PY) -m capprune demo
test:
	$(PY) -m pytest
check:
	.venv/bin/ruff format --check .
	.venv/bin/ruff check .
	.venv/bin/mypy
	$(PY) -m pytest
	$(PY) scripts/check_docs.py
benchmark:
	$(PY) benchmark.py --output results/local-$$(date -u +%Y%m%dT%H%M%SZ).json
analyze:
	$(PY) scripts/analyze.py results/reference.json
build:
	$(PY) -m build --no-isolation
docs-check:
	$(PY) scripts/check_docs.py
