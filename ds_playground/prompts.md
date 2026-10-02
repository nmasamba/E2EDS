# prompts.md — sprint prompts for DS Playground

> Paste-ready prompts, in order, for a coding agent. `AGENTS.md` governs *how*; this file says *what*.
> The specification is the planning suite in `../` (read-only). Prompts cite it by path and ID instead of
> restating it. Owner decisions in `docs/decisions.md` override the suite.

## How to use

One sprint at a time, prompts in order. The agent works autonomously and stops only for the `AGENTS.md` §8
stop list; planned stops are marked **STOP**. Tags: **(INFRA)** foundations, **(FEATURE)** a small tested
feature, **(CHERRY)** optional or complex, built last and skippable. Sprints 12–20 open with a re-plan
prompt because they depend on evidence from earlier gates.

**Standing rule — paste at the start of every session:**

```
Follow AGENTS.md. Read STATUS.md and docs/decisions.md first, then the active sprint in prompts.md and only
the suite sections it cites. Build additively with the smallest change; no filler code, no scaffolding for
later sprints. Tests with every feature, edge cases included, real execution over mocks, open models first.
Work inline; do not spawn agents except where AGENTS.md §11 allows. Both macOS and Linux must pass. Report
only what you ran. Stop only for the AGENTS.md §8 stop list; otherwise proceed.
```

**Exit sequence — the last prompt of every sprint means this:**

> Run the exit sequence in `.claude/skills/sprint-workflow/SKILL.md`: `make verify`, `make verify-linux`,
> `make sat`, the ID trace, a real run of what shipped on each OS, the docs checklist, `integrity-reviewer` on
> boundary sprints, commit, and the sprint report with each gate stated as PASS, FAIL or
> INSUFFICIENT_EVIDENCE.

## Sprint table

| # | Milestone | Ships |
|---|---|---|
| 0 | Setup | Toolchains, verified model file, scope record |
| 1 | M0 | Gate on macOS + Linux, contracts, ledger, store, CLI; **CSV → exported, hash-verified pack** |
| 2 | M1 | Harness, desktop app on both OSes, folder grants, hardware discovery, workflow plan, stage trail |
| 3 | M1 | Durable jobs, admission, conversation, pause/cancel/resume, requirement revisions |
| 4 | M1 | Sandboxed native runner and containment evidence |
| 5 | M1 | Model gateway, local open assistant, tool loop, intent extraction; opt-in remote models |
| 6 | M1 | Multi-format ingestion, quarantine, gold data products |
| 7 | M1 | Source collections and checked joins |
| 8 | M1 | Assistant-driven analysis, independent checks, report, analysis pack, export — **first usable slice** |
| 9 | M1 | Real classification and regression with sealed evaluation |
| 10 | M1 | `predict.py`, HTTP, MCP, signed service bundle, clean install |
| 11 | M1 | Task extension, assistant qualification, hardening, **M1 gate report** |
| 12 | M1B | Extraction, cited summaries, lexical RAG |
| 13 | M1C | Colab notebook portability |
| 14 | M1R | Remote runner and Runpod |
| 15–16 | M2 | Team coordination, scheduled monitoring, recovery |
| 17 | M3 | Broader generative search |
| 18 | M3Z | Optional ZeroGPU demo |
| 19–20 | M4 | LoRA fine-tuning; agent simulation |

---

## Sprint 0 — Setup (B01, O24)

**0.1 — Environment check (INFRA)**
```
Read AGENTS.md, STATUS.md, docs/decisions.md and ../delivery_plan.md "First implementation-session brief".
Without asking, record in STATUS.md what this machine has: OS, architecture, cores, RAM, free disk, and
versions of uv, python, node, pnpm, cargo, docker, git, gh, cmake, llama-server. List what is missing.
```

**0.2 — Toolchains (INFRA) — STOP for approval**
```
Show me, in fenced blocks, the exact commands to install what is missing: Python 3.12 via uv, the Rust
toolchain (for Tauri), cmake, and llama.cpp built from tag b11104 (commit 217f81c2…). Wait for my go-ahead,
then run them and record versions and the llama-server binary SHA-256 in STATUS.md. If the pinned build fails,
propose the nearest tag and log a DEVIATION. Install nothing else.
```

**0.3 — Assistant model (INFRA) — STOP for approval**
```
Show me the command to download Qwen3-8B-Q4_K_M.gguf (5.03 GB) from Qwen/Qwen3-8B-GGUF at revision
7c41481f57cb95916b40956ab2f0b139b296d974 into a models folder outside the repo. After my go-ahead, download
it and verify SHA-256 d98cdcbd03e17ce47681435b5150e34c1417f50b5c0019dd560e4882c5745785. A mismatch is a HALT.
Record path and verified digest in STATUS.md, not in the repo.
```

**0.4 — Scope record (INFRA)**
```
Write docs/gates/G0.md from ../delivery_plan.md gate G0: intended and prohibited use (A01), synthetic data
only, owner-holds-all-roles conflict declaration, the three owner deviations, open decisions O01–O24 with the
ones that block nothing yet marked so. State G0 as PASS for scoped synthetic work only. No code.
```

---

## Sprint 1 — M0: foundations and a thin real product (B02, B03, B05; R11; D20, D23)

Ships a CLI that profiles a CSV and exports a versioned, hash-verified pack, with the gate green on macOS and
Linux. Order: infrastructure 1.1–1.3, thin slice 1.4, gate 1.5.

