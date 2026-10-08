# STATUS

Resume point for every session. Read this first, then `docs/decisions.md`, then `AGENTS.md`.

## Now

- **Sprint:** 3 — M1 jobs, admission, conversation and control: complete, gate below. Sprint 4 is next.
- **Claimed prompt:** none. 3.1 to 3.7 are done and waiting in the pull request.
- **Branch:** `sprint-3-control`, from `main` at `cbde3fd`, with a pull request open against `main`

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
| 3 | M1 jobs, admission, conversation, control | done; in the pull request | PASS for Sprint 3 scope, see below |
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

## Prompt 3.3 — messages and receipts (2026-10-08)

- `application/conversation.py`, app `Conversation` 0.1.0, route `POST /v1/conversations/{id}/messages`
  (size in bytes before parsing, three string fields only, suite ConversationCommand records, receipt
  before acknowledgement, dedupe by client message ID, exact control phrases classified, instructions
  rejected as ASSISTANT_UNAVAILABLE).
- Tests (`tests/integration/test_messages.py`, 25 incl. parametrised): A27 same-ID retry, conflict,
  dropped acknowledgement over a raw socket against the real harness, cursor replay in order; D18
  16 KiB + 1 refused before parsing (also chunked), exact 16 KiB accepted, bytes not characters;
  inbound field rules; phrase exactness. `make test-fast` 243 passed on macOS. Guards mutation-checked:
  size before parsing, exactly three fields, string fields, service byte count, same ID one command,
  other text conflicts, exact phrases, instruction rejected.

## Prompt 3.4 — fast controls (2026-10-08)

- `application/controls.py` (phrases, buttons and menu on one path), pause/resume in the state machine,
  resume as readmission, `POST /v1/jobs/{id}/control`, `POST /v1/control`, `POST /v1/jobs/{id}/checkpoint`,
  the preflight grants `content-type`.
- Tests: `tests/integration/test_controls.py` (6): A25 pause racing a checkpoint and a commit with an
  explicit resume, a queued job pausing and resume as a fresh admission, phrases exact and quoted ones
  inert, a phrase with two live jobs asks which, the menu door, checkpoints native only. SAT
  `tests/sat/test_sprint_03.py` A24: 20 pause and 20 cancel phrases under full saturation with a hung
  worker each, p95 asserted ≤ 2 s (numbers recorded by `make sat` at the gate). Preflight header tests in
  `test_shell_origin.py`. `make test-fast` 254 passed on macOS. Guards mutation-checked: pause advances
  the fence, only paused resumes, PAUSED refuses leases, pause releases the reservation, resume rechecks
  capacity, repeated command not reapplied, ended jobs not live, command settled applied, refused
  control recorded, checkpoints native only, preflight refuses other headers, checkpoint needs the live
  attempt.

## Prompt 3.5 — requirement revisions (2026-10-08)

- `application/workloads.py`: change grammar, typed patch, impact through the dependency graph,
  immutable revision under compare-and-swap, stale marks; `controls.change` holds live work;
  `GET /v1/workload`.
- Tests (`tests/integration/test_revisions.py`, 4): A26 exclude a field mid-run (diff, impact, new
  revision, provenance, old result untouched on the old revision, hold and resume under the new revision,
  next admission on the new revision), two concurrent edits conflict predictably, budget and evaluation
  refused without the owner and unknown fields refused, the dependency graph. `make test-fast` 259
  passed on macOS. Guards mutation-checked: expected revision compared, owner paths refused, allowed
  predictor only, stale marks, holds, anchored grammar, provenance recorded, hold pauses, revision
  advances.

## Prompt 3.6 — composer and activity (2026-10-08)

- Renderer: `Controls`, `Composer`, `Run`, `ActivityTrail`; `trail.ts` gains `jobs`, `liveJob`,
  `expectedRevision`, `activity` and the develop stage by job state (Vitest: 9 tests). Rust menu: Pause
  (CmdOrCtrl+P) and Cancel run (CmdOrCtrl+.) post `/v1/control`; the Rust test sends both against a real
  harness. Playwright `tests/work.spec.ts` (2) against a real harness with real worker processes: the
  composer's receipts and the activity's command states; start the hung job, pause by keyboard, change a
  requirement, resume by keyboard, cancel by keyboard, reload and see it all again, axe clean; shared
  helpers moved to `tests/harness.ts`. Built-app test: Linux presses the real shortcuts and reads the
  trail through WebDriver across a relaunch; macOS drives the same requests against the bundled harness.

## Sprint 3 gate (2026-10-08)

- `make verify` on macOS arm64: format, lint, mypy strict, boundaries clean; **273 passed, 2 deselected**
  (the two `desktop` tests), coverage 95%, 4 min 30 s (the A24 measurement is about 150 s of it).
