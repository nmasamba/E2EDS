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
- **2026-10-02 — S2 — DECISION — who may turn a path into a grant** — `POST /v1/grants` accepts a path only
  from a request with no `Origin` header: the shell's Rust side and the CLI. A page cannot remove or forge
  that header, so the window, even with the owner token, cannot grant a path; it can list and revoke. The
  renderer asks the shell to open the picker and receives a handle and folder name. Alternative: a second,
  narrower credential for the window; more machinery for the same result today.
- **2026-10-02 — S2 — DECISION — `dsp profile` runs in the harness** — as the 2.1 entry planned, the command
  now goes through the harness with grants, which closes "two ledger openers": the harness process is the
  only ledger writer (one connection per request; SQLite's write lock serialises them). `dsp verify` stays
  local; it reads only the pack. Consequence: the gate takes about 27 s instead of 8 s, because the CLI tests
  start real harness processes.
- **2026-10-02 — S2 — ASSUMPTION — what a CLI command grants** — `dsp profile FILE --out FOLDER` grants that
  one file as a source and that folder as an output root; `dsp grant` grants a whole folder. Grants last until
  revoked and are reused when the same path is granted again for the same purpose.
- **2026-10-02 — S2 — ASSUMPTION — FolderGrant contract** — an app-owned `FolderGrant` 0.1.0 is the only
  record that holds the machine path. Events, answers and the window carry the handle and a label, which is
  the folder's own name (one path component, not a path). Revoking writes a successor revision; history stays.
- **2026-10-02 — S2 — ASSUMPTION — proposed OutputBinding** — an output grant also records a suite
  `OutputBinding` 0.6.0 as a planning record: `state: proposed`, no authorisation or receipt, `root_handle`
  the grant, `relative_directory: "."`. No project or output object exists yet, so `project_ref` is the
  constant `project-local` and `output_ref` is `output-<handle>` with a null digest; `max_export_bytes` is the
  suite example's 1 GiB and is declared, not enforced. Nothing reads the binding yet; the export in Sprint 8
  activates it against a real output.
- **2026-10-02 — S2 — FINDING — a planning binding cannot be revoked in the suite schema** — `planning_only:
  true` forces `state: proposed`. Revocation is therefore recorded on the FolderGrant; a binding whose handle
  is revoked resolves nothing.
- **2026-10-02 — S2 — ASSUMPTION — limits of the use-time check** — a path is resolved, with every symlink
  followed, and compared with the granted root each time it is used. A local process that swaps a link
  between that check and the open could still win the race; ordinary local-user compromise is outside the
  suite's promise, and generated code gets read-only inputs in the Sprint 4 sandbox. A folder that contains
  the harness's own state directory is not refused.
- **2026-10-02 — S2 — DEFECT — host path in the export event (fixed)** — since Sprint 1 the `export.committed`
  event and ExportReceipt held the output folder's host path in `destination`. It now holds the grant handle.
  Found by asserting that no ledger event contains a path after a profile.
- **2026-10-02 — S2 — DEFECT — the frozen harness could not start once it validated contracts (fixed)** —
  PyInstaller did not bundle the contract schemas or the `rfc3987_syntax` grammar, so the sidecar crashed on
  import as soon as the harness used the validator. `make harness-bin` now collects both. Found by the
  built-app test, which now also profiles a real file through the bundled harness.
- **2026-10-02 — S2 — DECISION — folder dialog and the shell's request** — `rfd` 0.16.0 directly (the version
  Tauri's dialog plugin wraps) with its GTK 3 backend on Linux, so the dialog is an ordinary in-process
  window; the plugin would add the filesystem plugin crate, and the portal backend needs a desktop portal
  service. The dialog is created on the main thread and awaited off it, as the plugin does. `ureq` carries
  the chosen path to the harness; the alternative, passing it through the renderer, is what C23 forbids.
- **2026-10-02 — S2 — FINDING — what the window can call** — the preflight allows only the `authorization`
  header, so a page cannot send a JSON body: the window can use `GET` and body-less `POST` (revoke) only, and
  `/v1/profiles` is reachable from the CLI alone. A prompt that lets the window start work must allow
  `content-type` for the shell origin.
- **2026-10-02 — S2 — FINDING — what is and is not automated for the folder dialog** — Automated: the
  shell's request that turns a chosen path into a grant (a Rust test against a real harness, run on both
  OSes by `make e2e`); the window's list, add, cancel, remove and error states (Playwright against a real
  harness, with Node standing in for the shell); and, on Linux in CI, the built app opening the real GTK
  dialog and granting nothing when it is cancelled. Not automated on either OS: choosing a folder in the
  real dialog. On Linux three attempts with xdotool failed (no window manager; then a window manager with
  activation; then repeated accept keys with screenshots): the typed path reached the dialog's location
  field but GTK kept its accept button disabled. On macOS the dialog cannot be scripted from this session;
  checked once by hand that it opens: with a scratch renderer that called the command on load, a new AppKit
  open-panel service process appeared and went away with the app.
