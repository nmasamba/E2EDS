# Dependencies

One line per production dependency: why it is here, its licence as stated upstream, and the alternative.
Exact versions are pinned in `pyproject.toml` and `uv.lock`. Licences below are upstream statements, not a
pin-level legal review (open decision O23).

| Package | Why | Licence (upstream) | Alternative |
|---|---|---|---|
| duckdb 1.5.5 | Embedded SQL over CSV/Parquet for profiling and preparation (suite pin, ADR24) | MIT | pandas or polars; more code for the same checks |
| fastapi 0.141.1 | The local harness API (suite pin) | MIT | Starlette alone; more code for the same routes |
| httpx 0.28.1 | The CLI's authenticated client to the harness | BSD-3-Clause | urllib; more code |
| jsonschema 4.26.0 (`format-nongpl`) | Validates objects against the draft 2020-12 contracts with format assertion | MIT | fastjsonschema; weaker format support |
| typer 0.27.2 | CLI | MIT | argparse; more code |
| uvicorn 0.54.0 | Serves the harness on the loopback socket it is handed | BSD-3-Clause | hypercorn |

Development only: ruff, mypy, pytest, pytest-cov, pytest-socket, types-jsonschema.

Build only (`build` dependency group, not installed by `uv sync`): pyinstaller 6.22.3 freezes the harness into
the desktop sidecar (GPL-2.0-or-later with an exception that allows distributing the frozen program under any
licence; alternative: Nuitka, a slower compile for the same single file).

## Desktop shell (`desktop/`)

Exact versions are pinned in `desktop/package.json` with `pnpm-lock.yaml`, and in
`desktop/src-tauri/Cargo.toml` with `Cargo.lock`.

| Package | Why | Licence (upstream) | Alternative |
|---|---|---|---|
| tauri 2.12.0, tauri-build 2.7.1 (crates) | The native window, menu and sidecar bundling (suite pin) | Apache-2.0 OR MIT | Electron; the suite's stated fallback |
| rfd 0.16.0 (crate, `gtk3`) | The native folder dialog; the version Tauri's own dialog plugin uses | MIT | tauri-plugin-dialog; it also brings the filesystem plugin crate |
| serde_json 1.0.151 (crate) | Reads `harness.json` and shapes the one command's answer | MIT OR Apache-2.0 | hand-parsing JSON |
| ureq 3.4.2 (crate, `json` only, no TLS) | The shell's own request that gives a picked folder to the harness | MIT OR Apache-2.0 | reqwest; far larger |
| @tauri-apps/api 2.12.0 | The renderer's call to the one shell command | Apache-2.0 OR MIT | calling the injected IPC object directly |
| react 19.3.0, react-dom 19.3.0 | Renderer views (owner default in `docs/decisions.md`) | MIT | plain DOM code |

Development only: @tauri-apps/cli, vite, typescript, @types/node, @types/react, @types/react-dom,
@playwright/test, @axe-core/playwright (MPL-2.0; test-time only, not shipped). CI also installs tauri-driver
2.1.0 from crates.io, and xdotool from the runner's package archive, for the Linux end-to-end test.
