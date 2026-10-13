# DS Playground

A desktop data-science workspace that analyses data and trains models on demand. It is being built sprint by
sprint from [prompts.md](prompts.md) under [AGENTS.md](AGENTS.md); the specification is the planning suite in
the parent folder. Current state and what is not built yet: [STATUS.md](STATUS.md).

## What works today (Sprint 1)

Profile a CSV file and export a versioned, hash-verified pack. Every row is read; nothing is sampled. Files
over the documented bounds (50 MiB, 100,000 rows, 200 columns) are refused rather than truncated.

```bash
uv sync --frozen
```

```bash
make runner-env
```

```bash
uv run dsp profile path/to/file.csv --out path/to/existing/folder
```

```bash
uv run dsp verify path/to/existing/folder/v1
```

The pack holds `manifest.json` (relative paths and SHA-256 digests), `profile.json` and a self-contained
`report.html`. Each export goes to a new `vN` folder; earlier versions are never overwritten. Local state
(ledger and artifact store) lives in `~/.dsp`, or in `DSP_HOME` if set. The profiling itself runs as a job in
the OS sandbox (Sprint 4, below), so `make runner-env` must have built the runner's environment.

The commands run through the local harness, which `dsp` starts if it is not running. Naming a file and a
folder in `dsp profile` grants the harness that file and that folder. Folders can also be granted on their
own; the harness and the desktop window then refer to them by handle and folder name, never by path.

```bash
uv run dsp grant path/to/folder --purpose source_root
```

```bash
uv run dsp grants
```

```bash
uv run dsp revoke grant-handle-from-the-list
```

Observe this machine and get a provisional plan (it authorises nothing), and stop the harness when done:

```bash
uv run dsp hardware
```

```bash
uv run dsp plan
```

```bash
uv run dsp stop
```

## Jobs, messages and controls (Sprint 3, in progress)

The window and the harness now run durable jobs. The only workload is the deterministic test worker: queue
it with "Start the hung test job" in the window (or `POST /v1/jobs` through the harness), then run the
worker against your profile; pause, resume and cancel from the header, the keyboard (Cmd/Ctrl+P and
Cmd/Ctrl+., handled by the window; the native menu has the same items) or by typing `pause now`, `resume`,
`cancel this run` or `status` in the composer;
change a requirement with `exclude field region`. Every receipt and state appears in the activity trail.

```bash
uv run python -m fixtures.worker --job <job id from the window>
```

## Sandboxed tasks (Sprint 4)

Python and SQL run only in the operating system's sandbox: Seatbelt on macOS (nothing to install), bubblewrap
with a seccomp filter on Linux (`sudo apt-get install bubblewrap`; on Ubuntu 24.04 bubblewrap also needs the
AppArmor profile `tools/bwrap_apparmor.sh` installs). A task reads only its declared inputs and the runner,
writes only its scratch folder, has no network, cannot start a process, and is stopped at its CPU, memory,
time, output and scratch limits. This is OS-sandbox assurance for one local user, not VM isolation.
Two gaps are open on macOS, where Seatbelt has no rule for either: task code can read the arguments
and environment variables of the owner's other programs, and can hold up to 4 MiB of System V shared
memory outside its memory limit (`STATUS.md`, open defects).

```bash
make runner-env
```

```bash
uv run dsp run-task fixtures/tasks/read_secret.json
```

`dsp run-task` runs a declared task as a job and prints how it ended; the fixture's read of `/etc/passwd` is
refused by the OS (`failed: undeclared_read: ... the OS answered ...`, exit status 2). The window's activity
trail shows each job and the reason it failed. The built app finds the runner's environment through
`DSP_RUNNER_ENV`; without it, sandboxed work is refused.

## Desktop shell (Sprint 2, in progress)

A native window on macOS and Linux that starts or reconnects to the local harness and shows the workspace as
the harness's ledger records it: the nine-stage work trail, the observed hardware (and what could not be
observed), a provisional plan, and the folders you grant through the native folder dialog. Closing the
window leaves the harness running; Quit stops the harness the app started, after work in progress finishes. Building it needs Rust, Node 22 and pnpm; on Linux also the system packages listed in the `desktop`
job of `../.github/workflows/ds-playground.yml`.

```bash
make desktop-dev
```

```bash
make desktop-build
```

```bash
make e2e
```

`make desktop-dev` opens the window against the dev server. `make desktop-build` freezes the harness into one
executable and builds the bundle (`.app` on macOS; deb and AppImage on Linux) under
`desktop/src-tauri/target/release/bundle/`; the app starts its own bundled harness, with no terminal and no uv.
`make e2e` runs the renderer and shell tests against a real harness and then launches the built app, so run
`make desktop-build` first. `make sat` runs the sprint acceptance tests and writes their evidence records to
`docs/evidence/`.

## Development

```bash
make verify
```

```bash
make verify-linux
```

`make verify` is the gate: format, lint, strict types, import boundaries and tests with coverage (the
desktop end-to-end test is left to `make e2e`). `make verify-linux` runs the same gate in a Linux container,
as an unprivileged user with bubblewrap installed, and `make sat-linux` runs the acceptance tests there and
copies their evidence into `docs/evidence/`. `make test-fast` is the inner loop.
