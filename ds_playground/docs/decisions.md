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

- **2026-10-02 — S0 — FINDING — model download truncation** — the transfer ended early three times (4.70, 4.79
  and 5.01 of 5.03 GB), once with curl reporting success, and each partial file had a different SHA-256. The
  source's headers confirmed the expected size and digest, so the transfer was resumed until the size matched;
  the complete file's digest equals the pinned one. Lesson for Sprint 5: verify size **and** digest before any
  load, and never treat a finished download command as a finished download.

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
- **2026-10-02 — S2 — DECISION — shell origins** — the harness admits two fixed origins: `tauri://localhost`
  (Tauri's custom-protocol origin on macOS and Linux) always, and `http://localhost:1420` only when the harness
  process is spawned with `--dev`, which the shell passes under `tauri dev` only. Every other origin is 403. A
  preflight from an allowed origin is answered (204) before the token check; a 401 to an allowed origin carries
  the CORS grant so the window can show the reason. Written in the guard rather than with Starlette's
  `CORSMiddleware`, which answers a foreign preflight with 400 and would run outside the 403 rule.
- **2026-10-02 — S2 — DECISION — shell privileges** — the app manifest lists the one command (`harness`), which
  makes commands deny-by-default; the only capability grants `allow-harness` to the `main` window. No Tauri
  plugin and no core permission (events, windows, paths) is granted. The command reads `harness.json` on each
  call and returns the base URL and token; its error text carries no path.
- **2026-10-02 — S2 — ASSUMPTION — frozen sidecar** — PyInstaller 6.22.3, one file, named for the Rust host
  triple. It unpacks itself to a temporary directory at each start (first answer in 1.0–1.4 s on this Mac) and
  runs as two processes (bootloader and harness). Alternative: a one-directory build, faster to start but many
  files to bundle and sign.
- **2026-10-02 — S2 — ASSUMPTION — the harness outlives the window** — the shell spawns the harness and never
  stops it; quitting the app leaves it running for the next launch or the CLI. Close, quit and crash behaviour
  (D24) is prompt 2.7.
- **2026-10-02 — S2 — ASSUMPTION — connection attempt** — the renderer retries an unreadable state file or an
  unanswered port for 15 s (the sidecar may still be starting), then shows "harness unavailable"; any answer
  from the harness is final. It does not retry after that; reconnect and replay are prompts 2.6 and 2.7.
- **2026-10-02 — S2 — ASSUMPTION — app identity** — bundle identifier `dev.dsplayground.desktop`, product name
  "DS Playground", and a generated placeholder icon (one 512 px PNG; Tauri derives the `.icns`). All three are
  the owner's to change before any signed release.
- **2026-10-02 — S2 — ASSUMPTION — renderer toolchain** — React 19.3.0, TypeScript 7.0.2, Vite 8.3.2, exact pins.
  No `@vitejs/plugin-react` and no Vite config file: Vite's built-in JSX transform is enough and the dev port
  is set on the command line. The Rust toolchain version is not pinned; CI uses the runner's stable.
- **2026-10-02 — S2 — DEVIATION — no Vitest yet (prompt 2.2 text)** — on the owner's direction for this prompt,
  Vitest is added only when a pure function exists to test; the renderer has none until the reducer in 2.6.
- **2026-10-02 — S2 — FINDING — CSP and Tauri's own IPC** — the CSP is `default-src 'self'; connect-src
  http://127.0.0.1:*`, as directed. Read from `tauri-2.12.0/scripts/ipc-protocol.js`: Tauri first tries its
  `ipc:` scheme with `fetch`, which this CSP blocks, then falls back to its `postMessage` channel for the rest
  of the session. The command works either way (verified by the window's requests reaching the harness); the
  fallback itself was not observed, because the webview console cannot be read from a script. Adding `ipc:
  http://ipc.localhost` to `connect-src` would avoid the fallback; left for the owner.
- **2026-10-02 — S2 — FINDING — what the macOS end-to-end test cannot see** — WKWebView has no WebDriver, and
  screen capture and accessibility scripting were refused to the build session, so the window's text is not
  read on macOS. The test launches the built `.app`'s binary on a temporary `DSP_HOME`, waits for
  `harness.json` and a 200 from `/v1/status`, and terminates the app with a signal; the Quit menu item is not
  exercised. Checked once by hand with a logging copy of the harness app holding the profile: the built app's
  window sent `OPTIONS` (204) then `GET` (200) with `Origin: tauri://localhost`, and under `tauri dev` with
  `Origin: http://localhost:1420`.
- **2026-10-02 — S2 — FINDING — dev window against an ordinary harness** — if a harness is already running for
  the profile without `--dev` (for example started by `dsp status`), `make desktop-dev` shows "harness
  unavailable": the dev origin is refused by design. Stop that harness first.
- **2026-10-02 — S2 — ASSUMPTION — Makefile PATH** — the Makefile prepends `/opt/homebrew/opt/rustup/bin` and
  `~/.cargo/bin` so the desktop targets find the keg-only Rust on this Mac; harmless on Linux.
- **2026-10-02 — S2 — FINDING — AppImage tooling is downloaded at build time** — Tauri's AppImage bundler
  fetched `AppRun-x86_64`, `linuxdeploy-x86_64.AppImage` and `linuxdeploy-plugin-appimage` (its `continuous`
  release, so not a fixed version) from GitHub on the CI runner. These are outside every lock file. Not acted
  on; pinning or vendoring them belongs with signing and release work.
- **2026-10-02 — S2 — ASSUMPTION — Linux end-to-end artifact** — the Linux desktop test unpacks the built deb
  (`dpkg-deb --extract`) and drives that app with tauri-driver 2.1.0 and WebKitWebDriver; it speaks WebDriver
  over `httpx`, so no Selenium dependency. The AppImage is built in CI but not launched.
