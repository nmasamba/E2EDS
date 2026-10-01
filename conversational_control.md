# Continuous conversation, visibility and intervention

Planning edition **0.7.0** · 29 September 2026. Architecture and delivery proposals are unimplemented; upstream facts retain their own verification dates. No compute is provisioned or purchased by this plan.

**Plain language is the primary M1 interface.** A user can describe an outcome, see the interpreted requirements and plan, follow real progress, and send new instructions while work runs. The conversation remains available across stages and reconnects. “Open stream” means a durable, resumable interaction; no design can guarantee a live connection during a device/network outage. CLI/typed API remain secondary automation and recovery paths.

## From language to enforceable intent

The assistant turns text into typed WorkloadSpec fields, each with source message/span, interpretation confidence (nullable), materiality and confirmation status. Confidence describes extraction uncertainty only; no model self-rating becomes a task-success probability. Show a compact plain-language readback plus expandable structured diff. Ask only about ambiguities that would change imminent material work. Routine choices inside the agreed scope proceed automatically; data rights, budgets, changed acceptance and consequential deployment use the existing accountable-owner gates.

| User instruction | Proposed typed interpretation | Validation and consequence |
|---|---|---|
| “Load these CSVs and PDFs and explain what is in them.” | Propose data_preparation/exploratory_analysis with analysis_release output; typed source/format, grain/join and quality contracts | No training assumed. Identify ambiguous keys/units, allowed source access and limits; execute bounded ETL/analysis and show actual provenance/quality. |
| “Keep the feature set minimal.” | Soft objective `minimise_feature_count`, subject to the frozen quality constraints; count source fields or transformed features explicitly | “Minimum” is ambiguous. Ask whether there is a hard maximum and how features are counted. Until resolved, preserve mandatory exclusions and compare complexity/quality on development data; do not invent a quality tolerance or claim the global minimum. |
| “Use account_num as the ID.” | String entity identifier; excluded from predictors and raw telemetry; preserve leading zeros | Check nulls, semantics and cardinality. Repeated accounts can identify an entity but not an individual row: retain a separate row ID. Group-split by account when the intended generalisation requires it. An identifier is not proof of anonymity. |
| “Anonymise regression results by rounding to the nearest 10.” | Proposed deterministic output transform: numeric increment 10 in target units; explicit tie rule; raw prediction excluded from public output/logs | Explain that rounding reduces precision, not necessarily identifiability [S47]. Ask/confirm units, tie handling and the intended privacy requirement. Privacy review may need more controls. Evaluate the released rounded output; keep raw diagnostics restricted. Tabular regression is planned in M1; support routing remains a separate task and neither is implemented by this document. |
| “Pause now; exclude region before continuing.” | First accept an authorised pause; then draft a patch excluding that field | Stop dispatch before model interpretation of the patch; explain affected fits/reports and additional cost. Work remains paused until explicit resume and new revision checks. |
| “Spend another £100.” | Proposed budget change only | FIN-authorised trusted grant is required. A message, model interpretation or user-supplied `approved=true` is not a grant. Unrelated no-cost work can continue if permitted. |

For a rounding illustration, declare nearest multiple of 10, ties away from zero: 124→120, 125→130, −125→−130. Use defined decimal semantics in target units rather than an implicit language default. The public operation returns the rounded value and transformation/version metadata. If account identifiers must be returned for authorised joins, those results remain linkable; a separate anonymised export would require a different contract and reidentification assessment. This is an illustrative contract, not implemented regression or privacy certification.

## What the user sees

[gui_workflow.md](gui_workflow.md) defines the stage rail, activity/artifact canvas, details drawer and persistent composer. [hardware_discovery_and_planning.md](hardware_discovery_and_planning.md) defines the early environment panel and task-aware recommendation. The workspace opens before the assistant; setup, status and explicit controls remain functional while the model loads or fails. Display self-check, independent evaluation and release approval separately.

Keep the message composer and pause/cancel controls usable during generation and tool execution. Display the current stage and requirement revision; completed/running/queued steps; active code-task or trial; admitted compute/provider and data placement; elapsed time, reserved/observed/uncertain cost; checkpoints; proposed changes/approvals; and links to code diffs, notebook cells, plots, report evidence and errors. Show concise reasons for decisions with references to real observations. Do not present invented progress percentages, estimated token confidence or raw internal reasoning as evidence.

