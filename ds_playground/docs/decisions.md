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
  (CmdOrCtrl+P) and `Cancel run` (CmdOrCtrl+.), send `POST /v1/control` from the Rust side the way Quit sends
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
