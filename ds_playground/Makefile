.PHONY: install runner-env format test-fast sat verify verify-linux harness-bin desktop-dev desktop-build e2e

# rustup from Homebrew is keg-only on macOS; the extra entries are harmless elsewhere.
export PATH := /opt/homebrew/opt/rustup/bin:$(HOME)/.cargo/bin:$(PATH)
# The runner's environment: the lock's runtime set and the project built as a wheel, byte-compiled,
# rebuilt on every use so the runner never lags the source.
export DSP_RUNNER_ENV ?= $(CURDIR)/.runner-env
RUNNER_SYNC = uv sync --quiet --frozen --no-dev --no-editable --compile-bytecode --reinstall-package dsp

install:        ## create the environment from the lock
	uv sync --frozen

runner-env:     ## the sandboxed runner's locked environment: runtime dependencies and the project, no dev tools
	UV_PROJECT_ENVIRONMENT=$(DSP_RUNNER_ENV) $(RUNNER_SYNC)

format:         ## format and apply safe lint fixes
	uv run ruff format src tools tests fixtures
	uv run ruff check --fix src tools tests fixtures

test-fast: runner-env  ## inner loop: no slow, sandbox, model, desktop or network tests
	uv run pytest -m "not slow and not sandbox and not live_model and not remote_model and not desktop and not network"

sat: runner-env        ## sprint acceptance tests, cumulative; writes evidence records to docs/evidence
	DSP_EVIDENCE=docs/evidence DSP_COMMIT=$$(git rev-parse --short HEAD) uv run pytest tests/sat

verify: runner-env     ## the sprint gate on this machine
	sh tools/verify.sh

LINUX = docker run --rm --security-opt seccomp=unconfined -v "$(CURDIR)/..":/repo:ro -w /repo/ds_playground \
	-e UV_PROJECT_ENVIRONMENT=/tmp/venv -e UV_CACHE_DIR=/tmp/uv -e RUFF_CACHE_DIR=/tmp/ruff \
	-e MYPY_CACHE_DIR=/tmp/mypy -e COVERAGE_FILE=/tmp/coverage -e PYTEST_ADDOPTS="-p no:cacheprovider" \
	-e DSP_RUNNER_ENV=/tmp/runner-env $(LINUX_MOUNTS) ghcr.io/astral-sh/uv:python3.12-bookworm-slim \
	sh tools/verify_linux.sh "uv sync --frozen && UV_PROJECT_ENVIRONMENT=/tmp/runner-env $(RUNNER_SYNC) && $(LINUX_RUN)"
LINUX_RUN = sh tools/verify.sh

verify-linux:   ## the same gate in a Linux container: repo read-only, bubblewrap, an unprivileged user
	$(LINUX)

harness-bin:    ## freeze the harness into one executable, named for the target triple, for the bundle
	uv run --frozen --group build pyinstaller --noconfirm --onefile --copy-metadata dsp \
		--collect-data dsp --collect-data rfc3987_syntax --add-data $(CURDIR)/src/dsp/recipes/profile_csv.py:dsp/recipes \
		--name dsp-harness-$$(rustc --print host-tuple) --distpath desktop/src-tauri/binaries \
		--workpath build/pyinstaller --specpath build/pyinstaller src/dsp/harness/__main__.py

desktop-dev: harness-bin    ## open the desktop window against the dev server
	cd desktop && pnpm install --frozen-lockfile && pnpm tauri dev

desktop-build: harness-bin  ## build the app bundle (.app on macOS; deb and AppImage on Linux)
	cd desktop && pnpm install --frozen-lockfile && pnpm tauri build

e2e: runner-env  ## renderer and shell tests on a real harness, then the built app; run desktop-build first
	cd desktop && pnpm test
	cd desktop/src-tauri && cargo test --release --features tauri/custom-protocol
	DSP_EVIDENCE=docs/evidence DSP_COMMIT=$$(git rev-parse --short HEAD) \
		uv run pytest -m desktop tests/e2e
