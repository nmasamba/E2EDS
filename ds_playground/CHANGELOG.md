# Changelog

## Sprint 2 — in progress

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
