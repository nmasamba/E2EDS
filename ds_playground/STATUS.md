# STATUS

Resume point for every session. Read this first, then `docs/decisions.md`, then `AGENTS.md`.

## Now

- **Sprint:** 1 — M0 foundations and thin slice
- **Claimed prompt:** 1.1
- **Branch:** `sprint-1-foundations`

## Done

- 2026-10-01 — Scaffolding: `AGENTS.md`, `CLAUDE.md`, `prompts.md`, `docs/decisions.md`, eleven skills, one
  reviewer subagent (`integrity-reviewer`). Script-checked: every B01–B37, A01–A45 and R01–R27 ID appears in
  `prompts.md`; every cited suite path resolves.

## Sprint board

| Sprint | Milestone | State | Gate outcome |
|---|---|---|---|
| 0 | Setup | done except the model download (0.3), still running | G0: PASS for synthetic scope |
| 1 | M0 foundations and thin slice | in progress | — |
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

## Open defects and gaps

None yet.

## Waiting on the owner

Nothing. Standing approvals are in `docs/decisions.md`.

## Handoff note

Sprint 1 in progress on `sprint-1-foundations`; start at the claimed prompt above.