**1.1 — Scaffold and gate (INFRA)**
```
Create the project per AGENTS.md §4 and §9: pyproject.toml (uv, Python 3.12, src layout, exact pins), ruff,
mypy --strict, pytest with --strict-markers, the markers in AGENTS.md §6 and sockets disabled by default.
Makefile: install, format, lint, type, test, test-fast, sat, boundaries, verify, verify-linux (same gate in a
linux container). tools/check_boundaries.py, tools/trace_ids.py (lists which suite IDs for sprint N appear in test
docstrings or docs/evidence), and a conftest guard that fails the run on any skipped or xfailed test. GitHub Actions: `make verify` on ubuntu-24.04
and macos. README with only commands that exist. One real test proves the gate fails when it should.
Add only the dependencies this sprint uses; log each in docs/dependencies.md.
```

**1.2 — Contracts (INFRA)** — skill: `contract-change`
```
Vendor ../contracts/*.schema.json into src/dsp/contracts/schemas/suite/ (package data) with a test that checks each digest against
../SUITE_MANIFEST.json. Implement canonical JSON and sha256 digests, typed Ref, the shared error codes from
../contracts.md "Trusted context and structured errors", and TrustedContext (single local tenant, derived
server-side, never from input). Validate all 22 ../examples against their schemas with format assertion on
(unwrap the four array files); add invalid and boundary fixtures per schema.
Do NOT hand-write models for the sixteen schemas: validate plain dicts with the schemas, and add a typed
model only when a sprint's code needs one. Add app-owned schemas in src/dsp/contracts/schemas/app/ only for DataManifest and
ExportReceipt and the pack manifest, which 1.4 needs.
```

**1.3 — Ledger, outbox and content store (INFRA)** — skill: `ledger-and-jobs`
```
SQLite ledger with a single writer: versioned object rows, per-aggregate sequence with expected-version
compare-and-swap, outbox event in the same transaction. Content-addressed file store with the staged commit
protocol from ../architecture.md "Authoritative state and rebuild paths". Tests: stale expected version is
rejected; crash between staging and commit leaves nothing referenced; duplicate event IDs deduplicate;
identical bytes give identical digests; rebuild a projection from the ledger alone.
```

**1.4 — Thin slice: profile and export (FEATURE)** — skills: `release-and-export`, `data-products-and-joins`
```
`dsp profile <file.csv> --out <dir>`: capture the file as an immutable raw snapshot with a DataManifest, run
a built-in reviewed DuckDB profiling recipe (row and column counts, types, nulls, distinct, min/max; string
IDs keep leading zeros) as a ledger job, commit artifacts to the store, and export manifest.json,
profile.json and a self-contained report.html to a NEW version directory through staged write, hash check,
atomic rename and an ExportReceipt (D23). Label the run `signed_recipe`: no generated code exists yet.
Tests: empty file, malformed rows, 100,001 rows (D20 refuses, no truncation), re-export makes a new version,
tampered staged file aborts, existing output is never overwritten.
```

**1.5 — Sprint 1 gate — STOP for first push**
```
Exit sequence. Then ask me whether to make the baseline commit on main and push, explaining that it publishes
the planning suite and that Linux CI depends on it. After my answer, confirm CI is green on both runners.
```
Acceptance: `dsp profile fixtures/orders.csv --out out/` produces `out/v1/` whose manifest hashes verify, on
macOS and Linux.

---

## Sprint 2 — M1: desktop shell, discovery and plan (B28, B35, B29; A31, A32, A44; R19, R20, R26; D19, D24)

Ships a native window on both OSes that opens without any model, grants folders, shows observed hardware and
a provisional plan on the nine-stage trail. Skill: `desktop-workspace-ui`.

**2.1 — Harness (INFRA)**
```
A FastAPI harness bound to loopback with a per-user instance lock and a generated owner-only token; `dsp`
starts or reconnects to it and `dsp status` reports it. Tests: a second instance reconnects instead of
starting; wrong token is 401; non-loopback bind is refused; Origin/Host checks reject a foreign origin.
```

**2.2 — Shell scaffold (INFRA)**
```
desktop/: Tauri 2.12.0 shell with React + TypeScript strict + Vite. Rust does only: start or reconnect to the
harness sidecar with the authenticated handshake, native menu, window lifecycle. Narrowest capabilities.
Vitest and Playwright + axe wired to the real harness. CI builds macOS and Linux bundles (AppImage and deb)
and runs a launch → handshake → quit test on Linux under a virtual display. `make desktop-dev`,
`make desktop-build`, `make e2e`.
```

**2.3 — Scoped folder grants (FEATURE)**
```
Native folder picker → opaque scoped handle in the harness → source roots and an OutputBinding
(../contracts/OutputBinding.schema.json). CLI equivalent `dsp grant`. The renderer never sees or sends raw
paths; a path named in text grants nothing. Tests: traversal and symlink escape denied at use time; revoked
handle refused.
```

**2.4 — Hardware discovery (FEATURE)**
```
Per ../hardware_discovery_and_planning.md "What is collected" and "Discovery, checks and freshness": a
deterministic collector with one adapter per OS, fixed allowlisted probes, ≤2 s per probe and ≤10 s total
(D19), producing HardwareSnapshot records that separate observed, user_declared and unknown, and omit
serials, usernames and home paths. Runs before any model. Tests (A31): no model, denied GPU probe, probe
timeout and no network all yield a partial snapshot with reasons and a usable workspace.
```

