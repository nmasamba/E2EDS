# STATUS

Resume point for every session. Read this first, then `docs/decisions.md`, then `AGENTS.md`.

## Now

- **Sprint:** 4 — M1 sandboxed native runner (B26; A28; R16; C14, C18; D01, D21).
- **Claimed prompt:** 4.7 (Sprint 4 gate): run; **HALT** on two macOS containment gaps that no
  Seatbelt rule closes (open defects, waiting on the owner).
- **Branch:** `sprint-4-runner`, from `main` at `0cb7674` (PRs #1 to #7 merged).

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
| 3 | M1 jobs, admission, conversation, control | merged to `main` (PRs #6, #7) | PASS for Sprint 3 scope, see below |
| 4 | M1 sandboxed native runner | on `sprint-4-runner`, pull request open; HALT | FAIL on macOS, PASS on Linux for Sprint 4 scope, see below |
| 5–11 | M1 | not started | — |
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
  shortcuts and the trail read; macOS through the bundled harness with the window open). Run by hand on macOS on
  2026-10-12: Pause from the real menu, the typed change and resume, and cancel through the menu's route
  all held; the Cancel run shortcut did not fire (open defect above).
- `integrity-reviewer`: REVIEW: PASS; two should-fix findings and five notes landed, one note logged
  (`docs/decisions.md`, 2026-10-08, "the integrity review").
- Gate outcome: **PASS** for Sprint 3 scope. Scenario outcomes are as listed; none is rounded up.

## Sprint 4 housekeeping (2026-10-12)

- Activity trail is the one place outcomes appear; `command.*` events carry the readable `reason`.
  Vitest 9 passed; Playwright work spec 3 passed (composer, buttons, a dropped request, Run and a refused
  admission). Guards mutation-checked: the not-received line only for an unanswered Run, the reason shown.
- Renderer shortcuts CmdOrCtrl+P and CmdOrCtrl+. on the live job; Playwright presses them on macOS (Meta).
  Guard mutation-checked: the platform's modifier. The built app's press is asked of the owner at the gate.
- Found and fixed: the harness published `harness.json` before listening (a client waited 10 s); a test
  connects to the published port before the server loop runs. Renderer suite on macOS: 20 passed.

## Prompt 4.1 — contracts for the runner (2026-10-12)

- App ComputeBinding 0.6.0 (OS-sandbox policy, `assurance`, darwin), CodeTask 0.1.0, Job 0.2.0; the loader
  dispatches on `schema_version`. The stored local binding `compute-local-native` 1.0.0 replaces
  `LOCAL_DRAFT`; admission stores and pins it and a stored CodeTask for every job, test-worker jobs included.
- Tests: `tests/contract/test_app_contracts.py` (9: app schemas meta-validate, the binding at OS-sandbox
  assurance on darwin and linux, a policy cannot claim another assurance, prior versions read, CodeTasks
  conform), `test_admission.py` (+2: binding and CodeTask stored and pinned, idempotent retry; undeclared
  input, duplicate name, missing source, over-envelope limit and a permission refused and recorded, no
  output refused before anything is written). `make test-fast` 288 passed on macOS. Guards mutation-checked
  (11): input captured, input names unique, source stored, limits within the envelope, no permission,
  caller sets only supplied fields, language Python or SQL, policy ties assurance and trust, Python
  declares an output, version dispatch, idempotency compares the payload.

## Prompt 4.2 — runner entry point and environment (2026-10-12)

- `src/dsp_runner` (`python -m dsp_runner <attempt>/task.json`), the shared process core
  `adapters/sandbox.py` (layout, fixed argv, scrubbed environment, wall clock, bounded tar channel),
  `Runner` in `ports.py`, app `RunnerResult` 0.1.0, `make runner-env` (0.4 s, rebuilt by `test-fast`,
  `sat`, `verify`; CI's verify job runs `make verify`). The boundary checker scans `src/dsp_runner`
  (contracts only, no `subprocess`) and now reads `from dsp import x` as `dsp.x`. Not reachable from the
  application; no sandbox yet.
- Tests: `tests/integration/test_runner.py` (8, real processes from the runner environment): Python and
  SQL outputs; undeclared reads (plain, swallowed, failing, SQL) and writes (path, `..`, symlink);
  output at, over and far over the cap; an exception, an exit status, a missing output, no result, three
  forged channels, a source that differs from its digest; the wall-clock limit kills the task and a
  process it started. `test_gate.py` +1 (the runner's imports), contract test +2 SQL cases. `make
  test-fast` 297 passed on macOS. Guards mutation-checked (19): the runner's allowed imports, `from dsp
  import`, the runner tree scanned, digests before running, undeclared read and write recorded, symlinks
  resolved, a refusal outranks its crash, DuckDB external access off, missing output, channel closed
  before exit, channel bounded while read, outputs summed against the cap, declared regular entries only,
  result validated, every output present, wall-clock deadline, group killed after the leader, SQL's one
  output (one found by the check: the refusal-over-crash case had no test; added).

## Prompt 4.3 — macOS sandbox adapter (2026-10-12)

- `adapters/seatbelt.py` (profile, sparse scratch image, jetsam limit and `CLOEXEC_DEFAULT` on the
  spawn, CPU poll), `adapters/seatbelt_child.py` (`sandbox_init`, then the runner in-process), the shared
  core as the `Confined` base with `sandbox.local()` choosing the OS's adapter. The runner's messages
  carry an OSError's errno and meaning, not its path. CI on `b8be28a` (the 4.2 push, run 38298066312):
  verify and desktop green on `ubuntu-24.04` and macOS.
- Tests: `tests/integration/test_containment.py` (10, `sandbox`, real tasks through libc past the audit
  hook): reads (planted secret, `~/.ssh`, the ledger, even `stat`) refused and the declared input read;
  writes by path, `..`, the inputs, a symlink and into the runner environment refused and scratch
  written; no connect to a loopback listener and no name resolved; only `HOME`/`TMPDIR` (and two the
  runtime adds) and only descriptors 0–4, an inheritable harness file left behind; fork, spawn and exec
  refused; memory over 256 MiB killed and 64 MiB allowed; CPU stopped with and without SIGXCPU
  ignored; scratch refuses at its size and is detached and deleted; wall time and output; a profile that
  does not compile runs nothing. `test_runner.py` now runs the core through a test-only `Unconfined`.
  macOS: 18 runner and containment tests pass; `make test-fast` 297 passed. Guards mutation-checked (16):
  deny by default, reads limited, metadata only on ancestors, writes only to scratch, no network, no
  process creation, environment scrubbed, only standard descriptors, memory limit on the spawn, an
  unexplained kill is memory, CPU poll, scratch volume capped, scratch volume detached, profile applied
  before the runner, a refused profile ends the process; the runner's CPU rlimit survives on macOS
  (the poll also stops the task) and is checked on Linux in 4.4. Two survivors on the first pass (metadata
  and inherited descriptors) led to sharper probes, then were caught.

## Prompt 4.4 — Linux sandbox adapter (2026-10-12)

- `adapters/bubblewrap.py` (bubblewrap, `prlimit --as`, the seccomp filter for x86-64 and aarch64);
  `sandbox.local()` chooses it on Linux; `chain()` is shared; `make verify-linux` installs bubblewrap
  and runs as an unprivileged user (`tools/verify_linux.sh`). **bubblewrap runs inside the
  verify-linux container** (linux/arm64, `seccomp=unconfined`, by owner approval), so the Linux sandbox
  tests run locally as well as on CI's `ubuntu-24.04`, where the verify job now installs bubblewrap.
- Tests: `test_containment.py` now 11, all on both OSes: + Python with a thread and DuckDB SQL run
  under the sandbox; the network test also tries a Unix listener by path and, on Linux, an abstract
  name; the process test also calls `clone3` directly on Linux; writes to `/` and `/dev/shm` refused.
  `make verify-linux`: format, lint, mypy, boundaries clean; **312 passed, 2 deselected**, coverage
  91.78%, 5 min 24 s. `make verify` on macOS arm64: **312 passed, 2 deselected**, coverage 91.11%,
  5 min 12 s.
- Guards mutation-checked on Linux (21): process creation refused but threads, the thread rule,
  `clone3` refused, the filter installed, the namespace alone (abstract socket), both network layers
  together, root read-only, `/dev` read-only, the attempt read-only, only the allowlist mounted,
  scratch tmpfs sized, `RLIMIT_AS`, inherited descriptors closed, environment scrubbed, signals relayed
  as 128 + n, the runner as first process, the runner's CPU rlimit (the 4.3 survivor, caught here),
  dies with its supervisor. Not caught: the socket rule alone (the namespace still refuses), logged;
  `clone3`'s ENOSYS rather than EPERM (threads do not use it on this glibc). Found by the checks: the
  first pass's survivors led to the thread, abstract-socket and `clone3` probes, and to dropping
  `--clearenv`, which duplicated the spawn's scrubbed environment.

## Prompt 4.5 — CodeTasks through jobs (2026-10-12)

- Coordinator: `execute`, `reconcile` (the tick), `tidy`; the harness's dispatcher and tick; app
  RunRecord 0.1.0 and Profile 0.1.0; the profiling recipe in the sandbox (`src/dsp/recipes`);
  `POST /v1/sources`; `dsp run-task`; `fixtures/tasks/read_secret.json`; the macOS orphan watcher; the
  trail's failure reasons. Run for real on macOS: `dsp run-task fixtures/tasks/read_secret.json` →
  `failed: undeclared_read: 1 open(s) outside the declaration; the OS answered PermissionError:
  [Errno 1] Operation not permitted`, exit 2.
- Tests: `tests/integration/test_runs.py` (9, sandbox): a sandboxed job commits a RunRecord naming its
  outputs, events replay; over the size cap fails, nothing stored; a late result after its fence moved
  is refused, nothing kept; cancel mid-run kills the task, no success, no artifact; the tick expires a
  dead attempt untouched; a lease expiring mid-run stops the run and attempt 2 commits; tidy finishes a
  crash between commit and storage; no runner environment refuses sandboxed work; a staged output
  changed after hashing is never stored. `test_containment.py` +1 (a dead harness ends its task);
  `test_profile_export.py` reworked (the recipe's logic unit-tested, the CLI path sandboxed); the
  built-app test profiles in the sandbox and sees the OS refuse `/etc/passwd`. Vitest 10, Playwright
  `runs.spec.ts` 1 (real sandboxed jobs in the trail). Guards mutation-checked (13): the tick expires
  due leases, the tick runs with the server, a stop request stops the run, a fenced attempt stops its
  run, outputs stored only after the commit, a refused result leaves no staging, a task's failure is
  final, stored bytes are the hashed bytes, tidy finishes a committed promotion, tidy clears a dead
  attempt, the dispatcher runs only sandboxed jobs, no runner no sandboxed job, the macOS orphan
  watcher. Found by the checks: a fenced run kept running until its end (now stops), and `tidy`'s
  live-attempt check could never matter under the lock (removed).

## Fixes after CI run 38305340576 (2026-10-12)

- CI on `addc8f7` (4.4): verify failed on `ubuntu-24.04` (every sandboxed task ended with status 1:
  bubblewrap could not build its namespaces there) and on macOS (the jetsam limit did not stop a 2 GiB
  allocation on GitHub's VM); the Linux desktop job's window showed "Resources not observed"; macOS
  desktop passed. Fixed in four commits: the harness's background work ends with its server (a stopped
  test server had kept a test process alive); macOS memory is also polled from the kernel's footprint
  (checked here with jetsam disabled: the poll alone stopped the task) and the runner keeps the OS's
  errno under a wrapper; CI gives `/usr/bin/bwrap` alone an AppArmor profile for user namespaces, then
  proves a sandbox can be built; the window reads the snapshot and plan again until a read succeeds.

## Prompt 4.6 — containment suite (2026-10-12)

- `tests/sat/test_sprint_04.py` (8, sandbox): a planted host secret and a key under `~/.ssh`; an HTTP
  fetch from a loopback listener and a name lookup; pip and a write into the runner environment; a
  state-folder file standing for a sealed partition; the ledger and the task's own declaration; fork
  and a shell's spawn; CPU, memory, wall time, output and scratch; the source and attempts kept. Each
  runs real Python through admission, the dispatcher and the OS sandbox, and writes its A28 part
  (`make sat`) at `os_sandbox_single_user` assurance. The evidence fixture records `assurance`.
- `make verify-linux` (container): **332 passed, 2 deselected**, coverage 90.15%, 6 min 07 s.
  `make verify` on macOS: **332 passed, 2 deselected**, 7 min 15 s of tests (one run's wall time was
  22 min, not reproduced: decisions, 2026-10-13); a rerun of the gate's pytest: 332 passed, coverage
  90%.

## Sprint 4 gate (2026-10-13)

- Shipped at 4.7: `dsp run-task`'s acceptance test and the overall A28 record (FAIL on an OS where a
  part failed, otherwise INSUFFICIENT_EVIDENCE with the missing parts named); `make sat-linux`; the
  integrity review's fixes (decisions, 2026-10-13): promotion checks a digest before it moves a file and
  finishes a part-way move, `tidy` sets aside once what it cannot finish (`.held`); Linux refuses
  `memfd_create` and `shmget`; a frozen harness uses only `DSP_RUNNER_ENV` and refuses an environment
  others could write; a failing watch kills and reaps the task first; no host path in a failure
  message; no outside lease of a sandboxed job; each A28 part requires the OS's own answer. After the
  first gate run: a sandbox that cannot start the task is a transient `sandbox_unavailable` failure,
  retried, not a stranded job; the window says why it could not read the snapshot ("Resources not read:
  <reason>") and calls an unanswered request "no answer"; the memory test removes its System V segment
  from outside the sandbox.
- Tests added at 4.7: `test_runner.py` +1 (a failure while a task runs leaves no task running);
  `test_runs.py` +3 (an environment others could write and a frozen harness's guess refused; no outside
  worker leases a sandboxed job; a sandbox that cannot start the task is retried) and the tidy test now
  covers a move stopped part-way; `test_containment.py`: C14 also reads the parent's environment
  through the process table, D21 also tries memfd and System V shared memory; `tests/sat/test_sprint_04.py`
  +1 (the acceptance line and the overall record). Guards mutation-checked: review fixes 9, 8 caught
  (digest before the move, an output already stored counts as moved, tidy holds what it cannot finish,
  the environment is the owner's alone, a frozen harness guesses no environment, a failing watch kills
  the task first, no host path in a message, no outside lease of a sandboxed job); the ninth, a
  file-size limit, survived because every writable file system is the sized scratch, so it was removed;
  memfd and `shmget` refused (Linux, 2, caught); a sandbox that cannot start the task caught and
  retried (2, caught); the memory test's segment removal (1, caught: without it 1 MiB was left).
- `make verify` on macOS arm64 (at `e6cf725`): format, lint, mypy strict, boundaries clean;
  **3 failed, 334 passed, 2 deselected**, coverage 90.68%, 7 min 05 s. Tail:
  ```
  FAILED tests/integration/test_containment.py::test_c14_the_task_sees_only_its_scrubbed_environment_and_standard_descriptors
  FAILED tests/integration/test_containment.py::test_d21_memory_past_the_limit_stops_the_task_and_memory_within_it_is_allowed
  FAILED tests/sat/test_sprint_04.py::test_a28_a_host_secret_cannot_be_read - a...
  3 failed, 334 passed, 2 deselected, 1 warning in 425.36s (0:07:05)
  ```
  The three are the two macOS gaps: C14 and the A28 host-secret part `assert True is False` (the
  harness's environment was read through the process table); D21 `{'shared': 1, 'sysv': 0}` (System V
  `shmget` made a segment). The run before it (at `b897ec6`) failed the same three; the one before that
  also failed the A28 bounds part on a spawn's `PermissionError` (fixed in `b897ec6`).
- `make verify-linux` (container, linux/arm64, at `e6cf725`): format, lint, mypy strict, boundaries
  clean; **337 passed, 2 deselected**, coverage 91.12%, 6 min 14 s. Tail:
  ```
  Required test coverage of 85% reached. Total coverage: 91.12%
  337 passed, 2 deselected, 1 warning in 374.01s (0:06:14)
  ```
- `make sat` on macOS (at `e6cf725`): **1 failed, 21 passed** in 4 min 24 s; the failure is the
  host-secret part (`assert True is False`: the harness's environment was read). `make sat-linux`
  (container, at `e6cf725`): **22 passed** in 3 min 53 s. Evidence for A28 (ten records per OS) and
  every earlier sprint's scenarios refreshed in `docs/evidence/`.
- **A28 outcomes, per part, at OS-sandbox single-user assurance:** Linux arm64: host-secret,
  network-fetch, dependency-install, final-set (a stand-in file), metadata-mutation, process, bounds
  (CPU, memory, wall time, output, scratch), preserved and the acceptance line all PASS; the overall
  record INSUFFICIENT_EVIDENCE (model-generated code and repairs need Sprint 5, sealed partitions
  Sprint 9, and the suite asks for a VM). macOS arm64: the same parts PASS except **host-secret FAIL**
  (the planted secret and `~/.ssh` were refused by the OS, but the harness's environment was read
  through the process table); the overall record **FAIL**. The macOS bounds part passes for the five
  limits it tests; System V memory outside the limit is the D21 test's failure, not part of that record.
- Acceptance line, run for real: macOS, `uv run dsp run-task fixtures/tasks/read_secret.json` →
  `failed: undeclared_read: 1 open(s) outside the declaration; the OS answered PermissionError: [Errno
  1] Operation not permitted`, exit status 2. Linux (container, the same command after the SAT) →
  `... the OS answered FileNotFoundError: [Errno 2] No such file or directory`, nonzero exit (`/etc` is
  not mounted in the sandbox at all). Both in `docs/evidence/A28-acceptance-read-secret-*.json`.
- `make desktop-build` then `make e2e` on macOS (at `b897ec6`; no Python or renderer change since):
  Vitest 10 passed, Playwright 21 passed, the shell's Rust test 1 passed, the built app 2 passed. No
  harness was left running afterwards this time.
- CI at the gate (run 38367812467, `509add9`): `verify (ubuntu-24.04)` pass (6 min 14 s), `desktop
  (ubuntu-24.04)` pass (10 min 13 s), `desktop (macos-latest)` pass (5 min 40 s), **`verify
  (macos-latest)` fail**: `3 failed, 334 passed, 2 deselected, 1 warning in 412.94s (0:06:52)`,
  coverage 90.92%, the same three tests. GitHub's runner image is `macos-26-arm64`, so both gaps hold
  on a second macOS 26 machine.
- ID trace (`tools/trace_ids.py 4`): A28, C14, C18, D01, D21, R16 covered; B26 is in test docstrings.
- `integrity-reviewer` (once, 249k tokens): REVIEW: PASS, six should-fix findings and five notes; all
  six fixed, notes 8 and 11 fixed, note 7 measured as worse (the process-table gap), notes 9 and 10
  logged for later sprints (decisions, 2026-10-13).
- Gate outcome: **FAIL on macOS** (two containment gaps, HALT below), **PASS on Linux** for Sprint 4
  scope. Scenario outcomes are as listed; none is rounded up.

## Open defects and gaps

- **HALT, open DEFECT (macOS): task code can read any of the owner's processes' arguments and
  environment.** `sysctl(KERN_PROCARGS2)` for the task's parent read the harness's environment; it works
  for any same-user process by ID. Measured on macOS 26.3.1 with no `sysctl-read` allowed at all, with
  `(deny process-info*)`, and with `kern.procargs2` denied by name: the read still succeeded. Tests
  `test_c14_…` and the A28 host-secret part state the policy and fail on macOS. Linux refuses it (no
  `/proc`, the task's own PID namespace).
- **HALT, open DEFECT (macOS): System V shared memory is not mediated.** `shmget` succeeds under the
  profile, also with `(deny ipc-sysv*)`, and the task's own `shmctl(IPC_RMID)` is refused (EPERM), so a
  segment outlives its task: up to `kern.sysv.shmall` (4 MiB) and 32 segments for the whole machine,
  outside the task's memory limit. Test `test_d21_memory_past_the_limit_…` fails on macOS (it now
  removes its own segment from outside). Linux refuses `shmget` and `memfd_create`.
- Linux desktop job on CI: the built app's window showed "Resources not observed" on run 38322576233
  while Python's read of the same harness succeeded. The gate's run (38367812467) passed, with the
  window now showing "Resources not read: <reason>" on failure; the earlier failure did not recur and
  its cause is not established.
- macOS: one gate run's dispatcher logged `PermissionError` starting a task (no traceback): which call
  refused is not established. It is now a retried transient failure, not a stranded job.
- macOS: after some `make e2e` runs a bundled harness was left running on one test's temporary profile,
  started by a process that had exited; origin not established (not seen in the 2026-10-13 run).
- One macOS gate run took 22 minutes of wall time against 7 to 8 minutes of tests; not reproduced.
- Logged from the review, not fixed: the Linux filter allows `execve` (a task can replace itself with
  the interpreter, still confined; there is no `/bin/sh`); admission accepts any captured DataManifest
  as an input and nothing reads the binding's `sealed_data_access: false` (Sprint 9 must exclude sealed
  manifests). A failure message is text the task chooses (up to 200 characters in the trail): Sprint 5
  must treat it as customer content before any of it reaches a prompt.
- Linux x86-64 is verified by CI only; the local container run is linux/arm64.
- macOS: the window's text is not read by any automated test (no WebDriver for WKWebView). The built-app
  tests check behaviour through the bundled harness: the window's own discovery, and in Sprint 3 the
  same requests the window and the menu send. The real Pause and Cancel menu items are exercised on
  Linux in CI and, on macOS, only as the request the shell sends (Rust test) and by the owner by hand.
- Linux: the desktop end-to-end test has run only in CI (x86-64). The AppImage is built but never
  launched. No Linux arm64 bundle is built.
- Jobs: a worker that dies is shown as running until its lease expires; the harness's tick (every
  second, Sprint 4) then reconciles it. Sandboxed jobs are run by the harness's own dispatcher, one at
  a time; a test job still waits for the outside test worker. A checkpoint is recorded but nothing
  restores from it yet.
- Controls: a phrase with several live jobs needs clarification; only the job's own controls (buttons)
  name a job. There is no Resume menu item. **Open DEFECT:** in the built macOS app Cmd+. cancels
  nothing. The owner's press on 2026-10-13: Cmd+P paused the job through the window's own handler;
  Cmd+. reached neither the window nor the native menu (no command arrived at the harness). Both
  chords work in Playwright and on Linux. Changing the chord is the owner's call (waiting on the
  owner). Action outcomes are shown in the activity trail only, with one wording (closed in Sprint 4
  housekeeping). Resume and admission are serialised on one aggregate; a
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

1. **HALT — the two macOS containment gaps** (open defects above). Options:
   - **A (default if told to proceed):** the harness restarts itself at launch with a minimal
     environment (so its own environment holds no secret); after every run it removes the System V
     segments the task created (by creator process ID, from outside the sandbox); the residual is
     recorded honestly: on macOS, task code can still read the arguments and environment of the
     owner's other programs, so no secret should sit in another program's environment while untrusted
     code runs. The two tests would then state that residual instead of the policy. No admin rights.
   - **B:** run tasks as a separate macOS user made for them (needs an admin to create the user and a
     privileged helper to switch to it): expected to close the process-table gap, since another
     user's process arguments are not readable without root (not measured here); System V segments
     would still need removing after each run.
   - **C:** a VM for task code on macOS (the suite's default, declined on 2026-10-01).
2. **Cmd+. in the built macOS app** reaches neither the window nor the native menu: choose another
   chord for Cancel run (for example Cmd+Shift+K) or keep it and rely on the button.
3. Merging the Sprint 4 pull request.

## Handoff note

Sprint 4 (prompts 4.1 to 4.7) is on `sprint-4-runner`, pull request against `main` titled "Sprint 4:
sandboxed native runner"; merging is the owner's. The gate is FAIL on macOS for two containment gaps
(HALT, waiting on the owner) and PASS on Linux. **Next is Sprint 5, prompt 5.1**, on a new branch from
`main`, once the HALT is decided and its fix (option A by default) has landed and the pull request is
merged.

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
worktree takes several minutes. `make sat` writes evidence for every sprint's scenarios on macOS and
`make sat-linux` in the container; the Linux A44 record comes from the CI artifact. Run `uv run mypy`
in the chain before every commit.

Sprint 4 notes: sandboxed tasks need `make runner-env` (the `runner_env` fixture refuses a stale one);
tests that run real tasks carry the `sandbox` marker, and one `executing` lock in the harness runs one
task at a time. On macOS each task mounts a scratch disk image (about 1.7 s); after interrupted runs,
detach only images under `pytest-of-…`, never the owner's. A macOS task's System V segment outlives
it (`ipcs -m`); remove only segments the tests' tasks made. `make verify-linux` runs bubblewrap
inside Docker with `seccomp=unconfined`; `/proc` cannot be mounted there.
