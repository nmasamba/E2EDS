# Decisions log

One dated line per entry, written when it happens.
`- **YYYY-MM-DD — S<N> — KIND — topic** — what and why; alternatives.`
KIND: DECISION (owner or agent choice), ASSUMPTION, DEVIATION (from the suite or a pin), DEFECT, FINDING
(out-of-scope concern noted, not fixed). Suite IDs refer to the planning suite in `../`.

## Owner decisions

- **2026-10-01 — S0 — DECISION — product name and location** — the suite is implemented as "DS Playground" in
  `ds_playground/`; the suite in `../` is the read-only specification.
- **2026-10-01 — S0 — DECISION — target operating systems (O24)** — macOS arm64 and Linux, with Linux working
  as early as possible. Linux is in every sprint gate from Sprint 1. Alternative: Linux x86-64 only per D16.
- **2026-10-01 — S0 — DEVIATION — code runner (ADR07, ADR20, C14, C18)** — generated and imported code runs as
  a native process in an OS sandbox (Seatbelt on macOS, bubblewrap + seccomp on Linux) instead of a dedicated
  VM. Owner's reason: run as close to natively as possible; a VM adds boot time, setup and loses GPU access for
  a single-user tool. Consequences: `ComputeBinding` needs a new schema version (an OS-sandbox value for
  `generated_code_policy` and its trust model; macOS allowed as an execution OS); acceptance scenario A28 is
  recorded at *OS-sandbox, single-user* assurance, not VM assurance; this is not a boundary for hostile
  multi-tenant code. The runner stays behind a port so a VM or remote runner can be added. Alternatives
  considered: Lima VM per task; environment only with no sandbox.
- **2026-10-01 — S0 — DEVIATION — assistant models (ADR17, ADR18, R16)** — open and proprietary models are both
  allowed; open models first and used first for testing. The gateway is provider-neutral: local Qwen via
  llama.cpp, then open models on an OpenAI-compatible endpoint, then proprietary providers. Hosted or
  proprietary use is an explicit opt-in binding with data-transfer disclosure and a spend limit; no silent
  fallback. `AssistantModelBinding` needs a new schema version (0.3.0 fixes `local_supervised` / `llama.cpp`).
- **2026-10-01 — S0 — DECISION — prompt scope** — `prompts.md` covers M0 through M4 (Sprints 0–20); M5, M6 and
  E1–E6 are an outlined backlog.
- **2026-10-01 — S0 — DECISION — build mode** — scaffolding first, then build sprint by sprint, stopping only on
  the `AGENTS.md` stop list.

- **2026-10-01 — S0 — DECISION — standing approvals** — the owner approved, without further asking: pulling a
  Linux base image for `make verify-linux`; committing and pushing to the private repo `nmasamba/E2EDS` with a
  branch and pull request per sprint (merging stays with the owner); installing cmake, Rust and a source build
  of llama.cpp b11104; downloading the pinned Qwen3-8B Q4_K_M model (5.03 GB).
- **2026-10-01 — S0 — DECISION — economy** — ruthless token efficiency and no filler code. Consequences already
  applied: one reviewer subagent instead of four; schemas validated as plain dicts, typed models only where
  code needs one; the harness moved from Sprint 1 to Sprint 2 because nothing in Sprint 1 uses it.
- **2026-10-01 — S0 — DEFECT — baseline commit message** — commit `825b12f` on `main` says it includes the
  DS Playground scaffolding but holds only the suite and `docs/gates/G0.md`: the folder had been renamed to
  "untitled folder" by Finder when the commit was made. The owner confirmed the rename was accidental; the
  folder was restored and the scaffolding is in the next commit. Pushed history was not rewritten.

## Agent defaults awaiting objection

- **2026-10-01 — S0 — ASSUMPTION — roles** — the owner holds every role (PO, DO, DE, AO, ML, EO, PL, SEC, CL,
  FIN, PUB, SO, UX) in the local build, with the conflict declaration the suite requires. Approvals are
  explicit GUI or CLI actions.
- **2026-10-01 — S0 — ASSUMPTION — stack pins** — from `../research_sources.md`: Python 3.12, Pydantic 2.13.5,
  FastAPI 0.141.1, MCP Python SDK 2.2.0, DuckDB 1.5.5, Docling 2.130.0, scikit-learn 1.9.1, Optuna 5.0.0,
  MLflow 3.16.1, Tauri 2.12.0, llama.cpp b11104, Qwen3-8B-GGUF Q4_K_M at revision
  `7c41481f57cb95916b40956ab2f0b139b296d974`. A pin that does not resolve is bumped to the nearest version and
  logged here as a DEVIATION.
