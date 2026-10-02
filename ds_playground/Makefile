.PHONY: install format test-fast sat verify verify-linux

install:        ## create the environment from the lock
	uv sync --frozen

format:         ## format and apply safe lint fixes
	uv run ruff format src tools tests fixtures
	uv run ruff check --fix src tools tests fixtures

test-fast:      ## inner loop: no slow, sandbox, model, desktop or network tests
	uv run pytest -m "not slow and not sandbox and not live_model and not remote_model and not desktop and not network"

sat:            ## sprint acceptance tests, cumulative
	uv run pytest tests/sat

verify:         ## the sprint gate on this machine
	sh tools/verify.sh

verify-linux:   ## the same gate in a Linux container (repo mounted read-only)
	docker run --rm -v "$(CURDIR)/..":/repo:ro -w /repo/ds_playground \
		-e UV_PROJECT_ENVIRONMENT=/tmp/venv -e UV_CACHE_DIR=/tmp/uv -e RUFF_CACHE_DIR=/tmp/ruff \
		-e MYPY_CACHE_DIR=/tmp/mypy -e COVERAGE_FILE=/tmp/coverage -e PYTEST_ADDOPTS="-p no:cacheprovider" \
		ghcr.io/astral-sh/uv:python3.12-bookworm-slim sh -c "uv sync --frozen && sh tools/verify.sh"