- `make verify-linux` (container, linux/arm64, Python 3.12.12): **273 passed, 2 deselected**, coverage 95%.
- `make sat`: 13 passed on macOS; the same 13 in the container with `docs/evidence` mounted writable.
  Evidence records for A03, A04, A07, A08, A24, A25, A26, A27 and A33 on darwin-arm64 and linux-aarch64
  (24 records in `docs/evidence/` with Sprint 2's). ID trace for Sprint 3: all fifteen IDs covered.
- **A24 measured p95** (20 pause and 20 cancel phrases, each trial with its own hung worker, every
  processor saturated by busy processes): macOS arm64 pause 0.032 s, cancel 0.063 s (max 0.107 s);
  Linux arm64 container pause 0.300 s, cancel 0.249 s (max 0.307 s). Threshold 2 s, unchanged.
- Evidence outcomes, as the suite words each scenario: **A03 PASS, A24 PASS, A27 PASS**;
  **A04, A07, A08, A25, A26, A33 INSUFFICIENT_EVIDENCE** on both OSes, each because a part of the
  scenario names an object that does not exist yet (release pointers, a provider that keeps charging,
  paid calls and late receipts, promotion, the evaluation owner and production, a model or provider to
  switch under memory pressure). Every part that could be exercised passed; the records say which could not.
- `make desktop-build` then `make e2e` on macOS: renderer 19 passed (Playwright + axe on a real harness,
  including the keyboard-only pause, change, resume and cancel flow and the reload), shell 1 passed (Rust,
  real harness, including the menu's Pause and Cancel commands), built app 2 passed (lifecycle, and the hung
  job paused, resumed and cancelled through the requests the window and menu send, states read back after a
  relaunch). CI: `verify` and `desktop` green on `ubuntu-24.04` and macOS for the 3.6 push (run
  37830126122); on Linux the built app started the hung job from its window, pressed the real Ctrl+P and
  Ctrl+. shortcuts and read the trail through WebDriver, again after a second launch.
- Acceptance line ("start the hung test job from the app, pause, change a requirement, resume, cancel; the
  trail shows receipts and actual states, and survives an app restart"): shown by the renderer test
  (`work.spec.ts`, every step by keyboard, then a reload) and the built-app test (Linux with the real
  shortcuts and the trail read; macOS through the bundled harness with the window open). Not run by hand
  with the real macOS menu in this session (the owner's check).
- `integrity-reviewer`: REVIEW: PASS; two should-fix findings and five notes landed, one note logged
  (`docs/decisions.md`, 2026-10-08, "the integrity review").
- Gate outcome: **PASS** for Sprint 3 scope. Scenario outcomes are as listed; none is rounded up.

## Open defects and gaps

- Linux x86-64 is verified by CI only; the local container run is linux/arm64.
- macOS: the window's text is not read by any automated test (no WebDriver for WKWebView). The built-app
  tests check behaviour through the bundled harness: the window's own discovery, and in Sprint 3 the
  same requests the window and the menu send. The real Pause and Cancel menu items are exercised on
  Linux in CI and, on macOS, only as the request the shell sends (Rust test) and by the owner by hand.
- Linux: the desktop end-to-end test has run only in CI (x86-64). The AppImage is built but never
  launched. No Linux arm64 bundle is built.
- Jobs: a worker that dies is shown as running until the next operation touches its job (a lease,
  heartbeat, report, control or read reconciles the expired lease); no reconciler runs on a timer until
  the Sprint 4 runner. The only worker is the test worker, started outside the harness; a queued job
  waits for one. A checkpoint is recorded but nothing restores from it yet.
- Controls: a phrase with several live jobs needs clarification; only the job's own controls (buttons)
  name a job. There is no Resume menu item. Resume and admission are serialised on one aggregate; a
  revision followed by a crash before the hold leaves a job on the old revision until its next resume.
- Requirements: three change instructions are understood by a fixed grammar; a budget or evaluation
  change is refused because the owner action that would approve it does not exist yet.
- Admission: the local draft option is unqualified (no qualification report, isolation unknown) and is
  admitted for the test job by an explicit deviation; the plan outcome stays INSUFFICIENT_EVIDENCE.
- The A24 measurement takes about 150 s under full saturation and is in the gate (`slow`).
- Sleep and wake are not exercised on either OS. Choosing a folder in the native dialog is not automated.
- The feasibility rules do not yet filter on operation, region, egress, isolation policy or data rights.
- Discovery lists only NVIDIA accelerators on Linux and estimates available memory on macOS.
- A proposed OutputBinding declares `max_export_bytes` that nothing enforces yet.

## Waiting on the owner

Nothing. Standing approvals are in `docs/decisions.md`.

## Handoff note

Sprints 1 to 3 are built. Sprint 3 (prompts 3.1 to 3.7) is on `sprint-3-control`, pull request against
`main` titled "Sprint 3: jobs, admission, conversation and control"; merging is the owner's. **Next is
Sprint 4, prompt 4.1**, on a new branch from `main` once the pull request is merged.

Notes for the next session: the `harness` fixture serves the real app from the test process on a loopback
socket with a clock the test moves (`clock.advance(61)` expires a lease); the `worker` fixture starts
`fixtures/worker.py` as a real process (`heartbeat=0` makes it silent). Tests that admit more than one job
must fix the machine with `fixed_probes` (the Linux runner admits one test job on its own quota). Every
coordinator operation reconciles an expired lease first; a result commit needs the live attempt in a
result-accepting state; pause and cancel advance the fence. Admission commits request, reservation and
job together on the `admission:host-local` aggregate; resume rides the same aggregate and relies on Job
revision immutability against a racing transition. The window derives everything from `/v1/events`
(`trail.ts`: `trail`, `jobs`, `liveJob`, `expectedRevision`, `activity`); the Rust menu posts
`/v1/control`. `make e2e` needs `make desktop-build` after any Python change; the Rust build in a fresh
worktree takes several minutes. `make sat` writes evidence with `sprint=3` for the Sprint 3 scenarios;
the Linux records come from running `tests/sat` in the container with `docs/evidence` mounted writable,
and the Linux A44 record from the CI artifact. Run `uv run mypy` in the chain before every commit.
