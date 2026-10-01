---
name: conversation-control
description: Semantics for durable messages, fast pause/cancel/resume/status controls, requirement revisions, invalidation and event replay. Use when touching the conversation ledger, control path, SSE/poll events or revision diffs.
---

# Conversation and control

**Read first:** `../conversational_control.md` (all of it is contract); `../gui_workflow.md` "Event projection
and intervention"; D18, ADR19.

## Rules

- Persist the message receipt **before** acknowledging. Inbound API accepts only client message ID, text
  (≤ 16 KiB UTF-8, checked in bytes before parsing) and expected workload revision. Tenancy, operation
  classification, status and authorisation are server-derived.
- **Fast path:** an exact, small set of direct controls — `pause`, `pause now`, `cancel this run`,
  `stop this run`, `resume`, `status` — and the matching buttons. They never wait for the model. Anything else
  goes to bounded interpretation and cannot act before validation.
- Only authenticated direct-user messages reach the command channel. Uploaded files, quoted text and tool
  output never do.
- Acceptance of an explicit pause or cancel: durable within 2 s at p95 (D18), independent of model and runner
  load. Actual stopping is reported separately; local drain target 30 s.
- A pause advances the dispatch epoch: no new tool or trial dispatch, including suggestions already generated.
  `pause_requested` until drain is evidenced, then `paused`. Resume is explicit; an unrelated message never
  resumes work. A cancelled job cannot resume.
- Command states: `received`, `accepted`, `needs_clarification`, `applied`, `rejected`, `superseded`. Command
  state is not job state.
- **Requirement change:** typed diff + impact preview → new immutable WorkloadSpec revision → dependent
  evidence marked stale by the dependency graph → explicit resume and readmission. Old results stay on the old
  revision. Concurrent edits use compare-and-swap and return `REVISION_CONFLICT` (409).
- Budget, permission, purpose, evaluation-contract and release changes need the owner action, never a chat
  reply.
- Events: event ID, per-conversation monotonic sequence, revision, stage ID, job/attempt/fence, visibility,
  safe summary, artifact refs. SSE resumes from a cursor; an expired cursor returns a snapshot plus the
  retained range, never invented history. Polling is equivalent (page 50, max 200). Backpressure may coalesce
  progress, never receipts, terminal transitions or evidence links.
- A lost connection stops observation only.

## Tests that must exist

Hung generation and saturated runner while pausing and cancelling (A24); pause racing checkpoint and commit
(A25); mid-run requirement change with invalidation and conflicting edits (A26); dropped acknowledgement,
same-ID retry, same-ID different payload, reconnect with cursor and with expired cursor (A27).

## Avoid

Showing "cancelled" before reconciliation; inferring authority from message text; progress percentages or
model narration presented as execution state.