**2.5 — Feasibility and WorkflowPlan (FEATURE)**
```
A versioned rule table (filter → size → place → compare → explain) per the same document's "Deterministic
feasibility" that turns WorkloadSpec + snapshots + bindings into an immutable WorkflowPlan with alternatives
and evidence gaps; `authorises_execution` is always false. Tests (A32): more host RAM than usable quota, a
visible but unqualified GPU, a declared-only inventory and a zero-budget paid option each produce the right
disposition; fixture inventories never qualify anything.
```

**2.6 — Event stream and work trail (FEATURE)**
```
SSE endpoint with cursor replay and an equivalent polling endpoint over the outbox. A pure reducer derives
the nine stage states (../gui_workflow.md "Stages and evidence") from events. Render header, work trail,
environment panel and resource status. Tests: duplicate, out-of-order and replayed events converge; expired
cursor returns a snapshot; display goes stale after 60 s; lost stream shows last known state.
```

**2.7 — Lifecycle (FEATURE)**
```
../desktop_experience.md lifecycle table: close detaches, quit drains, crash and reopen reconnect and replay,
second window attaches to the same harness. Tests on both OSes for close, quit, kill, reopen, second
instance; record evidence for A44 and state what could not be automated on macOS.
```

**2.8 — Sprint 2 gate**
```
Exit sequence.
```
Acceptance: launch the app with no model and no terminal, pick source and output folders, see observed and
unknown hardware and a provisional plan; reopen and see the same state.

---

## Sprint 3 — M1: jobs, admission, conversation and control (B25, B05, B03; A03, A04, A07, A08, A24–A27, A33; R05, R15; D03, D05, D06, D18)

Ships durable jobs and a conversation that can pause, cancel, resume and change requirements while a
deliberately hung task runs. Boundary sprint. Skills: `ledger-and-jobs`, `conversation-control`.

**3.1 — Job coordinator (INFRA)**
```
The job state machine from ../architecture.md "Job state machine": attempts, 15 s heartbeat, 60 s lease,
monotonic fence, at most two transient retries, idempotent result commit by result key. A deterministic test
worker (sleep, hang, crash on cue) is the only workload. Tests: A03 kill before and after commit; A04 stale
worker rejected after fencing; A07 cancel while queued, running and after success.
```

**3.2 — Admission and reservations (INFRA)**
```
ExecutionRequest admission per ../compute_backends.md "Binding selection and admission": authority from
TrustedContext only, binding revision and digest pinned, fresh capacity check, atomic resource and spend
reservation, zero external charge by default. Tests: wrong role, undeclared operation, GPU request on a CPU
binding, nonzero charge without a grant are rejected before any work (A18-style, local scope); two admissions
racing for the last reservation never exceed the cap (A08); a plan older than its inputs is rechecked (A33).
```

**3.3 — Messages and receipts (FEATURE)**
```
POST /v1/conversations/{id}/messages and the events endpoints from ../conversational_control.md "Transport
and durable records", storing ConversationCommand records. Receipt is durable before acknowledgement; inbound
accepts only message ID, text and expected revision. Tests (A27): dropped acknowledgement then same-ID retry
gives one command; same ID with different text conflicts; reconnect with a cursor replays in order; >16 KiB
is refused before parsing.
```

**3.4 — Fast controls (FEATURE)**
```
POST /v1/jobs/{id}/control and the exact control phrases, on a path that shares nothing with generation or
job execution. Pause advances the dispatch epoch. Tests: A24 with a hung fake generation and a saturated
worker, pause and cancel are durable within 2 s (measure and record p95); A25 pause racing a checkpoint and a
commit; resume is explicit and readmits; a cancelled job cannot resume; quoted "pause" inside an uploaded
document does nothing.
```

**3.5 — Requirement revisions (FEATURE)**
```
A change instruction becomes a typed patch on WorkloadSpec with an impact preview, a new immutable revision,
and stale marks on dependent evidence through a dependency graph. Tests (A26): exclude a field mid-run;
old results stay on the old revision; two concurrent edits → REVISION_CONFLICT; a budget or evaluation
change is refused without the owner action.
```

**3.6 — Composer and activity (FEATURE)**
```
Persistent composer, activity trail of real events, command states, Pause and Cancel in the header and as
native menu items with shortcuts, all usable while the renderer is busy. Keyboard-only test for pause and
cancel; axe clean.
```

**3.7 — Sprint 3 gate**
```
Exit sequence, including integrity-reviewer on the sprint diff.
```
Acceptance: start the hung test job from the app, pause, change a requirement, resume, cancel; the trail
shows receipts and actual states, and survives an app restart.

---

## Sprint 4 — M1: sandboxed native runner (B26; A28; R16; C14, C18; D01, D21)

Ships real code execution inside the OS sandbox on macOS and Linux, with containment evidence. Boundary
sprint. Skill: `sandboxed-runner`.

**4.1 — Contracts for the runner (INFRA)** — skill: `contract-change`
```
New app schema versions: ComputeBinding with an OS-sandbox generated_code_policy and trust model and with
darwin allowed as an execution OS; an app-owned CodeTask schema per ../contracts.md "Conversation, model and
user-constraint contracts". Create the local binding record with `assurance: os_sandbox_single_user`.
Log the DEVIATION.
```

**4.2 — Runner entry point and environment (INFRA)**
```
src/dsp_runner: `python -m dsp_runner <task.json>` loads a CodeTask, executes its Python or DuckDB SQL
against declared read-only inputs, writes declared outputs and a bounded result file to scratch. A locked
runner environment built by `make runner-env`. RunnerPort in ports/. No sandbox yet; not reachable from the
application until 4.3/4.4 land.
```