- **2026-10-01 — S0 — ASSUMPTION — renderer** — React + TypeScript + Vite inside the Tauri shell; the suite
  says only "a small web renderer".
- **2026-10-01 — S0 — ASSUMPTION — git** — one branch per sprint, Conventional Commits with a sprint prefix.
  The first push is asked for in Sprint 1 because `main` has no commits and pushing publishes the suite.
- **2026-10-01 — S0 — ASSUMPTION — licence** — no `LICENSE` file or licence headers until the owner ratifies
  the proposed Apache-2.0 core (O05, ADR08).

## Suite findings to carry

- **2026-10-01 — S0 — FINDING — objects without a schema** — CodeTask, RunManifest, EvaluationContract,
  EvaluationReport, DataManifest, SplitManifest, ExportReceipt, DeploymentBinding, Conversation, UsageRecord
  and ChangeProposal are described in `../contracts.md` but have no JSON Schema. The app authors schemas for
  the ones it implements, as new app-owned contracts.
- **2026-10-01 — S0 — FINDING — schema quirks** — secret references use two schemes (`secret-ref:` in
  ComputeBinding, `secret://` in AssistantModelBinding); some titles and descriptions carry stale version
  numbers (the `schema_version` const is authoritative); `format` keywords need format assertion enabled;
  several rules the suite requires are not schema-enforced (unique stage IDs, acyclic JoinPlan graph, non-null
  refs when `planning_only` is false) and must be semantic validators.
- **2026-10-01 — S0 — FINDING — example fixtures** — four example files are wrapper arrays (commands, requests,
  snapshots, capabilities); `reference_objects.json` and `analysis_reference_objects.json` hold many
  unschema'd object types with inconsistent field naming; every example is `planning_only: true` with null
  digests.
- **2026-10-01 — S0 — FINDING — suite table defects** — in `../requirements_and_decisions.md` the "Traceability
  for the general data workflow" table has rows R24–R27 pasted into it, and R23, ADR25 and O20 appear out of
  numeric order. The IDs themselves are intact.

## Sprint 1

- **2026-10-01 — S1 — DECISION — no typed models yet** — objects are plain dicts validated against the JSON
  Schemas; pydantic is not a dependency until the harness needs it (Sprint 2). Less code, one source of truth.
- **2026-10-01 — S1 — DECISION — pack manifest** — the Sprint 1 export uses a small app-owned `PackManifest`
  (relative paths, digests, recipe, source; no timestamps, so the same input gives identical bytes on macOS
  and Linux). The suite's `AnalysisReleaseManifest` needs run, report and evidence references that do not
  exist until Sprint 8; filling them now would mean fabricating them.
- **2026-10-01 — S1 — ASSUMPTION — recipe execution** — the built-in profiling recipe runs in-process and is
  labelled `signed_recipe`. It is reviewed code in this repository, not generated code; it moves into the
  sandboxed runner in Sprint 4.
- **2026-10-01 — S1 — ASSUMPTION — error code for a digest mismatch** — the suite's shared codes have none for
  integrity failures; a staged file that does not match its digest raises `INTERNAL_ERROR`.
- **2026-10-01 — S1 — DEFECT — integer detection** — found by test: DuckDB rounds `'43.2'` when cast to
  BIGINT, so decimals were proposed as integers. Fixed by requiring a full digit match; integer ranges come
  from exact BIGINT values, not doubles.
- **2026-10-01 — S1 — ASSUMPTION — fixture randomness** — the orders generator uses `random.Random(seed)`;
  numpy is not a dependency until model fitting needs it (Sprint 9).
- **2026-10-01 — S1 — FINDING — Linux architecture coverage** — `make verify-linux` on this Mac runs
  linux/arm64. The docs' x86-64 profile is exercised only by the GitHub Actions `ubuntu-24.04` job.

## Sprint 2

- **2026-10-01 — S2 — ASSUMPTION — two ledger openers until 2.3** — the harness now exists, but `dsp profile`
  still opens the ledger itself. SQLite's write lock keeps this safe; the single-writer rule is met when 2.3
  moves the command behind the harness with scoped folder handles.
- **2026-10-01 — S2 — DECISION — browser origins** — the harness refuses any request carrying an `Origin`
  header. Prompt 2.2 allows exactly the desktop shell's origin.
- **2026-10-01 — S2 — FINDING — test client deprecation** — Starlette 1.7.0 warns that using `httpx` with its
  test client is deprecated in favour of `httpx2`. Not acted on: the pinned FastAPI works and the warning is
  not an error.
- **2026-10-01 — S2 — DEVIATION — socket guard** — the default test run now allows connections to 127.0.0.1
  only (`--allow-hosts`), instead of disabling sockets outright, because harness tests use a real loopback
  server. Every other host is still blocked.