- **2026-10-02 — S2 — FINDING — tests were mutation-checked** — each guard added in 2.3 (path containment,
  revoked and wrong-purpose handles, the no-Origin rule, the file check, the active-only list, the
  structured internal error, the window's Remove, handles kept out of the page) was broken in turn to
  confirm a test fails. One guard was found redundant this way and removed (re-resolving the granted root).
- **2026-10-02 — S2 — DEFECT — a late refresh could wipe a newer message in the Folders view (fixed)** — the
  view started a list refresh on load and another update on a click; if the first finished second it cleared
  the newer result, so an error could vanish. It showed up as one failed renderer test on the slower Linux
  runner. Updates now run one at a time in order, and a test delays the first refresh to hold the race open.
- **2026-10-02 — S2 — DECISION — manual check of the folder dialog** — the owner tested the real app: a source
  folder can be added through the native dialog, appears by its correct name, and can be removed. This closes
  the one check that could not be automated in prompt 2.3.
- **2026-10-02 — S2 — DECISION — discovery probes (2.4)** — five fixed probes: system, CPU, memory, storage
  and accelerators. macOS reads `sysctl`, `vm_stat` and `system_profiler` by absolute path; Linux reads
  `/proc/meminfo`, cgroup v2 limits, CPU affinity and `nvidia-smi` if it is installed. Probes run side by
  side with two seconds each, so discovery takes about two seconds at most, inside D19's ten. A denied,
  missing, slow or failed probe leaves its fields null with a fixed reason; exception text never enters a
  snapshot. No serial, user name, host name or path is read.
- **2026-10-02 — S2 — ASSUMPTION — discovery limits (2.4)** — available memory on macOS is an estimate from
  VM statistics (free, inactive and speculative pages). An Apple GPU is recorded as sharing the host's memory
  domain with no memory of its own. On Linux only NVIDIA devices are listed; without `nvidia-smi` the
  inventory is unknown, not absent. CPU features are not collected. `available_to_plan_cpus` stays null: the
  planner, not the collector, decides what may be used. Isolation readiness is always unknown until the
  sandboxed runner exists (Sprint 4). No user-declared inventory can be entered yet; the planner already
  treats one as unqualified.
- **2026-10-02 — S2 — DECISION — feasibility rule table (2.5)** — `feasibility-rules-1.0.0`, first matching
  rule decides: blocked for an unsupported family, a paid option at a zero charge cap, an unsupported
  profile, or capacity below need within the option's limits (never host totals; devices never added up);
  unknown when nothing was observed, including fixture inventories; unqualified for a visible but unchecked
  accelerator, a user-declared inventory, an unqualified profile or unqualified isolation; otherwise
  eligible. The selected option is the best ranked, preferring options with no external charge. PASS needs
  an eligible option, a real workload and qualification evidence; FAIL means every option is blocked;
  anything else is INSUFFICIENT_EVIDENCE. No runtime, cost or quality estimate is produced.
- **2026-10-02 — S2 — ASSUMPTION — host reserve (2.5)** — when the workload shares the host, the rule table
  keeps 1 CPU and 2 GiB of memory for the host. A policy figure, not a measurement.
- **2026-10-02 — S2 — ASSUMPTION — what the app plans for until Sprint 3 (2.5)** — no workload or compute
  binding exists yet, so the harness plans a draft of the one thing the product can run, the built-in CSV
  profile (1 CPU, 1 GiB memory, 1 GiB scratch, 600 s, zero external charge), on a draft local option. The
  plan's workload, binding and evaluation references are placeholders with null digests, the plan is a
  planning record, and it says so in its conditions. Each discovery proposes a new plan that supersedes the
  last.
- **2026-10-02 — S2 — FINDING — the suite's WorkloadSpec cannot describe a field-agnostic workload** — it
  requires at least one field role and an evaluation contract, so the CSV profile cannot be written as a
  valid WorkloadSpec without inventing a field. The draft above is therefore not validated as one. The
  ComputeBinding schema still allows only Linux and a VM policy (the standing owner deviation; Sprint 4).
- **2026-10-02 — S2 — DECISION — events and the stage reducer (2.6)** — `GET /v1/events?after=` returns
  events after a cursor, and `GET /v1/events/stream` serves the same over SSE: replay, then follow, with a
  keep-alive comment every five quiet seconds. The ledger keeps every event, so no cursor expires; a cursor
  the ledger never issued gets a reset flag (or `stream.resynchronised`) and the whole history, which is the
  snapshot until retention exists. The window polls every two seconds rather than holding a stream. A pure
  reducer in the renderer derives the stages: discovery completes or leaves the environment inconclusive, a
  plan leaves the review waiting for the owner, job events drive develop; every other stage stays not
  started, and unknown event types change nothing.
- **2026-10-02 — S2 — ASSUMPTION — header and controls (2.6)** — the header shows the connection only. There
  is no workload, budget, Pause or Cancel to show until Sprint 3 adds jobs and conversation, so none is drawn.
- **2026-10-02 — S2 — DECISION — lifecycle (2.7)** — closing the window ends the app and leaves the harness
  running. Quit from the menu or its shortcut sends `POST /v1/shutdown` when the shell started the harness
  and it is still running; the harness finishes requests in progress, ends open streams and exits. A shell
  that attached to someone else's harness leaves it running. `dsp stop` is the CLI's Quit. A window that
  loses the harness keeps its last known state, asks the shell for the harness's current address and
  replays from its cursor. D24's pause-then-quit has nothing to pause until jobs exist (Sprint 3).
- **2026-10-02 — S2 — FINDING — lifecycle limits (2.7)** — Quit from the macOS Dock, a logout or a signal is
  indistinguishable from a close and therefore leaves the harness running. Quitting the shell that owns the
  harness stops it under any second window, which then shows the connection as lost. Sleep and wake were
  not exercised. On macOS the Quit menu item and window close cannot be scripted from the build session; on
  Linux both are pressed for real in CI.
- **2026-10-02 — S2 — DECISION — evidence outcomes (2.8)** — an evidence record states the scenario as the
  suite words it and gives PASS only when the run showed all of it. A31 is PASS. A32 and A44 are
  INSUFFICIENT_EVIDENCE: every part exercised passed, but each scenario includes parts whose objects do not
  exist until later sprints. The Sprint 2 gate is PASS for the sprint's own scope.
- **2026-10-02 — S2 — DEFECT — a background refresh cleared the owner's problem message (fixed)** — in the
  Folders view, a list refresh triggered by events from elsewhere cleared an error left by the owner's own
  action. It showed as one failed renderer test on the Linux runner, twice. Only the owner's own action now
  sets or clears that message; a test reproduces it with a grant made elsewhere.
- **2026-10-02 — S2 — FINDING — test checks that needed changing (2.7, 2.8)** — the Linux container has no
  `ps`, so tests wait for the harness's instance lock to be free instead; a window close under Xvfb is asked
  of the window manager with `wmctrl`, because an Alt+F4 chord sent with xdotool did not close it. The gate
  now takes about 50 s on macOS: the CLI and lifecycle tests start real harness processes.

## Sprint 3

- **2026-10-08 — S3 — DECISION — job record and fence (3.1)** — a job is an app-owned `Job` 0.1.0 object whose
  every transition is a new immutable revision committed with one `job.*` event in one ledger transaction
  under the job aggregate's compare-and-swap; the event body carries the action and its input, so the
  pure state machine (`domain/jobs.py`) replays a job's events to the stored job. One integer `fence`
  serves as the dispatch epoch: lease expiry, pause and cancel each advance it. A result commit needs the
  live attempt (its attempt number and the fence it was leased under) and a state that accepts results;
  pause and cancel leave those states as they advance the fence, so a fenced attempt can still report that
  it stopped (drain evidence) but never commit a result. Alternative: event-sourced jobs with no object
  row, which would make every list and capacity check a scan of the event log.
- **2026-10-08 — S3 — FINDING — a redundant fence clause (3.1)** — the explicit check that the lease's fence
  still equals the job's fence survived no mutation test: every fence advance either clears the lease or
  leaves the result-accepting states, so the attempt-and-state check already enforces it. Removed, as
  Sprint 2 removed its redundant guard; the state check was then mutated and is caught by the A07 tests.
- **2026-10-08 — S3 — DECISION — lease expiry is reconciled on touch (3.1)** — a lease that has run out is
  expired, and the fence advanced, by the next coordinator operation on that job (a lease request, a
  heartbeat, a report, a control or a read); the expiry counts as one transient failure, so three silent
  attempts end in `failed`. Consequence until the Sprint 4 runner brings a reconciler: a job whose worker
  died is shown as running until something touches it. Alternative: a timer thread in the harness; not
  needed by any test or flow this sprint.
- **2026-10-08 — S3 — ASSUMPTION — the worker runs outside the harness (3.1)** — the only workload is the
  deterministic test worker in `fixtures/worker.py`, a separate process started by the tests, by
  `make e2e`, or by the owner with the pasted command; the harness never spawns it, and the frozen
  sidecar does not carry test fixtures. A queued job therefore waits for a worker. The sandboxed runner of
  Sprint 4 is the first worker the harness dispatches itself.
- **2026-10-08 — S3 — ASSUMPTION — worker routes are native only (3.1)** — `lease`, `heartbeat` and `report`
  refuse a request with an `Origin` header, like `POST /v1/grants`: the window may queue and control jobs
  but is never a worker. A stale or refused report is recorded on the job as `job.result_rejected` with its
  attempt, fence and the refusing code, so a fenced worker's return is visible (A04), then refused.
- **2026-10-08 — S3 — ASSUMPTION — test harness on a movable clock (3.1)** — leases are 60 s and tests must
  not wait: the `harness` fixture serves the real app from the test process on a loopback socket with a
  clock the test moves forward (the clock is now a parameter of `workspace.mount`), and worker processes
  find it through `harness.json` like any harness. Heartbeats are the worker's real time (`--heartbeat-
  seconds`, default 15; 0 makes a silent worker). No production code knows it is under test.
- **2026-10-08 — S3 — ASSUMPTION — `inconclusive` is not produced yet (3.1)** — nothing in this sprint can
  leave a job's evidence unresolved (no external execution), so the schema's state list omits it; the
  Sprint 4 runner adds it with the first path that needs it. `Job` 0.1.0 is finalised at the end of this
  sprint; prompts 3.2 and 3.5 add fields to the same file before anything is released.
- **2026-10-08 — S3 — DECISION — admission records (3.2)** — `POST /v1/jobs` is admission: the caller
  supplies the operation, a logical idempotency key and the task; everything else is derived. One ledger
  transaction on a single `admission:host-local` aggregate commits the suite `ExecutionRequest` 0.5.0
  (`planning_only: false`, `state: admitted`, workload, binding and plan pinned by digest, authorisation
  context the trusted principal), an app-owned `Reservation` 0.1.0 (cpu, memory, scratch, external charge
  zero) and the queued `Job`. Two requests racing for the last reservation both read the same aggregate
  sequence, so one commit conflicts, reloads what is held and is refused (A08). A refusal other than
  missing authority is recorded as a rejected request with its reason; a missing scope is refused before
  anything is read or written. The reservation is released in the same commit as the job's terminal
  transition.
- **2026-10-08 — S3 — DECISION — the test job's WorkloadSpec arrives with admission, not 3.5 (3.2)** — an
  admitted ExecutionRequest must pin a workload revision by digest, and a conversation command must
  reference one, so `application/workloads.py` defines revision 1.0.0 now (`workload-test-job`, the
  smallest schema-valid WorkloadSpec: `data_analysis`, `exploratory_analysis`, `headless`, the orders
  fixture's three field roles, 1 CPU, 1 GiB, 1 GiB scratch, 600 s, zero charge). It is a planning record
  with null evidence references; it is stored with the first admission and read back as the current
  revision; prompt 3.5 adds revisions. The plan now plans for it, so Sprint 2's `profile_draft` is gone;
  the plan's text is unchanged because the resources are the same. The suite schema forces
  `conversational` workloads to name an assistant binding, which does not exist until Sprint 5, hence
  `headless`; the conversation references the workload, not the other way round.
- **2026-10-08 — S3 — ASSUMPTION — the code task behind the test job (3.2)** — a non-planning
  ExecutionRequest must reference a `source_code_task_ref` with a digest. No CodeTask object exists before
  Sprint 4, so the reference is `code-task-test-worker` 1.0.0 with the digest of the task itself (its
  cues and seconds): the declared work, content-addressed. Sprint 4 replaces it with the hashed CodeTask.
- **2026-10-08 — S3 — DEVIATION — an unqualified local option may run the test job (3.2)** — the suite
  admits only a qualified, authorised binding. The local draft binding has no qualification report and
  its isolation is unknown until Sprint 4, so a strict reading would admit nothing this sprint. Admission
  therefore refuses `blocked` (no family, paid at zero, no capacity) and `unknown` (nothing observed)
  dispositions and admits `eligible` or `unqualified` ones for the local test worker; the plan it pins
  records the disposition and the plan outcome stays INSUFFICIENT_EVIDENCE. The gate for real
  workloads returns to "qualified only" with the runner's qualification evidence.
- **2026-10-08 — S3 — DECISION — a stale plan is rechecked by proposing a fresh one (3.2)** — admission
  pins the latest WorkflowPlan only when it names the current workload revision and the latest
  HardwareSnapshot; otherwise it proposes a fresh plan from the current inputs (which supersedes the
  stale one) and pins that, then applies the rule table and the reservation sum to the latest snapshot
  (A33). A plan is advice; capacity is always rechecked at admission.
- **2026-10-08 — S3 — DECISION — typeless suite objects are stored under an explicit kind (3.2)** — the
  ledger keyed objects by their `type` field; `WorkloadSpec` (like `ComputeBinding`, `ReleaseManifest`
  and `ServiceSpec`) has none and forbids unknown fields. `Ledger.commit` now also accepts
  `(kind, object)` pairs. Alternative: an app envelope around suite objects, which would hash and store
  something other than the suite object.
- **2026-10-08 — S3 — FINDING — a redundant admission guard (3.2)** — an explicit "no snapshot" refusal
  survived no mutation: the planner's rule table already judges a missing observation as `unknown`,
  which admission refuses. Removed; the remaining eleven admission guards each fail a test when broken.
- **2026-10-08 — S3 — DECISION — messages and receipts (3.3)** — `POST /v1/conversations/{id}/messages`
  reads the raw body, refuses more than 16 KiB before parsing it (declared length first, then the bytes
  that arrive, so a chunked body is measured too), accepts exactly `client_message_id`, `text` and
  `expected_revision` as strings, and commits a suite `ConversationCommand` 0.3.0 (`received`) with its
  `message.received` event on the `conversation:<id>` aggregate before answering. The receipt names the
  command and its receipt event; the command's `receipt_event_ref` carries the event body's digest. The
  same ID again returns the same receipt and writes nothing; the same ID with other text is an
  IDEMPOTENCY_CONFLICT. Replay is the existing `/v1/events` cursor. The first message of a conversation
  creates an app-owned `Conversation` 0.1.0 in the same commit; the command pins it and the current
  workload by digest.
- **2026-10-08 — S3 — ASSUMPTION — operation classification without an assistant (3.3)** — the operation
  is derived on the server by exact match on the six control phrases (case, surrounding whitespace and a
  trailing full stop or exclamation mark ignored); anything else is an `instruction`. With no assistant
  bound until Sprint 5, an instruction is recorded as received and then `rejected` with
  ASSISTANT_UNAVAILABLE, which is the truthful answer; quoted or embedded phrases are instructions, so
  text from a document never becomes a control. Prompt 3.5 adds the deterministic requirement-change
  grammar in front of the assistant.
- **2026-10-08 — S3 — ASSUMPTION — command state changes are revisions (3.3)** — a command's state moves
  by a successor revision (`2.0.0`, `3.0.0`) with a `command.<state>` event, never in place, so the
  activity trail can show the receipt and each later state from events alone.
- **2026-10-08 — S3 — DECISION — the fast path (3.4)** — `application/controls.py` is the one path for
  the exact phrases, the window's buttons (`POST /v1/jobs/{id}/control`) and the native menu
  (`POST /v1/control`, which acts on the live job): each becomes a ConversationCommand whose receipt is
  committed first, then the coordinator transition, then the command's end state (`applied`,
  `superseded` when the job had already settled it, `rejected` with the code when the state refuses it).
  The path reads and writes the ledger only; no model and no worker is on it, which is what D18 asks and
  what A24 measures. Pause advances the fence (the dispatch epoch) at once and the lease route refuses a
  paused or pausing job; the worker learns of the pause at its next heartbeat, reports that it stopped,
  and only then is the job `paused`. The command ID is the client's idempotency key: a repeated ID is
  answered with the same receipt and the job as it is now, never applied twice.
- **2026-10-08 — S3 — DECISION — resume is a readmission on the admission aggregate (3.4)** — resume
  rechecks capacity against the latest observation less what is held, holds a new reservation (pause
  released the old one) and sets the job's workload reference to the current revision, in one commit on
  the admission aggregate so a race for capacity is serialised. A job transition that raced it loses on
  the Job revision's immutability (the same successor revision cannot be written twice), which acts as a
  per-object compare-and-swap; the loser reloads and reapplies. A refused resume is recorded as
  `admission.rejected` naming the job, which stays paused. A cancelled job cannot resume (`CANCELLED`);
  resuming a running job is refused.
- **2026-10-08 — S3 — ASSUMPTION — one local conversation, and what a phrase names (3.4)** — the local
  build has one conversation, `conversation-local`, which the buttons and the menu use. A phrase names no
  job: with exactly one live job (queued, running, pausing, paused, cancelling) it acts on that job; with
  none it is rejected ("no job is live"); with several it ends `needs_clarification`, as the suite asks
  for ambiguity, and the job's own controls remain available. Found by the A24 measurement, whose first
  version kept a second hung job alive as load and watched the phrase pause the wrong one.
- **2026-10-08 — S3 — DECISION — the preflight grants two headers (3.4)** — the shell origin's preflight
  now allows exactly `authorization` and `content-type`, so the window can send a JSON body; a preflight
  naming any other header is refused with 403 and no CORS grant.
- **2026-10-08 — S3 — FINDING — a checkpoint is only recorded, never resumed from (3.4)** — the worker
  may post a durable checkpoint digest, which is kept across pause and resume and shown with the job;
  the test worker never writes one and nothing restores from one until the Sprint 4 runner. During a
  cancel no checkpoint is taken.
- **2026-10-08 — S3 — DEFECT — a type error reached CI (3.2)** — the 3.2 push failed `mypy` on both
  runners (the desktop jobs passed): the guard removed after the mutation check left `needs` with a
  possibly-missing snapshot, and the type check was not rerun before the commit. Fixed in the 3.3 commit;
  from here every commit chain ends with lint, types and boundaries.
- **2026-10-08 — S3 — FINDING — the A24 measurement is slow (3.4)** — twenty pause and twenty cancel
  trials, each with its own hung worker process under every processor saturated, take about 150 s on
  this Mac; the test is `slow`, so it is in the gate and out of the inner loop.
- **2026-10-08 — S3 — DECISION — requirement revisions (3.5)** — a change instruction becomes a typed
  JSON-Patch-style list on the WorkloadSpec (`proposed_patch` on the command record), an impact preview
  (changed paths, the evidence kinds that depend on them through a small dependency graph, the stale
  items of jobs on this revision, the live jobs to hold), and a new immutable revision committed on the
  `workload:<id>` aggregate with a `workload.revised` event. The expected revision the message named must
  be the current one (REVISION_CONFLICT otherwise), and two edits that read the same revision are
  serialised by the aggregate so the second conflicts. Old revisions and the Job records that point at
  them are untouched; the stale marks live in the revision event. Live jobs on the old revision are paused
  after the revision commits, so the owner's explicit resume readmits them under the new one (a crash
  between the two leaves a job on the old revision until its next resume, which readmits anyway).
- **2026-10-08 — S3 — ASSUMPTION — the change grammar stands in for the assistant (3.5)** — with no
  assistant until Sprint 5, three deterministic instructions are understood: `exclude [the] field <name>`
  (keywords in any case, the field as typed; only a currently allowed predictor), `set [the] budget to
  <n>` and `change|set|replace [the] evaluation …`. The last two are typed on the owner's paths and
  refused with REQUIRES_CONFIRMATION, since budget and evaluation changes need the owner's own action
  (which does not exist yet as a UI). Anything else is an instruction. The assistant will propose patches
  into the same validation and application path.
- **2026-10-08 — S3 — ASSUMPTION — the dependency graph (3.5)** — three edges are enough for the sprint's
  workload: a feature change invalidates results and checkpoints; a resource change, reservations; an
  evaluation change, evaluations. The revision also makes the latest plan stale, so the next admission
  re-proposes it (A33) and pins the new `requirement_revision`.
- **2026-10-08 — S3 — DECISION — `GET /v1/workload` (3.5)** — the window reads the current revision to
  send as `expected_revision` and to show the fields; it is the current WorkloadSpec as stored.
- **2026-10-08 — S3 — DECISION — composer, activity and controls in the window (3.6)** — the renderer
  grew four pieces and no store: `Controls` (Pause or Resume, and Cancel run, in the header, each press one
  command with a fresh ID on `POST /v1/jobs/{id}/control`, answered with the job's actual state), the
  `Composer` (fixed above the resource bar; it keeps its draft and its message ID until the harness has the
  message, so a retry after a lost answer is the same message; `expected_revision` is derived from the
  events), `Run` (the one workload: "Start the hung test job", which admits the job and shows the worker
  command to run) and the `Activity` trail, a pure projection of committed events: what the owner said with
  the state each command reached, every job transition but heartbeats, revisions, refused admissions and
  the workspace's own events. `trail.ts` reads a job's state only from the coordinator's fourteen event
  types, so a spoofed type with a `state` field changes nothing. Plain CSS; axe clean on every page state
  the tests reach; Pause, Resume and Cancel are pressed with the keyboard alone in the renderer tests.
- **2026-10-08 — S3 — DECISION — the native menu's Pause and Cancel (3.6)** — two menu items, `Pause`
  (CmdOrCtrl+P) and `Cancel run` (CmdOrCtrl+., see the 2026-10-12 defect), send `POST /v1/control` from the Rust side the way Quit sends
  the shutdown: no renderer in the loop, so they work while the window is busy, and the command is in the
  ledger for the window to show. The command ID is the shell's process ID and a counter. There is no
  Resume item: resume is the header button or the phrase, an explicit act on a visible paused job.
- **2026-10-08 — S3 — FINDING — what the built-app test reads on each OS (3.6)** — on Linux the window
  starts the hung job, the real shortcuts pause and cancel it, and the trail is read through WebDriver,
  again from a second launch. On macOS, with no WebDriver for WKWebView, the same requests the window and
  the menu send are made against the bundled harness while the app is open, and the states are read back
  after a relaunch; the menu items themselves are exercised by the Rust test's `control` calls against a
  real harness. The owner's manual run on macOS remains the check of the real menu.
- **2026-10-08 — S3 — DEFECT — two tests assumed room for a second job (3.6)** — the Linux runner's CPU
  quota admits one test job at a time, so a controls test and the A26 test, which admit two, failed in CI
  after the 3.4 push (every other job passed). They now fix the machine with the same probes the A08 test
  uses. Tests that need capacity must say so rather than inherit the host's.
- **2026-10-08 — S3 — FINDING — no retention exists, so D06 holds by keeping everything (3.7)** — the
  ledger deletes nothing: idempotency records, commands, result keys and events are kept for ever, which
  meets D06's seven-day retry window trivially and is why an unknown cursor never means expired history.
  A retention policy (and the explicit expired-cursor snapshot it would need) is later work.
- **2026-10-08 — S3 — DECISION — evidence outcomes for Sprint 3 (3.7)** — by the Sprint 2 rule (PASS only
  when the run showed the whole scenario as the suite words it): A03, A24 and A27 are PASS at local scope;
  A04, A07, A08, A25, A26 and A33 are INSUFFICIENT_EVIDENCE because each names a part whose objects do not
  exist yet (release pointers, a provider that keeps charging, paid calls and late receipts, promotion,
  the evaluation owner and production, a model or provider to switch). Every part that could be exercised
  passed; the records say which parts could not be.
- **2026-10-08 — S3 — DECISION — the integrity review and what was done with it (3.7)** — the one
  `integrity-reviewer` run (as a general-purpose agent carrying the reviewer's own instructions, because
  the project's agent file is not in this session's registry; about 240k tokens) returned REVIEW: PASS with
  two should-fix findings and six notes. Landed: (1) the hold after a requirement revision could refuse
  (the held job had ended) and leave the revision's command `received` and the retry rejected; the hold is
  now best effort and the command settles applied, with a test that forces the refusal. (2) The A27 SAT
  claimed a dropped acknowledgement it did not perform; it now sends the first message over a raw socket
  that closes before any answer. (3) A retry racing its own commit was recorded as a rejection; the
  refusal is re-checked against the committed key. (5) A task longer than the workload's wall time
  (`seconds` up to 3600 against 600) was admitted; admission now refuses it. (6) A chunked message body
  was buffered whole before the size check; it is now bounded as it streams. (7) `readmit` and the
  command path trusted their caller; both now check the context's scopes (`job:submit`;
  `workload:interact` and `job:<action>`). (8) The admission compare-and-swap was proven only by thread
  timing; a ledger that interposes a second admission between the read and the commit now proves it
  deterministically. Logged, not fixed: (4) a worker's reported `charge_minor` is added to the job's
  incurred charge without comparison to the reservation's approved cap of zero; the test worker reports
  zero and cost settlement is out of this sprint's scope, so the record stays truthful but unflagged until
  Sprint 4 brings the first real cost. Each new guard was mutation-checked.
- **2026-10-08 — S3 — FINDING — no wall-time limit runs yet (3.7)** — admission refuses a task longer than
  the workload's 600 s, but nothing stops a heartbeating attempt that overruns it; the limit is enforced
  by the Sprint 4 runner.
- **2026-10-12 — S3 — DEFECT — the Cancel run shortcut does not fire on macOS (open)** — the owner's
  hands-on check of the built app: Cmd+P paused the job through the real menu three times (the ledger
  holds the shell's own command IDs), but Cmd+. produced nothing, and neither did a rebuilt app with
  CmdOrCtrl+Shift+C. muda registers both chords as real key equivalents, so the item exists; the
  difference from Pause is not understood yet, and the Cancel run item was not tried by mouse. Nothing
  shipped: the chord stays CmdOrCtrl+., which the Linux end-to-end test presses successfully in CI. The
  owner's one key press is the only way to prove a macOS chord from a session like this one; Sprint 4's
  housekeeping takes it up, with a renderer-handled shortcut (testable in Playwright) as the proposed
  route and the menu item kept for the mouse.
- **2026-10-12 — S3 — DEFECT — action feedback is scattered in the window (open)** — the owner's check:
  outcomes appear next to the buttons, next to the composer, in the Run section and in the status line,
  with no single place to read them, and the wording differs between places and from what the activity
  trail shows. Sprint 4's housekeeping makes the activity trail the one place every outcome appears,
  removes the inline notes, and tests the wording once.

## Sprint 5

- **2026-10-15 — S5 — DECISION — the owner's Sprint 5 choices (prompt 5.0)** — D1 = A: the Cancel run chord is
  `CmdOrCtrl+Shift+K` on both OSes, a letter chord like the working Cmd+P. D2 = A: `make live-linux` builds
  llama.cpp b11104 inside the verify container (a named Docker volume as its build cache), mounts the model
  read-only and runs the `live_model` tests there. D3 = A: after 5.1 the build stops at a checkpoint with a
  measured table (CPU 2 threads, CPU all cores, Metal full offload: load time, first-token latency, tokens/s,
  peak memory) and waits for the owner's pick. D4 = B: 5.6 ships the OpenAI-compatible adapter only, tested
  against a local OpenAI-compatible server (llama-server itself); no proprietary adapter, no keys, £0 spend,
  only synthetic fixtures may leave the machine. D5 = A: before any technical HALT one bounded investigation
  workflow may run (at most 9 agents, cost stated first); the `integrity-reviewer` runs once at 5.7.
- **2026-10-15 — S5 — DECISION — Cancel run is CmdOrCtrl+Shift+K (5.0, D1)** — closes the 2026-10-13 defect
  as far as code can: the renderer's chord table now keys on the chord without the platform modifier
  (`p`, `shift+k`), so Shift is part of a chord rather than a reason to ignore it; the native menu item says
  `CmdOrCtrl+Shift+K`; Playwright presses Meta+Shift+K on macOS and Ctrl+Shift+K on Linux against a real
  harness, and the Linux built-app test presses the real Ctrl+Shift+K through xdotool. Mutation-checked:
  with the old chord back in the renderer the Playwright spec fails. Whether the built macOS app delivers
  Cmd+Shift+K is the owner's press at the gate (the Cmd+. failure was seen only there).
- **2026-10-15 — S5 — DECISION — the launch contract as this build's flags (5.1)** — llama-server b11104
  (0.4.1-dev) on this Mac, each flag proven by a run: `-m`, `--host 127.0.0.1 --port 8081`, `-c 8192`,
  `-np 1`, `-t <threads>`, `-ngl <layers>`, `--offline`, `--no-webui` (`/` answers 404), `--no-agent` and
  no `--tools`, `--no-slots` (`/slots` answers 501; it would show prompt content), `--log-disable` (the
  server wrote 51 bytes of start-up text to its own stderr and nothing afterwards; no log file), `--reasoning
  off` (an answer carries no `reasoning_content` and no `<think>`: proven; the chat-template kwargs route was
  not needed), `--jinja` (tool calls come back as OpenAI-shaped `tool_calls` with `tool_choice: required`).
  `/metrics` is off by default (501); `GET /props` answers with the server's settings and chat template (no
  prompt content) and is used once at readiness to pin the template's digest; `POST /props` is off. The API
  key is generated once (`secrets.token_urlsafe(32)`), kept in the OS secret store under
  `secret://local/assistant-api-key`, written to a 0600 file under the state directory and passed with
  `--api-key-file`; it is in no process's arguments or environment (checked through `ps`), and the file is
  deleted when the server stops. The seed and temperature are per request, so the live tests fix them.
- **2026-10-15 — S5 — DECISION — the model server is confined by the OS (5.1)** — macOS: a deny-by-default
  Seatbelt profile applied by `sandbox-exec -f` (the binary is not ours, so the in-process `sandbox_init`
  of Sprint 4 does not apply): `file-read*` on the binary's folder, the model file, the key file, `/usr/lib`,
  `/System/Library` and the shared libraries the binary links outside those (read from `otool -L`: Homebrew's
  OpenSSL), metadata on their ancestors; `process-exec` of the server binary alone; `network-bind` and
  `network-inbound` on `localhost:8081` and no outbound rule, so egress is denied by the kernel, not by
  `--offline`; `(deny process-info*)` with `(allow process-info* (target self))` (the server reads its own
  process info and traps without it); sysctl reads by exact name only (36 names, taken from the denial log
  while it started under CPU and under Metal; none is `kern.proc*`); the Sprint 4 System V denial; and for
  Metal `iokit-open` on `IOSurfaceRootUserClient` and `AGXDeviceUserClient` plus `mach-lookup` of
  `com.apple.MTLCompilerService` (the shader library is embedded as source and compiled at start through
  that XPC service; without it Metal fails to create its library). Denials that remain and do not matter
  (the server works): `com.apple.bsd.dirhelper`, `opendirectoryd`, `diagnosticd` (so os_log is off),
  `windowserver`, `tccd`, metadata of `/etc`, `/var/db/timezone`, `/System/Cryptexes/App` and
  `.GlobalPreferences.plist`. Memory on macOS is polled (the kernel's footprint, every check and before
  every call) against the binding's `model_memory_gib` and the server killed past it: `sandbox-exec`'s exec
  drops a jetsam limit (the Sprint 4 measurement), so the limit is not kernel-enforced there. Linux:
  `prlimit --as` then bubblewrap with `--unshare-all --die-with-parent --new-session`, read-only binds of
  the system libraries, `ld.so.cache`, the binary's folder, the model and the key file, `--dev`, the root
  remounted read-only, no `/proc` (Docker forbids a fresh one) and the socket folder bound writable.
- **2026-10-15 — S5 — DEVIATION — on Linux the listener is a UNIX socket (5.1)** — with every namespace new
  the harness cannot reach `127.0.0.1:8081` inside the server's network namespace, so on Linux the server
  listens on `<state>/assistant/socket/llama.sock` (`--host` takes a socket path in this build) and the
  harness speaks HTTP over it; the binding record keeps the suite's `127.0.0.1:8081` (its schema allows no
  other host). The alternative, sharing the network namespace and trusting `--offline`, is what the suite
  says is not the boundary.