**4.3 — macOS sandbox adapter (FEATURE)**
```
Seatbelt adapter implementing the policy in the skill: deny by default, allowlisted reads, scratch-only
writes, no network, scrubbed environment, CPU/memory/time/output/scratch limits, fixed argv.
```

**4.4 — Linux sandbox adapter (FEATURE)**
```
bubblewrap + seccomp adapter with the same policy and limits. If bubblewrap cannot run inside the
verify-linux container, run these tests in CI and record that in STATUS.md.
```

**4.5 — CodeTasks through jobs (FEATURE)**
```
Execute a CodeTask as a fenced job: stage, run in the sandbox, validate and ingest results, commit artifacts.
Move the Sprint 1 profiling recipe into the runner. Tests: result over the size cap is rejected; a stale
fence rejects a late result; killed task leaves no succeeded job.
```

**4.6 — Containment suite (FEATURE)**
```
Implement every containment test listed in the skill as real tasks on both OSes (A28) and write evidence
records at os_sandbox_single_user assurance with the stated limits.
```

**4.7 — Sprint 4 gate**
```
Exit sequence, including integrity-reviewer.
```
Acceptance: `dsp run-task fixtures/tasks/read_secret.json` is denied by the OS on both platforms and the
denial is in `docs/evidence/`.

---

## Sprint 5 — M1: assistant gateway, open model first (B24, B26, B27; A24, A29, A30; R16, R17, R18, R22; D16, D17)

Ships a real conversation: instruction → typed plan → generated code → sandbox → result, on the local open
model. Boundary sprint. Skill: `assistant-gateway`. Needs Sprint 0.2 and 0.3.

**5.1 — Gateway, binding and supervisor (INFRA)**
```
ModelGatewayPort and a llama.cpp adapter: a supervisor that verifies the model hash, starts llama-server on
127.0.0.1:8081 with the launch contract in ../local_model_runtime.md mapped to real flags, waits for
readiness plus a typed tool-response probe, and stops it. SecretPort with a keychain adapter (macOS) and a
Secret Service adapter with an owner-only file fallback (Linux). AssistantModelBinding record for the local
model. The workspace still opens with the model absent.
```

**5.2 — Tool dispatcher and loop (FEATURE)**
```
The application-owned loop with the narrow tool list in the skill and D17 limits. Every proposed call is
schema-validated, then checked for principal, revision, scope, budget and fence. Tests with a scripted fake
gateway for determinism: invalid call rejected, 21st call refused, call after a pause never dispatches,
injected "ignore the budget" text in tool output has no effect.
```

**5.3 — Intent extraction (FEATURE)**
```
Text → WorkloadSpec fields with field_provenance and intent_constraints, a plain readback and a structured
diff; ask only material questions. live_model tests on the reference instructions in
../conversational_control.md "From language to enforceable intent" (A29 interpretation): account_num as ID,
minimal features, round to nearest 10, pause-then-exclude, "spend another £100".
```

**5.4 — Generate, run, repair (FEATURE)**
```
The assistant writes a CodeTask, the runner executes it, the assistant sees redacted results and may repair
at most twice. live_model test: "load this CSV and show transit hours by service level" yields a committed
table artifact that matches an independent query.
```

**5.5 — Failure and independence (FEATURE)**
```
Model missing, hash mismatch, OOM, hang and deadline each give assistant_unavailable with conversation and
controls intact; no other model is tried. Tests: A24 with a genuinely hung generation; offline start with the
network denied (A30 part); restart does not redispatch committed tools.
```

**5.6 — Remote and proprietary bindings (CHERRY) — STOP for keys**
```
New AssistantModelBinding schema version for remote providers; an OpenAI-compatible adapter (test with an
open model first: Hugging Face router or a local server) and a proprietary adapter behind the same port; a
per-project data policy shown before first use; key from SecretPort; owner-approved spend limit. Ask me for
keys before writing tests that need them. Still no fallback between bindings. Skip if I say so.
```

**5.7 — Sprint 5 gate**
```
Exit sequence, including integrity-reviewer. Record first-response latency, step latency and peak memory for
the local model as measured facts, not claims of adequacy.
```
Acceptance: in the app, type the 5.4 instruction, watch real progress, pause mid-run, resume, and open the
resulting table.

---

## Sprint 6 — M1: ingestion and gold data (B30, B04; A35; R21; D20; ADR24)

Ships bounded multi-format ingestion with quarantine and a browsable gold product.
Skill: `data-products-and-joins`.

**6.1 — Fixtures (INFRA)**
```
fixtures/operations: a seeded generator for the six-source set in ../reference_workload.md (2,000 orders, 400
accounts, items, events, policy versions, policy text, a native-text PDF, a scanned PDF, PNG and JPEG
receipts) plus malformed, oversized, encrypted and ambiguous variants. Generated at test time, not committed.
```

**6.2 — Raw capture (FEATURE)**
```
Batch ingestion with D20 bounds checked on bytes, pages and pixels before decoding; magic-number checks;
immutable raw snapshots with DataManifests. First limit reached stops the batch with a report.
```

**6.3 — Tables (FEATURE)**
```
CSV and Parquet into the prepared layer inside a runner task: proposed types, explicit casts, preserved
identifier text and time zones, quarantine ledger. Source count = accepted + rejected, tested.
```

**6.4 — Text, PDF and images (FEATURE)**
```
UTF-8 text with offsets; native-text PDF through Docling 2.130.0 in the sandbox with page and span
provenance, no network or model download; images and scanned pages as assets marked needs_ocr. An OCR profile
is out of scope unless I approve its model and licence.
```

