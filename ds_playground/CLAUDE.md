# Working in this repository

This file exists so a tool looking for `CLAUDE.md` finds the right instructions. It adds no rules of its own.

Read, in this order:

1. **[STATUS.md](STATUS.md)** — where the build is and the handoff note from the last session.
2. **[docs/decisions.md](docs/decisions.md)** — owner decisions and logged deviations from the spec.
3. **[AGENTS.md](AGENTS.md)** — product boundaries, architecture rules, work loop, testing, stop list, code
   review rules and the skill routing table. Read it before changing anything.
4. **[prompts.md](prompts.md)** — the sprint prompts. Work one sprint at a time, in order.

The specification is the planning suite in the parent folder (`../README.md` is its entry point). It is
read-only.

Skills are in `.claude/skills/`, reviewer subagents in `.claude/agents/`.

Commands (available from Sprint 1; run only targets that exist):

```
make verify         # the sprint gate on this machine
make verify-linux   # the same gate in a Linux container
make test-fast      # inner loop
```
