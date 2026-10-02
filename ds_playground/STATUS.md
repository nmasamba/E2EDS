# STATUS

Resume point for every session. Read this first, then `docs/decisions.md`, then `AGENTS.md`.

## Now

- **Sprint:** 1 — M0 foundations and thin slice
- **Claimed prompt:** 1.5 (gate) — awaiting CI
- **Branch:** `sprint-1-foundations`

## Done

- 2026-10-01 — Scaffolding: `AGENTS.md`, `CLAUDE.md`, `prompts.md`, `docs/decisions.md`, eleven skills, one
  reviewer subagent (`integrity-reviewer`). Script-checked: every B01–B37, A01–A45 and R01–R27 ID appears in
  `prompts.md`; every cited suite path resolves.

## Sprint board

| Sprint | Milestone | State | Gate outcome |
|---|---|---|---|
| 0 | Setup | done except the model download (0.3), still running | G0: PASS for synthetic scope |
| 1 | M0 foundations and thin slice | built; gate green locally on macOS and linux/arm64 | see below |
| 2–11 | M1 | not started | — |
| 12–20 | M1B, M1C, M1R, M2, M3, M3Z, M4 | not started | — |

## Environment observed (2026-10-01, this Mac)

macOS 26.3.1, arm64 (Apple M1 Max), 10 cores, 64 GiB RAM, about 714 GiB free. Present: uv 0.10.8, Python 3.12.13
and 3.13 (uv-managed), Node 22.17.1, pnpm 10.32.1, Docker 29.8.1, git, gh, Homebrew.

Installed in Sprint 0.2: cmake and rustup via Homebrew (rustup is keg-only: `/opt/homebrew/opt/rustup/bin`),
Rust stable 1.99.0. llama.cpp built from tag `b11104` at commit `217f81c266a7b7c986ee3d2c58e1cccee05a0744`
into `~/.local/share/dsp/llama.cpp/build/bin/llama-server` (reports 0.4.1-dev, Darwin arm64; binary SHA-256
`10f66aeed2d40ae707ee189748738ac6db97995ff18990dafa9c0e5b73d94128`, dynamically linked to the libraries beside
it). Absent: Tesseract (no OCR profile is planned without owner approval).

## Sprint 1 gate (2026-10-01)

- `make verify` on macOS arm64: format, lint, mypy strict, boundaries all clean; **95 passed**, coverage 99%.
- `make verify-linux` (container, linux/arm64, Python 3.12.12): **95 passed**, coverage 99%.
- `make sat`: 1 passed. ID trace for Sprint 1: D20, D23, R11 covered.
- Live run on both: `dsp profile orders.csv --out out/` on the 2,000-order fixture exported `v1` (3 files),
  `dsp verify` printed `verified`, a second run produced `v2`, and `manifest.json` has the same SHA-256 on
  macOS and Linux (`6aeb5ad8…5cadf`).
- Gate outcome: **PASS** for Sprint 1 scope. No acceptance scenario (A##) is in scope for this sprint.

## Open defects and gaps

- Linux x86-64 is verified only by CI, not locally (see `docs/decisions.md`).
- The assistant model download (Sprint 0.3) is still running; its SHA-256 has not been verified yet.

## Waiting on the owner

Nothing. Standing approvals are in `docs/decisions.md`.

## Handoff note

Sprint 1 is built and committed on `sprint-1-foundations`. Next: confirm CI is green on both runners, then
start Sprint 2 at prompt 2.1 (harness). Rust is installed but keg-only: prepend `/opt/homebrew/opt/rustup/bin`
and `~/.cargo/bin` to PATH for cargo.
