#!/bin/sh
# The sprint gate. `make verify` runs it here; `make verify-linux` runs it in a Linux container.
set -e
export UV_FROZEN=1
uv run ruff format --check src tools tests fixtures
uv run ruff check src tools tests fixtures
uv run mypy
uv run python tools/check_boundaries.py
uv run pytest --cov=dsp --cov-report=term-missing:skip-covered --cov-fail-under=85