**6.5 — Gold product (FEATURE)**
```
DataProductManifest with grain, keys, units, time semantics, lineage and a quality report; states planned →
materialised → checked; `accepted` only by the owner action.
```

**6.6 — Data stage view (FEATURE)**
```
Sources with sizes and status, typed schema, labelled sample preview, quarantined records with reasons.
Table view only; keyboard reachable.
```

**6.7 — Sprint 6 gate**
```
Exit sequence. A35 evidence across valid and malformed inputs.
```
Acceptance: ingest the operations folder from the app; counts reconcile; the scanned PDF shows `needs_ocr`.

---

## Sprint 7 — M1: collections and joins (B33; A39–A41; R24; D22; ADR26)

Ships multi-source relationship planning with checked exact, aggregate, as-of and union joins.
Skill: `data-products-and-joins`.

**7.1 — Collections (INFRA)**
```
DatasetCollectionManifest with inline and paged membership. Test (A39): register more than 100 sources across
batches; the membership snapshot survives restart; every source is included, excluded or unprofiled.
```

**7.2 — Profiles and candidates (FEATURE)**
```
Bounded profiles and relationship candidates per ../multi_dataset_planning.md "Discovery, evidence and
authority", with a finite candidate budget and visible coverage when it runs out.
```

**7.3 — JoinPlan (FEATURE)**
```
Typed JoinPlan with semantic validators: resolved aliases, acyclic graph, unique output names, every scoped
source handled. Expressions are untrusted and run only in the sandbox.
```

**7.4 — Operators and materialisation (FEATURE)**
```
Exact, aggregate-then-join, as-of and union operators with full key, cardinality and count checks and D22
bounds; fenced, crash-safe materialisation. Tests: A40 (leading zeros, composite keys, duplicate and null
keys, intended and unintended many-to-many); A41 (future-known policy, overlapping validity, crash during
commit, refresh marks descendants stale).
```

**7.5 — Joins by conversation (FEATURE)**
```
"Join accounts on account_num, one row per order, policy as known at order time" produces a JoinPlan diff
with grain, unmatched policy and time rule; a non-unique account key pauses that materialisation and asks.
Relationship map with an equivalent table.
```

**7.6 — Sprint 7 gate**
```
Exit sequence.
```
Acceptance: the six sources become one-row-per-order gold with reconciled counts and no future leakage.

---

## Sprint 8 — M1: analysis release — first usable product slice (B31, B36, B07; A13, A34, A36, A37, A45; R11, R20, R23, R27; D21, D23; ADR23, ADR25)

Ships: describe a question, get checked findings, a notebook and report, and a reproducible pack in your
folder. Skills: `evaluation-integrity`, `release-and-export`.

**8.1 — Analysis workload (FEATURE)**
```
A data_analysis WorkloadSpec (zero trials, D21) driven by conversation: the assistant writes SQL/Python
tasks over gold data and commits tables and static charts.
```

**8.2 — Independent claim checks (FEATURE)**
```
An app-owned EvaluationContract and EvaluationReport. Material aggregates are recomputed by a separately
written query in a separate task; outcome PASS, FAIL or INSUFFICIENT_EVIDENCE. Tests (A13, A36): a wrong
claim fails; missing coverage is inconclusive; analysis completes with no model and no trials.
```

**8.3 — Notebook and report (FEATURE)**
```
Generate the notebook and a self-contained HTML/JSON report from committed artifacts only, per
../data_and_evaluation.md "Notebooks and HTML evidence". Fresh-kernel replay test; no scripts or remote
assets; injected HTML in a column name is escaped.
```

**8.4 — Analysis pack (FEATURE)**
```
AnalysisReleaseManifest and the pack layout from the release-and-export skill. A failed or inconclusive
result exports as unapproved.
```

**8.5 — Export and output shelf (FEATURE)**
```
Full export protocol for packs with receipts; output shelf with produced, checked, exported, incomplete and
stale states and "Open output folder". Tests (A45): every case listed in the skill.
```

**8.6 — Versions and manual checks (FEATURE)**
```
Output version history with diffs, and a manual `check_output` under a MonitoringSpec. Tests (A37): a changed
source marks the output stale and proposes a rerun; nothing is replaced automatically; no schedule means
"manual only", never "healthy".
```

**8.7 — Report view and evidence margin (FEATURE)**
```
Report in the inert viewer; each figure links to its artifact, definition and revision. Tests (A34): spoofed
completion prose changes nothing; unsafe artifact HTML is inert; a revised requirement marks evidence stale.
```

**8.8 — Sprint 8 gate — STOP for walkthrough**
```
Exit sequence. Then ask me to run the journey in ../reference_workload.md "Output and monitoring
walkthrough" steps 1–3 myself and record what I report.
```
Acceptance: from the app, load the operations data, ask about transit times by service level, and open the
exported pack without the app.

---

## Sprint 9 — M1: real models with sealed evaluation (B04, B06, B07, B32; A01, A02, A13, A14, A29, A36; R01, R05, R17, R22; D01, D09, D10, D12)

Ships fitted classification and regression with honest, independent evaluation. Boundary sprint.
Skill: `evaluation-integrity`.

**9.1 — Splits and cohorts (INFRA)**
```
App-owned SplitManifest; grouped and time-aware splitting before any learned step. Fixtures: the separate
predictive cohort (240/80/80 accounts) and the 6,000-case support-routing set (1,500 families × 4 variants,
60/20/20) with duplicate and template-leak checks.
```

