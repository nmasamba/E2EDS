.PHONY: install format test-fast sat verify verify-linux harness-bin desktop-dev desktop-build e2e

# rustup from Homebrew is keg-only on macOS; the extra entries are harmless elsewhere.
export PATH := /opt/homebrew/opt/rustup/bin:$(HOME)/.cargo/bin:$(PATH)

install:        ## create the environment from the lock
	uv sync --frozen

format:         ## format and apply safe lint fixes
	uv run ruff format src tools tests fixtures
	uv run ruff check --fix src tools tests fixtures

test-fast:      ## inner loop: no slow, sandbox, model, desktop or network tests
	uv run pytest -m "not slow and not sandbox and not live_model and not remote_model and not desktop and not network"

sat:            ## sprint acceptance tests, cumulative; writes evidence records to docs/evidence
	DSP_EVIDENCE=docs/evidence DSP_COMMIT=$$(git rev-parse --short HEAD) uv run pytest tests/sat

verify:         ## the sprint gate on this machine
	sh tools/verify.sh

verify-linux:   ## the same gate in a Linux container (repo mounted read-only)
	docker run --rm -v "$(CURDIR)/..":/repo:ro -w /repo/ds_playground \
		-e UV_PROJECT_ENVIRONMENT=/tmp/venv -e UV_CACHE_DIR=/tmp/uv -e RUFF_CACHE_DIR=/tmp/ruff \
		-e MYPY_CACHE_DIR=/tmp/mypy -e COVERAGE_FILE=/tmp/coverage -e PYTEST_ADDOPTS="-p no:cacheprovider" \
		ghcr.io/astral-sh/uv:python3.12-bookworm-slim sh -c "uv sync --frozen && sh tools/verify.sh"

harness-bin:    ## freeze the harness into one executable, named for the target triple, for the bundle
	uv run --frozen --group build pyinstaller --noconfirm --onefile --copy-metadata dsp \
		--collect-data dsp --collect-data rfc3987_syntax \
		--name dsp-harness-$$(rustc --print host-tuple) --distpath desktop/src-tauri/binaries \
		--workpath build/pyinstaller --specpath build/pyinstaller src/dsp/harness/__main__.py

desktop-dev: harness-bin    ## open the desktop window against the dev server
	cd desktop && pnpm install --frozen-lockfile && pnpm tauri dev

desktop-build: harness-bin  ## build the app bundle (.app on macOS; deb and AppImage on Linux)
	cd desktop && pnpm install --frozen-lockfile && pnpm tauri build

e2e:            ## renderer and shell tests on a real harness, then the built app; run desktop-build first
	cd desktop && pnpm test
	cd desktop/src-tauri && cargo test --release --features tauri/custom-protocol
	DSP_EVIDENCE=docs/evidence DSP_COMMIT=$$(git rev-parse --short HEAD) \
		uv run pytest -m desktop tests/e2e
