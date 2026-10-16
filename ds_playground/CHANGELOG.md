# Changelog

## Sprint 5 — assistant gateway, open model first (in progress)

- Cancel run is Cmd+Shift+K on macOS and Ctrl+Shift+K on Linux (in the window and in the native menu);
  Cmd+. reached nothing in the built macOS app.
- The local open model: the harness verifies the model's size and SHA-256, starts llama-server confined
  by the OS (Seatbelt on macOS with Metal; bubblewrap on Linux, where it listens on a UNIX socket),
  with its API key from the OS secret store in a 0600 file, and marks the assistant ready only after the
  health endpoint and a typed tool-response probe. The workspace opens with the model absent and the
  header and trail say `assistant unavailable: <reason>`. `make live` and `make live-linux` run the
  model tests; `make verify` leaves them out.
- An instruction becomes an assistant job: the assistant proposes typed tool calls (inspect a granted
  CSV's schema, propose a requirement patch, write a code artifact, submit a code task, inspect its
  results), the application validates and runs each one, and the trail shows every call, refusal and
  the assistant's answer, marked as a proposal. Pause and cancel reach the jobs the assistant
  submitted; the instruction's command is accepted, then applied, rejected or needs clarification.
- Requirement changes from the assistant are typed patches with where in your words each came from;
  the trail shows a plain readback of each revision; "Pause now; exclude region before continuing"
  pauses first; a budget change through the assistant is refused for your own action.
- The assistant writes SQL or Python, runs it in the sandbox as a job, sees a bounded preview of the
  result and repairs a failed task at most twice; the Results section opens a committed table.
- Every failure of the model ends in `assistant unavailable` with its reason, the conversation and
  the controls untouched and no other model tried: a missing or corrupt model, a server that does not
  fit its memory limit, a hung server (killed at the generation deadline, the task failed with that
  reason, the same binding restarted) and a harness restart, which never dispatches a committed tool
  call twice. Pause and cancel receipts stay within 2 s with the model stopped mid-generation.
- Opt-in remote binding (D4 = B): a record at `<profile>/assistant/binding.json` points the assistant
  at an OpenAI-compatible endpoint, with its key read from the OS secret store, the project's data
  policy and the owner's spend limit shown in the header and trail before the first instruction, a
  charge the limit cannot cover refused before it is sent, and never the local model in its place.
  Tested against llama-server itself; no proprietary adapter.

## Sprint 4 — sandboxed native runner (2026-10-13)

- The activity trail is the one place outcomes appear: command receipts and their states with one wording,
  job states, refused admissions, the job the Run button queued, and any request the harness never
  received. The notes beside the buttons, the composer and the Run section are gone.
- Cmd+P and Cmd+. (Ctrl on Linux) pause and cancel the live job from anywhere in the window, as well as
  from the native menu.
- The harness listens before it publishes its port, so a client that starts at the same moment no longer
  waits for a connect timeout.
- The local compute option is a stored record at OS-sandbox, single-user assurance (not VM isolation),
  with macOS as an execution OS; every admitted job pins it and a stored CodeTask declaring its source,
  inputs, outputs, limits and permissions. A task whose input was not captured through a grant, whose
  source is missing, that declares no output, asks for more than the workload allows or asks for a
  permission is refused.
- The runner: `python -m dsp_runner <attempt>/task.json` runs one CodeTask's Python, or its DuckDB SQL
  against the inputs loaded as tables, in the task's scratch folder, and sends a result and the declared
  outputs on one bounded channel. `make runner-env` builds its locked environment.
- Generated or submitted Python and SQL run only in the OS sandbox: Seatbelt on macOS, bubblewrap with a
  seccomp filter on Linux, at single-user OS-sandbox assurance (not VM isolation). A task reads only its
  declared inputs and the runner, writes only its scratch folder, has no network, cannot start a process,
  and is stopped at its CPU, memory, time, output and scratch limits.
- `dsp run-task <task.json>` runs a declared task in the sandbox as a job and reports how it ended;
  `fixtures/tasks/read_secret.json` is refused by the OS. `dsp profile` now runs its profiling in the
  sandbox as a job the activity trail follows, and `profile.json` names its schema. A sandboxed job's
  failure appears in the trail with its reason.
- The resource bar says why the window could not read the observed hardware, instead of showing it as
  not observed; a request that got no reply is listed as "no answer", since it may have been received.
- On macOS, task code can no longer read the arguments and environment of the owner's other programs
  (the harness included) or create System V shared memory, message queues or semaphores, which
  outlived the task; Linux refuses both as well.

## Sprint 3 — jobs, admission, conversation and control (2026-10-08)

