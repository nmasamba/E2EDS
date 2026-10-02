# STATUS

Resume point for every session. Read this first, then `docs/decisions.md`, then `AGENTS.md`.

## Now

- **Sprint:** 2 — M1 desktop shell, discovery and plan (Sprint 1 is merged to `main` through PR #1)
- **Claimed prompt:** 2.4 to 2.8 (hardware discovery, plan, work trail, lifecycle, sprint gate). 2.1 to 2.3
  are merged to `main` (PRs #2, #3, #4).
- **Branch:** `sprint-2-finish`, from `main` at `8909aa7`

## Done

- 2026-10-01 — Scaffolding: `AGENTS.md`, `CLAUDE.md`, `prompts.md`, `docs/decisions.md`, eleven skills, one
  reviewer subagent (`integrity-reviewer`). Script-checked: every B01–B37, A01–A45 and R01–R27 ID appears in
  `prompts.md`; every cited suite path resolves.

## Sprint board

| Sprint | Milestone | State | Gate outcome |
|---|---|---|---|
| 0 | Setup | done | G0: PASS for synthetic scope |
| 1 | M0 foundations and thin slice | merged to `main` (PR #1) | PASS, see below |
| 2 | M1 desktop, discovery, plan | 2.1 to 2.3 merged; 2.4–2.8 in progress | — |
| 3–11 | M1 | not started | — |
| 12–20 | M1B, M1C, M1R, M2, M3, M3Z, M4 | not started | — |

## Environment observed (2026-10-01, this Mac)

macOS 26.3.1, arm64 (Apple M1 Max), 10 cores, 64 GiB RAM, about 714 GiB free. Present: uv 0.10.8, Python 3.12.13
and 3.13 (uv-managed), Node 22.17.1, pnpm 10.32.1, Docker 29.8.1, git, gh, Homebrew.

Installed in Sprint 0.2: cmake and rustup via Homebrew (rustup is keg-only: `/opt/homebrew/opt/rustup/bin`),
Rust stable 1.99.0. llama.cpp built from tag `b11104` at commit `217f81c266a7b7c986ee3d2c58e1cccee05a0744`
into `~/.local/share/dsp/llama.cpp/build/bin/llama-server` (reports 0.4.1-dev, Darwin arm64; binary SHA-256
`10f66aeed2d40ae707ee189748738ac6db97995ff18990dafa9c0e5b73d94128`, dynamically linked to the libraries beside
it). Absent: Tesseract (no OCR profile is planned without owner approval).

Assistant model (Sprint 0.3, verified 2026-10-02): `~/.local/share/dsp/models/Qwen3-8B-Q4_K_M.gguf`,
5,027,783,488 bytes, SHA-256 `d98cdcbd03e17ce47681435b5150e34c1417f50b5c0019dd560e4882c5745785` — matches the
suite's pinned digest and the size and digest the source reports for revision `7c41481f…`. Not loaded yet.

## Sprint 1 gate (2026-10-01)

- `make verify` on macOS arm64: format, lint, mypy strict, boundaries all clean; **95 passed**, coverage 99%.
- `make verify-linux` (container, linux/arm64, Python 3.12.12): **95 passed**, coverage 99%.
- `make sat`: 1 passed. ID trace for Sprint 1: D20, D23, R11 covered.
- Live run on both: `dsp profile orders.csv --out out/` on the 2,000-order fixture exported `v1` (3 files),
  `dsp verify` printed `verified`, a second run produced `v2`, and `manifest.json` has the same SHA-256 on
  macOS and Linux (`6aeb5ad8…5cadf`).
- CI on PR #1: both jobs passed (`ubuntu-24.04` x86-64 and macOS).
- Gate outcome: **PASS** for Sprint 1 scope. No acceptance scenario (A##) is in scope for this sprint.

## Prompt 2.2 — desktop shell (2026-10-02)

- `make verify` on macOS arm64: **132 passed, 1 deselected** (the `desktop` test), coverage 95.70%.
- `make verify-linux` (container, linux/arm64): **132 passed, 1 deselected**, coverage 95.70%.
- `make desktop-build` on macOS: `DS Playground.app` (29.28 MiB) with the frozen harness beside the shell
  binary. Launched through LaunchServices on a temporary `DSP_HOME`, its own harness answered `/v1/status`
  in 1.04 s, with no terminal and no uv.
- `make desktop-dev` on macOS: the window opened and its sidecar ran with `--dev`.
- `make e2e` on macOS: renderer **4 passed** (Playwright + axe on a real harness), desktop **1 passed**.
- CI on `a0a1e77` (run 37003990879): `verify` green on `ubuntu-24.04` and macOS; `desktop` green on both. On
  Linux it built `DS Playground_0.1.0_amd64.deb` (21.10 MiB) and the AppImage, then under a virtual display
  launched the app unpacked from the deb through WebDriver, read "Harness connected" with the harness's
  version and process, and quit: renderer 4 passed, desktop 1 passed.

## Prompt 2.3 — scoped folder grants (2026-10-02)

- `make verify` on macOS arm64: **168 passed, 1 deselected**, coverage 95.88%. `make verify-linux` (container,
  linux/arm64): **168 passed, 1 deselected**, coverage 95.88%.
- `make desktop-build` then `make e2e` on macOS: renderer **11 passed**, shell (Rust, real harness)
  **1 passed**, built app **1 passed**. The `.app` is 45.51 MiB now that the frozen harness carries
  DuckDB and the contract schemas.
- CI on `998226c` (run 37029137568): `verify` and `desktop` green on `ubuntu-24.04` and macOS. On Linux the
  built app, unpacked from the deb, showed "connected", refused a command its capability does not grant,
  opened the real GTK folder dialog and granted nothing when it was cancelled; then its bundled harness
  profiled a file through grants and refused a path outside them: renderer 10 passed, shell 1 passed, built
  app 1 passed. The next run failed one renderer test on Linux: a real race in the Folders view, fixed with
  an eleventh test that holds the race open (`docs/decisions.md`).
- Run for real with the installed CLI on a temporary profile: `dsp status`, `dsp grant`, `dsp profile`,
  `dsp verify`, `dsp grants`, `dsp revoke`. Afterwards no ledger event held a host path; only the four
  FolderGrant records did.
- ID trace for Sprint 2 so far: R26 and A44 appear in tests; D19, D24, R19 and R20 belong to prompts 2.4–2.7.

## Open defects and gaps

- Linux x86-64 is verified by CI only; the local container run is linux/arm64.
- macOS: the window's text is not read by any automated test (no WebDriver for WKWebView); the end-to-end
  test checks the harness the app started. The window's requests were checked once by hand
  (`docs/decisions.md`, 2026-10-02).
- Linux: the desktop end-to-end test has run only in CI (x86-64). The AppImage is built but never launched;
  the test launches the app unpacked from the deb. No Linux arm64 bundle is built.
- The Quit menu item is not exercised by a test on either OS.
- Choosing a folder in the native dialog is not automated on either OS (see `docs/decisions.md`,
  2026-10-02). The owner checked it by hand on 2026-10-02: a source folder can be added and removed in the
  real app and appears by its name.
- The window cannot yet send a request with a body (the preflight allows only `authorization`), so profiling
  is reachable from the CLI only.
- A proposed OutputBinding declares `max_export_bytes` that nothing enforces yet, and names a placeholder
  project and output.

## Waiting on the owner

Nothing. Standing approvals are in `docs/decisions.md`.

## Handoff note

Sprint 1 (PR #1), prompt 2.1 (PR #2) and prompt 2.2 (PR #3) are merged to `main`. Prompt 2.3 (scoped folder
grants) is done on `sprint-2-grants` and waiting for the owner in PR #4; merging is the owner's. **Next is
prompt 2.4** (hardware discovery), on a new branch from `main` once PR #4 is merged.

Notes for the next session: every CLI command except `dsp verify` now goes through the harness, so tests
that call the CLI use the `home` fixture, which stops the harness they start. The frozen sidecar must be
rebuilt (`make desktop-build`) after any Python change before `make e2e`; new package data or lazily loaded
modules need a `--collect-data` or hidden-import flag in `make harness-bin`, and the built-app test will show
it. The Makefile puts the keg-only Rust on PATH for its own targets; outside make, prepend
`/opt/homebrew/opt/rustup/bin` and `~/.cargo/bin`. `make e2e` needs Playwright's Chromium
(`pnpm --dir desktop exec playwright install chromium`). The dev window is refused by a harness that was not
spawned with `--dev`, so stop any running harness before `make desktop-dev`. The harness keeps running after
the window quits until 2.7 defines the lifecycle.
