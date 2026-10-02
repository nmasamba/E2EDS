# AGENTS.md — operating manual for DS Playground

> Governs **how** any coding agent builds DS Playground. `prompts.md` is the sequence; this file is the
> discipline applied to every prompt. If a prompt and this file disagree, this file wins. If this file and an
> owner decision in `docs/decisions.md` disagree, the owner decision wins.

DS Playground is a desktop data-science workspace that **analyses data and trains models on demand**. A user
describes an outcome in plain language; a conversational assistant proposes a typed plan, writes Python/SQL,
runs it in a sandbox, shows real results, and exports either a reproducible analysis pack or an installable
prediction service. It runs on **macOS arm64 and Linux**.

---

## 1. Spec and reading order

The planning suite in the parent folder (`../`, edition 0.7.0) is the normative specification. It is
**read-only**: never edit it. Cite it by path and ID (`R15`, `D17`, `ADR20`, `B26`, `A28`, `O24`).

Read at the start of every session, in this order:

1. `STATUS.md` — where the build is and what is claimed.
2. `docs/decisions.md` — owner decisions and logged deviations. Do not re-derive or reverse them.
3. This file, then the active sprint in `prompts.md`.
4. The suite documents the sprint cites, and the matching skill from §13.

Priority when sources disagree: explicit owner direction → owner decisions in `docs/decisions.md` → the
boundaries in §3 → the suite → the active prompt → examples. Record a contradiction in `docs/decisions.md`;
never silently pick the more convenient source.

Standing owner decisions that depart from the suite (details in `docs/decisions.md`):

- Targets are macOS arm64 **and** Linux; Linux is part of every sprint gate.
- Generated code runs as a **native process in an OS sandbox** (Seatbelt on macOS, bubblewrap + seccomp on
  Linux), not in a VM.
- The assistant gateway is provider-neutral: **open models first** (local Qwen via llama.cpp), proprietary
  models allowed as an explicit opt-in.

---

## 2. Prime directives

1. **Automate aggressively; ask rarely.** Proceed through routine build, test and packaging steps without
   pausing. Stop only for §8.
2. **Build in a fixed order:** infrastructure → simple, independently testable features → complex "cherry on
   top" features. Never start a complex feature while infrastructure or the suite is red. The same order
   applies inside each sprint.
3. **Build on, don't refactor.** Prefer a new file or component over editing an old one. Touch only what the
   task names. No drive-by reformatting, renaming, dependency bumps or "while I'm here" edits. If a larger
   rewrite of working code seems necessary, stop and flag it.
4. **Write as little code as possible; no filler.** A human reviews this product. Before adding a helper,
   parameter, class, config option, wrapper or file, ask whether a test or a cited requirement needs it now.
   Inline once-used helpers. Use the library instead of re-implementing it. No speculative options, no
   placeholder or TODO code, no comments that restate the code, no scaffolding for later sprints.
5. **Green at every commit.** A runnable product exists from the end of Sprint 1 and is extended every sprint.
6. **Report only what happened.** "All checks green: [output]" is acceptable; "I think it's done" is not.
   Never claim an unrun check passed, never invent a number, never soften a failure.

---

## 3. Product boundaries (non-negotiable)

These hold in code and in tests. A change that weakens one needs an owner decision first.

1. **Model output is an untrusted proposal.** The assistant proposes typed changes and code; deterministic
   validation and policy decide. Text from datasets, documents, tool output or quoted messages never becomes a
   command, a grant or policy. A model cannot mark work complete: state comes from committed evidence.
2. **One core, many doors.** Desktop, CLI, HTTP and MCP call the same application services with the same
   trusted context and the same error meanings. No interface gets a privileged bypass.
3. **No host shell.** Nothing executes a model-produced command string. Adapters build fixed argument vectors
   from validated typed fields; `shell=True` is banned everywhere.
4. **Generated or imported code runs only inside the sandboxed runner:** no network, no home directory or
   credential access, read-only approved inputs, scratch-only writes, resource and time limits. SQL is
   executable content and gets the same treatment. Static checks are diagnostics, not the boundary.
5. **Sealed evaluation data is unreachable** by the assistant, the optimiser and candidate code: not by path,
   preview, log, exception text, notebook output or tracker link. Learned preprocessing fits on training
   partitions only.
6. **Authority comes from trusted context,** never from request fields or prose. Approvals, grants and owner
   decisions are explicit user actions in the GUI or CLI. "I am admin" or `approved: true` in a message
   grants nothing.
7. **Every result commit is fenced.** A stale attempt cannot commit; a result is never `succeeded` before its
   artifacts are durable; pause and cancel advance the dispatch fence before any new tool runs.