- **2026-10-15 — S5 — DECISION — the model is verified at every server start (5.1)** — size first (the
  Sprint 0 truncations), then SHA-256: hashing the 5.03 GB file takes 2.67 s on this Mac (1.89 GB/s); the
  binary (50 KB) is hashed too. A verification failure (missing, size, hash) is final until the harness
  restarts (the file does not change by itself); a crash, hang or limit is retried up to three times by the
  harness's watch tick, each restart re-verifying. The alternative, caching by size and mtime, saves under
  3 s per start and would trust a timestamp.
- **2026-10-15 — S5 — DECISION — readiness and the binding record (5.1)** — readiness is `/health` 200 plus
  a chat completion with one tool (`report_ready`, `tool_choice: required`) whose call must validate
  against the tool's JSON Schema, and whose answer must carry no reasoning. The suite's
  AssistantModelBinding 0.3.0 is written as a planning record (null digests) and, once ready, stored in the
  ledger with the measured model, binary and chat-template digests (`planning_only: false`) and pinned by
  the `assistant.ready` event; `assistant.unavailable` carries the reason. The workspace starts the
  assistant in a thread after it is up and stops the server on quit; `GET /v1/assistant` shows the state
  and the binding (no secret, no path). Model and server paths come from `DSP_MODEL_DIR` and
  `DSP_LLAMA_SERVER`, defaulting to `~/.local/share/dsp`; a port held by another process is refused before
  spawning, and a server a crashed harness left is killed by its pid file only if its command line is ours.
- **2026-10-15 — S5 — DECISION — the secret store (5.1)** — macOS: the Security framework's generic-password
  C API through ctypes (`SecKeychainAddGenericPassword`, `SecKeychainFindGenericPassword`,
  `SecKeychainItemModifyAttributesAndData`; deprecated since 10.10, working on 26.3.1, proven here), never
  the `security` command with `-w`, which would put the secret in a process's arguments; the login keychain
  by default, a keychain file with its password for tests (`security create-keychain` under tmp). Linux:
  `secret-tool` (the value on its standard input) when present, else a 0600 file under a 0700
  `<state>/secrets/` (the container and CI); a folder others can read is refused. Service name
  `dev.dsp.assistant`, account the last part of the `secret://local/<account>` reference. Not tested:
  `secret-tool` present without a Secret Service (no such host here).
- **2026-10-15 — S5 — ASSUMPTION — no test loads the model by accident (5.1)** — every pytest harness runs
  with `DSP_MODEL_DIR` pointed at an empty folder (an autouse fixture), as do Playwright's harnesses, the
  shell's Rust test and the built-app tests; `live_model` tests start one real server per session and lend
  it to each harness. A harness start therefore records `assistant.unavailable: model missing` as its
  first event, and four tests that asserted exact event lists now expect it.
- **2026-10-15 — S5 — FINDING — what the D3 measurement shows (5.1)** — see the checkpoint table in
  `STATUS.md`: under the Seatbelt profile on this M1 Max, CPU with 2 threads generates 11.5 tokens/s, CPU
  with all 10 cores 11.1 tokens/s (the efficiency cores slow the whole), Metal full offload 45 tokens/s with
  prompt processing at 258 tokens/s and the typed probe in 1.1 s against 10 s on 2 CPU threads. The
  footprint the kernel accounts (what the memory poll reads) is 5.6 GiB on CPU and 1.2 GiB on Metal, whose
  weights live in GPU-mapped memory the footprint does not count; resident size is 9.9 GiB and 6.0 GiB.
- **2026-10-15 — S5 — DEFECT — a server that answered health but failed readiness was left running
  (5.1, fixed)** — found by a mutation run that put the key in the arguments: the server started, health
  answered, the authenticated probe got 401, the adapter raised without stopping the process and the
  port stayed held. Readiness after health is now one step whose failure stops the server; a unit test
  runs a real process that answers health and refuses everything else and checks it is gone afterwards
  (mutation-checked). On Linux `ps -o command=` cuts the command line at the terminal's width, which hid
  `--api-key-file` from the live test and would have stopped the stale-server check from recognising its
  own server: both use `ps -ww` now.
- **2026-10-15 — S5 — FINDING — guards mutation-checked (5.1)** — each broken in turn, each caught by a test:
  the size check, the hash check, a stale server killed only when its command line is ours, a port held by
  another process refused before spawning, `(deny default)` in the profile, `--unshare-all` on Linux, the
  keychain's replace path, the fallback folder's permissions, the key as a file rather than an argument
  (both the flag and the value), outbound network denied in the profile (the A30 probe connects when it is
  allowed), the typed probe deciding readiness (made stricter: the real model cannot be made to fail it, so
  the check was shown to run), `--no-slots`, `--reasoning off` (with reasoning on the answer carries
  `reasoning_content`), the quit stopping the server, and a readiness failure stopping the server.
