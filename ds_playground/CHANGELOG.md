# Changelog

## Sprint 2 — in progress

- Local harness: one authenticated, loopback-only instance per user profile; `dsp status` starts or
  reconnects to it.
- Desktop shell (`desktop/`, Tauri 2.12.0): a native window on macOS and Linux that starts its bundled harness,
  or reconnects to the one already running, and shows "connected" with the harness version and process, or
  "harness unavailable" with the reason. `make desktop-dev`, `make desktop-build`, `make e2e`.
- The harness admits exactly the desktop shell's origin; every other browser origin is still refused and the
  token is still required.

## Sprint 1 — foundations (2026-10-01)

- `dsp profile <file.csv> --out <folder>`: full-file CSV profile exported as a new, hash-verified version
  folder; `dsp verify <folder>` checks a pack against its manifest.
- Contracts: the suite's sixteen JSON Schemas vendored and digest-checked; all suite examples validate.
  App-owned schemas for DataManifest, PackManifest and ExportReceipt.
- SQLite ledger with compare-and-swap appends and idempotent event commits; content-addressed artifact store.
- Gate (`make verify`, `make verify-linux`) and CI on Linux and macOS.
