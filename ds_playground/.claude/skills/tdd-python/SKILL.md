---
name: tdd-python
description: Test-first loop and test conventions for DS Playground (pytest markers, deterministic fixtures, real execution over mocks, edge cases, no network, no skips). Use before writing or changing any code under src/, tools/ or tests/.
---

# TDD for DS Playground

## Loop

1. **Red.** One test named `test_<behaviour>`; docstring starts with the suite ID it covers (`A03:`, `D20:`).
   It must fail for the intended reason, not an import typo.
2. **Green.** The minimum code that passes. No speculative parameters or branches.
3. **Refactor** only with the suite green.

## Where tests go

`tests/unit` (pure logic), `tests/contract` (schema ↔ model, examples, parity), `tests/integration` (ledger,
store, runner, harness over real SQLite/DuckDB/files), `tests/e2e` (CLI and desktop flows), `tests/sat`
(sprint acceptance, cumulative).

## Rules

- **Real over mocked:** real SQLite, DuckDB, sklearn fits, sandbox and local model. A fake is allowed only
  where the real thing cannot run offline, and it must mirror the real shape.
- **Edge cases with every feature:** empty input, malformed file, duplicate or null key, leading-zero ID,
  stale revision, crash before and after commit, denied permission, limit exactly reached and exceeded by one.
- **Deterministic:** fixtures come from `fixtures/` generators with a fixed seed and known generating
  parameters; inject clock, ID source and RNG. Same seed, same bytes.
- **Offline:** sockets are disabled in the default run. Mark what needs more: `slow`, `sandbox`, `live_model`,
  `remote_model`, `desktop`, `network` (`AGENTS.md` §6).
- **Assert on stable things:** error codes, states, digests, counts. Not log text or message wording.
- **Statistical assertions** state tolerance and the sample size that justifies it; `pytest.approx` with
  `abs=` near zero, `rel=` otherwise.
- Use `monkeypatch` in tests instead of adding test-only parameters to production code.

## Never

- Skip, xfail, delete or weaken a test to get green; loosen a threshold; add `# type: ignore` or `# noqa`.
- Mock the module under test.
- Edit a test to match wrong output. If the test is wrong, fix it and log a DEFECT in `docs/decisions.md`.