- **2026-10-15 — S5 — FINDING — one model server at a time in the Linux container (5.1)** — Docker
  Desktop's VM has 7.75 GiB; inside it llama-server holds the model as 5.7 GiB of anonymous memory
  (`anon-rss` in the kernel's out-of-memory record; the bind-mounted file is not kept as file pages), so a
  second server does not fit and the kernel killed the first (`make live-linux`, status 137, twice). The
  live tests therefore start one server per session, and the quit test lends that server to its harness
  and runs last. A machine with the model on a local disk would map it instead; not measured here.
- **2026-10-15 — S5 — DECISION — D3 pick: Metal full offload (owner, after 5.1)** — from the measured table
  (STATUS, "D3 checkpoint"): `-ngl 99 -t 2`, profile `assistant-local-metal-v1`, 45 tokens/s against 11.5
  on two CPU threads. Consequences: the binding's `cpu_threads` stays 2 and the Seatbelt profile keeps the
  two IOKit classes and the Metal compiler lookup; on Linux the CPU-only build ignores `-ngl` with a
  warning, so the same binding runs on the CPU there (the `live-linux` numbers in STATUS). The suite's
  contract said CPU only; this is the owner's deviation from it for this host.
- **2026-10-15 — S5 — DECISION — an instruction is an assistant job (5.2)** — the application owns the
  loop: an instruction the assistant can take is admitted as a Job whose task names the command
  (`{"command": <id>}`), on the same admission path as every other job (request, reservation, plan
  recheck), and the command is settled `accepted` with the job as its effect; when the loop ends, the
  command is `applied` (a plain-text answer), `needs_clarification` (the assistant asked one question) or
  `rejected` with the reason the task failed. With the assistant not ready the instruction is rejected
  with its actual state. Jobs give the loop what the suite asks of it for free: lease and heartbeat while
  the model generates, a fence that pause and cancel advance, resume as readmission, the trail. The
  harness runs one assistant job at a time (`attend`, every half second) in its own thread, beside the
  dispatcher that runs the sandboxed jobs. Alternative: an AssistantTask object with its own state
  machine and its own control path, which would have duplicated the Job's.
- **2026-10-15 — S5 — DEVIATION — Job 0.3.0 and CodeTask 0.2.0 (5.2)** — Job 0.3.0 adds the assistant task
  shape and a nullable `parent`: a job the assistant submitted (a profile, a code task) names the
  assistant job, so a pause or cancel of the parent reaches its live children (`jobs.control`
  cascades, best effort) and the phrases and the window's controls address the parent while it is
  live (a child is never the "live job" then). CodeTask 0.2.0 adds the language `assistant` for the
  loop's own declaration (the instruction's digest as its source; no inputs or outputs; never run by
  the runner). Both prior versions stay readable under their own schema files. The ExecutionRequest of
  an assistant job and of its children pins the conversation and the assistant binding, as the suite's
  schema provides.
- **2026-10-15 — S5 — DECISION — the tool-call ledger (5.2)** — app AssistantCall 0.1.0: one record per
  generation (the model's proposal: a tool call, or `answer` for the final text), written `dispatched`
  before the tool runs and committed with the quoted result, or `refused` with the code and reason,
  under the job's attempt and fence on the `assistant-task:<job>` aggregate, with events
  `assistant.call_dispatched`, `assistant.call_committed`, `assistant.call_refused` and
  `assistant.answered`. The model's context is rebuilt from these records on every generation (the
  canonical state, the instruction, each proposal and its quoted result or refusal), so a resumed or
  restarted attempt replays what was committed and never dispatches a committed call twice. A call
  interrupted between dispatch and commit (a pause, a crash) stays `dispatched` and runs again on the
  next attempt, idempotently: an artifact is content-addressed, admission is idempotent by the call's
  id, and a job the call submitted that was paused with its parent is resumed rather than started over.
  A tool's own refusal (a budget change for the owner, a tool that has nothing to act on yet) is the
  model's data (`{"error", "reason"}`), never an exception for it.
- **2026-10-15 — S5 — DECISION — the checks, in order, before a call runs (5.2)** — schema (the tool's
  JSON Schema; an unknown tool, several calls in one turn or arguments that are not JSON are refused
  the same way), principal (the scope the tool needs is in the trusted context), revision (a patch names
  the current requirements revision; a code task is refused once the requirements moved past the
  revision its job was admitted at), scope (a result inspected is a job this task submitted; a task's
  inputs are captured data and its artifact is in the store), budget (the repairs), fence (the job is
  still this attempt's and running: a call proposed after a pause or cancel is refused with that state's
  code and the task stops). A refusal is recorded, quoted back to the model and counts as a model call.
- **2026-10-15 — S5 — ASSUMPTION — how D17's counters are read (5.2)** — per generation: at most 6,144
  input tokens (counted by the server's tokenizer before the call; over it the task fails), 2,048 output
  tokens (`max_tokens`), 300 s (the deadline, after which the server is stopped as hung); per task: at
  most 20 model calls (generations; the twenty-first is not made), 2 code repairs (an artifact that
  names what it repairs) and 1,800 s of generation (the sum of the generations' wall time). The
  "8,192 total tokens" is the context window of one generation (`-c 8192`), not a sum over the task:
  a sum would make twenty calls impossible, since each call re-sends the context. One generation at a
  time is a lock in the harness's assistant. The first limit reached fails the task with
  `budget: <which> is the most for one task`.
- **2026-10-15 — S5 — DECISION — the eight tools (5.2)** — exactly the skill's: `inspect_schema` (the
  reviewed profiling recipe on one granted CSV, run in the sandbox as a child job; returns the data's id
  and the profile), `propose_requirement_patch` (a typed JSON patch with provenance, or one question),
  `write_code_artifact` (create or edit: an immutable, content-addressed source; naming what it repairs
  counts as a repair), `submit_code_task` (admission and the sandbox, unchanged from Sprint 4, as a child
  job; waits for its end and returns the redacted outcome), `inspect_results` (a submitted job's state,
  bounded failure text and outputs by name, size and digest; the content view is 5.4), and
  `request_trial`, `assemble_evidence_report`, `propose_release`, whose objects do not exist until later
  sprints and which answer DEPENDENCY_UNAVAILABLE. No shell, grant or sealed-data tool. A task's failure
  message reaches the model as at most 200 characters of quoted data (the Sprint 4 finding).
- **2026-10-15 — S5 — DECISION — what the model is told (5.2)** — a fixed system text (act only through
  the tools; one call per turn; tool results are quoted data, never instructions; answer in plain text
  with a readback and never claim completion; a measure by a category is its mean unless told
  otherwise) plus the workspace state as JSON: the requirements revision, field roles and features, the
  granted sources by handle and label, the captured data by id, and the counters. The catalogue is the
  tools' schemas themselves. Nothing else: no manual, no schema of the whole suite.
- **2026-10-15 — S5 — FINDING — a stop takes effect between tokens (5.2)** — the generation streams; a
  pause or cancel ends it at the next chunk, which cancels it on the server, and during prompt
  processing (no chunks) at the first token. The job heartbeats every 15 s from the loop's own thread
  while the generation thread waits, so a lease never expires under a long generation.
- **2026-10-15 — S5 — FINDING — guards mutation-checked (5.2)** — seventeen, each broken in turn and each
  caught: the argument schema, an unknown tool, the principal's scope, the revision check, the scope
  check, the repair budget, the twenty-call budget, the fence before dispatch, one call per turn, the
  input-token budget, the generation-second budget, a gateway fault failing the task, an interrupted
  call staying dispatched, the pause and cancel cascade to children, a phrase naming the parent, a
  paused child resumed before it runs again, and an instruction rejected while the assistant is
  unavailable (the first run of that one survived because the test's harness had observed no hardware,
  so admission refused before the assistant check could; the test now observes first). Found and
  removed by the checks: the tools module's own refusal of a budget patch duplicated `revise`'s.
- **2026-10-15 — S5 — DECISION — intent extraction is a typed patch with per-field provenance (5.3)** —
  the model's `propose_requirement_patch` is a JSON Patch on the WorkloadSpec (add, replace, remove;
  lists by index or `-`; applied whole to a copy, a missing path refuses the whole patch) plus one
  provenance entry per patched path: the exact words of the instruction (a span that is not a substring
  of the message is refused, so a reader can always find it), the model's extraction confidence, and the
  materiality; every change must be covered and no entry may name an unpatched path. The entries are
  written on the new revision as `direct_user_message`, `confirmation_status: proposed`,
  `confirmed_by: null`; the Sprint 3 grammar's own change stays one `confirmed` entry, since the owner
  typed it. The `workload.revised` event carries the structured diff (the patch) and a plain readback
  the application writes from it (each path and value, nothing invented), which the trail shows; the
  model's final text stays a proposal. A question (`question` set) applies nothing and ends the command
  `needs_clarification` with the question as its reason: the suite's "ask only about ambiguities that
  change imminent material work" is the model's call, bounded to one question per task.
- **2026-10-15 — S5 — DECISION — the owner's paths through the assistant (5.3)** — a proposal on
  `/requested_resources/max_external_charge_minor` or the evaluation contract is refused by `revise`
  (REQUIRES_CONFIRMATION, as in Sprint 3), the refusal is the model's data, the task ends with its
  proposal recorded, and the command is settled `rejected` with REQUIRES_CONFIRMATION and the reason:
  "spend another £100" changes nothing and says who must act. The grant itself (FIN) does not exist yet.
- **2026-10-15 — S5 — DECISION — a leading control phrase (5.3)** — a direct message that opens with an
  exact control phrase followed by `;`, `.`, `,`, `:` or a line break and more text is that control
  first (the fast path, settled before the model sees anything) and then a second command,
  `<message id>:then`, whose text is the rest and which the assistant takes as an instruction; a retry
  of the message id repeats neither. "Pause now; exclude region before continuing" therefore pauses the
  live job, then revises the requirements while it stays paused (resume is explicit). A phrase quoted,
  embedded or followed by other words in the same clause ("pause the music") remains an instruction,
  as Sprint 3 decided.
