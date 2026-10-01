---
name: sprint-workflow
description: How to start, run and close a DS Playground sprint from prompts.md — session start, per-prompt loop, exit sequence, evidence records, docs checklist and handoff. Use at the start and end of every sprint and whenever closing a prompt.
---

# Sprint workflow

## Start of session

1. Read `STATUS.md`, `docs/decisions.md`, then the active sprint in `prompts.md`.
2. Read only the suite sections that sprint cites.
3. Check the stop list (`AGENTS.md` §8) for anything the sprint needs from the owner; ask for all of it in one
   message, then continue with unblocked prompts.
4. Work on branch `sprint-N-<slug>`.

## Per prompt

Claim it in `STATUS.md` → failing test → smallest change → `make test-fast` + lint + types → review the diff
against `AGENTS.md` §3 and §12 → commit `[sN] type(scope): summary` → one-line status: files, tests added,
result.

## Exit sequence (the sprint's last prompt)

1. `make verify` — paste the tail of the real output.
2. `make verify-linux` — same. If it cannot run, log an open DEFECT with the reason; do not call it green.
3. `make sat` — this sprint's acceptance tests and every earlier sprint's.
4. `uv run python tools/trace_ids.py <N>` — every ID in the sprint's scope appears in a test docstring or an
   evidence record; list the ones that do not.
5. Run what shipped for real on each OS (the command is in the sprint's acceptance line) and keep the output.
6. Docs checklist, inline:
   - `README.md` commands exist and were run.
   - `STATUS.md` board, gate outcome, open defects and handoff note are current.
   - `docs/decisions.md` has every assumption, deviation and defect from this sprint.
   - `CHANGELOG.md` has the sprint's user-visible changes.
   - Search the docs for claims this sprint made false.
7. Boundary sprints (3, 4, 5, 9, 10) only: run `integrity-reviewer` on the sprint diff; fix blockers.
8. Commit `[sN] chore: sprint N complete`. Push or open a PR only if the owner has approved pushing.
9. Report: what shipped, tests added, gate output per OS, IDs covered and not covered, outcome per gate
   (PASS / FAIL / INSUFFICIENT_EVIDENCE), logged decisions, what is waiting on the owner.

## Evidence record

Each acceptance scenario writes `docs/evidence/A##-<slug>.json` from its test:

```json
{"id": "A28", "sprint": 4, "os": "darwin-arm64", "fixture": "containment-v1", "commit": "<sha>",
 "expected": "...", "actual": "...", "outcome": "PASS", "assurance": "os_sandbox_single_user",
 "limits": ["not VM isolation"]}
```

`outcome` is what the run showed. If the scenario needs something unavailable (an owner, a recipient, a
provider account), write INSUFFICIENT_EVIDENCE with the reason.

## Handoff

At about half the context window, or at sprint end, write the handoff note in `STATUS.md`: branch, last green
commit, the next prompt, anything half-done, anything waiting on the owner.
