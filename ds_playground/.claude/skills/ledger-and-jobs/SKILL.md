---
name: ledger-and-jobs
description: Rules and test recipes for the SQLite ledger, outbox, content-addressed store, durable jobs, leases, fences, idempotency, admission and reservations. Use when touching src/dsp/adapters/ledger*, the artifact store, the job coordinator or admission.
---

# Ledger and jobs

**Read first:** `../architecture.md` ("Authoritative state and rebuild paths", "Job state machine", "Request,
execution and recovery flows"); `../requirements_and_decisions.md` D03, D05, D06.

## Ledger

- One writer process owns SQLite. Model and code processes never write it.
- Every object row has `schema_version`, opaque ID, immutable revision and digest.
- Append state changes with a per-aggregate sequence and **expected-version compare-and-swap**. No global
  order is promised.
- The state change and its outbox event commit in **one transaction**. Consumers deduplicate by event ID and
  can rebuild from the ledger.

## Artifact commit protocol

Write to attempt-scoped staging → hash and validate → in one transaction record the artifact references and
the terminal result **under the current fence**. A result is never `succeeded` before artifacts are durable.
Unreferenced staging is garbage-collected after reconciliation.

## Jobs

States: `draft → validated → queued → running → checkpointed`, `pause_requested → paused`,
`cancel_requested → cancelled`, terminal `succeeded | failed | inconclusive | cancelled`. `failed` is an
execution failure, never poor model quality.

- Heartbeat 15 s, lease 60 s, at most 2 automatic retries for transient faults (D03). A retry is a new
  attempt; an operator retry after a terminal state is a new linked job.
- Lease expiry does not prove death: advance the fence, then reconcile.
- Pause and cancel advance the fence first. If success committed first in ledger order, it stands.
- Idempotency key = tenant + operation + canonical payload digest (D05); same key with a different payload is
  `IDEMPOTENCY_CONFLICT`; records kept 7 days after terminal state (D06).
- Admission derives authority from trusted context, re-checks capacity, and reserves resources and spend
  atomically. External charge defaults to zero (D02); a request cannot grant itself money or data.

## Tests that must exist

- Kill the worker before and after commit; retry the same result key → exactly one committed result (A03).
- Expired lease, replacement admitted, old worker returns → old commit rejected (A04).
- Cancel while queued, running and after success; recorded acknowledge and stop times (A07).
- Two admissions race for the last reservation → total never exceeds the cap (A08).
- Crash between staging and commit leaves no `succeeded` job and no dangling reference.

## Avoid

"Exactly once" claims; a JSON blob standing in for a constraint; a projection deciding a transition; workers
updating lifecycle or budget rows directly.
