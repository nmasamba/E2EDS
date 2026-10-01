---
name: sandboxed-runner
description: How generated or imported Python/SQL is executed in DS Playground — the runner port, CodeTask, the native OS sandbox (Seatbelt on macOS, bubblewrap on Linux), limits and the containment tests. Use when touching the runner, sandbox profiles, CodeTask handling or anything that starts a process.
---

# Sandboxed runner

**Owner decision:** native process in an OS sandbox, not a VM (`docs/decisions.md`, 2026-10-01). The suite's
requirements on *what must be denied* still apply: `../local_model_runtime.md` "What the agent writes and
executes", `../security_and_assurance.md` C14 and C18, acceptance scenario A28.

## Shape

- `RunnerPort.run(code_task) -> RunResult`. One adapter per OS; nothing else is OS-specific.
- **CodeTask** records: source digest, parent revision, declared inputs and outputs, dependency lock digest,
  resource caps, required permissions, requirement revision, attempt and fence, outcome.
- The harness starts `python -m dsp_runner <task.json>` from a **locked runner environment** with a fixed
  argument vector. No shell, no string interpolation into a command.
- Result channel: files written to the task's scratch directory, size-capped and validated on ingestion.
  Candidate output is untrusted data.

## Policy (both OSes)

No network. No read of the home directory, keychain, SSH/cloud credentials, the ledger, the content store or
any sealed partition. Read-only: the runner environment, system libraries, the task's declared inputs.
Write: the task scratch directory only. Environment variables scrubbed to an allowlist. Limits: CPU time,
memory, wall clock, open files, output bytes, scratch bytes (D01, D21). Kill on limit; partial output is not a
result.

- **macOS:** `sandbox-exec -f <profile>` with `(deny default)`, explicit `file-read*` for the allowlist,
  `file-write*` for scratch, no `network*`.
- **Linux:** `bwrap --unshare-all --die-with-parent --new-session --clearenv --ro-bind` for the allowlist,
  `--bind` for scratch, `--tmpfs /tmp`, plus a seccomp filter; `prlimit` or cgroups for resources.
- DuckDB inside the task: `enable_external_access=false`, no extension loading, `lock_configuration=true`.
  This is defence in depth, not the boundary.

## Containment tests (A28, `sandbox` marker, both OSes)

Real code in a real task tries each of these and is denied by the OS, with the denial captured as evidence:
read `~/.ssh` or a planted host secret; open a socket and resolve DNS; `pip install`; read a sealed-partition
file; write outside scratch (including via symlink and `..`); modify the ledger file; exceed CPU, memory,
time, output and scratch caps; spawn a process that outlives the task.

## Repair loop

At most two repairs per task within the original budget (D17); every version and traceback is kept. A stale
fence or revision rejects the result.

## Honest labelling

Record `assurance: os_sandbox_single_user` on the binding, run manifest and evidence. Never describe this as VM
isolation or as safe for other people's code on shared infrastructure.

## Pitfalls

Python needs read access to its own environment and system libraries or it will not start; resolve symlinks
before building the allowlist; bubblewrap may be blocked inside a default container, so run Linux sandbox
tests in CI and say so; a static AST check is a diagnostic, never the control.