Progress events originate in the coordinator/runner, not an LLM's narrative. Mark an assistant claim as a proposal until the associated task/artifact exists. Differentiate `received`, `accepted`, `applied`, `rejected` and `needs_clarification` commands. “Cancel requested; remote worker status unknown; costs may continue” is a valid honest status. “Cancelled” is reserved for reconciled work state. Protect raw data/code/log access by role; visibility does not grant sealed-test access.

## Transport and durable records

Use authenticated HTTP POST for messages/control requests, HTTP SSE for progress, and cursor-based polling as a fallback. SSE avoids a second command transport and supports reconnect; it is not the job store. Persist a message receipt before acknowledging acceptance. Emit events through the relational outbox with conversation ID, event ID, monotonically increasing per-conversation sequence, occurrence/recording timestamps, requirement revision, stage ID, job/attempt/fence, visibility and optional artifact reference. The GUI derives stage states from these authoritative transitions; an assistant narrative cannot mark work completed. At-least-once delivery is deduplicated by event ID. No global ordering across conversations is assumed.

| Business operation | Proposed HTTP / MCP equivalent | Scope and semantics |
|---|---|---|
| Send instruction | `POST /v1/conversations/{id}/messages` / `send_workload_instruction` | `workload:interact`; client message ID + expected WorkloadSpec revision + bounded text. Returns command receipt. No embedded trusted actor/grants. |
| Observe | `GET /v1/conversations/{id}/events?after=…` (SSE or paged JSON) / `get_workload_events` | `workload:read`; same filtered events; default 50/max 200 per JSON page. Token streaming is optional progress, not completion. |
| Pause/resume/cancel | `POST /v1/jobs/{id}/control` / `control_workload` | `job:pause`, `job:resume` or `job:cancel`; command ID + action + expected revision; returns actual state and pending effects. Same policy as language commands. |
| Inspect change | `GET /v1/change-proposals/{id}` / `get_change_proposal` | Authorised diff, impact, evidence invalidation and required decision owners |

These are platform development operations, separate from an installed service's task tools, such as the support reference `route_document`. Do not add control-plane tools to every exported customer inference service. Commands have a proposed 16 KiB text payload limit (D18); file inputs use bounded artifact transfer. Errors include REVISION_CONFLICT (HTTP 409), PAUSE_REQUESTED, PAUSED, REQUIRES_CONFIRMATION and ASSISTANT_UNAVAILABLE alongside existing errors. A denied operation maps to the same permissions/error meaning in HTTP and MCP. MCP clients may poll rather than display SSE; no universal client task feature is assumed.

Keep event IDs and command deduplication records for D06's seven-day retry window after terminal state; payload retention follows DO policy. Return an explicit expired-cursor response with the current state snapshot and retained-history range, never fabricate missing events. A message retry with the same ID and different payload conflicts. A disconnected GUI only stops observation; it does not pause a job. On reconnect, retrieve current state plus missed events before offering a stale resume/change.

## Fast controls and races

The coordinator recognises a small deterministic set of direct user controls such as “pause”, “pause now”, “cancel this run”, “stop this run”, “resume” and “status”; optional buttons invoke the identical command. Other phrasing uses a bounded interpretation task that cannot execute a consequential action before validation. Do not promise arbitrary language is recognised instantly. If ambiguous, acknowledge and ask a short clarification; clear pause/cancel controls remain available even with the assistant unavailable. Uploaded documents, quoted text and tool outputs never enter this command channel.

Proposed D18 target: persist and acknowledge an authorised explicit pause/cancel within 2 seconds at p95 under the declared local test load, independent of model/code activity. This measures command acceptance, not the time to stop a provider. Isolate the control task from long-running work and reserve host resources; test with a hung model/runner. SEC/PL own authority and liveness; PO owns usability. Do not show acknowledgement until durable commit, and report unavailable control service honestly.

An accepted pause advances a dispatch epoch and prevents new trials/tool actions, including already generated but undispatched suggestions. Work moves to `pause_requested` until the adapter has safely stopped and committed any checkpoint, then `paused`. Fences reject stale final result commits. A separately scoped checkpoint receipt for the old attempt may be accepted by the coordinator during draining, solely as evidence for a later authorised resume. It cannot grant completion or promotion. If success committed before pause/cancel in the same serialized ledger order, show the completed state instead; commands cannot erase past work.