**9.2 — Evaluation contract — STOP for thresholds**
```
Freeze metrics, denominators, slices and uncertainty method. Run the baselines, show me their real numbers
with lettered threshold options and a recommendation, and wait. Record my choice as a DECISION.
```

**9.3 — Baselines and fitting (FEATURE)**
```
classical_ml adapter: baselines, then sklearn Pipelines with train-only transforms — Ridge for transit
hours, logistic for late-vs-quoted, TF-IDF + logistic for support routing — executed as runner tasks.
Tests: A02 sentinel; A14 learned parameters exist; same seed gives identical metrics bytes.
```

**9.4 — Bounded search (FEATURE)**
```
At most 12 declared configurations, one at a time, every trial (including failures) in the ledger; pause
stops new trials and resumes the ledger. Plain enumeration unless Optuna is needed; log the choice.
```

**9.5 — Sealed evaluator (FEATURE)**
```
A separate evaluator principal and store; candidate runs inference-only in the sandbox on streamed inputs;
one evaluation per authorisation; aggregate-only return. Tests: A01 every route denied; A13; A36. State
`operator_controlled_local` on the report.
```

**9.6 — User constraints (FEATURE)**
```
Enforce field roles, exclusions, feature caps and output transforms end to end (A29): ID exclusion, grouped
split, hard cap, rounding ties 124→120, 125→130, −125→−130 evaluated on the released output.
```

**9.7 — Develop and evaluate views (FEATURE)**
```
Trials, code diffs, self-checks and the independent outcome shown separately; a completed evaluation with
outcome FAIL displays as exactly that.
```

**9.8 — Sprint 9 gate**
```
Exit sequence, including integrity-reviewer.
```
Acceptance: "predict transit hours with a small feature set" produces a fitted pipeline and a report whose
every number comes from the EvaluationReport, whatever the outcome.

---

## Sprint 10 — M1: installable service (B08, B09, B10, B36; A09–A12, A30, A45; R02, R03, R04, R11, R18, R27; D04; ADR05, ADR10–ADR12)

Ships a signed bundle another machine can install and call through Python, HTTP and MCP. Boundary sprint.
Skill: `release-and-export`.

**10.1 — Service core and predict.py (INFRA)**
```
src/dsp_service: one operation per task (`predict_transit`, `route_document`) over the persisted pipeline;
ServiceSpec; `predict.py` calling the core directly with a no-network verification mode. skops persistence
with an allowed-type check.
```

**10.2 — HTTP adapter (FEATURE)**
```
FastAPI adapter with D04 limits and the status mapping in the skill; loopback and owner-only credential by
default; OpenAPI 3.1.0 export.
```

**10.3 — MCP adapter (FEATURE)**
```
MCP Python SDK 2.2.0 adapter (stdio and Streamable HTTP) over the same core. Test (A09): identical result,
denial and error semantics across predict.py, HTTP and MCP.
```

**10.4 — Release builder and signing (FEATURE)**
```
ReleaseManifest with the required roles, environment lock, SBOM, notices, detached Ed25519 signature; verify
before load. Tests (A12): flipped byte, swapped dependency, missing evidence, wrong signer.
```

**10.5 — Bundle export and clean install (FEATURE)**
```
Export the service bundle through OutputBinding (no endpoint started). Install it in a clean environment on
macOS and Linux from the bundle alone; reinstall the previous release as rollback. Tests: A10 and A30 with
harness and assistant stopped; A11 rollback; A45 for bundles.
```

**10.6 — Operate view (FEATURE)**
```
Install status, health and versions for a requested service; endpoint controls appear only for service
outputs with their gates met.
```

**10.7 — Sprint 10 gate**
```
Exit sequence, including integrity-reviewer. Recipient independence without a second person is
INSUFFICIENT_EVIDENCE; say so.
```
Acceptance: `python predict.py --release ./release --binding ./binding.json --input ./request.json` and the
HTTP and MCP calls return the same answer from a clean install.

---

## Sprint 11 — M1: extension mechanism, qualification, hardening, gate (B34, B27, B35; A16, A34, A38, A42–A44; R25; ADR27)

Ships the task-extension path, a measured assistant, and the M1 gate report.

**11.1 — Task capabilities (FEATURE)**
```
TaskCapabilitySpec registry with proposed, experimental and qualified states; admission resolves namespaced
task kinds against it. Test (A43): a recipe that imports but has no oracle or target profile stays
experimental and cannot be served.
```

**11.2 — Docs broker and implementation diffs (FEATURE)**
```
A restricted broker that fetches approved, version-matched public docs (or cached copies) as
DocumentationEvidence, never sending customer content as a query; a reviewable code and dependency diff. Tests
(A42): version-mismatched doc flagged; prompt-injected example grants nothing; no unreviewed install.
```

**11.3 — Assistant qualification (FEATURE)**
```
Build and run the held-out suite in ../local_model_runtime.md "Qualification" against the local open model.
Report counts, intervals and every failure. Do not tune the suite to pass. Any other binding gets its own
run.
```

**11.4 — Accessibility and lifecycle hardening (FEATURE)**
```
Keyboard and screen-reader pass over every view; dense list mode; lifecycle cases from A44 on both OSes;
workspace evidence cases from A34.
```

**11.5 — Privacy sweep (FEATURE)**
```
Plant canary secrets and raw rows; assert none appear in logs, events, bundles, exports or prompts (A16,
local scope).
```

**11.6 — Offline kit (CHERRY)**
```
An offline wheelhouse and installer notes so the core installs with the network denied (R02).
```