- Durable jobs: `POST /v1/jobs` queues a job; a worker process leases one attempt at a time (60 s lease,
  15 s heartbeat), reports once, and is fenced out when its lease expires or the job is cancelled. At most
  two automatic retries after a transient failure; a result is committed once per result key and a retry
  of a committed key gets the committed result back; cancel records acknowledge and stop times and never
  erases a committed result. `fixtures/worker.py` is the deterministic test worker (sleep, hang, crash
  before or after its commit, fail), the only workload this sprint.
- Admission: a job is admitted only with the owner's authority, for an operation the workload declares
  and the local option offers, with no accelerator the option lacks and no external charge (none can be
  granted yet), after a fresh capacity check against the latest observation less what running jobs hold;
  the request, its reservation and the job are recorded together, and a plan older than its inputs is
  rechecked before anything is admitted. The plan now plans for the test job's WorkloadSpec.
- Messages: `POST /v1/conversations/{id}/messages` stores each message as a command with a durable
  receipt before it answers; a retried message ID gets the same receipt, the same ID with other text is
  refused, bodies over 16 KiB are refused before they are parsed, and the window replays commands and
  their states through the events it already polls. The exact phrases `pause`, `pause now`, `cancel this
  run`, `stop this run`, `resume` and `status` are recognised as controls; other text is answered as
  "assistant unavailable" until an assistant is bound.
- Fast controls: `pause`, `pause now`, `cancel this run`, `stop this run`, `resume` and `status` act on the
  live job at once, as do the window's controls (`POST /v1/jobs/{id}/control`) and the native menu
  (`POST /v1/control`); pause stops any new attempt from being leased, the worker reports that it stopped
  before the job shows as paused, resume re-admits the job under the current requirements, and a
  cancelled job cannot resume. A phrase with several live jobs asks which; a quoted or embedded phrase
  does nothing. Workers may record a checkpoint. The window may now send JSON bodies.
- Requirement revisions: "exclude field <name>" while work runs becomes a typed change with an impact
  preview and a new immutable revision of the workload; results already committed stay on the old
  revision and are marked stale; the running job is held and resumes, explicitly, under the new
  revision; two edits against the same revision conflict predictably; a budget or evaluation change is
  refused until the owner acts on it. `GET /v1/workload` shows the current revision.
- Window: a composer for messages with the harness's receipt shown, an activity trail of every committed
  event with the state each command reached, Pause/Resume and Cancel run in the header and as native menu
  items (CmdOrCtrl+P, CmdOrCtrl+.), "Start the hung test job" to queue the sprint's one workload, and the
  develop stage of the work trail following the job's actual state (queued, running, pausing, paused,
  cancelling, cancelled, failed, completed). Everything is a projection of the ledger and survives a
  reload or a relaunch.

## Sprint 2 — desktop shell, discovery and plan (2026-10-02)

- Local harness: one authenticated, loopback-only instance per user profile; `dsp status` starts or
  reconnects to it.
- Desktop shell (`desktop/`, Tauri 2.12.0): a native window on macOS and Linux that starts its bundled harness,
  or reconnects to the one already running, and shows "connected" with the harness version and process, or
  "harness unavailable" with the reason. `make desktop-dev`, `make desktop-build`, `make e2e`.
- The harness admits exactly the desktop shell's origin; every other browser origin is still refused and the
  token is still required.
- Folder grants: choose source and output folders in the desktop window's native dialog, or with
  `dsp grant`; list them with `dsp grants` and remove them in the window or with `dsp revoke`. Grants are
  shown by folder name, survive a restart, and are checked each time they are used.
- `dsp profile` now runs inside the harness and exports only into a granted folder.
- Hardware discovery: `dsp hardware` and the desktop window observe processors, memory, storage and
  accelerators in about two seconds, with no model, no network and no elevated rights. Anything that could
  not be observed is shown as unknown with the reason, never as absent.
- Provisional plan: `dsp plan` and the window show what a fixed rule table makes of the observed hardware:
  each option is eligible, unqualified, unknown or blocked, with one reason. A plan never authorises execution.
- Work trail: the window shows the nine stages, the environment and the plan from the harness's event log,
  follows work started from the CLI, marks the environment stale after 60 seconds, and keeps the last known
  state when the harness cannot be reached.
- Lifecycle: closing the window leaves the harness running; Quit (and `dsp stop`) lets work in progress
  finish and then stops it; reopening shows the same state.

## Sprint 1 — foundations (2026-10-01)

- `dsp profile <file.csv> --out <folder>`: full-file CSV profile exported as a new, hash-verified version
  folder; `dsp verify <folder>` checks a pack against its manifest.
- Contracts: the suite's sixteen JSON Schemas vendored and digest-checked; all suite examples validate.
  App-owned schemas for DataManifest, PackManifest and ExportReceipt.
- SQLite ledger with compare-and-swap appends and idempotent event commits; content-addressed artifact store.
- Gate (`make verify`, `make verify-linux`) and CI on Linux and macOS.
