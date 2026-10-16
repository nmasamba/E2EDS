# STATUS

Resume point for every session. Read this first, then `docs/decisions.md`, then `AGENTS.md`.

## Now

- **Sprint:** 5 — M1 assistant gateway, open model first (B24, B26, B27; A24, A29, A30; R16, R17, R18,
  R22; D16, D17).
- **Claimed prompt:** 5.7, the gate, run on both OSes (below). **Not called done**: the live
  acceptance's generated-code part (A28) is FAIL on the known over-grouping, and on Linux the
  container cannot meet D17's deadline for the assistant's prompts (a measured fact). Everything
  else is green on both OSes. Next is Sprint 6, prompt 6.1. D3: A (Metal); D4: B; D5: A.
- **Branch:** `claude/sprint-5-assistant-gateway-fc1f11`, from `main` at `73698be` (PRs #1 to #8 merged).

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
| 4 | M1 sandboxed native runner | merged to `main` (PR #8) | PASS for Sprint 4 scope, see below |
| 5 | M1 assistant gateway, open model first | on `claude/sprint-5-assistant-gateway-fc1f11` | in progress |
| 6–11 | M1 | not started | — |
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
  <reason>") and calls an unanswered request "no answer"; the overall A28 record is FAIL on an OS where
  a part failed. Then the two macOS containment gaps were closed (below).
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
- Closing the two macOS gaps (`9be5f61`; decisions, 2026-10-13, "both macOS containment gaps
  closed"): the profile denies `process-info*` and allows sysctl reads by exact name only (eleven,
  measured from the sandbox's denial log), and denies every System V call by number, the multiplexers
  included; Linux also refuses `msgget` and `semget`. C14 also reads an unrelated sibling's
  environment; D21 also tries message queues, semaphores and the `shmsys` multiplexer and removes with
  `ipcrm` anything a task made. Mutation-checked: macOS 6 (the blanket sysctl allowance back, no
  `(deny process-info*)`, no System V rule, no multiplexers, no `msgget`, no `semget`), Linux 2 (no
  `msgget`, no `semget`), all caught; the sibling probe alone catches the old profile.
- `make verify` on macOS arm64 (at `9be5f61`): format, lint, mypy strict, boundaries clean;
  **337 passed, 2 deselected**, coverage 90.89%, 6 min 57 s. Tail:
  ```
  Required test coverage of 85% reached. Total coverage: 90.89%
  337 passed, 2 deselected, 1 warning in 417.52s (0:06:57)
  ```
  The earlier runs failed on the two gaps: at `e6cf725` and `b897ec6` 3 failed, 334 passed (C14, D21
  and the A28 host-secret part), and the first also failed the A28 bounds part on a spawn's
  `PermissionError` (fixed in `b897ec6`).
- `make verify-linux` (container, linux/arm64, at `9be5f61`): format, lint, mypy strict, boundaries
  clean; **337 passed, 2 deselected**, coverage 90.98%, 6 min 29 s. Tail:
  ```
  Required test coverage of 85% reached. Total coverage: 90.98%
  337 passed, 2 deselected, 1 warning in 389.91s (0:06:29)
  ```
- `make sat` on macOS (at `9be5f61`): **22 passed** in 4 min 21 s. `make sat-linux` (container, at
  `9be5f61`): **22 passed** in 3 min 44 s. Evidence for A28 (ten records per OS) and every earlier
  sprint's scenarios refreshed in `docs/evidence/`.
- **A28 outcomes, per part, at OS-sandbox single-user assurance, the same on macOS arm64 and Linux
  arm64:** host-secret (a planted secret, `~/.ssh`, and the harness's environment through the process
  table), network-fetch, dependency-install, final-set (a stand-in file), metadata-mutation, process,
  bounds (CPU, memory, wall time, output, scratch), preserved and the acceptance line all PASS; the
  overall record INSUFFICIENT_EVIDENCE (model-generated code and repairs need Sprint 5, sealed
  partitions Sprint 9, and the suite asks for a VM). At `e6cf725` the macOS host-secret part and the
  overall record were FAIL.
- Acceptance line, run for real at `9be5f61`: macOS, `uv run dsp run-task fixtures/tasks/read_secret.json`
  → `failed: undeclared_read: 1 open(s) outside the declaration; the OS answered PermissionError:
  [Errno 1] Operation not permitted`, exit status 2. Linux (container, the same command after the SAT)
  → `... the OS answered FileNotFoundError: [Errno 2] No such file or directory`, nonzero exit (`/etc`
  is not mounted in the sandbox at all). Both in `docs/evidence/A28-acceptance-read-secret-*.json`.
- `make desktop-build` then `make e2e` on macOS (at `9be5f61`): Vitest 10 passed, Playwright 21
  passed, the shell's Rust test 1 passed, the built app 2 passed. No harness was left running.
- CI at the first gate push (run 38367812467, `509add9`): `verify (ubuntu-24.04)`, `desktop
  (ubuntu-24.04)` and `desktop (macos-latest)` pass; `verify (macos-latest)` failed on the same three
  tests on GitHub's `macos-26-arm64` image. On the fix (run 38379462014, `a58ad3b`) both
  verify jobs and macOS desktop passed and the Linux desktop job failed on the test's race (open
  defects); on its fix (run 38380964046, `c367957`) **all four pass**: `verify (ubuntu-24.04)` 6 min
  29 s, `verify (macos-latest)` 6 min 47 s, `desktop (ubuntu-24.04)` 10 min 31 s, `desktop
  (macos-latest)` 7 min 43 s.
- ID trace (`tools/trace_ids.py 4`): A28, C14, C18, D01, D21, R16 covered; B26 is in test docstrings.
- `integrity-reviewer` (once, 249k tokens): REVIEW: PASS, six should-fix findings and five notes; all
  six fixed, notes 8 and 11 fixed, note 7 measured as worse (the process-table gap), notes 9 and 10
  logged for later sprints (decisions, 2026-10-13).
- Gap investigation (at the owner's request, after the gate's CI read): one workflow, 9 agents, 1.05M
  tokens; five investigators and an adversarial verifier per claimed closure (decisions, 2026-10-13).
- Gate outcome: **PASS** on macOS and Linux for Sprint 4 scope. Scenario outcomes are as listed; none
  is rounded up.

## Sprint 5 housekeeping (2026-10-15)

- D1 = A: Cancel run is `CmdOrCtrl+Shift+K` in the renderer's chord table, the native menu, the Playwright
  work spec (Meta+Shift+K on macOS) and the Linux built-app test (real Ctrl+Shift+K through xdotool).
  Playwright work spec on macOS: 3 passed. Guard mutation-checked: the old chord back in the renderer
  fails the spec. The built macOS app's press is the owner's, at the gate.

## Prompt 5.1 — gateway, binding, supervisor, SecretPort (2026-10-15)

- `ports.py`: `SecretStore`, `ModelGateway`, `ModelServer`. `adapters/llama_server.py`: the launch contract
  as this build's proven flags; the model's size and SHA-256 checked at every start (2.67 s for 5.03 GB);
  the key from the secret store into a 0600 file (`--api-key-file`), never argv or environment; Seatbelt
  deny-by-default profile through `sandbox-exec` on macOS (loopback listener only, Metal allowed by name),
  bubblewrap with every namespace new on Linux (a UNIX socket: logged DEVIATION); memory polled on macOS,
  `prlimit --as` on Linux; readiness is `/health` plus the typed `report_ready` probe; a hang, a crash, a
  limit or a deadline ends in ASSISTANT_UNAVAILABLE. `adapters/secrets.py`: the keychain through the
  Security framework's C API; `secret-tool` or an owner-only file on Linux. `application/assistant.py`:
  the suite's AssistantModelBinding 0.3.0 for the local model, planning until observed; the harness starts
  the assistant in a thread after the workspace is up, watches it (three restarts after a crash, none after
  a verification failure) and stops it on quit; `GET /v1/assistant`; events `assistant.ready` (pins the
  stored, observed binding) and `assistant.unavailable`. The window's header and trail show the state.
  `make live` (macOS) and `make live-linux` (D2: llama.cpp b11104 built in the container into a named
  volume, the model mounted read-only); `make verify` deselects `live_model`.
- Tests: `tests/unit/test_llama_server.py` (5: the flags, the macOS profile, the Linux vector, size and
  hash refusals, the binding record); `tests/integration/test_secrets.py` (3: get, put, replace, missing on
  the OS's store — a throwaway keychain here; the file fallback's modes and a readable folder refused; the
  OS's choice); `tests/integration/test_assistant.py` (1: the workspace opens with the model absent, says
  `model missing`, rejects an instruction and still answers a control); `tests/integration/
  test_live_gateway.py` (6, `live_model`: ready only after health and the typed probe, the key in no
  process's arguments or environment, slots, metrics and web UI off, thinking off, the tokenizer; model
  missing, wrong size and a right-sized sparse file refused before any load; the key reused from the store
  and generated once; the real keychain holds it; A30: under the server's own profile an outbound connect
  and a name lookup are refused while the server keeps answering; the harness reports ready and stores the
  observed binding). Vitest 11 (the assistant view from events only). Playwright status spec 17 (the
  header and trail say `assistant unavailable: model missing`). On macOS: `make test-fast` 304 passed,
  live gateway 6 passed.
- Guards mutation-checked (16, all caught; decisions 2026-10-15 "guards mutation-checked (5.1)"): size,
  hash, stale server only when ours, port held refused, deny default, `--unshare-all`, keychain replace,
  fallback permissions, key as a file (flag and value), outbound denied, the probe decides readiness,
  `--no-slots`, `--reasoning off`, quit stops the server, a readiness failure stops the server. Found by
  the checks: a server that answered health but failed readiness was left running (fixed, with a test).
- `make live-linux` (container, linux/arm64, CPU only): the first run failed on `ps` truncating the
  command line and on the A30 probe's binds placed after the root was made read-only (both in the tests),
  the second on the quit test's 90 s wait, the third and fourth on the kernel killing one of two servers
  (the VM holds 7.75 GiB; decisions 2026-10-15 "one model server at a time"); with the quit test lending
  the session's server: **7 passed** in 1 min 55 s (container, linux/arm64, CPU only). On macOS the same
  file: 7 passed, three runs; one earlier full run failed the quit test while the container run shared
  the processors and its output was not kept (open defect below).

## Prompt 5.2 — tool dispatcher and loop (2026-10-15)

- An instruction the assistant can take is admitted as a Job (0.3.0: an assistant task names its
  command; a child job names its parent) and the command is `accepted` with the job as its effect;
  `application/assistant.py::run` is the application-owned loop (the harness's `attend` worker, one job
  at a time): the context is rebuilt from canonical records on every generation, each generation is an
  app AssistantCall 0.1.0 record (dispatched before the tool runs, committed with the quoted result, or
  refused with its code), the checks run in order (schema, principal, revision, scope, budget, fence)
  and D17's counters are sums over the records (20 model calls, 2 repairs, 1,800 s; 6,144 in and 2,048
  out and 300 s per generation). `application/tools.py` is the skill's eight tools and nothing else;
  `inspect_schema` and `submit_code_task` run as child jobs through Sprint 4's admission and sandbox
  unchanged; pause and cancel cascade from a parent to its children and the phrases and the window's
  controls address the parent; a call interrupted between dispatch and commit stays dispatched and runs
  again on resume, resuming a paused child rather than starting it over. Generations stream so a pause
  stops one between tokens; the job heartbeats from the loop's thread. CodeTask 0.2.0 adds `assistant`.
- Tests: `tests/integration/test_assistant_loop.py` (8, the scripted gateway on a real harness): an
  invalid call, an unknown tool, two calls in one turn and arguments that are not JSON are each
  refused, quoted back and counted; the input-token and generation-second budgets stop the task and a
  gateway fault fails it; the twenty-first model call is never made; a call proposed after a pause
  never dispatches and resume replays the committed call once; revision, scope and repair-budget
  refusals in order and a budget change refused for the owner; a principal without the scope refused
  after the schema; injected "ignore the budget" text in a CSV header (tool output) and in a task's
  failure message has no effect (`sandbox`); with a parent and its running child live, "pause now"
  pauses both and resume resumes the child (`sandbox`). Contract tests: the three Job versions and
  the assistant CodeTask. Vitest 12 (a child addressed through its live parent; assistant lines are
  proposals). Playwright 21 passed (an instruction is rejected with the assistant's real reason).
- Guards mutation-checked (17, all caught; decisions 2026-10-15 "guards mutation-checked (5.2)"). Found
  by the checks: a duplicate owner-path refusal (removed) and a test that could not tell the assistant
  check from admission's (fixed).

## Prompt 5.3 — intent extraction (2026-10-15)

- `propose_requirement_patch` is a JSON Patch applied whole (`workloads.apply_patch`: add, replace,
  remove, lists by index or `-`) with one provenance entry per patched path: the exact words of the
  instruction (a span that is not in the message is refused), the model's confidence and the
  materiality, recorded on the revision as `proposed` (the grammar's own change stays `confirmed`);
  the `workload.revised` event carries the diff and a plain readback the application writes, shown in
  the trail. Grounding checks before anything applies: no number the instruction does not contain, no
  removal of a field it does not name, no empty or no-op patch without a question. The requirements'
  own rules then complete a patch: a predictor in neither feature list is excluded, an added output
  transform puts privacy under review, a row identifier must remain, a field in both lists is refused.
  A question (with or without a patch, which applies first) ends the command `needs_clarification`;
  a proposal on the owner's budget path ends it `rejected` with REQUIRES_CONFIRMATION. A message that
  opens with an exact control phrase is that control first, settled before the model sees anything,
  then its own instruction command (`<id>:then`). The interpretation policy of the suite's reference
  table is in the model's instructions as numbered procedures; typed proposals run at temperature 0,
  seed 1 (a logged deviation from the example's 0.7).
- Tests: `tests/unit/test_intent.py` (12: patches applied or refused whole, the readback, the leading
  phrase, the completion rules); `test_assistant_loop.py` +4 scripted (provenance verbatim and
  covering, recorded as proposed with the readback; a question needs clarification and a budget
  proposal needs the owner; "Pause now; exclude region before continuing" pauses first and keeps the
  work paused; an invented number, an unnamed drop and a no-op patch are refused);
  `tests/integration/test_live_intent.py` (1, `live_model`): the five reference instructions against
  the real model, one A29 evidence record per binding.
- Guards mutation-checked (18, all caught; decisions 2026-10-15 "guards mutation-checked (5.3)").
- **Live result, binding `assistant-local-qwen` (Metal, seed 1, temperature 0), 2026-10-15:** all five
  as the suite describes on the final run: `use account_num as the ID` added an entity_id string role
  excluded from predictors (one operation; the row id kept); `keep the feature set minimal` set the
  soft objective and asked the counting question (`needs_clarification`); `anonymise regression
  results by rounding to the nearest 10` added the typed transform (increment 10, ties away from zero)
  and the privacy status went under review; `Pause now; exclude region before continuing` paused the
  running job, then moved `region` from allowed to excluded with the job still paused;
  `spend another £100` was proposed on the budget path and refused for the owner (the model wrote
  110000 minor units, which is £1,100: its arithmetic, logged). Earlier runs, before the grounding
  checks and the procedural rules, failed every case (decisions, 2026-10-15): the model repurposed
  the row id, set a hard maximum of 2, rounded to even, deleted a role instead of excluding a field,
  and answered the budget change in prose. Results are per binding and not merged.

## Prompt 5.4 — generate, run, repair (2026-10-16)

- "Redacted" is defined in `docs/decisions.md` before the code: the job's state, a failure's kind and at
  most 200 characters of its message as quoted data, each output's name, size and digest, and for one
  named output a bounded preview (a CSV's header and first 20 rows with cells cut at 200 characters,
  or the first 2,000 characters of a JSON or text file). `inspect_results` gives that preview; a repair
  is a new artifact naming the failed one, at most two per task (5.2's counter); the model's
  instructions carry the data procedure (name the input as the data's name, query it as a table, one
  CSV output, read the failure, repair, resubmit) and that a data request is done only by a code task.
  `GET /v1/artifacts/{sha256}` serves a committed artifact by digest; the window's Results section
  lists each succeeded job's CSV outputs from its RunRecord and opens one as a table of cells; the
  `data.captured` event carries the capture's digest; a granted file is named by its own label. The
  5.2 check that refused a code task once the requirements moved past the job's revision is removed
  (the task's own patch tripped it; an outside change holds the task anyway). The Sprint 4 SAT's
  wording that no generated code existed is replaced.
- Tests: `test_assistant_loop.py` +1 (`sandbox`: a failing SQL task repaired once, the quoted failure,
  the bounded preview, a third repair refused, the committed table equal to DuckDB's, the artifact
  route's refusals, the preview bounds); `tests/integration/test_live_generate.py` (1, `live_model`
  and `sandbox`: the acceptance instruction on the orders fixture, an A28 part per binding);
  `test_grants.py` +1 (a granted file by its own name); Playwright `runs.spec.ts` +1 (a committed table
  opens from its record as cells; a profile's JSON is not listed). Vitest 13 passed, Playwright 2
  passed on the runs spec.
- **Live result, binding `assistant-local-qwen` (Metal, seed 1, temperature 0), 2026-10-16: FAIL as
  asked, right for what it chose.** The model inspects the schema, writes SQL, runs it in the sandbox,
  inspects the result and answers from it (5 generations, about 35 s, 0 repairs), but groups by
  `region` and `service_level`: eight rows whose values are DuckDB's mean `actual_transit_hours` per
  (region, service level), not the two rows per service level the independent query gives. Identical on
  four runs under three wordings of a rule against added groupings; not tuned further (open DEFECT
  below; decisions 2026-10-16). Each earlier failure was a product gap, fixed: prose instead of a task,
  the granted file's label as a path, the input queried as a file, resubmissions refused as stale.

## Prompt 5.5 — failure and independence (2026-10-16)

- Every failure of the model ends in `assistant unavailable` with its reason, the conversation and the
  controls untouched and no other model tried: a missing model or binary and a size or hash mismatch
  are verification failures the watch never retries (final until the harness restarts); out of memory
  is the footprint poll's kill on macOS (`prlimit` on Linux) before the server is ever ready; a hung
  server is killed at the generation deadline, the task fails with "no answer within the N s generation
  deadline", the command is rejected with it, `status` still answers, and the watch restarts the same
  binding (at most three times); a harness restart expires the dead attempt's lease and the next
  attempt rebuilds its context from the committed AssistantCall records, so no committed call is
  dispatched twice. A tokenizer call that cannot reach the server fails the task with
  `ASSISTANT_UNAVAILABLE` instead of leaving the job leased.
- Tests: `test_assistant.py` +2 (`slow`: a right-sized file with other bytes, and a missing binary,
  each refused with its reason, no server process, the instruction rejected, a control phrase
  answered, one `assistant.unavailable`; a harness that dies mid-generation and its successor on the
  same ledger: attempt 2 replays the committed call, dispatches nothing twice, and the first harness's
  loop wakes fenced out); `test_live_failure.py` (3, `live_model`): A24 under a hung generation
  (SIGSTOP on the real server, every processor busy, 20 pause and 20 cancel trials on hung jobs, the
  hung assistant job's own pause durable at once, nothing dispatched afterwards, the generation ending
  when the server resumes), the deadline (5 s: killed, failed, rejected, restarted on the same binding,
  a new instruction succeeds), out of memory (a 0.5 GiB limit: never ready, nothing of it left). A30's
  offline part is the 5.1 probe test's evidence. `make sat` and `make sat-linux` now leave `live_model`
  out, as `make verify` does.
- Live result on this Mac (2026-10-16): `uv run pytest tests/integration/test_live_failure.py` →
  `3 passed in 268.06s (0:04:28)`, no server left running (A24 PASS: pause and cancel p95 within 2 s;
  the measured values are the record `make live` writes at the gate). The two earlier runs found two
  test defects, both fixed (decisions 2026-10-16): the harness fixture's quit was not joined, so one
  test's stop could kill the server the next test had just been lent; and the deadline test read the
  events before the watch's one-second tick.
- Mutation checks (`mutate55.py`, scratch): 4/5 caught — the context rebuilt from records, the deadline
  kill, the watch's restart, the memory poll; `verification-final` survived because the branch was
  dead code (the watch never restarted from unavailable), fixed and caught in 5.6 (decisions
  2026-10-16).
- The 5.4 CI read (run 38895075855, cancelled after 37 min): the corrupt-model test failed on both
  OSes (the binary is checked before the hash; CI has no llama-server) and its failed assertion left
  the inline harness's threads alive, so pytest never exited; the Sprint 1 SAT profile test got exit 2
  from the CLI on macOS only (output not shown; a cold harness had 10 s, now 30 s); the Linux built app
  did not end within 20 s of a real window close. The first two are fixed and verified here (the
  corrupt test reproduced and then passed with a HOME that has no binary); the third is open (below).
  `make test-fast`: 333 passed with the fixture join. One run of the Sprint 1 SAT and llama-server
  unit tests had one failure while the live file ran; it passed three times after and the failing test
  was not captured.

## Prompt 5.6 — remote OpenAI-compatible binding, D4 = B (2026-10-16)

- The app owns `AssistantModelBinding` 0.4.0, the remote mode only (a local binding keeps the suite's
  0.3.0): provider and model, `endpoint.base_url` (http, https or `unix://`) and `api_key_ref`,
  `placement`, `data_policy` (`none` or `synthetic_fixtures_only`; sealed data and secrets `false` by
  the schema), `spend` (price per million tokens, owner-approved, when), the D17 limits with
  `max_external_charge_minor` as the spend limit, `remote_fallback: false`, `observed` once ready.
  `OpenAICompatible` sits behind the same port: policy (`none` refuses before the key is read), key
  from the secret store (none: the exact `security` / `secret-tool` commands of D4 in the reason), the
  model in `GET /v1/models` (401/403: "the endpoint refused the key"), then the same typed probe as
  the local server; a call whose projected charge would pass the limit is refused before it is sent;
  the count is the endpoint's tokenizer or, on 404, one token per two bytes. The harness opts in by
  `<profile>/assistant/binding.json`; an invalid record leaves the assistant unavailable with its
  first schema error and the local model is never tried instead. The ready event carries placement,
  policy, spend and limit; the header shows `assistant ready (profile · remote <host> · synthetic
  fixtures only · spend limit £0.00)` and the trail's ready line the same, before the first
  instruction. No proprietary adapter (D4 = B). The supervisor's restart bound is now real: a death
  or a failed launch is started again at most three times in one harness's life; failures no restart
  can change are final at once (found by the 5.5 mutation check; decisions 2026-10-16).
- Tests: `tests/unit/test_remote_binding.py` (3: the schema's refusals, the charge arithmetic, the
  account and the socket client); `tests/integration/test_remote_harness.py` (4, no model: the opt-in
  file without a key is unavailable with how to store one, final, no local server; an invalid record;
  policy, key and endpoint refusals in that order against the harness's own address as a 404 and 401
  endpoint; the charge refused before sending and the two-bytes bound); `test_assistant_loop.py` +1
  (a server dead at every tick: four ready, four unavailable, then nothing more); the corrupt-model
  test waits two ticks for no second attempt; `tests/integration/test_live_remote.py` (4,
  `live_model`): ready on llama-server itself with the policy shown, the server's own tokenizer, "7
  times 8" answered, the local binding never named; a wrong model, a refused key and an unaffordable
  probe each unavailable once with its reason. Vitest +1 (the remote view and the ready line).
- Results on this Mac (2026-10-16): unit 3 passed; `test_remote_harness.py`, `test_assistant.py` and
  `test_assistant_loop.py` 21 passed (the three `sandbox` tests after `make runner-env`, which the new
  contract file made stale); `test_live_remote.py` 3 passed then the fourth after a helper fix:
  `3 passed, 1 error in 42.57s` then `1 passed, 3 deselected in 29.34s` for the fourth (the helper
  passed `provider` twice); `make test-fast` → `342 passed, 64 deselected, 1 warning in 152.21s`
  (a first run refused two test modules with one basename; the integration one was renamed);
  vitest 13 passed; `uv run python tools/trace_ids.py 5` names no missing ID once D16 and R22 are
  cited by the out-of-memory and the generate-run-repair tests.
- Mutation checks (`mutate56.py`, scratch): 10/10 caught — the `none` policy refused before the key;
  no key refused; 401 named as a refused key; the spend guard; the two-bytes bound; the opt-in file
  read; a verification failure final (the 5.5 survivor, caught now); the restart bound; the policy
  shown in the ready event; the model checked against what is served.
- Two processes left by earlier runs were found and killed (a llama-server from the 5.5 out-of-memory
  mutation, which held port 8081, and a pytest hung since before this session's compaction on the
  restart test); the out-of-memory test now stops its adapter in a `finally` (decisions 2026-10-16).

## Sprint 5 gate (2026-10-16)

- `make verify` on macOS arm64 (at `4eef69d`): format, lint, mypy strict, boundaries clean;
  **388 passed, 18 deselected**, coverage 88.31%, 7 min 50 s. Tail:
  ```
  Required test coverage of 85% reached. Total coverage: 88.31%
  388 passed, 18 deselected, 1 warning in 470.91s (0:07:50)
  ```
- `make verify-linux` (linux/arm64 container) at `4eef69d`: **1 failed, 387 passed** — the stale-server
  check shelled out to `ps`, which the plain verify container lacks (decisions 2026-10-16; on Linux it
  now reads `/proc/<pid>/cmdline`). Rerun with the fix: **388 passed, 18 deselected**, coverage 86.33%,
  6 min 49 s. Tail:
  ```
  Required test coverage of 85% reached. Total coverage: 86.33%
  388 passed, 18 deselected, 1 warning in 409.88s (0:06:49)
  ```
- The integrity review (PASS, two should-fix, six notes; decisions 2026-10-16) and its fixes landed
  after those two runs, so both gates are rerun on the final commit below.
- Final runs at `f4c6690` (the review's fixes and the `ps` fix):
  - `make verify-linux`: **389 passed, 18 deselected**, coverage 88.12%, 7 min 4 s. Tail:
    ```
    Required test coverage of 85% reached. Total coverage: 88.12%
    389 passed, 18 deselected, 1 warning in 424.23s (0:07:04)
    ```
  - `make verify` on macOS: **1 failed, 388 passed** in 8 min 3 s — the Sprint 4 CPU-time containment
    test, on the intermittent `killpg` EPERM (open defects below; the test passed three times alone
    right after). Tail:
    ```
    FAILED tests/integration/test_containment.py::test_d21_cpu_time_past_the_limit_stops_the_task_even_when_it_ignores_sigxcpu
    1 failed, 388 passed, 18 deselected, 1 warning in 483.76s (0:08:03)
    ```
- Final runs at `937e42b` (every fix of the gate in):
  - `make verify` on macOS: **392 passed, 18 deselected**, coverage 89.15%, 8 min 14 s. Tail:
    ```
    Required test coverage of 85% reached. Total coverage: 89.15%
    392 passed, 18 deselected, 6 warnings in 494.78s (0:08:14)
    ```
  - `make verify-linux` at `937e42b`: 1 failed, 391 passed — the new symlink unit test read the macOS
    profile text on Linux; the test now reads the confinement each OS builds (`2712b6b`, a test-only
    change, 10 unit tests passing on macOS). Rerun at `2712b6b`: **392 passed, 18 deselected**,
    coverage 88.36%, 7 min 2 s. Tail:
    ```
    Required test coverage of 85% reached. Total coverage: 88.36%
    392 passed, 18 deselected, 1 warning in 422.97s (0:07:02)
    ```
- **Gate outcome:** macOS arm64 — verify, SAT, desktop build, end-to-end, the Playwright acceptance
  spec, A24, A29 and A30 green; A28's generated-code part FAIL (the over-grouping). Linux arm64
  (container) — verify and SAT green; the live suite red by the D17 deadline fact (four tests).
  `tools/trace_ids.py 5`: every ID in scope is in a test docstring or an evidence record. The
  `[s5] chore: sprint 5 complete` commit is not made: two live records are red.
- **CI at the gate** (run 38950633517 at `2712b6b`, the one read): `desktop (macos)` passed; `verify`
  failed one test on each OS and `desktop (ubuntu)` one, all three test races (decisions
  2026-10-16: a liveness helper reading `/proc` of a task that had just ended; a message test's
  expected event order on a slow runner, now fixed by the `harness` fixture waiting for the
  assistant's first event; the window check waiting for the plan's line). Fixed and pushed; the
  pull request's checks carry the result (no further read, the three read points being spent).
- `make sat` on macOS at `f4c6690`: **22 passed** in 3 min 47 s (every sprint's acceptance tests, the
  `live_model` ones left to `make live`); evidence rewritten under `docs/evidence/`. Tail:
  ```
  22 passed, 6 warnings in 227.66s (0:03:47)
  ```
- `make sat-linux` (linux/arm64 container) at `f4c6690`: the first run refused pytest's marker
  expression (the quotes were lost on the way into the container; decisions 2026-10-16, fixed in the
  Makefile); the rerun **22 passed** in 3 min 32 s, evidence copied out. Tail:
  ```
  22 passed, 1 warning in 212.88s (0:03:32)
  ```
- `make desktop-build` then `make e2e` on macOS at `f4c6690`: the bundle built (`DS Playground.app`);
  vitest **13 passed**, Playwright **22 passed** (50.5 s; the `@live_model` spec left to `make live`),
  the Rust shell test **1 passed**, the built-app tests **2 passed** in 23 s. Tail:
  ```
  22 passed (50.5s)
  test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 2.73s
  2 passed, 5 warnings in 22.97s
  ```
  (pytest's temp cleanup warned about a scratch image the failed CPU-time test had left mounted;
  detached by hand under `pytest-of-nm`.)
- `make live` on macOS, with `/usr/bin/log stream` watching for Seatbelt denials throughout:
  - first run at `f4c6690`: the `@live_model` Playwright acceptance spec failed before the first
    keystroke, the harness it started saying "the model server exited with status 1" four times; the
    watch showed Seatbelt denying the server its own key file, named through `/var` instead of
    `/private/var` (decisions 2026-10-16; the adapter now resolves its paths, `5f2cec9`). Tail:
    ```
    Received string:    "version 0.1.0 · process 81896 · assistant unavailable: the model server exited with status 1"
    1 failed
    make: *** [live] Error 1
    ```
  - second run at `5f2cec9`: the acceptance spec **passed in 72 s** (type the instruction, the first
    tool call in the trail, pause by the chord, the job paused, Resume, the proposal line, the table
    opened); then every Python live test errored at setup, "127.0.0.1:8081 is held by another
    process": the spec's plain kill of its harness had left the model server running (decisions
    2026-10-16; the spec now quits through `/v1/shutdown`). Tail:
    ```
    ✓  1 tests/live.spec.ts:23:1 › @live_model A28, A24: type the instruction, see real progress, pause mid-run, resume, open the table (1.2m)
    3 passed, 392 deselected, 6 warnings, 13 errors in 7.15s
    ```
  - third run (the spec quitting its harness): the acceptance spec **passed in 66 s** again; the
    Python suite then ran: 10 passed, but the acceptance, intent and remote tests saw the model
    server gone ("the model server did not answer (ConnectError)", 0 generations): the gateway
    file's quit test (D24) stops the session's server, and only the failure tests' wrapper revived
    it; the shared wrapper now revives a stopped session server for every later harness, and the
    remote fixture revives it before reading the served models (decisions 2026-10-16). Tail:
    ```
    ✓  1 tests/live.spec.ts:23:1 › @live_model A28, A24: type the instruction, see real progress, pause mid-run, resume, open the table (1.1m)
    2 failed, 10 passed, 392 deselected, 6 warnings, 4 errors in 303.45s (0:05:03)
    ```
  - fourth run (the shared wrapper reviving the server): the acceptance spec **passed in 66 s**;
    Python **12 passed, 4 failed** in 6 min 30 s — the model refused the essay the hung-generation
    test needed (answered in 1.3 s), two readiness waits were 20 s against a 25 s restart, the quit
    test read the key file before the stop had unlinked it, and the "minimal features" case ended on
    an empty answer the loop accepted (decisions 2026-10-16: all four fixed; an empty answer is now
    refused). A24 under a hung generation was already recorded PASS by the third run (p95 pause
    0.019 s, cancel 0.036 s). Tail:
    ```
    ✓  1 tests/live.spec.ts:23:1 › @live_model A28, A24: type the instruction, see real progress, pause mid-run, resume, open the table (1.1m)
    4 failed, 12 passed, 392 deselected, 6 warnings in 390.48s (0:06:30)
    ```
  - fifth run (the four fixes): the acceptance spec **passed in 78 s**; Python **14 passed, 2 failed**
    in 7 min 5 s: A28's generated-code part FAIL on the known over-grouping (8 rows by region and
    service level, values equal to DuckDB's for that grouping; 5 generations, 37 s, 0 repairs), and
    A29 with four of the five reference instructions as described and "keep features minimal" not:
    the model set the soft objective and answered instead of asking about a hard maximum (the
    intent test's step summary printed that answer as empty; it was not). The watch saw, of ours,
    only the known benign denials plus `file-read-metadata /private/var/db/timezone/zoneinfo`; no
    sysctl was asked for. Tail:
    ```
    ✓  1 tests/live.spec.ts:23:1 › @live_model A28, A24: type the instruction, see real progress, pause mid-run, resume, open the table (1.3m)
    FAILED tests/integration/test_live_generate.py::test_a28_the_acceptance_instruction_yields_a_committed_table_equal_to_duckdb
    FAILED tests/integration/test_live_intent.py::test_a29_the_five_reference_instructions
    2 failed, 14 passed, 393 deselected, 6 warnings in 425.72s (0:07:05)
    ```
- `make live-linux` (linux/arm64 container, CPU only, 2 threads) at `77420d8`: **12 passed, 4 failed**
  in 28 min 38 s. Passed: the seven gateway tests (readiness, verification, the key, A30 offline), the
  hung-generation A24 and the out-of-memory tests, the three remote refusals. Failed: A28 and A29,
  each "no answer within the 300 s generation deadline" with 0 generations — the container processes
  prompts at 3.1 tokens per second (D3), so the 2,700-token system context of one call needs about
  15 minutes against D17's 300 s; then the remote readiness and the deadline tests timed out behind
  the abandoned generations, which hold the server's single slot until their deadline. A fact of
  this container's speed, not a product defect: the harness said so truthfully at each step. The
  run's evidence files were not copied out (the copy follows a failing pytest; fixed below). Tail:
  ```
  FAILED tests/integration/test_live_generate.py::test_a28_the_acceptance_instruction_yields_a_committed_table_equal_to_duckdb
  FAILED tests/integration/test_live_intent.py::test_a29_the_five_reference_instructions
  FAILED tests/integration/test_live_remote.py::test_r17_the_remote_binding_is_ready_with_its_policy_shown_and_answers_from_llama_server
  FAILED tests/integration/test_live_failure.py::test_r16_a_hung_server_is_killed_at_the_deadline_and_the_assistant_recovers_on_the_same_binding
  4 failed, 12 passed, 394 deselected, 1 warning in 1718.71s (0:28:38)
  ```
  - sixth run at `77420d8` (the two product rules): the acceptance spec **passed in 72 s**; Python
    **15 passed, 1 failed** in 7 min 9 s. **A29 PASS**: the five reference instructions as described
    ("keep features minimal" now ends with the application's question). **A28 FAIL** on the known
    over-grouping only (8 rows by region and service level, values equal to DuckDB's for that
    grouping; 5 generations, 42 s, 0 repairs). **A24 PASS** (p95 pause 0.019 s, cancel 0.036 s;
    third run) and **A30 PASS** (the offline part). Tail:
    ```
    ✓  1 tests/live.spec.ts:23:1 › @live_model A28, A24: type the instruction, see real progress, pause mid-run, resume, open the table (1.2m)
    FAILED tests/integration/test_live_generate.py::test_a28_the_acceptance_instruction_yields_a_committed_table_equal_to_duckdb
    1 failed, 15 passed, 394 deselected, 6 warnings in 429.59s (0:07:09)
    ```
- Integrity review (one run, general-purpose agent with the reviewer's definition; 259k tokens):
  **REVIEW: PASS**, two should-fix and six notes, all answered (decisions 2026-10-16): the model's
  patch could set the derived privacy status or name an unlisted field, and a bare-prefix provenance
  covered every path (fixed: refused, parent-or-exact provenance); the generation deadline was a
  per-read timeout (fixed: the whole generation); the tool catalogue is counted in the input bound
  and the Metal memory poll counts resident memory (notes taken); replay idempotency of two tools, a
  text answer settling `applied` without effect, Linux live coverage and the in-memory spend sum
  (notes recorded, the first two open for Sprint 6). Every fix mutation-caught.
- **Measured facts** (facts, not claims of adequacy; the local binding `assistant-local-qwen`,
  llama.cpp b11104, Qwen3-8B Q4_K_M, seed 1, temperature 0; the acceptance instruction on the
  500-row orders fixture, from the A28 generated-code record's `measured` field; the D3 rows are the
  5.1 checkpoint above):

  | Fact | macOS arm64 (Metal, `-t 2 -ngl 99`) | Linux arm64 container (CPU, `-t 2`) |
  |---|---|---|
  | First useful response (the first tool call, from the instruction) | 8.5–9.7 s (two runs) | none: the first call ran past the 300 s deadline (the 2,700-token prompt at 3.1 tok/s needs ~15 min) |
  | Step latency (mean seconds per generation, prompt and answer) | 6.8–7.7 s over 5 generations | not reached: no generation completed within D17 |
  | Tokens per second | 45.3 generation / 258 prompt (D3, prose); 14.4–16.1 completion tokens per second of generation time in the task (prompt processing included) | 1.6 generation / 3.1 prompt (D3); none completed in the task |
  | Peak memory of the model server | 6.39 GiB `phys_footprint`, sampled every 0.5 s during the task (D3: 1.24 GiB at readiness; resident 5.98 GiB, the mapped weights) | not sampled (no task ran); the server loaded within the `prlimit` address-space bound |
  | Repairs per task | 0 of at most 2 (one task submitted) | no task submitted |
  | Load to health | 23.6–25.5 s (D3) | 16.2 s (D3) |

## D3 checkpoint — launch profile (2026-10-15, measured under the Seatbelt profile on this M1 Max)

| Profile | Flags | Load to health | First token (cold / warm) | Prompt tok/s | Generation tok/s | Typed probe | Peak footprint | Resident |
|---|---|---|---|---|---|---|---|---|
| CPU, 2 threads (the contract) | `-t 2 -ngl 0` | 28.1 s | 1.04 s / 0.96 s | 23.0 | 11.5 | 10.0 s | 5.62 GiB | 9.86 GiB |
| CPU, all 10 cores | `-t 10 -ngl 0` | 30.6 s | 1.49 s / 0.94 s | 23.7 | 11.1 | 7.0 s | 5.62 GiB | — |
| Metal, full offload | `-t 2 -ngl 99` | 23.6–25.5 s | 0.27 s / 0.09 s | 258 | 45.3–45.4 | 1.1 s | 1.24 GiB | 5.98 GiB |

Each row passed the typed probe with thinking off. Generation is 164–175 tokens of prose at temperature
0, seed 1; "cold" is the first request after load. Peak footprint is the kernel's `phys_footprint`;
Metal's weights live in GPU-mapped memory it does not count, hence the resident column (`ps`). Since the
5.7 review the memory poll takes the larger of the two, so the binding's limit bounds the weights too. Load times are with the file in the page cache. Linux (the container, CPU only, 2 threads):
health in 16.2 s, 3.1 prompt tok/s, 1.6 generation tok/s.

## Open defects and gaps

- **5.4 acceptance, local binding:** "load this CSV and show transit hours by service level" yields a
  table grouped by region and service level (values right for that grouping), not per service level;
  `A28-generated-code-live-assistant-local-qwen` is FAIL on macOS and `make live` is red by that one
  test until the model's interpretation is qualified or changed (Sprint 11's suite is where adequacy
  is judged). Identical on every gate run (six).
- **Linux container, the assistant's prompts past D17's deadline:** at 3.1 prompt tokens per second
  the 2,700-token context of one call needs about 15 minutes against 300 s, so A28 and A29 fail there
  with "no answer within the 300 s generation deadline" and the next tests wait behind the abandoned
  generation (decisions 2026-10-16). `make live-linux` is red by four tests; the gateway, failure and
  remote-refusal tests pass. A fact of this container, not of the product; a Linux machine with a
  GPU or more cores is the real target.
- Review notes deferred to Sprint 6 (decisions 2026-10-16): a `dispatched` patch or schema call
  replayed after a crash is not idempotent (no double commit); a text answer settles `applied` even
  when no call had an effect; the remote spend sum lives in memory.
- A SIGTERM to a harness started by a Playwright spec did not stop its model server (the spec now
  quits through the API); why the supervisor's stop did not run is not established.
- CI, Linux built app (run 38895075855): after the real window close the shell did not end within 20 s;
  the Sprint 4 gate passed this step and the shell's close path is unchanged since; the step had not
  run on CI in Sprint 5 before (earlier runs failed before it). The waits now report what is left on a
  timeout. Not reproducible here; open until the gate's CI run.
- `make live`: the quit test (`test_d24_quitting_the_harness_stops_the_model_server_it_started`) failed
  once in a full macOS run that overlapped a container run, and its output was not captured; it passed in
  the three runs since. Not established whether the 30 s waits are too short under load.

- macOS sandbox: sysctl reads are allowed by name only, the eleven measured for the standard library and
  DuckDB; a future library reading another one gets EPERM (add it by name after checking it reveals
  nothing of another process; never by a `kern.` prefix). The System V rule uses Seatbelt's private
  `syscall-unix` filter and needs the profile's deny-by-default; the D21 test guards it.
- Linux desktop job on CI (runs 38322576233 and 38379462014): the built-app test read the window's
  text once the plan showed and required the snapshot in that same text, but the window reads the
  snapshot with a separate request that can land later (the failing text had the plan and "Resources
  not observed", no read error). The test now waits for the snapshot's line; it passed on run
  38380964046. One pass does not prove a race gone; the Linux built-app test runs only on CI.
- macOS: `os.killpg(pid, SIGKILL)` in the sandbox's `stop()` (`sandbox.py:104`) is refused with
  `EPERM` now and then: at the Sprint 4 gate the dispatcher logged it without a traceback; at the
  Sprint 5 gate it failed `test_d21_cpu_time_past_the_limit_stops_the_task_even_when_it_ignores_sigxcpu`
  once in a full `make verify` (the test passed three times alone right after, and in the two other
  full runs that day). The likely cause is a process-group id reused by a process of another user
  between the task's end and the kill; not established. A retried transient failure in the
  dispatcher, a red test when it lands in the containment test. Open (Sprint 6 housekeeping: check
  the group is still the task's before the kill, or kill the known pids).
  The failed run also left that task's scratch image mounted (`/dev/disk4`, under `pytest-of-nm`):
  `hdiutil detach` and a forced `diskutil unmountDisk` both answer "Resource busy" though `lsof`
  finds no holder; left mounted, to be detached after a reboot (never any other disk).
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
  name a job. There is no Resume menu item. The Sprint 4 defect (in the built macOS app Cmd+. reached
  neither the window nor the native menu) is answered by D1: Cancel run is now CmdOrCtrl+Shift+K
  everywhere; whether the built macOS app delivers it is the owner's press at the Sprint 5 gate
  (open until then). Action outcomes are shown in the activity trail only, with one wording (closed in Sprint 4
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

1. In the built macOS app (`make desktop-build` left `DS Playground.app` under
   `desktop/src-tauri/target/release/bundle/macos/`): start a job, press Cmd+P and Cmd+Shift+K, and
   say what happened (the chord is D1's; no automated test can press it in the real window).
2. The acceptance line in the real macOS window: type "load this CSV and show transit hours by service
   level" with the orders fixture granted, watch the progress, pause mid-run, resume, open the table.
   On the first run macOS may ask to allow keychain access: expected, the harness reads the server's
   key from the login keychain (service `dev.dsp.assistant`), and the table will be grouped by region
   and service level (the open A28 defect).
2. Optional: remove `~/Library/Containers/dsp.probe.appsandbox` (28 KB), left by the gap investigation's
   App Sandbox probe; the system refused its deletion from this session.

## Handoff note

Sprint 5 is on `claude/sprint-5-assistant-gateway-fc1f11` (from `main` at `73698be`), pushed through
the gate's commits, with the pull request "Sprint 5: assistant gateway, open model first" open for the
owner to merge. **Next is Sprint 6, prompt 6.1** (fixtures), on a new branch from `main` after the merge.
Carry into Sprint 6 housekeeping: the open defects above (the over-grouped acceptance table, the Linux
deadline fact, the `killpg` EPERM, the two review notes, the kill that left a server). The `make live`
suites: macOS green but for A28; Linux red by the deadline fact. `make test-fast` was 342 passed at 5.6;
the gate's `make verify` runs are recorded above. The D3 pick is Metal (applied); D4 = B is built.

Sprint 4's handoff: the gate was PASS on macOS and Linux for Sprint 4 scope after the two macOS
containment gaps were closed (PR #8, merged).

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