**11.7 — Acceptance sweep and audit — STOP for walkthrough**
```
Rerun A01–A04, A07–A10, A12–A14 and A24–A45 at local scope. Tell me the expected cost, then run ONE
adversarial audit of the M1 boundaries and verify survivors yourself. Ask me to do the A38 walkthrough as a
data scientist and as a software engineer.
```

**11.8 — M1 gate report**
```
docs/gates/M1.md: G0–G3 per ../delivery_plan.md "Evidence gates", each criterion PASS, FAIL or
INSUFFICIENT_EVIDENCE with its evidence file; the three owner deviations and what they limit; measured
assistant and resource numbers; what is not supported. Exit sequence. Tag `m1`.
```

---

## Sprint 12 — M1B: grounded text (B14; A14; R22; ADR13)

**12.0 — Re-plan (INFRA)**
```
Re-read docs/gates/M1.md and ../reference_workload.md V2 and "Task-specific acceptance beyond V1". Write
.claude/skills/grounded-text/SKILL.md from the suite and what M1 taught. List changes to this sprint's
prompts in docs/decisions.md before building.
```
**12.1 — Fixtures and contracts (INFRA)**
```
Seeded fictional FAQ corpus, extraction examples (1,200/400/400 by group) and labelled questions; their
manifests, split and evaluation contract. The workload model has its own binding, never the assistant's by
accident.
```
**12.2 — Lexical retrieval with citations (FEATURE)** — single-process BM25, pinned corpus and chunking.
**12.3 — Structured extraction (FEATURE)** — schema-validated fields with source spans and `present | missing | conflicting`; a span must occur in the source.
**12.4 — Cited summarisation (FEATURE)** — every claim carries a passage ID; unsupported claims are reported.
**12.5 — Bounded configuration search (FEATURE)** — at most 8 configurations, call and token budget, zero weight updates (A14).
**12.6 — Evaluation — STOP for rubric** — exact and normalised field match, citation support, recall@k; the human rubric and thresholds are an owner checkpoint with real numbers.
**12.7 — Gate** — exit sequence.

---

## Sprint 13 — M1C: Colab portability (B19; A20; R14)

**13.0 — Re-plan (INFRA)** — as 12.0; write `.claude/skills/compute-bindings/SKILL.md` from `../compute_backends.md`.
**13.1 — Notebook generator (FEATURE)**
```
Generate a pinned notebook that runs the same workload contract on train/tune data only, records the observed
runtime, and exports checkpoints and manifests to persistent storage. Colab ComputeBinding record.
```
**13.2 — Export, resume, import (FEATURE)** — runtime loss restores only a compatible checkpoint or restarts a bounded attempt (A20); results import through the normal fenced commit.
**13.3 — Run — STOP: owner launches** — I launch the notebook; record observed profile, timings and failures.
**13.4 — Independent install and gate** — install the result locally from the bundle; exit sequence.

---

## Sprint 14 — M1R: remote runner and Runpod (B20, B21; A17–A22; R08, R13; D13, D15)

**14.0 — Re-plan — STOP for account and spend limit** — as 12.0; ask for the provider account, region and an approved spend limit before any paid step.
**14.1 — Provisioner and executor ports with a fault-injecting fake (INFRA)** — contract tests for lost create and stop responses, cleanup failure and late charges before any real call.
**14.2 — Attached remote runner (FEATURE)** — outbound-only, signed scoped jobs, same RunnerPort; local and remote give matching contract results (A17).
**14.3 — Runpod provisioner (FEATURE)** — owned-resource ledger, ambiguous-create reconciliation, release only what it created (A19).
**14.4 — Budget and reconciliation (FEATURE)** — tranche reservations, UsageRecord, estimated → observed → invoiced → reconciled; the zero-spend example stays blocked (A18, A21, A22).
**14.5 — Paid run and gate — STOP before spend** — run the same task remotely within the grant; record costs; exit sequence.

---

## Sprint 15 — M2: shared coordination (B11; A06; R05, R12)

**15.0 — Re-plan — STOP for host choice** — as 12.0; write `.claude/skills/team-coordination/SKILL.md`.
**15.1 — PostgreSQL ledger adapter (INFRA)** — passes the same ledger contract suite as SQLite.
**15.2 — Object store adapter (INFRA)** — same commit protocol, tenant-scoped keys.
**15.3 — Identity and tenancy (FEATURE)** — verified claims → TrustedContext; object-level checks; A06 including forged IDs and cache paths.
**15.4 — Private catalogue (FEATURE)** — CapabilityListing with evidence grade; a listing grants no artifact access.
**15.5 — Gate** — exit sequence, integrity-reviewer.

## Sprint 16 — M2: fleet, schedules, recovery (B12, B13; A08, A11, A16, A37; R06, R10, R23)

**16.1 — Runner fleet (FEATURE)** — multi-user leases and concurrency.
**16.2 — Budgets across workers (FEATURE)** — reservation splits and disconnected receipts (A08).
**16.3 — Scheduled monitoring (FEATURE)** — owner, cadence, grant; pausing stops new jobs (A37).
**16.4 — Backup, restore, deletion (FEATURE)** — restore into a clean environment with tombstones replayed (A11, A16).
**16.5 — Change control (FEATURE)** — ChangeProposal and ObligationControlMapping export; nothing promotes silently.
**16.6 — Gate** — exit sequence; M2 gate report.

---

## Sprint 17 — M3: broader generative search

