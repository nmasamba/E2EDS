# STATUS

Resume point for every session. Read this first, then `docs/decisions.md`, then `AGENTS.md`.

## Now

- **Sprint:** 3 — M1 jobs, admission, conversation and control (prompts 3.1 to 3.7). Sprints 1 and 2 are
  merged to `main` (PRs #1 to #5).
- **Claimed prompt:** 3.3 — messages and receipts. 3.1 and 3.2 are done (below).
- **Branch:** `sprint-3-control`, from `main` at `cbde3fd`

## Done

- 2026-10-01 — Scaffolding: `AGENTS.md`, `CLAUDE.md`, `prompts.md`, `docs/decisions.md`, eleven skills, one
  reviewer subagent (`integrity-reviewer`). Script-checked: every B01–B37, A01–A45 and R01–R27 ID appears in
  `prompts.md`; every cited suite path resolves.

## Sprint board

| Sprint | Milestone | State | Gate outcome |
|---|---|---|---|
| 0 | Setup | done | G0: PASS for synthetic scope |
| 1 | M0 foundations and thin slice | merged to `main` (PR #1) | PASS, see below |
| 2 | M1 desktop, discovery, plan | merged to `main` (PR #5) | PASS for Sprint 2 scope, see below |
| 3 | M1 jobs, admission, conversation, control | in progress: 3.1–3.2 done, 3.3 claimed | — |
| 4–11 | M1 | not started | — |
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

## Sprint 2 gate (2026-10-02)

Code commit `2c81168`; the evidence and this file were committed after it.

- `make verify` on macOS arm64: **197 passed, 1 deselected**, coverage 92.57%. `make verify-linux`
  (container, linux/arm64): **197 passed, 1 deselected**, coverage 92.93%.
- `make sat` on macOS and in the Linux container: **4 passed** (Sprint 1's test and Sprint 2's three).
- `make desktop-build` then `make e2e` on macOS: reducer **6 passed**, renderer **17 passed**, shell (Rust,
  real harness) **1 passed**, built app **1 passed**.
- CI run 37050679422 on `2c81168`: `verify` and `desktop` green on `ubuntu-24.04` and macOS. On Linux the
  desktop job built the deb and AppImage and passed reducer 6, renderer 17, shell 1 and built app 1; that
  last test inspects the real window through WebDriver, opens and cancels the real folder dialog, closes the
  real window through the window manager and presses the real Quit shortcut.
- ID trace for Sprint 2: A31, A32, A44, D19, D24, R19, R20 and R26 all appear in tests or evidence.
- Evidence records in `docs/evidence/`, one per scenario and OS, all at `2c81168`:
  - **A31 (truthful discovery): PASS** on macOS arm64 and linux/arm64.
  - **A32 (hardware does not confer eligibility): INSUFFICIENT_EVIDENCE** on both. Every case exercised
    gave the expected disposition; the rule table does not yet filter on operation, region, egress,
    isolation policy or data rights, whose objects arrive in later sprints.
  - **A44 (native lifecycle): INSUFFICIENT_EVIDENCE** on macOS arm64 and Linux x86-64. Everything
    exercised passed; jobs, pause, workers and the relationship graph do not exist yet and sleep was not
    exercised.
- Acceptance line ("launch with no model and no terminal, pick source and output folders, see observed and
  unknown hardware and a provisional plan; reopen and see the same state"): shown by the built-app test
  (launch, the window's own discovery and plan, reopen with the same history), the renderer tests (unknown
  hardware with its reason), the CLI acceptance test (stop, reopen, identical state) and the owner's manual
  folder pick. Run for real with the installed CLI: `dsp hardware`, `dsp plan`, `dsp stop`.
- Gate outcome: **PASS** for Sprint 2 scope. Scenario outcomes are as listed; none is rounded up.

## Prompt 3.1 — job coordinator (2026-10-08)

- Pure state machine `src/dsp/domain/jobs.py`, coordinator `src/dsp/application/jobs.py`, app-owned `Job`
  0.1.0 schema, ledger `latest` and `seq`, routes `POST /v1/jobs`, `GET /v1/jobs/{id}`, `lease`,
  `heartbeat`, `report` (native only) and `control` (cancel). Test worker `fixtures/worker.py`.
- Tests: 8 unit (machine) + 8 integration (real harness on a movable clock, real worker processes):
  A03 before and after commit, A04, A07 (queued, running, after success, silent worker), D03 retries,
  mid-transaction failure, events replay to the stored job, window-versus-worker routes. `make test-fast`
  212 passed on macOS. Guards mutation-checked: lease held, retry bound, digest under a committed key,
  expiry and cancel advance the fence, result refused outside running/checkpointed, worker routes refuse
  the window, stale report recorded, expiry reconciled on touch (one redundant clause found and removed).

## Prompt 3.2 — admission and reservations (2026-10-08)

- `application/admission.py` + `domain/admission.py`: `POST /v1/jobs` admits an ExecutionRequest (suite
  0.5.0) with a `Reservation` 0.1.0 and the queued job in one transaction on one aggregate; the test
  job's WorkloadSpec 1.0.0 in `application/workloads.py`; the plan plans for it. Ledger stores typeless
  suite objects by explicit kind.
- Tests (`tests/integration/test_admission.py`, 5): role, undeclared operation (workload and binding),
  accelerator on a CPU option and nonzero charge refused before any work and recorded; reservation held
  and released with the terminal transition, idempotent key; A33 stale plan rechecked and refused, fresh
  plan pinned, current plan reused; A08 race through the real harness five times; no observation refuses
  the window's request and the window submits after discovery. `make test-fast` 217 passed on macOS.
  Guards mutation-checked: scope, operation declared, operation offered, accelerator, charge, unknown
  disposition, capacity after held, single admission aggregate, stale plan recheck, idempotent key,
  release with the terminal transition (one redundant guard found and removed).

## Open defects and gaps

- Linux x86-64 is verified by CI only; the local container run is linux/arm64.
- macOS: the window's text is not read by any automated test (no WebDriver for WKWebView). What is
  checked there is behaviour: the built app's own window makes the first discovery, which only happens if
  the real webview loaded, connected and posted to the bundled harness.
- Linux: the desktop end-to-end test has run only in CI (x86-64). The AppImage is built but never launched;
  the test launches the app unpacked from the deb. No Linux arm64 bundle is built.
- macOS: the Quit menu item and window close are not scripted; Quit is tested as the request the shell
  sends (Rust test) and, on Linux, by pressing the real shortcut. Quit from the Dock or a logout is treated
  as a close and leaves the harness running. Sleep and wake are not exercised on either OS.
- The feasibility rules cover family, charge cap, capacity, accelerators, evidence source and
  qualification; they do not yet filter on operation, region, egress, isolation policy or data rights.
- The plan shown in the app is for a draft of the built-in CSV profile with placeholder references; real
  workloads arrive with Sprint 3. The header has no workload, budget, Pause or Cancel yet.
- The window polls for events every two seconds; the SSE endpoint is served and tested but the window does
  not use it. The ledger keeps every event, so "expired cursor" means a cursor it never issued.
- Discovery lists only NVIDIA accelerators on Linux and estimates available memory on macOS.
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

Sprints 1 and 2 are built. Prompts 2.1 to 2.3 are merged to `main` (PRs #2 to #4); 2.4 to 2.8 (hardware
discovery, feasibility plan, event stream and work trail, lifecycle, the gate) are on `sprint-2-finish` and
waiting for the owner in PR #5; merging is the owner's. **Next is Sprint 3, prompt 3.1**, on a new branch
from `main` once PR #5 is merged.

Notes for the next session: every CLI command except `dsp verify` goes through the harness, so tests that
call the CLI use the `home` fixture, which stops the harness they start; to check that a harness has exited,
use the `harness_stopped` fixture (the Linux container has no `ps`). `make sat` and `make e2e` write evidence
records to `docs/evidence/` (an `evidence` fixture; give it the scenario's real outcome); the Linux A44
record comes from the CI desktop job's artifact, and the Linux A31/A32 records from running `tests/sat` in
the container with `docs/evidence` mounted writable. The frozen sidecar must be rebuilt (`make
desktop-build`) after any Python change before `make e2e`; new package data needs a `--collect-data` flag in
`make harness-bin`. The Makefile puts the keg-only Rust on PATH for its own targets; outside make, prepend
`/opt/homebrew/opt/rustup/bin` and `~/.cargo/bin`. `make e2e` needs Playwright's Chromium (`pnpm --dir
desktop exec playwright install chromium`). The dev window is refused by a harness that was not spawned
with `--dev`, so run `dsp stop` before `make desktop-dev`. Sprint 3 brings jobs: the stage reducer
(`desktop/src/trail.ts`), the event endpoints and the shutdown drain are the pieces it extends, and the
window needs `content-type` allowed in the preflight before it can send a request with a body.