- **2026-10-15 — S5 — DECISION — the requirements' own rules complete a patch (5.3)** — three rules the
  schema cannot express run on every proposed patch (`workloads.complete`, the contract-change skill's
  semantic validators): a predictor field left in neither feature list by the patch is excluded (the
  derived operation is appended, recorded with `trusted_observation` provenance and shown in the
  readback as the application's), a field in both lists refuses the whole patch, adding an output
  transform while the privacy status is `not_requested` sets it to `requires_review` (rounding is a
  precision change, not anonymity), and a patch that leaves no row identifier is refused. Found by the
  live runs: the 8B model does one of a two-step edit (drops `region` from the allowed list but does
  not add it to the excluded one; adds the rounding transform but not the review), and once removed
  the row id's role while adding the entity id's. The rules make the record right whatever the model
  managed, without inventing intent: nothing is added that the proposal did not imply.
- **2026-10-15 — S5 — DECISION — a proposal is grounded in the instruction or refused (5.3)** — before
  the completion rules, three checks on what the model proposed, each with the instruction's text:
  every number in a value under the intent constraints must appear in the instruction (a hard maximum
  of 2 for "keep the feature set minimal" is an invention; the increment 10 for "nearest 10" is not), a
  field role may be removed only when the instruction names that field (the model dropped the row id
  to make "the ID" the only identifier, three times, under three wordings), and a patch that changes
  nothing or is empty without a question is refused with "ask a question instead". The owner's budget
  path is exempt from the number rule (minor units are a conversion). Found by the live runs; each is a
  general rule, not a case.
- **2026-10-15 — S5 — DECISION — the interpretation policy is in the model's instructions (5.3)** — the
  reference cases of `conversational_control.md` "From language to enforceable intent" are stated as
  numbered procedures, path by path (a named field not yet in the roles is added, never another field's
  role changed; "the ID" is an entity id, a string, excluded; "minimal" features asks a fixed question;
  rounding adds the typed transform; excluding moves a field between the two lists; a spend change is
  a patch on the owner's budget path). Without them the model repurposed the row id's role for "the
  ID", set a hard maximum instead of asking, rounded with ties to even and answered the budget change
  in prose; measured on 2026-10-15, seed 1 (STATUS, 5.3). This is the product's policy from the suite,
  not an aid to the tests; the tests check the typed records, never the prose.
- **2026-10-15 — S5 — DEVIATION — typed proposals at temperature 0 (5.3)** — the binding's decoding is
  `temperature 0` (the suite's example says 0.7): tool calls and patches are structured output, and at
  0.7 the same instruction gave a different wrong patch on each run. The seed stays 1. A later binding
  may set its own decoding; the record says what was used.
- **2026-10-15 — S5 — FINDING — what the model got wrong that the application let stand (5.3)** —
  "spend another £100" was proposed as 1,100 minor units (£11) and refused anyway for the owner; the
  ID case once added `order_id` to the excluded list twice (the schema allows duplicates in that list).
  Neither changed a record's meaning; both are the model's arithmetic and tidiness, logged for the
  qualification suite (Sprint 11).
- **2026-10-15 — S5 — FINDING — guards mutation-checked (5.3)** — eighteen, each broken in turn and each
  caught: a span must be verbatim, a provenance field must be patched, every change must be covered,
  provenance is recorded as proposed, a missing path refuses the whole patch, a field in both lists,
  the derived exclusion, the derived review, a row id must remain, a question ends in clarification,
  an owner-only proposal ends rejected, the leading phrase, the `:then` command, the readback on the
  event, a number not in the instruction, an unnamed removal, a no-op patch and an empty patch.
- **2026-10-15 — S5 — ASSUMPTION — repeatable live runs (5.3)** — every generation uses seed 1 and the
  binding's temperature (0.7), so a run can be repeated on the same server; llama.cpp is deterministic
  for one build, one profile and one seed. The five reference instructions are one `live_model` test
  that writes an A29 evidence record whose slug names the binding (`interpretation-assistant-local-
  qwen`), so another binding's record is a separate file and never merged.
- **2026-10-15 — S5 — DECISION — what "redacted" means for results the assistant sees (5.4, before the
  code)** — of a job the assistant submitted, the model is shown: the job's state; a failure's kind
  and at most 200 characters of its message, as quoted data (the message is text the task chose); each
  declared output's name, size and digest; and, for one output it asks to see by name, a bounded
  preview: for a CSV the header and the first 20 rows with each cell cut at 200 characters and the
  total row count, for a JSON or text file its first 2,000 characters, for anything else nothing but
  the size. Never: a file outside the job's declared outputs, the inputs themselves, the ledger, the
  store, a path on this machine, a secret (none can reach an output: the sandbox refuses the reads),
  or a sealed partition (none exists yet; Sprint 9 excludes sealed manifests at admission and the
  binding's `sealed_data_access: false` will be read then). A remote binding (5.6) shows a preview only
  when its data policy allows the data class; the local binding allows the owner's own data, which
  never leaves the machine. The preview is a view of a committed artifact, built by the harness from
  the content store; the model's context holds it only as quoted data.
- **2026-10-16 — S5 — DECISION — generate, run, repair (5.4)** — the assistant writes an artifact
  (`write_code_artifact`), submits it (`submit_code_task`: Sprint 4's admission, dispatcher and sandbox
  unchanged, as a child job) and sees the redacted outcome; `inspect_results` with an output's name adds
  the bounded preview defined above; a repair is a new artifact naming the failed one and is counted
  against D17's two. The model's instructions say how (SQL on a table named like the input; one output;
  read the failure, repair, resubmit) and that an instruction to load, show, compute or summarise data
  is done only when a code task produced the table, never by describing data in the answer: on the
  first live run the model inspected the schema and answered in prose (no task). The window's Results
  section lists each succeeded job's CSV outputs from the RunRecord its success names and opens one as
  a table of cells (`GET /v1/artifacts/{sha256}`, read-only, by digest only); a profile's JSON is a
  record, not a table, and is not listed. The `data.captured` event now carries the capture's digest,
  so a client can name captured data as a task input without reading the manifest.
- **2026-10-16 — S5 — DECISION — a task's own requirement change does not stale its code tasks (5.4)** —
  5.2 refused `submit_code_task` once the requirements had moved past the revision the assistant job
  was admitted at. On the first live run the model registered the CSV's field roles with a patch (a
  reasonable "load this CSV" step), the revision moved, and every resubmission of its repaired code
  was refused as stale; the task ended without a table. The check is gone: a child job is admitted
  under the current revision by construction, and a change made outside the task (the owner's typed
  change) already pauses the task through the revision's hold, which is the suite's own rule. The
  patch's `expected_revision` check stays.
- **2026-10-16 — S5 — DEFECT — the local model over-groups the acceptance instruction (5.4, open)** —
  "load this CSV and show transit hours by service level" on the orders fixture: after the procedure
  and naming fixes the model inspects the schema, writes SQL, runs it in the sandbox, inspects the
  result and answers from it, in 5 generations and about 35 s, but its SQL groups by `region` and
  `service_level` (identical on four runs at seed 1, temperature 0, under three wordings of a rule
  against added groupings), so the committed table is not the table per service level the independent
  query gives, though its values are DuckDB's means for the grouping it chose. The A28 part
  `generated-code-live-assistant-local-qwen` is therefore FAIL on this binding; the gate's `make live`
  is red by it. Not fixed by more prompting on purpose: the application cannot know the instruction's
  categories, and tuning the model's instructions to one test is not a product change. Earlier failed
  runs, each fixed in the product: the model answered in prose after the schema (rule added), named the
  granted file by its label (the resolver now accepts it), queried its input as a file (the rules now
  name the input as the data's name) and lost its resubmissions to the stale-revision check (removed).
- **2026-10-16 — S5 — ASSUMPTION — what "equal to an independent query" accepts (5.4)** — the
  acceptance instruction names "transit hours" and the fixture has quoted and actual transit hours;
  the live test accepts a committed CSV with one row per service level whose numeric column equals
  DuckDB's mean of either column within 0.01 (rounding by the model's SQL), and the record says which;
  the row count, column names and order are the model's. Nothing else about the model's prose is read.
- **2026-10-16 — S5 — DECISION — A28's record after 5.4** — the Sprint 4 SAT's wording that no model
  generates code until Sprint 5 is replaced: model-generated code and its repairs are the
  `live_model` part `A28-generated-code-live-<binding>` (written by `make live`, PASS only when the
  committed table equals DuckDB's); the overall record stays INSUFFICIENT_EVIDENCE for sealed
  partitions (Sprint 9) and VM isolation (the owner's deviation), not rounded up.
- **2026-10-16 — S5 — DEFECT — the confinement named the state folder by an unresolved path (5.7, fixed)** —
  the first `make live` of the gate failed its Playwright acceptance spec before the first keystroke:
  the harness it started reported "the model server exited with status 1" four times (the initial
  start and the watch's three). The `log stream` watch kept beside the run shows why: Seatbelt
  denied `file-read-data` on the key file at `/private/var/folders/…/dsp-renderer-…/assistant/api-key`;
  the profile had named it as `/var/folders/…`, the path Node's temp directory gives, and the OS
  sandbox matches the real path. pytest's temp paths are already real, so no Python test saw it;
  an owner whose profile folder sits behind a symlink would have. The adapter now resolves the
  model, the binary and the state folder before any path reaches a profile, an argv or a bind
  (unit test with a symlinked folder on both OSes). The watch found no other denial of ours beyond
  the known benign ones (`com.apple.diagnosticd`, `com.apple.bsd.dirhelper`, `/System/Cryptexes/App`
  metadata, `/etc` metadata); no sysctl was asked for.
- **2026-10-16 — S5 — DEFECT — `make sat-linux` lost the marker expression's quotes (5.7, fixed)** — the
  5.5 change that leaves `live_model` out of the acceptance runs wrote `-m "not live_model"` into the
  target's `LINUX_RUN`, which the Linux recipe passes to the container inside a double-quoted
  string, so pytest received `-m not` and refused ("expected not OR left parenthesis OR
  identifier; got end of input"); the first gate run of `make sat-linux` failed at once. The quotes
  are now escaped (`\"not live_model\"`) and the dry run shows them reaching the container.
  `make sat` on macOS, which runs pytest directly, was never affected.
- **2026-10-16 — S5 — DEFECT — `killpg` refused with EPERM in the sandbox's stop, intermittent (open)** —
  the final `make verify` on macOS failed the Sprint 4 CPU-time containment test once:
  `sandbox.py:104` `os.killpg(pid, signal.SIGKILL)` → `PermissionError: [Errno 1]` while stopping
  a task past its CPU limit; the test passed three times alone right after and in the two earlier
  full runs of the day. The same refusal was logged without a traceback at the Sprint 4 gate. Not
  touched by this sprint; recorded with the traceback, open for Sprint 6 housekeeping (the kill
  should check the group is still the task's, or signal the known pids), and the gate's record
  below keeps the failed run beside the rerun.
- **2026-10-16 — S5 — FINDING — the integrity review at 5.7: PASS, two should-fix, six notes** — run once
  as a general-purpose agent carrying the reviewer's definition (the project agent is not in the
  session's registry), on `73698be..4eef69d`. Should-fix, both fixed: (1) authority — a model
  `replace` of a string leaf under `/intent_constraints` was applied unchecked, so a patch could set
  `privacy_status` to `reviewed_with_evidence` or add a role for a field the instruction never
  names, and one provenance entry with the bare prefix `/intent_constraints` covered every path;
  now the privacy status is refused as derived by the application, a field name a value introduces
  (`field`, `output_field`) must be in the instruction or in the current roles, and a provenance
  field must be the patched path or its parent. (2) containment — the generation deadline was
  passed to httpx as a per-read timeout, so a generation that kept streaming chunks was never
  stopped (at the container's 1.6 tok/s a 2,048-token answer would run 21 minutes past a 300 s
  deadline); `assemble` now carries the absolute deadline and a chunk past it is the hang, in
  both adapters (unit test on a slow stream; the SIGSTOP live test keeps the no-chunk case).
  Notes, taken: (3) the input bound now counts the tool catalogue with the messages; (4) on Metal
  the footprint account leaves the mapped weights out, so the memory limit now takes the larger
  of footprint and resident. Notes, deferred and open: (5) a `dispatched` call replayed after a
  crash is not idempotent for `propose_requirement_patch` (the revision applied; the replay is
  quoted a conflict) and `inspect_schema` (a second capture); no double commit, so Sprint 6
  housekeeping. (6) a plain-text answer settles the command `applied` even when every call was
  refused; the trail calls the answer a proposal, so nothing is rounded up, but "applied" means
  the job ended; to settle on effect in Sprint 6. (7) the live failure and remote tests had run on
  macOS only at review time; `make live-linux` at the gate runs them on Linux. (8) the remote
  spend sum lives in memory and a harness restart resets it; harmless while the schema holds
  `max_external_charge_minor` at 0, to come from the ledger when that is lifted.
- **2026-10-16 — S5 — DEFECT — the stale-server check needed `ps`, which the verify container lacks (5.7, fixed)** —
  the first `make verify-linux` of the gate failed one unit test: `stale()` read a pid file's process
  through `ps -ww -o command=`, and the plain Linux container has no `ps` (the live container had it
  from its build tools). On Linux the check now reads the kernel's own record, `/proc/<pid>/cmdline`,
  with no dependency; macOS keeps `ps` (there is no `/proc`). The unit test is unchanged and covers
  the negative case on both OSes; the positive kill is exercised by the live restart path.
- **2026-10-16 — S5 — ASSUMPTION — the acceptance line's Playwright spec is selected by tag (5.7)** —
  Playwright has no markers, so the `live_model` spec (`desktop/tests/live.spec.ts`, titled
  `@live_model`) is left out of `make e2e` by `--grep-invert @live_model` in the renderer's test
  script and run by `make live` with `--grep @live_model`, before the Python live tests so a red
  acceptance record does not hide it. It starts a real harness on the real model folder, grants the
  generated orders fixture through the harness (the folder picker is the owner's), types the 5.4
  instruction into the composer, waits for the first tool call in the trail, pauses with the chord,
  waits for the job to show paused, presses Resume, waits for the assistant's proposal line, and
  opens the first committed CSV as a table. Deselection, never a skip, as the gate rule asks.
- **2026-10-16 — S5 — FINDING — two processes left behind by earlier runs (5.6)** — the live remote
  tests first failed with "127.0.0.1:8081 is held by another process": a llama-server from the 5.5
  mutation run was still up, started by the out-of-memory test under the mutation that disabled the
  footprint kill (the model loaded in full, the test failed, and nothing stopped the adapter it had
  built). That test now stops its adapter in a `finally`. The same look found a pytest from before
  this session's context was compacted, 51 minutes old, on the restart test: the non-daemon harness
  thread hang of the CI defect above, seen here first and not understood then. Both killed by hand.
- **2026-10-16 — S5 — DECISION — remote OpenAI-compatible binding, D4 = B (5.6)** — the app owns
  `AssistantModelBinding` 0.4.0, the remote mode only (`mode: remote_openai_compatible`; a local binding
  keeps the suite's 0.3.0): provider and model name, `endpoint.base_url` (http, https, or `unix://` for
  a server on a socket) and `api_key_ref` (`secret://local/<account>`), `placement` (host; whether data
  leaves the machine), `data_policy` (`none` or `synthetic_fixtures_only`; sealed data and secrets are
  `false` by the schema), `spend` (the price per million tokens in minor units, approved by the owner,
  when), the D17 limits with `max_external_charge_minor` as the owner's spend limit, standard decoding
  fields only, `remote_fallback: false`, and `observed` (the model id and the probe's seconds) once
  ready. The adapter `OpenAICompatible` sits behind the same `ModelServer` port: `start` checks the
  policy (`none` lets nothing leave: refused before the key is read), reads the key from the secret
  store under the account (none: refused with the exact `security` and `secret-tool` commands of D4),
  sees the model in `GET /v1/models` (401 or 403: "the endpoint refused the key"), then passes the same
  typed tool-response probe as the local server; `complete` refuses a call whose projected charge
  (the counted input plus `max_tokens`, at the price, rounded up) would take the spend past the limit,
  before anything is sent, and adds the reported usage's charge after; `count` is the endpoint's own
  tokenizer (`/tokenize`: llama-server, vLLM) or, on 404, one token per two bytes. The harness opts in
  by a record at `<profile>/assistant/binding.json`; an invalid record leaves the assistant unavailable
  with the first schema error, and never the local model in its place (no fallback, by the skill). The
  ready event carries placement, data policy, spend and limit, so the window's header and trail show
  them before the first instruction ("shown before first use"). Tested against llama-server itself
  on TCP (macOS) and its socket (Linux), with the session server's own key in a test-only store: no
  key of the owner's, no spend, nothing leaves (D4 = B). The proprietary adapter is not built.
- **2026-10-16 — S5 — ASSUMPTION — the data policy is declared and shown, not enforced on content (5.6)** —
  under D4 = B the only data that may leave is synthetic fixtures; the harness cannot tell a synthetic
  file from a real one, so the policy is the owner's declaration recorded with the binding, shown at
  readiness and in the trail, and enforced only where it can be: sealed data and secrets never enter
  a prompt (Sprint 9 adds sealed data; the key is never in the context). An endpoint without a
  tokenizer gets a high token bound (two bytes per token), so the D17 input limit refuses an input
  the endpoint might cut, at the cost of usable context.
- **2026-10-16 — S5 — FINDING — the restart bound was not real (5.5, found by its mutation check)** — the
  "verification failures are final" branch survived its mutation because the watch only ever restarted
  from the ready state and reset its counter on every success: a server that kept dying was restarted
  without bound, and a failed launch was never retried. Now: the watch starts a server again after a
  death or a failed launch, at most three times in one harness's life, and leaves it unavailable
  past that; failures no restart can change are final at once (a missing, corrupt or mis-sized model
  or binary, the memory limit, no key, a refused key, a `none` data policy, an unaffordable probe).
  Tests: a server dead at every tick ends with four ready and four unavailable events and no more;
  the corrupt-model test waits two ticks and sees no second attempt; the remote failures likewise.
- **2026-10-16 — S5 — DEFECT — CI run 38895075855, the 5.4 read (fixed, one open)** — (1) both `verify`
  jobs: the corrupt-model test expected "model hash mismatch" for its second case and got "model server
  binary missing": verification checks the binary before the model's hash, and CI has no llama-server.
  The failed assertion left that test's inline harness threads alive (not daemons: a quit must stop the
  model server), so pytest never exited and both jobs ran until cancelled 37 minutes later. The case now
  names an existing file (`sys.executable`) as its binary, and both inline-harness tests stop their
  servers in a `finally`. Reproduced here with a HOME that has no binary: the failure and the hang, then
  the fixed test passing and exiting. (2) `verify (macos-latest)` only: the Sprint 1 SAT profile test got
  exit 2 from the CLI, a `DspError` whose text the test did not show; it passes here and a cold harness
  answers the CLI in 1.6 s. The CLI gave a cold harness 10 s (100 tries of 0.1 s) under a coverage-traced
  subprocess on a shared runner; it now gives 30 s, and the test shows the CLI's output when it fails.
  Not reproduced: a hypothesis until the gate's run. (3) `desktop (ubuntu-24.04)`: after the real window
  close the shell did not end within 20 s. The Sprint 4 gate passed this step; the shell's close path and
  the window's title are unchanged since; the 5.2 and 5.3 runs failed earlier in that test, so this step
  had not run on CI since Sprint 4. The three close waits now report the windows and shells left when
  they time out. **Open** until the gate's run; not reproducible here (no Linux desktop).
- **2026-10-16 — S5 — FINDING — a test harness's quit must be joined (5.5)** — the harness's supervisor
  thread stops the assistant's server after uvicorn has exited; the `harness` fixture joined only
  uvicorn, so one test's stop could land after the next test's harness had reported the shared live
  server ready: the first deadline run died at its own SIGSTOP with "no such process", and the loop,
  whose tokenizer call hit a bare connection error, left the job leased and logged "attend failed".
  The app now keeps the supervisor on `app.state`, the fixture joins it (a quit's stop finishes before
  the next harness starts), a tokenizer call that cannot reach the server is `ASSISTANT_UNAVAILABLE`
  with the error's type, and the loop fails the task with that reason.
- **2026-10-16 — S5 — FINDING — the deadline test raced the watch's tick (5.5)** — the watch marks the
  server dead and restarts it on a one-second tick; the test read the events 60 ms after the task
  failed and found the state still ready and no outage recorded. The test now waits for the restart's
  second `assistant.ready` before counting the one `assistant.unavailable`. Product unchanged: the
  window can show "ready" for up to a second after a deadline kill, and an instruction in that second
  fails with the gateway's own reason.
- **2026-10-16 — S5 — DECISION — failure and independence (5.5)** — every failure of the model ends in
  `assistant_unavailable` with the conversation and the controls untouched and no other model tried:
  a missing model or binary and a hash or size mismatch are verification failures, final until the
  harness restarts (the watch never retries them: the file does not change by itself); out of memory
  is the kernel's kill on macOS (jetsam is not available through `sandbox-exec`, so the footprint poll
  kills past the binding's limit) or `prlimit`'s refusal on Linux, before the server is ever ready; a
  hung server is killed at the generation deadline (the stream's read timeout, 300 s by the binding;
  5 s in the test), the task fails with that reason, the command is rejected with it, and the watch
  restarts the same binding up to three times; a restart of the harness expires the dead attempt's
  lease, and the next attempt rebuilds the context from the committed AssistantCall records, so a
  committed call is never dispatched twice and an interrupted one runs again idempotently. The fast
  controls never touch the model: with the server stopped mid-generation (SIGSTOP) and every
  processor busy, pause and cancel receipts stay within 2 s at p95 (the A24 record for Sprint 5), a
  pause of the hung assistant job is durable at once and nothing it proposes afterwards runs. A30's
  offline part is the 5.1 probe under the server's own confinement, now written as evidence.
- **2026-10-16 — S5 — ASSUMPTION — Sprint 5's acceptance tests live with the live tests (5.5)** — A24
  under a hung generation, A29 and the A28 generated-code part need the real model, so they are
  `live_model` tests under `tests/integration/` whose evidence `make live` writes (and `make live-linux`
  copies out); `make sat` and `make sat-linux` leave `live_model` out, as `make verify` does, and rerun
  every earlier sprint's file. The live failure tests end the session's server on purpose, so the
  integration conftest orders them after the other live tests, and each later harness restarts it.
- **2026-10-15 — S5 — ASSUMPTION — the sprint branch** — the work is on the branch the desktop app made for
  this session, `claude/sprint-5-assistant-gateway-fc1f11`, from `main` at `73698be`, rather than a
  branch named `sprint-5-assistant`; the pull request carries the sprint's title.

## Sprint 4

- **2026-10-12 — S4 — DEFECT — the harness published its port before listening (housekeeping)** — `serve`
  wrote `harness.json` after `bind()` and before uvicorn's `listen()`. On this Mac (macOS 26.3.1) a client
  that read the file in that window had its connection left unanswered, not refused: Node's `fetch`
  waited out its 10 s connect timeout, which pushed the renderer's "lost harness, restarted one rejoined"
  test past its 30 s limit on every run (it passed at the Sprint 3 gate). The listener now listens before
  the port is published; a test connects to the published port before the server loop runs.
- **2026-10-12 — S4 — DECISION — the activity trail is the one place outcomes appear (housekeeping)** —
  closes the 2026-10-12 feedback defect. The notes beside the header buttons, under the composer and in
  the Run section are gone. Every outcome the harness commits is shown once, in the activity trail, from
  its events: command receipts and states with one wording (`command.*` events now carry `reason`, the
  same sentence the HTTP answer gives, beside the `because` code), job states, refused admissions and
  the job the Run button queued. A request the harness never recorded (no answer, or refused before it
  was read) is listed in the same trail as "not received" with the reason; the Run button adds such a
  line only when the harness did not answer, since every admission refusal is itself an event. The
  folder list keeps its own alert: a refused grant is not an event. Tested once in Vitest (`activity`)
  and once in Playwright (composer, buttons, a dropped request, Run and a refused admission).
- **2026-10-12 — S4 — DECISION — the Pause and Cancel chords are handled in the renderer too
  (housekeeping)** — for the open macOS Cancel run defect. A document `keydown` handler in the window
  sends the same command as the header buttons for CmdOrCtrl+P (pause) and CmdOrCtrl+. (cancel) on the
  live job, and calls `preventDefault`, so one press sends one command whichever of the webview and the
  native menu sees it first. Cmd is the modifier on macOS, Ctrl elsewhere; Shift or Alt with it is not a
  shortcut. The native menu items stay, unchanged (`CmdOrCtrl+.` for Cancel run), for the mouse and for
  when no job is live (the menu's command is then refused, "no job is live", which the trail shows).
  Playwright presses both chords on macOS (Meta) and Linux (Ctrl) against a real harness. Whether the
  built app on macOS delivers Cmd+. to the webview is not known until the owner presses it at the gate.
- **2026-10-12 — S4 — DECISION — bubblewrap in the local Linux container (owner)** — the owner approved
  installing Debian's `bubblewrap` package inside the throwaway `make verify-linux` container and running
  that container with `--security-opt seccomp=unconfined`, because Docker's default seccomp profile
  refuses user namespaces (measured: `unshare -Urn` fails with EPERM by default and succeeds unconfined
  on Docker Desktop 29.8.1, kernel 7.0.14-linuxkit). The sandbox tests then run in the container as a
  non-root user, so the Linux sandbox is built and checked locally, not only in CI.
- **2026-10-12 — S4 — FINDING — what macOS 26 can enforce for the runner's limits** — measured on this
  Mac (macOS 26.3.1, arm64): a bare Python process maps about 415 GiB of virtual address space, so
  `RLIMIT_AS` and `RLIMIT_DATA` cannot be set below about 512 GiB and do not cap memory; `RLIMIT_RSS` is
  not enforced by Darwin; `memorystatus_control` limits need privileges (EPERM). A fatal jetsam limit set
  on the spawn attributes (`posix_spawnattr_setjetsam_ext`) is kernel-enforced without privileges: a child
  with a 256 MiB limit was killed by SIGKILL after about 192 MiB. A size-capped disk image gives a
  kernel-enforced scratch cap (ENOSPC at 62 MiB of a 64 MiB image; about 2.4 s to create, attach and
  detach). The macOS adapter uses both; no limit the skill requires is left unenforced.
- **2026-10-12 — S4 — DEVIATION — ComputeBinding 0.6.0, the app's successor of suite 0.5.0 (4.1)** — carries
  the owner's 2026-10-01 runner decision into the contract: `generated_code_policy` gains
  `restricted_os_sandbox`, `isolation.trust_model` gains `customer_os_sandbox_single_user`,
  `resource_requirements.os` gains `darwin`, and a required `assurance` (`none`, `dedicated_vm`,
  `os_sandbox_single_user`) must match the policy (denied → none, VM → dedicated_vm, OS sandbox →
  os_sandbox_single_user with the single-user trust model and process execution only). The suite file
  stays vendored and unchanged; its 0.5.0 example still validates. The schema loader now picks the schema
  by the instance's `schema_version` (an older app version keeps its file as `Name@x.y.z.schema.json`).
- **2026-10-12 — S4 — DECISION — the stored local binding replaces `LOCAL_DRAFT` (4.1)** — `local_binding`
  in `application/planning.py` is a full ComputeBinding 0.6.0 (`compute-local-native` 1.0.0) for this host:
  OS and instruction set from the discovery adapter, data analysis only, one concurrent attempt, D01's two
  hours, `restricted_os_sandbox` at `os_sandbox_single_user` assurance, limitations saying it is not VM
  isolation. Admission stores it with the first request that pins it, as it stores the WorkloadSpec. It
  stays `proposed` and its qualification `planned` until the owner reviews the containment evidence as
  its qualification (no such owner action exists yet), so the plan still calls it unqualified and the
  Sprint 3 deviation that admits an unqualified local option continues, now for sandboxed tasks too. The
  profile ID stays `local-native-draft` because WorkloadSpec 1.0.0, which is immutable, targets it.
- **2026-10-12 — S4 — ASSUMPTION — the local binding's data policy (4.1)** — it allows synthetic and the
  owner's own confidential data (`customer_data_allowed: true`) for data analysis, because the data never
  leaves the owner's machine; sealed data access is false. No rule reads the data policy yet.
- **2026-10-12 — S4 — DECISION — CodeTask 0.1.0 and Job 0.2.0 (4.1)** — an app-owned CodeTask records the
  source by digest, the parent revision, the requirement revision, named read-only inputs with digests,
  output names, the runner environment's lock digest (null until 4.2 builds the locked environment),
  limits (CPU seconds, memory, wall seconds, output bytes, scratch bytes, open files) and the permissions it
  asks for (`network`, `process`; the binding grants none, so asking is refused). The caller supplies only
  language, source digest, inputs, outputs, limits and permissions; every other field, the requirement
  revision included, is derived, and naming one is refused. Limits default to, and may not exceed, the
  workload revision's envelope (D01, D21). The ID is derived from the content. Every admitted request now
  pins a stored CodeTask: a test-worker job's CodeTask has language `test_worker` and its cues' digest as
  its source, and is never run by the runner. Job 0.2.0 lets a runner job carry no test-worker task and
  records the submitted payload's digest, which an idempotent retry must repeat (D05); a Sprint 3 job's
  payload was its task. Execution outcome fields are added to the CodeTask when 4.5 commits them.
- **2026-10-12 — S4 — ASSUMPTION — what an undeclared input or output is at admission (4.1)** — an input is
  undeclared unless its digest is data captured through a grant (a DataManifest in this tenant); two inputs
  may not share a name; the source must already be in the content store; a Python or SQL task that declares
  no output is malformed and refused before anything is written. Reads and writes beyond the declaration
  at run time are the runner's and the sandbox's to stop (4.2 to 4.4).
- **2026-10-12 — S4 — DECISION — the runner and its one channel (4.2)** — the sandbox adapter lays out
  an attempt directory (`task.json`, the CodeTask; `source`; the declared inputs under `inputs/`; an empty
  `scratch/`) and starts `<runner env>/bin/python -I -B -X utf8 -m dsp_runner <attempt>/task.json` by
  `posix_spawn` in a new session, with a fixed argument vector and an environment of `HOME` and `TMPDIR`
  set to scratch, nothing else. The runner checks the source and inputs against their digests, lowers its
  own CPU-time (hard limit one second above the soft) and open-file limits, which an unprivileged process
  cannot raise again, then runs the code in its own interpreter in scratch (a separate process would need
  the process permission the binding withholds). It writes `result.json` (app RunnerResult 0.1.0: null or
  a failure kind and a message of at most 500 characters) and, on success, the declared outputs to its
  standard output as one tar stream; the task's own output goes to `/dev/null`. The adapter reads that
  channel bounded by the output cap plus 64 KiB of framing (more kills the run), accepts only regular
  entries with declared names, refuses outputs whose sum exceeds the cap, validates the result, hashes
  each output itself, kills the process group at the wall-clock limit and again after the runner ends,
  and names what it saw (`timeout`, `cpu_limit`, `output_limit`, `killed`, `crash`, `result_invalid`).
  Memory and scratch limits, reads and network are the OS adapters' (4.3, 4.4). Alternatives: outputs
  read from a host-visible scratch folder, which on Linux would leave scratch without a kernel-enforced
  size; a JSON channel with encoded outputs, a third bigger.
- **2026-10-12 — S4 — DECISION — an audit hook detects, the sandbox refuses (4.2)** — the runner adds a
  Python audit hook that records every open outside the declaration (reads outside the runner
  environment, the base Python and the attempt; writes outside scratch, symlinks and `..` resolved), so
  the task fails as `undeclared_read` or `undeclared_write` even when its code swallows the error; a
  recorded refusal outranks the crash it caused. SQL runs on a DuckDB connection that loads the inputs as
  tables named as declared, then disables external access and extension loading and locks its
  configuration; DuckDB's refusals are `undeclared_access`. Neither is the boundary: code can bypass
  both, and the containment tests (4.6) show the OS refusing what they miss.
- **2026-10-12 — S4 — DECISION — the runner environment (4.2)** — `make runner-env` runs `uv sync --frozen
  --no-dev --no-editable --compile-bytecode --reinstall-package dsp` into `DSP_RUNNER_ENV` (default
  `.runner-env`; `/tmp/runner-env` in the read-only Linux container): the lock's runtime set and the
  project as a built wheel, byte-compiled so imports write nothing, in 0.4 s. `test-fast`, `sat` and
  `verify` rebuild it, CI's verify job now runs `make verify`, and the `runner_env` fixture refuses an
  environment whose runner or contracts differ from the source. Its lock digest goes on the CodeTask when
  the harness dispatches (4.5).
- **2026-10-12 — S4 — FINDING — the runner environment carries the whole runtime set (4.2)** — it holds
  every runtime dependency of the project (FastAPI, uvicorn and httpx included), not only what the runner
  imports (DuckDB, and the standard library). A narrower set needs its own lock group; nothing needs it
  yet, and the sandbox, not the package list, is the boundary.
- **2026-10-12 — S4 — FINDING — the runner validates nothing itself (4.2)** — importing jsonschema's format
  checker costs 0.5 s (`rfc3987_syntax` alone), on every task. Validation inside the runner would prove
  nothing, since that process also runs the untrusted code, so the trusted side validates: the CodeTask
  at admission and the RunnerResult when the adapter reads the channel. Runner start-up fell from 0.65 s
  to 0.07 s.
- **2026-10-12 — S4 — DECISION — a SQL task has exactly one output (4.1 schema, amended in 4.2)** — its
  last statement's rows are written as CSV to the one declared output; CodeTask 0.1.0 says so before
  anything was released.
- **2026-10-12 — S4 — DECISION — the macOS adapter (4.3)** — `adapters/seatbelt.py`. Profile, deny by
  default: `file-read*` on the runner environment, the base Python, `/usr/lib`, `/System/Library` and the
  attempt directory; `file-read-metadata` on those paths' ancestors and on every symlink from
  `bin/python` to the interpreter; the root's listing (Python does not start without it); `file-write*`
  on scratch; `/dev/null`; `sysctl-read` (without it `os.cpu_count()` is None). No network, process,
  IPC or Mach-service rule, so all are denied. Paths are written as JSON strings. The spawn carries
  `POSIX_SPAWN_CLOEXEC_DEFAULT`, so the task inherits only its standard descriptors, and a fatal jetsam
  limit of the task's memory. Scratch is a sparse HFS+ disk image of the scratch size mounted on
  `scratch/` (`-nobrowse`), detached and deleted after the run. CPU time: the runner's own limit sends
  SIGXCPU, and the adapter polls the kernel's account of the process (`proc_pid_rusage`, Mach time
  units) and kills it at the limit. A SIGKILL the adapter did not send is reported as `memory_limit`,
  since jetsam is the only other sender.
- **2026-10-12 — S4 — DECISION — Seatbelt applied in the process, not by `sandbox-exec` (4.3)** —
  measured on this Mac: a jetsam limit set on the spawn kills a directly spawned Python at about 240 MiB
  of 256 MiB, but `sandbox-exec`'s `execvp` drops it (1 GiB allocated, exit 0). So the adapter spawns
  `python -m dsp.adapters.seatbelt_child <profile> <task.json>`, which calls `sandbox_init` on itself (the
  call `sandbox-exec` makes) and then runs `dsp_runner` in the same process. Only that module and the
  interpreter run unconfined; a profile that does not compile ends the process before any task code
  exists, and, with no exec afterwards, the profile can deny `process-exec` outright. The skill's
  `sandbox-exec -f <profile>` line is updated to say so. Alternative: polling memory from outside,
  which is not kernel-enforced.
- **2026-10-12 — S4 — FINDING — Darwin does not kill at the hard CPU limit (4.3)** — measured: with
  `RLIMIT_CPU` at (1, 2) a busy Python ends by SIGXCPU after 1 s, but one that ignores SIGXCPU ran its
  full 10 s. Hence the adapter's own poll on macOS; on Linux the kernel kills at the hard limit (4.4).
  The mutation that removes the runner's limit survives on macOS for that reason and is checked on Linux.
- **2026-10-12 — S4 — ASSUMPTION — private and deprecated macOS calls (4.3)** — `sandbox_init` is
  deprecated and `posix_spawnattr_setjetsam_ext` is private (`spawn_private.h`); both work on macOS
  26.3.1 without privileges, and they are the only unprivileged kernel controls for the profile and the
  memory limit. A macOS that drops either fails closed: the profile is refused or the limit cannot be
  set, the spawn raises, and the containment tests fail.
- **2026-10-12 — S4 — FINDING — the cost of a capped scratch volume on macOS (4.3)** — creating,
  attaching and detaching the sparse image takes about 1.7 s per task on this Mac (create 1.1 s, attach
  0.25 s, detach 0.4 s); a 16 MiB image refuses writes with ENOSPC at 15,936 KiB. Accepted for now; a
  cloned template image would cut it to about 0.7 s if tasks become short and many.
- **2026-10-12 — S4 — FINDING — a scratch volume can outlive a crashed harness (4.3)** — the volume is
  detached in the run's `finally`; a harness killed mid-run leaves it mounted until something detaches
  it (found when a mutation check skipped the detach: pytest then renamed the folder under the mounted
  volume and only `umount -f` on the new path released it). Reconciling stale attempts is 4.5's.
- **2026-10-12 — S4 — DECISION — the Linux adapter (4.4)** — `adapters/bubblewrap.py`: `prlimit
  --as=<memory> -- bwrap --unshare-all --as-pid-1 --die-with-parent --new-session`, read-only binds of
  `/usr/lib`, `/usr/lib64`, `/lib*` (symlinks recreated as symlinks), `/etc/ld.so.cache` alone of `/etc`
  (without it the loader cannot find `libpython`), the interpreter binary, its `lib`, the runner
  environment and the attempt; a `--size`d tmpfs on scratch; `--dev` with `/dev` and `/` remounted
  read-only; `--chdir` scratch; the seccomp filter on descriptor 3. The spawn's environment is the
  scrubbed one (so no `--clearenv`), and inheritable descriptors other than 0–3 are closed by the
  spawn's file actions. The filter (classic BPF built in Python, x86-64 and aarch64 tables) kills a
  foreign architecture and the x32 ABI, answers `clone3` with ENOSYS (its flags are in memory, out of
  reach, so glibc falls back to `clone`), allows `clone` only with `CLONE_THREAD`, allows only Unix
  sockets, and refuses fork, vfork, ptrace, mount, namespaces, BPF, keys, io_uring, modules and
  `process_vm_*`. It is a deny list in front of a default allow: an allowlist for Python with DuckDB
  would be long and brittle, and the namespaces and mounts are the main boundary.
- **2026-10-12 — S4 — DEVIATION — no `/tmp` and no `/proc` in the Linux sandbox (4.4)** — the skill
  named `--tmpfs /tmp`; a second tmpfs would double the scratch cap, and `TMPDIR` is scratch, so there
  is none. `/proc` is not mounted: bubblewrap cannot mount a fresh one inside Docker (its masked paths
  forbid it), and neither the runner nor a task needs it; the same policy holds on every Linux host.
- **2026-10-12 — S4 — DECISION — the runner is the namespace's first process (4.4)** — with bubblewrap's
  own reaper as PID 1, a task killed at the hard CPU limit came back as an unexplained SIGKILL: the
  outer bubblewrap never accounted for the inner runner's CPU time. With `--as-pid-1` the runner is
  bubblewrap's own child, its CPU time returns with the exit status, and the core names the kill
  `cpu_limit`. As PID 1 it ignores SIGXCPU by default, so the kernel's SIGKILL at the hard limit is
  what stops a busy task on Linux. bubblewrap reports a signal as 128 plus its number, which the core
  turns back into the signal (`relays_signals`).
- **2026-10-12 — S4 — FINDING — `/dev` took writes (4.4)** — the first probe found `/dev` and
  `/dev/shm` writable inside the sandbox: a memory-backed place outside scratch and its cap. `/dev` is
  now remounted read-only (its device nodes are separate binds and still work); the write test covers
  `/dev/shm` and `/`.
- **2026-10-12 — S4 — FINDING — the network is refused twice on Linux (4.4)** — by the empty network
  namespace and by the filter's socket rule. Removing the namespace alone is caught (an abstract Unix
  socket, scoped to the namespace, becomes reachable); removing the socket rule alone is not
  observable from inside, since the empty namespace still refuses every connection (ENETUNREACH
  instead of EACCES). It stays as defence in depth.
- **2026-10-12 — S4 — DECISION — bubblewrap in the local Linux gate (4.4)** — `make verify-linux` runs
  `tools/verify_linux.sh` in the throwaway container: it installs Debian's `bubblewrap` (0.8.0) and
  runs the gate as an unprivileged user (`setpriv`), with the container under
  `--security-opt seccomp=unconfined` (the owner's 2026-10-12 approval). The Linux sandbox tests run
  there and on CI's `ubuntu-24.04` (bubblewrap installed by apt in the verify job), so they are not
  CI-only.
- **2026-10-12 — S4 — FINDING — CI on the 4.4 push (run 38305340576)** — on `ubuntu-24.04` every
  sandboxed task ended with status 1 before it ran (bubblewrap could not set up its namespaces; the
  container run passed); on `macos-latest` the 2 GiB allocation at a 256 MiB limit was not stopped
  (the jetsam limit held on this Mac, not on GitHub's macOS VM); the Linux desktop job's window showed
  "Resources not observed" after discovery had finished (it passed at 4.2; cause not established from
  the log). Each is fixed after 4.5, below.
- **2026-10-12 — S4 — DECISION — CodeTasks run as fenced jobs (4.5)** — `application/jobs.py` gains
  `execute` (lease to the harness's worker `runner-local`, run through the `Runner` port with a
  callback that heartbeats every 15 s and, every quarter second, stops the task on a pause or cancel
  request or when the lease is no longer this attempt's; report the outcome under the attempt's fence),
  `reconcile` (the D03 tick: expire every lease that has run out, nobody touching the job) and `tidy`
  (store a committed result's outputs still in staging; release and delete any other attempt's
  folder). Outputs stay in the attempt's staging folder until the result that names them is
  committed, then move into the content store: a refused result leaves nothing, and a crash between
  commit and storage is finished by `tidy`. A sandboxed task's failure is final (not transient):
  repairs are new tasks (D17, Sprint 5). The harness runs the tick every second and the dispatcher
  every quarter second while its server runs; one lock serialises every sandboxed attempt (the
  binding allows one), so a route running its own job and the dispatcher never race.
- **2026-10-12 — S4 — DECISION — a RunRecord is a succeeded attempt's outcome (4.5)** — app RunRecord
  0.1.0 (job, attempt, fence, CodeTask and binding by digest, `assurance: os_sandbox_single_user`, each
  output by digest and size) is stored in the content store and its digest is the job's result. This
  replaces the 4.1 plan to add outcome fields to the CodeTask, which stays the declaration; a failed
  or stopped attempt has no record, and its job says why (`<kind>: <message>`, at most 200
  characters).
- **2026-10-12 — S4 — DECISION — profiling runs in the sandbox (4.5)** — Sprint 1's DuckDB profiling
  moved unchanged into `src/dsp/recipes/profile_csv.py`, run as a Python CodeTask whose one input is
  the captured file (`data.csv`) and whose one output is `profile.json`, now app Profile 0.1.0 (it gains
  `schema_version` and `type`). The parser touches the owner's data, so it runs confined (C18); the
  harness validates the profile and renders the report, escaping every value. `/v1/profiles` captures
  the file, admits the recipe (observing the hardware first on a fresh profile, since nothing is
  admitted blind), runs the job inline under the lock, and exports the pack once the job succeeded; a
  recipe failure is the job's failure and nothing is exported. The trail shows the job and the export.
  The recipe's source ships with the frozen harness (`--add-data`).
- **2026-10-12 — S4 — DECISION — `dsp run-task` and task sources (4.5)** — `POST /v1/sources` (native
  only, at most 1 MiB) stores a task's source and returns its digest; `dsp run-task <task.json>`
  stores the named source, admits the task, waits for it and prints its end and reason (exit 2 unless
  it succeeded). The harness finds the runner environment at `DSP_RUNNER_ENV`, else `.runner-env`
  beside the source; without it, or without the OS's sandbox (bubblewrap and `prlimit` on Linux),
  Python and SQL tasks and profiles are refused (DEPENDENCY_UNAVAILABLE), never run another way. Its
  lock digest (each installed distribution's name and version) is recorded on every Python or SQL
  CodeTask.
- **2026-10-12 — S4 — DECISION — a quit drains a running task; a dead harness ends it (4.5)** — on a
  graceful quit the dispatcher starts nothing new and a job already running finishes (D24: the drain
  test lets a profile in progress export). If the harness dies, its task ends with it: on Linux by the
  kernel (`--die-with-parent`); on macOS, which has no parent-death signal, by a watcher thread in the
  task's own process that exits when it is orphaned, a mitigation a hostile task could starve. The
  harness's wall and CPU limits would otherwise end with it.
- **2026-10-12 — S4 — FINDING — what a quit costs while a task runs (4.5)** — a drain can last up to the
  task's wall time (600 s by default), and a stopping harness accepts no new request, so the task
  cannot be cancelled once Quit is pressed. Cancel first, then quit.
- **2026-10-12 — S4 — FINDING — the built app needs the runner environment named (4.5)** — no runner
  environment ships in the bundle; the frozen harness uses `DSP_RUNNER_ENV` (the built-app test sets
  it through `make e2e`) and otherwise refuses sandboxed work. Shipping one is distribution work.
- **2026-10-12 — S4 — DECISION — runner jobs in the activity trail (4.5)** — a job line carries the
  reason the coordinator recorded: a failure's `<kind>: <message>`; a refused late result reads
  "<outcome> result refused" with that report's own attempt and fence and the refusing code. Tested
  once in Vitest and once in Playwright against a real harness running real sandboxed jobs.
- **2026-10-12 — S4 — DEFECT — a stopped server left its background work running (4.5, fixed)** — the
  reconcile tick and dispatcher threads are not daemons (a quit drains), and they run while the server
  has not been asked to exit. A server that stopped any other way (in a test, `run` replaced by a stub
  that returns at once) left them running, and the test process never exited after reporting its
  results (seen twice as a gate that did not end). `serve` now marks the server as exiting whenever
  `run` returns, so the background work ends with it however it ended.
- **2026-10-12 — S4 — DECISION — macOS memory is also polled (after CI run 38305340576)** — the jetsam
  limit did not stop a 2 GiB allocation at 256 MiB on GitHub's macOS VM. The adapter now also polls the
  kernel's footprint account of the task (the figure jetsam uses) every 50 ms and kills it past its
  limit (`memory_limit`); on this Mac jetsam usually stops it first. Checked here with jetsam set far
  above the limit: the poll alone stopped the task; with neither, the test fails. Polling is not
  kernel-enforced: a task can overshoot by what it allocates in 50 ms.
- **2026-10-12 — S4 — DECISION — the OS's answer under a wrapper (after CI run 38305340576)** — a library
  that wraps the OS's refusal (urllib's `URLError` has no errno) lost the code in the runner's message;
  the runner now reports the innermost `OSError` with an errno ("URLError: [Errno 61] Connection
  refused"), still without its path.
- **2026-10-12 — S4 — DECISION — bubblewrap's user namespaces on CI's Ubuntu 24.04 (after CI run
  38305340576)** — Ubuntu 24.04 restricts unprivileged user namespaces through AppArmor unless a profile
  allows them, which would stop bubblewrap on that runner (every sandboxed task ended with status 1
  there; the inferred cause is this restriction, to be confirmed by the next CI read). `tools/
  bwrap_apparmor.sh` adds a profile that allows them to `/usr/bin/bwrap` alone, as Ubuntu's own
  profiles do for the programs that need them, rather than lifting the restriction for every program,
  and then builds the smallest sandbox bubblewrap can make, so a failure names its cause. It changes
  only the throwaway CI runner. A user on Ubuntu 24.04 needs the same profile for the Linux sandbox to
  work: a distribution matter, logged.
- **2026-10-12 — S4 — DEFECT — a lost read left the window without its snapshot (after CI run
  38305340576, fixed)** — the Linux built-app test saw "Environment observed" in the trail while the
  window still said "Resources not observed": the window read the snapshot once when the discovery event
  arrived and dropped a failed read. Why that read failed on that run is not established from the log.
  The window now reads the snapshot and the plan the events name again on every poll until a read
  succeeds.
- **2026-10-12 — S4 — DECISION — the A28 containment suite (4.6)** — `tests/sat/test_sprint_04.py` runs
  every item of the skill's list as real Python through admission, the dispatcher and this host's
  sandbox, and writes one A28 evidence part per item (`make sat`), each at `os_sandbox_single_user`
  assurance with the limit that this is not VM isolation: a planted host secret and a key under the
  home's `.ssh`; an HTTP fetch from a listener on this host and a name lookup; starting pip and writing
  into the runner environment; a file in the state folder standing for a sealed final partition; writing
  the ledger and the task's own declaration; fork and a shell's spawn; CPU, memory, wall time, output
  and scratch limits; the source and every attempt kept. Each part is PASS only when the run showed it.
  The scenario as the suite words it also needs model-generated code and at most two repairs (Sprint 5)
  and real sealed partitions (Sprint 9); the overall A28 record (4.7) says so.
- **2026-10-13 — S4 — FINDING — one gate took 22 minutes for 7 of tests (4.6)** — a `make verify` on this
  Mac reported 332 passed in 7 min 15 s and ended 22 min after it began. A rerun of the same pytest
  command with a thread dump armed for a process that outlived its summary ended 7 s after its summary
  (10 min 29 s of tests); the cause of the first is not established. The gate is longer than at Sprint 3
  (about 7 to 10 minutes on this Mac, 6 in the Linux container) because some 60 tests now start a
  sandboxed task, each about 1.7 s on macOS for its scratch volume.
- **2026-10-13 — S4 — DEFECT — the built-app tests stopped a harness with a window still open (fixed)**
  — on macOS both built-app tests sent the stop request while an app window was open; the shell then
  starts a new harness, as designed, so the lock could be taken again before the test saw it free
  (one run of the second test failed so), and the first test left a harness running after it. Sprint
  4's harness releases the lock about a second later than before (its background threads end first),
  which widened the race. The tests now close the remaining window before the stop request. That was
  not all of it: every launch spawns a harness, which exits when the profile is already served, but
  a frozen harness takes about 3 s to reach the profile lock (measured: 2.95 to 3.36 s, unpacking a
  21 MB one-file binary), and the tests waited a fixed 3 s after a launch. A harness still starting
  when the serving one stopped took the lock: the failing check and the harnesses left running. The
  tests now wait until each launch made while another harness serves has spawned its own harness and
  seen it exit (the first version checked before the shell had spawned it, and passed at once). Three
  runs then passed. A one-directory bundle would start faster; that is packaging work, logged.
- **2026-10-13 — S4 — FINDING — a harness sometimes outlives the built-app tests on macOS** — in two of
  three passing runs one bundled harness was still running afterwards, on one test's profile, started
  by a process that had exited; where it comes from is not established. The tests pass; the process
  holds only its temporary profile and stops on SIGTERM.
- **2026-10-13 — S4 — DECISION — the integrity review and what was done with it (4.7)** — the one
  `integrity-reviewer` run (a general-purpose agent following the reviewer's file, since the project's
  agent type is not in this session's registry; 249k tokens) returned REVIEW: PASS with six should-fix
  findings and five notes. Fixed, each with a test and a mutation check: (1) promotion compared a digest
  after moving the file, so one that stopped part-way blocked the dispatcher for good: it now checks
  before moving, counts an output already stored under its digest as moved, and `tidy` sets a folder it
  cannot finish aside once (`.held`); (2) on Linux a memfd or System V segment held memory `RLIMIT_AS`
  does not count: the filter refuses `memfd_create` and `shmget`, and the memory test probes both (a
  file-size limit was added too, then removed: every writable file system is the sized scratch, so no
  test could fail without it); (3) a frozen harness guessed a runner environment under its unpack folder
  (`/tmp/.runner-env` on Linux, which another user could plant): it now uses only `DSP_RUNNER_ENV`, and
  an environment whose folders are not the owner's alone is refused; (4) A28 parts asserted only a prefix
  the audit hook alone produces: each read and write part now requires the OS's answer and errno, and
  the lookup must fail as `gaierror`; (5) an error while watching a task left it running unwatched: the
  core now kills and reaps it first; (6) a failure message could carry the runner environment's path:
  the runner names the attempt, runner and interpreter paths, in DuckDB's messages too. Of the notes,
  (8) an outside worker could lease a sandboxed job and report a success no sandbox ran: the lease route
  refuses it; (11) a request with no reply was called "not received" though it may have been: the trail
  now says "no answer" (a refusal before reading stays "not received"). Note (7) is worse than the
  review could tell from the code: see the next entry. Logged, not fixed: (9) the Linux filter allows
  `execve`, so a task can replace itself with the interpreter (still confined, and `/bin/sh` is not
  mounted); (10) admission accepts any captured DataManifest as an input and nothing reads the binding's
  `sealed_data_access: false`: Sprint 9 must exclude sealed manifests there.
- **2026-10-13 — S4 — DEFECT — on macOS a task can read every same-user process's environment (closed
  the same day: see "both macOS containment gaps closed")** — measured on macOS 26.3.1: real task code reading `KERN_PROCARGS2` for its parent read the
  harness's arguments and environment (a variable planted in the harness's environment was found). No
  Seatbelt rule this sandbox can express stops it: with no `sysctl-read` allowed at all, with
  `(deny process-info*)`, and with `kern.procargs2` denied by name, the read still succeeded. The same
  call works for any process of the owner's by its ID, so environment variables of the owner's other
  programs are readable too. On Linux the task cannot (no `/proc`, its own process IDs). The containment
  test and the A28 host-secret part state the policy as the skill does and fail on macOS; the macOS A28
  host-secret record is FAIL.
- **2026-10-13 — S4 — DEFECT — on macOS Seatbelt does not mediate System V shared memory (closed the same
  day: see "both macOS containment gaps closed")**
  — measured: `shmget` succeeds under the profile, also with an explicit `(deny ipc-sysv*)`. A task can
  hold memory its limit does not count, up to the kernel's System V quota (`kern.sysv.shmall` 1024 pages,
  4 MiB, and 32 segments for the whole machine). A task cannot remove its own segment: inside the
  sandbox `shmctl(IPC_RMID)` fails with EPERM, so every segment outlives its task and takes from that
  shared quota until something outside removes it. Earlier probe runs had left six such segments
  (3 MiB), which is why two gate runs saw `shmget` fail with ENOMEM rather than succeed; they were
  removed with `ipcrm` (only segments the tests' tasks had made: the owner's own were not touched).
  The memory test now removes its probe's segment from outside the sandbox (mutation-checked: without
  that, a 1 MiB segment is left). It requires a refusal and fails on macOS.
- **2026-10-13 — S4 — FINDING — a failure message is text the task chooses (4.7)** — up to 200
  characters of it go into the `job.failed` event and the trail. Sprint 5 must treat it as customer
  content before any of it reaches a prompt.
- **2026-10-13 — S4 — DEFECT — Cmd+. in the built macOS app (still open; the owner's press)** — the
  owner pressed each shortcut once in the built app (2026-10-13, a fresh profile, a queued job): Cmd+P
  paused the job, and the ledger shows the window's own handler sent it (a `command-…` ID, the
  renderer's form); Cmd+. produced nothing: no command reached the harness, from the window's handler
  or from the native menu. In Playwright (Chromium) and on Linux both chords work. This is the evidence
  the 2026-10-12 entry asked for before changing the chord: on macOS Cmd+. reaches neither the webview
  nor the menu. Changing the chord is the owner's call (waiting on the owner).
- **2026-10-13 — S4 — DECISION — the window says why it could not read the snapshot (after CI run
  38322576233)** — the Linux built-app test failed again on that run, so the retry was not the cause:
  the window's read of `/v1/hardware` fails there while Python's read and the window's read of the plan
  succeed. The resource bar now shows "Resources not read: <reason>" instead of "Resources not
  observed", which is more honest for the owner and puts the reason into the test's failure text.
- **2026-10-13 — S4 — DEFECT — a sandbox that could not start stranded a job (fixed; cause open)** — in
  one macOS gate run the dispatcher logged `dispatch failed: PermissionError` while starting the A28
  bounds part's task, and the job sat on a lease no one held until it expired, so the part timed out.
  The log has no traceback, so which call refused (the scratch image or the spawn) is not established;
  the part passed alone twice afterwards. `execute` now reports any OS error or
  refusal from the runner as a transient `sandbox_unavailable` failure, so the job is requeued at once
  and given up after the usual retries (a test with a runner that refuses; mutation-checked twice).
- **2026-10-13 — S4 — DECISION — the overall A28 record takes FAIL from a failed part** — the overall
  record was INSUFFICIENT_EVIDENCE whatever its parts showed, which on macOS rounded up the failed
  host-secret part. It is now FAIL when a part the same run recorded on that OS (same commit) failed,
  and names the failed parts; otherwise it stays INSUFFICIENT_EVIDENCE for the parts that cannot exist
  yet. On Linux the acceptance line's answer is ENOENT rather than EPERM: `/etc` is not mounted in the
  sandbox, so the file does not exist for the task.
- **2026-10-13 — S4 — DECISION — both macOS containment gaps closed (the HALT withdrawn)** — at the
  owner's request ("run workflows or extra agents to get CI green") one workflow ran five investigators
  on this Mac (every Seatbelt rule, the XNU source, the App Sandbox and built-in profiles, System V, and
  separate-user or VM execution) and an adversarial verifier on each claimed closure (9 agents, 1.05M
  tokens). Two closures held against every bypass tried, and were then reproduced here, mutation-checked
  and gated. (1) **Other processes:** the profile's blanket `(allow sysctl-read)` granted the procargs
  read before the process-info check; with it removed *and* `(deny process-info*)` stated, every route
  (KERN_PROCARGS2, KERN_PROCARGS, kinfo_proc, listing, libproc) is refused with EPERM, for the parent,
  an ancestor and an unrelated sibling (Mach task ports were refused already). The earlier measurement had tried each of the two
  changes alone, never together, and denying `kern.procargs2` by name could never match: the kernel names
  that read `kern.procargs2.<pid>`. Sysctl reads are now allowed by exact name only: the eleven that
  libSystem, Python, `os.uname()` and DuckDB read, taken from the sandbox's denial log while every sandbox
  test ran (`log stream`); afterwards only the probes' procargs reads and the network test's routing
  table are denied. A library reading another sysctl gets EPERM; add it by name after checking it reveals
  nothing of another process. (2) **System V:** creating an object passes no ipc rule in XNU (only reading
  an existing key is hooked), so the profile denies every System V call by number with `syscall-unix`,
  the `shmsys`, `msgsys` and `semsys` multiplexers included (a `shmget` rule alone is bypassed through
  `shmsys`). The rule relies on a private SBPL feature and on the profile denying by default; the D21 test
  is its regression test. Corrections to the defect entries above: under the old profile a task could not
  attach a segment (`shmat` was refused), so it could hold no memory in one; the harm was exhausting the
  machine-wide System V quota, and message queues and semaphores escaped as well. Linux now also refuses
  `msgget` and `semget` (they would have died with the IPC namespace, but the policy is the same on both
  OSes). Tests: C14 also reads an unrelated sibling's environment; D21 tries shared memory, queues,
  semaphores and the multiplexer, and removes with `ipcrm` anything a task made. Mutation-checked (macOS
  6, Linux 2, all caught): the blanket sysctl allowance back, no `(deny process-info*)`, no System V
  rule, no multiplexers, no `msgget`, no `semget`; on Linux no `msgget`, no `semget`; and the sibling probe
  alone catches the old profile. Left by the investigation: `~/Library/Containers/dsp.probe.appsandbox`
  (28 KB, from the App Sandbox probe; the system refused its deletion), which the owner may remove; two
  System V objects of the owner's that predate it (shared memory 131073, semaphore 4915207) were not
  touched. Not adopted: running tasks as another user (needs admin setup and moves supervision into a
  root helper), the App Sandbox (closes neither gap), and marking the harness `CS_RESTRICT` (hides only
  the marking process's environment; arguments and every other process stay readable).
- **2026-10-13 — S4 — DEFECT — the Linux built-app test raced the window's snapshot read (fixed in the
  test)** — the test captured the window's text when the plan appeared and asserted the snapshot's CPU
  line in that capture; the window reads the plan and the snapshot with separate requests, so the plan
  can show first. Runs 38322576233 and 38379462014 failed this way (the plan shown, the trail's
  "Environment observed", and "Resources not observed" with no read error), run 38367812467 passed. The
  test now waits for the snapshot's line. The window was right throughout; the "Resources not read:
  <reason>" line added for diagnosis stays, as it names a real read failure.