**17.0 — Re-plan (INFRA)** — as 12.0; proceed only where M1B baselines justify it.
**17.1 — Wider configuration search (FEATURE)** — models, context and, only with measured benefit, embeddings.
**17.2 — Judge calibration — STOP for labels** — an LLM judge is used only after comparison with human labels.
**17.3 — Call accounting and hardening (FEATURE)** — reserved tokens and steps, cancellation, cost records.
**17.4 — Gate** — exit sequence.

## Sprint 18 — M3Z: optional ZeroGPU demo (B22; A23; R14; D14)

**18.0 — STOP: do you want this?** — needs a Hugging Face account; public exposure needs gate G5.
**18.1 — Curated adapter (CHERRY)** — one operation, synthetic inputs only, no paid overflow.
**18.2 — A23 and gate** — queue, quota, oversize and cancel cases; exit sequence.

---

## Sprint 19 — M4: weight training (B15; A14; R01)

**19.0 — Re-plan — STOP for GPU and spend** — as 12.0; write `.claude/skills/weight-training/SKILL.md`; qualify the hardware that actually exists (local Apple GPU or a remote binding) before promising a profile.
**19.1 — Training adapter (FEATURE)** — LoRA on Qwen3-0.6B at the pinned revision with the M4 library pins; baseline evaluated first.
**19.2 — Checkpoints (FEATURE)** — atomic trainer state, resume from a compatible checkpoint only.
**19.3 — Evidence (FEATURE)** — adapter weights change, base weights do not (A14); base-versus-adapter on the same task contract.
**19.4 — Release and gate** — bundle with adapter and base reference; exit sequence, integrity-reviewer.

## Sprint 20 — M4: agent simulation (B16; A05, A15; R01; ADR14)

**20.0 — Re-plan (INFRA)** — as 12.0; write `.claude/skills/agent-simulation/SKILL.md`.
**20.1 — Resettable simulator (FEATURE)** — observations and the five actions in `../reference_workload.md`; no real effects.
**20.2 — Episodes and action ledger (FEATURE)** — durable action IDs; a retried action has one effect (A05).
**20.3 — Independent oracle (FEATURE)** — final-state success separate from reward; loops, forbidden actions and false "done" rejected (A15).
**20.4 — Bounded configuration search (FEATURE)** — at most 4 configurations, 8 steps and 60 s per episode.
**20.5 — Gate** — exit sequence; M4 gate report.

---

## Backlog (outline only, not prompts)

- **M5 pilot (B17):** representative customer data, shadow mode, measured handling time, gate G4.
- **M6 public listing (B18):** claim review, signing identity, gate G5.
- **E1–E6 (B37):** clustering and anomaly; SciPy and volatility forecasting; vision; audio and multimodal;
  Unsloth; bounded RL — each through the Sprint 11 extension mechanism with its own oracle.
- **More compute (B23):** Hugging Face Jobs, then partner clouds on evidenced demand.
- **Runner hardening:** a VM or remote backend behind RunnerPort if shared or hosted use is ever needed.

## Traceability

| IDs | Sprint |
|---|---|
| B01 | 0 |
| B02, B03, B05 | 1 (B03 and B05 complete in 3, B05 runner in 4) |
| B28, B35, B29 | 2 (B29 continues in 3 and 8, B35 in 11) |
| B25 | 3 |
| B26 | 4, 5 |
| B24, B27 | 5 (B27 complete in 11) |
| B30, B04 | 6 (B04 splits in 9) |
| B33 | 7 |
| B31, B36, B07 | 8 (B07 and B36 complete in 9 and 10) |
| B06, B32 | 9 |
| B08, B09, B10 | 10 |
| B34 | 11 |
| B14 | 12 |
| B19 | 13 |
| B20, B21 | 14 |
| B11 | 15 |
| B12, B13 | 16 |
| B22 | 18 |
| B15 | 19 |
| B16 | 20 |
| B17, B18, B23, B37 | Backlog |
| A01, A02 | 9 |
| A03, A04, A07, A08 | 3 (A08 multi-worker in 16) |
| A05, A15 | 20 |
| A06 | 15 |
| A09, A10, A11, A12 | 10 (A11 hosted restore in 16) |
| A13 | 8, 9 |
| A14 | 9, 12, 19 |
| A16 | 11, 16 |
| A17, A18, A19, A21, A22 | 14 |
| A20 | 13, 14 |
| A23 | 18 |
| A24 | 3, 5 |
| A25, A26, A27, A33 | 3 |
| A28 | 4 |
| A29 | 5, 9 |
| A30 | 5, 10, 11 |
| A31, A32 | 2 |
| A34 | 8, 11 |
| A35 | 6 |
| A36 | 8, 9 |
| A37 | 8, 16 |
| A38, A42, A43 | 11 |
| A39, A40, A41 | 7 |
| A44 | 2, 11 |
| A45 | 8, 10 |
| R01 | 8, 9, 12, 19, 20 |
| R02, R03, R04 | 10 (R02 offline kit in 11) |
| R05 | 3, 9, 15 |
| R06, R10 | 16 |
| R07 | 4, 11 |
| R08, R13 | 14 |
| R09 | 4, 14 |
| R11 | 1, 8, 10 |
| R12 | 15 |
| R14 | 13, 18 |
| R15 | 3 |
| R16, R18 | 5 |
| R17 | 5, 9 |
| R19, R20, R26 | 2 |
| R21 | 6 |
| R22 | 5, 8, 9, 12 |
| R23 | 8, 16 |
| R24 | 7 |
| R25 | 11 |
| R27 | 8, 10 |