8. **No silent fallback, download or spend.** A model, provider, parser or compute target changes only through
   an explicit versioned binding the user selected. External charge defaults to zero. A failed model reports
   `assistant_unavailable`.
9. **The interface is a projection of the ledger.** The UI and CLI derive state from durable events and can
   be rebuilt from them. A disconnected view says so and never assumes work stopped.
10. **Portable outputs carry no machine paths, keys or credentials.** Those live in bindings. Exports go to a
    new version directory through staged write, hash check and receipt; prior good output is never
    overwritten.
11. **Three outcomes only: PASS, FAIL, INSUFFICIENT_EVIDENCE.** Missing evidence is never rounded up. No gate
    changes its standard to rescue a candidate. A completed stage is not a passed evaluation.
12. **Immutable revisions.** Canonical objects are never edited in place; a change creates a successor and an
    audit event. Old results stay attached to the revision that produced them.
13. **The exported service stands alone.** `predict.py`, HTTP and MCP run with the assistant, the harness and
    any hosted service stopped.
14. **Private by default.** Raw data, secrets and customer content stay out of logs, telemetry, fixtures,
    prompts to hosted models (unless the binding's data policy allows it) and exported bundles.

---

## 4. Architecture rules

- Modular monolith in Python; the sandboxed runner, the model server and the desktop shell are separate
  processes. No broker, workflow engine, feature store or agent framework.
- Layout: `src/dsp/{contracts,domain,application,ports,adapters,interfaces,harness}`, `src/dsp_runner` (the
  entry point that runs inside the sandbox), `src/dsp_service` (the exported inference core), `desktop/`
  (Tauri shell and renderer), `fixtures/` (deterministic generators),
  `tests/{unit,contract,integration,e2e,sat}`, `tools/`.
- Import boundaries, enforced by `tools/check_boundaries.py`: `contracts` and `domain` import nothing from the
  project's outer layers; `application` depends on `ports`, never on `adapters`; `dsp_service` never imports
  `dsp.harness` or any assistant module; `dsp_runner` imports only `dsp.contracts`; `subprocess` appears only
  in adapters and the harness.
- **OS-specific code lives only in adapters** (sandbox, discovery, secret store, desktop shell). Everything
  else is identical on macOS and Linux.
- JSON Schema files in `src/dsp/contracts/schemas/` are the external contracts (draft 2020-12, unknown
  fields rejected). Objects are plain dicts validated against them; add a typed model only where code needs
  one. `../examples/` are conformance fixtures.
- SQLite ledger with a single writer; per-aggregate sequence with expected-version compare-and-swap; state
  change and outbox event commit in one transaction; consumers deduplicate by event ID.
- Content-addressed artifact store: write to attempt-scoped staging, hash, then record the reference and the
  terminal result under the current fence in one transaction.
- Inject clocks, IDs and the random generator. Domain code reads no global time or randomness.
- A new production dependency needs a line in `docs/dependencies.md` (why, licence, alternative) and an exact
  `==` pin in the lock.

---

## 5. Work loop

1. Claim one prompt or task ID in `STATUS.md`.
2. State the observable behaviour that will exist when it is done.
3. Write the failing test first where practical (`tdd-python` skill).
4. Implement the smallest vertical change through the real application boundary.
5. Run the narrow tests, then `make test-fast`, then lint and types.
6. Review the diff against §3 and §12.
7. Update `STATUS.md`, `docs/decisions.md` and `CHANGELOG.md` when behaviour, contracts or assumptions
   changed.

One prompt, one concern. Do not bleed work across prompt boundaries.

---

## 6. Testing

**Single gate:** `make verify` = format check, lint, strict types, import boundaries, unit + contract +
integration tests with coverage ≥ 85%; any skipped or xfailed test fails the run. `make verify-linux` runs the same gate
in a Linux container. CI runs it on `ubuntu-24.04` and macOS for every push.

**Inner loop:** `make test-fast` (skips `slow`, `sandbox`, `live_model`, `desktop`). Run the full gate at
prompt close-out and sprint exit, not on every edit.

**Real execution over mocks.** Tests run real DuckDB, real model fits, the real sandbox and the real local
model. Mock only what cannot run offline, and shape every fixture after the real thing.

| Marker | Meaning | In the sprint gate |
|---|---|---|
| (none) | Offline, deterministic, fast | Always |
| `slow` | More than two seconds | Yes |
| `sandbox` | Needs the OS sandbox | Yes, on both OSes |
| `live_model` | Needs the local open model | Yes locally; in CI only where the model is cached |
| `remote_model` | Needs a hosted or proprietary model key | Only after the owner supplies the key |
| `desktop` | Needs the built desktop app | Yes from Sprint 2 |
| `network` | Touches the public network | Never in the gate; opt-in target |

Rules:

- The default suite is network-free and proves it (sockets disabled).
- Open models are the test target first. A hosted or proprietary binding is tested only after the local open
  path passes, and its results are recorded separately.
- Every feature lands with tests for the simple case **and** the edge and failure cases (empty input, corrupt
  file, duplicate key, stale revision, crash mid-commit, permission denied).
- One behaviour per test; the docstring starts with the suite ID it covers (`A28:`, `D20:`, `R17:`).
- Statistical tests state the tolerance and the sample size that justifies it.
- Same seed, same bytes: a seeded run reproduces identical metrics.
- Never delete, skip or weaken a test to get green; never loosen a threshold; no `# type: ignore` or `# noqa`
  to pass. If a test is wrong, fix it and log a DEFECT.
- **Sprint acceptance tests** live in `tests/sat/test_sprint_NN.py`. Each sprint's gate reruns every earlier
  sprint's file. An acceptance scenario (`A##`) writes an evidence record to `docs/evidence/` with fixture
  version, environment, expected and actual result.
- Three honest attempts at a failing check, then HALT with a diagnosis. Do not loop.

---

## 7. Definition of done

**Per prompt:** implemented additively; tests added; `make test-fast`, lint and types green; behaviour shown
by a command, test or artifact; diff minimal and reviewed; `STATUS.md` updated.

**Per sprint:** `make verify` green on macOS and `make verify-linux` green (or the Linux gap logged as an open
DEFECT with its reason); all sprint acceptance tests green; what shipped has been run for real on each OS and
the output recorded; the exit checklist in `sprint-workflow` applied (and `integrity-reviewer` findings
addressed on boundary sprints); evidence records written; every gate outcome stated as PASS, FAIL or INSUFFICIENT_EVIDENCE; `STATUS.md` carries a handoff note;
commits made.

Files existing is not done. Evidence that needs something the agent cannot supply (owner sign-off, an
independent recipient, real customer data, a qualified hardware profile) is INSUFFICIENT_EVIDENCE.

---

## 8. Stop list

Proceed autonomously for scaffolding, coding, testing, locked package installs from PyPI, npm and crates.io,
and commits on the sprint branch. **Stop and ask only when:**

1. A credential, API key, external account, payment or paid compute is needed. Ask for keys **before**
   writing the tests that need them.
2. A download outside the lock files is needed: toolchain installers, the model file, a guest or base image.
3. A git push, pull request, publication or anything else outward-facing is about to happen for the first
   time, or outside what the owner already approved.
4. An owner decision is required: data rights, evaluation thresholds, spend, release approval, licence choice.
5. A claim or statistic cannot be verified from a real source or a real run.
6. Two sources conflict with no tiebreak, or the task needs a large rewrite or deletion of working code.
7. A check still fails after three honest fixes.

Before halting, try the failure ladder: make a defensible choice within conventions and log it; if that is
unsafe, skip the unclear sub-task, log it and continue with unblocked work; HALT only when neither is safe.

Format:

```
HALT — input needed: <one line>
Context: <what was being done>
Tried: <what was attempted>
Blocker: <the precise thing in the way>
Decision needed: <the smallest choice the owner must make; options A/B with trade-offs>
Default if told to proceed: <recommended option>
```

Planned checkpoints (for example freezing an evaluation contract or choosing a model) present a table of real
numbers from a real run, lettered options and a recommended default, then wait. Never invent the owner's
answer.

---

## 9. House conventions

- **Python 3.12**, uv, `src` layout, exact `==` pins, `uv.lock` committed. ruff (line length 100, Google
  docstrings), `mypy --strict` on `src` and `tools`, pytest with `--strict-markers`.
- Type hints and a docstring on every public function; `logging`, never `print`; pydantic models for config
  and contracts; typer for the CLI.
- **TypeScript strict** in `desktop/`; no `any` without a justifying comment; pnpm; Vitest and Playwright.
- One seeded `numpy.random.Generator` threaded from configuration; no module-level randomness.
- Notebooks and HTML reports are **generated from committed run artifacts** by package code; never hand-edit
  a notebook. Every number in a report comes from a computed artifact, never from model prose.
- Money is integer minor units plus an ISO currency; times are UTC RFC 3339; durations are seconds; memory is
  GiB.
- String identifiers keep their exact text (leading zeros preserved) and are never predictors by default.
- Secrets: OS secret store through the secret port; never in code, logs, fixtures, bundles, renderer code or
  job payloads. `.env.example` documents names only.
- Commits: Conventional Commits with a sprint prefix, one logical change each: `[s3] feat(jobs): fence stale
  result commits`. Close a sprint with `[sN] chore: sprint N complete`.
- When the owner must run something, paste the full command inline in a fenced block. When pointing into a
  third-party dashboard, name what to find and offer the click path as approximate.
- No licence headers or `LICENSE` file until the owner ratifies the licence (open decision O05/ADR08).

---

## 10. Documentation upkeep

- `STATUS.md`: current sprint, claimed prompt, what is done, gate outcomes, open defects, and a **handoff
  note** a fresh session can resume from.
- `docs/decisions.md`: one dated line per entry, at the time it happens —
  `- **YYYY-MM-DD — S<N> — KIND — topic** — what and why; alternatives.` KIND is DECISION, ASSUMPTION,
  DEVIATION (from the suite or a pin), DEFECT or FINDING (out-of-scope concern noted, not fixed).
- `CHANGELOG.md`: user-visible changes per sprint.
- `README.md`: only commands that exist and have been run.
- After any feature, search the docs for sentences the feature made false, not only the files you edited.
- At about half the context window, write the handoff note and suggest a fresh session.

---

## 11. Reviews and token economy

The owner wants ruthless token efficiency. An agent run must earn its cost.

- **Default: do it inline.** Run the gate, the ID trace (`tools/trace_ids.py`, a script, zero tokens) and the
  docs checklist in the `sprint-workflow` skill yourself. Do not spawn an agent for work a command or a
  direct read can do.
- **One reviewer subagent, used sparingly:** `integrity-reviewer`, once at the exit of a sprint that changes
  a security or integrity boundary (Sprints 3, 4, 5, 9, 10), on the diff only. Its value is a read that is
  not anchored on yours.
- **One adversarial audit**, at the M1 gate (Sprint 11), and otherwise only when the owner asks. State the
  expected cost before launching any multi-agent run.
- No agent panels to design something the owner will review anyway: write it, then let the owner object.
- Read only the suite sections a prompt cites; do not re-read whole documents each sprint.
- A request to "write a prompt" or "draft a plan" is satisfied by the prompt or plan. Do not execute it
  unbidden.

---

## 12. Code review rules

Flag these even when tests pass:

- Any path from model, document or dataset text to tool execution, approval, grant, spend or file write
  without typed validation and trusted authority.
- Any process start that takes a shell string, or any code execution outside the sandboxed runner.
- Any way for optimiser, assistant or candidate code to read sealed data, including through logs, errors,
  previews or report links.
- Any transform fitted on data outside the training partition, or a split applied after learned preparation.
- Any policy, state transition or default implemented in one interface instead of the shared service.
- Any result, export or release committed without a fence check, a hash check or a receipt.
- Any state shown as complete, cancelled, exported or passed without the durable evidence behind it.
- Any number in a report, notebook or status message that does not come from a committed artifact.
- Any silent substitution: model, provider, parser, sample instead of full data, dropped rows, truncated
  input.
- Any join that can multiply rows, lose unmatched keys or use information not available at prediction time,
  without an explicit check.
- Any secret, raw customer row or host path in a log, event, fixture, bundle or error message.
- Any OS-specific branch outside an adapter, and any behaviour tested on one OS only.
- Any canonical object updated in place instead of creating a new revision and audit event.

---

## 13. Skill routing

| Work | Skill (`.claude/skills/<name>/SKILL.md`) |
|---|---|
| Starting, running or closing a sprint; evidence records; handoff | `sprint-workflow` |
| Any Python code or test | `tdd-python` |
| A JSON Schema, canonical object, error code or API shape | `contract-change` |
| Ledger, outbox, jobs, leases, fences, reservations, artifact commits | `ledger-and-jobs` |
| Messages, fast controls, revisions, event replay | `conversation-control` |
| The runner, CodeTasks, sandbox profiles, containment tests | `sandboxed-runner` |
| Model gateway, model bindings, tool loop, assistant evaluation | `assistant-gateway` |
| Ingestion, data products, collections, joins | `data-products-and-joins` |
| Splits, baselines, fitting, sealed evaluation, reports | `evaluation-integrity` |
| Analysis packs, service bundles, HTTP/MCP, signing, filesystem export | `release-and-export` |
| Desktop shell, renderer, stage rail, accessibility | `desktop-workspace-ui` |

Skills for later milestones (grounded text, compute bindings, team coordination, weight training, agent
simulation) are written by the first prompt of the sprint that needs them.