| Work type | Meaning of pause | Resume / cancellation limit |
|---|---|---|
| Queued step | No lease/dispatch | Resume checks current requirements, rights, budget and capability |
| Nonincremental classical fit | Stop new trials; finish the current trial if policy permits within 30-second drain, otherwise terminate and discard incomplete estimator | Resume completed trial ledger; interrupted fit restarts within remaining budget. Do not claim mid-fit checkpoint support. |
| Checkpointable trainer | Request safe step checkpoint, then stop worker | Resume only compatible code/data/model/checkpoint revision; provider storage costs may remain |
| Model/API call | Stop new calls; cancel local generation or request provider cancellation | Partial tool JSON cannot execute. Remote invocation may complete or incur cost despite lost connection. |
| External action | Hold subsequent actions; reconcile the current request/action ID | No blind retry or claim that cancel undoes an effect. Only approved compensation; M1 has no real external actions. |

`paused` is not permanent resource suspension: release idle platform-owned remote resources under D15, retaining only authorised checkpoint storage; never destroy attached customer resources. Do not retain scarce GPU allocations indefinitely because chat is open. Unreachable providers remain pending/unknown with a cleanup owner. Cancelling a paused run invalidates resume; a later rerun is a new linked job. Resuming is explicit, never triggered by an unrelated message.

## Changing requirements during a run

1. Persist the instruction and identify its target workload/revision. If the change could invalidate currently dispatching work, hold the affected branch promptly; unrelated status/read work stays available.
2. Produce a typed diff plus impact: inputs, pipeline/code, feature roles, metrics/criteria, cost, data movement, artifacts and approval domains. Preserve the source message. Clarify only material ambiguities.
3. Apply an unambiguous authorised change inside the original scope as a new immutable WorkloadSpec revision; automatic application is recorded. Require the appropriate owner for enlarged budget/permissions, new purposes/providers, changed evaluation contract or production action. A chat response cannot impersonate FIN/DO/EO approval.
4. Invalidate downstream evidence according to the dependency graph, rather than relabel old results. Excluding a fitted feature requires a new fit and evaluation; changing output rounding requires a new full-output evaluation and release, though raw fit may be reusable. A notebook title change does not require retraining. EO decides whether prior final-set exposure requires a new independent cohort.
5. Explicit resume admits eligible remaining work with the new revision, grant, code hashes and fence. Preserve old run/results as superseded audit evidence; do not silently splice them into the new candidate. New changes while a diff is pending use compare-and-swap; return a revision conflict or regenerate the diff for review.

Promotion remains separate: conversation can request a ChangeProposal, but cannot silently replace production. The control stream and assistant model can change only through versioned, reviewed contracts. The optimiser cannot edit its own judge, permissions, budgets, sealed data or logging.

## M1 acceptance evidence

A24–A34 in [delivery_plan.md](delivery_plan.md) cover hung-model controls, pause/checkpoint races, revision invalidation, reconnect/deduplication, generated-code containment, user-constraint enforcement and the assistant's own qualification. Record expected/actual event order, grants, hashes, state, cost exposure and user-visible messages. The canonical example is [conversation_commands.json](examples/conversation_commands.json); all its commands remain planned, with no claimed execution or approval.

## Analysis and output changes

The conversation spans preparation, investigation and output maintenance as well as model development. “Use this existing notebook”, “change the join”, “summarise these PDFs” and “monitor the dataset” propose different task/code/monitoring contracts. Imported code is inspected/versioned before execution under the same restrictions as generated code. A changed join invalidates dependent gold tables, plots, statistics and fits; a narrative typo affects only the report version. Monitoring requests identify target, metric, cadence, access, owner and budget; absent agreement remains manual/inactive. See data_products_and_tasks.md and A35–A38.

## Multi-source instructions and local delivery

“Join accounts on account_num, aggregate items per order, use policy as known at order time, then save the report here” resolves into collection scope, a typed JoinPlan/CodeTask diff and requested filesystem delivery. “Here” is a trusted selected folder handle; prose does not authorise arbitrary paths. Show the proposed grain, key checks, unmatched policy, temporal rule and affected downstream evidence. Ask only unresolved material semantics; confirmed safe joins need no repeated permission. Excluding a source changes the collection/plan revision and invalidates only descendants that depend on it.

“Try clustering using the installed scikit-learn version” may select a qualified recipe or propose an experimental capability. Show docs provenance, code/dependency diff, target profile and oracle gaps before execution. Pause/cancel remains live during docs retrieval, environment preparation, joins and export, with separate actual stopping/commit receipts. CLI commands use the same ledger; native window close/quit choices are specified in [desktop_experience.md](desktop_experience.md), not inferred from network disconnect.
