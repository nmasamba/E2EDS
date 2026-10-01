# Execution and serving through qualified provider adapters

Planning edition **0.7.0** · 29 September 2026. Architecture and delivery proposals are unimplemented; upstream facts retain their own verification dates. No compute is provisioned or purchased by this plan.

Execution is selected through a ComputeBinding and authorised ExecutionRequest. D01–D21 govern resource/budget defaults. The customer can attach resources or delegate their lifecycle; serving remains separately qualified. Nothing in this document claims an implemented connector or operational SLA.

## Adapter boundaries and workload families

A workload-family adapter implements learning/task semantics. A compute executor supplies a compatible process, notebook, batch job or bounded function. An optional provisioner owns resource acquisition/release. A serving adapter installs the approved application release. Preparation adapters are a fifth responsibility with source/quality contracts. These are distinct responsibilities; no universal training method or generic container declaration proves all of them.

| Boundary | Inputs | Required result |
|---|---|---|
| Family adapter | WorkloadSpec, permitted data, frozen search/evaluation references | Parameters/configuration/episodes, checkpoints and artifact manifest |
| Compute executor | Admitted ExecutionRequest and scoped identity/grant | Observed runtime, attempt progress, bounded completion/cancellation and durable outputs |
| Provisioner | Delegated account authority and resource reservation | Owned native resource IDs, reconciled lifecycle and charge exposure |
| Serving adapter | Approved ReleaseManifest + DeploymentBinding + qualified profile | Authenticated HTTP/MCP operations and declared operating evidence |

The reference SDK resolves these boundaries from M1, even when all initial processes run on one customer machine. Detailed infrastructure methods are in compute_backends.md. Unsupported family, operation, runtime, region, duration or checkpoint semantics fail admission; an optimiser cannot bypass this with shell text.

An adapter advertises `family`, tasks, input modalities, hardware profiles, adaptation targets, checkpoint/resume support, cancellation granularity, output artifact roles and reproducibility level. The common lifecycle invokes prepare, validate, execute, checkpoint, cancel and collect; method names describe a contract, not an implemented universal trainer. Unsupported capabilities fail before resource reservation where possible.

| Adapter / planned stage | Preparation and validation | Execution / what changes | Checkpoint / cancel | Collection and failure semantics |
|---|---|---|---|---|
| Preparation / M1 | Validate file bytes/magic, format, rights, declared schema/limits; immutable raw capture | Parse/normalise/join into gold tables plus linked assets; quality/quarantine ledger | File/partition boundary; never publish half a product as complete; bounded local termination | DataProductManifest, code/parser versions, source-to-row/span lineage, rejected counts; ambiguous types/keys require decision |
| Data analysis / M1 | Typed question, gold refs, method/denominator and material-claim checks; no fictitious labels | Bounded Python/SQL/notebooks, zero optimisation trials, actual tables/plots | Stage artifact boundary; restart incomplete query under same immutable inputs | Reproduced findings and AnalysisReleaseManifest; invalid join/claim fails, missing evidence is inconclusive |
| Classical classification / M1 | Validate label/schema/rights and group split; train-only TF-IDF; fixed baseline; finite Optuna domain | Fit preprocessing, classifier and permitted calibration; at most 12 configurations | Trial-boundary checkpoints. No promise of mid-fit resume for nonincremental estimators. Kill fit process after grace; partial estimator unusable. | Fitted pipeline, full trial ledger, notebook and environment. OOM/schema failures diagnosed; only transient infrastructure failures retry. |
| Tabular regression / M1 | Target units, prediction-time availability, group/time split, constant/conventional baseline and permitted feature set | sklearn Pipeline with Ridge candidate, train-only transforms; ≤12 trials under D01 | Trial boundary/restart; no mid-fit resume guarantee | MAE/RMSE/bias and slices in target units, raw versus released-rounding effect; missing labels cannot pass |
| Forecasting/clustering / later | Horizon/temporal or unsupervised usefulness contract | Adapter-specific methods; no universal accuracy | Capability-specific checkpoint declaration | New oracle/profile evidence required |
| Generative application / M1B foundation, M3 extension | Validate provider/model revisions, prompt variables, corpus ACL, retrieval recipe, judge independence, token caps | Compare model choice, prompt, context/retrieval/routing; **no weight updates** | Completed case/trial ledger; resume only remaining calls. Cancel stops new calls; in-flight provider call may still cost. | Changed configuration artifacts, call accounting and citations. Unpinnable provider revisions lower replay guarantee. |
| Generative weight training / M4 | Base revision/licence/tokenizer; examples and split; trainable modules; memory estimate; evaluate baseline first | SFT using PEFT LoRA; record trainable count, optimiser and schedule; frozen base + learned adapter | Atomic trainer state: adapter, optimiser, scheduler, RNG, dataloader progress and shard/version info where supported. Cancel checkpoint at safe step then terminate. | Adapter/weights and hashes, actual gradient-step evidence, losses, task evaluation and licence graph. Resume from valid checkpoint only; changed world size may be unsupported. |
| Agent evaluation/configuration / M4 | Resettable environment, obs/action schemas, tool permissions, independent terminal-state oracle, reward provenance | Episodes; search bounded prompt/workflow/policy configuration; no weight update implied | Episode boundary state + action ledger. Restore simulator snapshot for retry; do not replay real side effects. | Trajectories, terminal-state proof, success/violations/recovery/escalation metrics. Reward and true success reported separately. |
| Agent trajectory SFT / later M4 extension | Approved trajectories, independent held-out tasks, rights and weight-training adapter | Supervised parameter updates from selected trajectories | Weight-training semantics; environment version included | Evaluate against original task oracle and simulator-gap tests. |
| Preference optimisation / RL / deferred | Independent preference/reward provenance and necessity evidence; explicit safety/exploration review | DPO or RL only under a separately approved adapter contract | Algorithm/environment-specific; no generic support claim | Not in initial product claims; reward hacking and real-world transfer gates mandatory. |

TRL/PEFT capabilities are upstream facts [S07–S09], not evidence that these adapters work. Large-scale pretraining and unconstrained real-world RL are outside scope.

## Hardware-aware admission and visible work

Early deterministic discovery precedes assistant loading; fresh effective-capacity and runtime checks precede dispatch/resume. [hardware_discovery_and_planning.md](hardware_discovery_and_planning.md) defines HardwareSnapshot, WorkflowPlan, D19 limits and unknown/failure handling. The plan recommends placement without granting authority. Reserve assistant, VM and workload resources by physical domain; a guest allocation is not extra host memory. Capacity pressure stops/replans under existing bounded controls rather than switching provider or weakening evaluation.

The GUI in [gui_workflow.md](gui_workflow.md) projects committed events into stages, activity, artifacts and reports. Stage completion, job termination, evaluation outcome, resource cleanup and financial closure remain different facts. HTTP/MCP operations use the same permission and evidence filters. Installed serving does not need the discovery planner or GUI on its inference path.

## Runners, durable jobs and provider lifecycle

**Common runner and M1 local profile:** required local conversation and CLI/SDK, SQLite event/job/resource ledger and local CAS. A supervised llama.cpp process handles assistant inference; generated Python/SQL runs in a restricted customer-controlled VM through CodeTask and ExecutionRequest. The coordinator remains responsive to controls. Discover CPU/ISA/RAM/disk/OS/virtualisation against D16 before dispatch; D01/D21 limit the workload; D20 caps parser inputs. No malicious local-owner sealing or universal hardware guarantee. One trial and one generation at a time; share host resources by explicit reservations. See [local_model_runtime.md](local_model_runtime.md).

**Attached/delegated runner (M1R; collaborative fleet in M2):** outbound connection/polling with workload identity; signed jobs contain exact adapter/image/code/artifact digests, approved input references, expiry, scopes, profile and spend subgrant. Resolve secrets inside customer environment; no broad cloud account credentials in jobs. Separate optimiser and evaluator identities. Pin allowlisted egress and registry domains; validation rejects arbitrary shell text even if produced by an LLM.

**Managed runner:** curated free demos execute a fixed signed recipe with bounded inputs. Customer code/packages/model loaders require per-job or per-tenant dedicated VM isolation, narrow credentials, network policy and clean teardown. CPU containers inside a VM help resource control but are not the sole tenant boundary. GPU work uses a dedicated VM/node with exclusive allocation in the initial qualified profile; MIG/device partitioning and a scheduler are not independently assumed to prevent malicious cross-tenant access. Hypervisor/device/driver vulnerabilities remain a residual risk; highly sensitive workloads may require dedicated physical hardware/customer operation.

Colab is user-launched interactive execution with persistent export; it never joins an unattended account pool. ZeroGPU accepts only the curated demo operation after its separate profile gate. Both may lose execution or observation; report known state and preserve committed evidence.

Use a relational queue with atomic claim, lease expiry and monotonically increasing fencing token. PostgreSQL may claim eligible jobs with row locking; SQLite uses a single coordinator/writer. Enforce worker capabilities and per-project concurrency before lease issuance. Do not give workers direct authority to update lifecycle or budget totals. A worker can report heartbeat/progress; the coordinator checks attempt/fence and commits.

Retries: initial attempt plus at most two transient retries (D03), exponential backoff with jitter, all bounded by original grant and deadline. Data/contract failures and model evaluation FAIL do not retry automatically. Log retry attribution: infrastructure fault, provider fault, invalid workload or caller cancellation. Billing policy is separate from incurred cost: do not charge the customer twice for an internal duplicate request; platform-caused waste can be absorbed while still recorded.

Before a retry after an ambiguous provider/tool response, query its durable request/action ID if possible. If it offers no idempotency or reconciliation, suspend that action as inconclusive and require operator resolution. At-least-once delivery plus a database unique key prevents duplicate **result commits**, not all external side effects.

### Conversation control and requirement changes

All adapters declare pause granularity, drain/checkpoint capability and whether resume restarts the current trial. Pause stops new dispatch, advances a fence, drains at a safe boundary or terminates controlled local work after D18's grace, and reaches `paused` only on evidence. Resume checks the current requirement revision and remaining grant; cancel is terminal once reconciled. Unknown remote work/cost remains pending. New text creates a versioned diff and invalidates affected results, never overwrites a running WorkloadSpec. Generated tool actions include an expected requirement revision and dispatch fence; stale suggestions cannot execute.

[conversational_control.md](conversational_control.md) specifies HTTP messages/SSE, MCP polling/control parity, deduplication, ambiguous language and command receipts. A GUI connection loss does not cancel durable work. Finishing a model call is not authority to dispatch its tool after a user's pause. A code-generated metric does not bypass the independent evaluator.

### Disconnected operation

Installed inference uses local identity/policy and signed release bytes. Customer runners may finish only preauthorised jobs within a signed offline subgrant and policy expiry. Reserve the full offline envelope centrally until reconciliation; do not reissue its money/resources to another runner during disconnection. Proposed offline job policy validity is 24 hours; longer periods require FIN/SEC approval and device-bound anti-replay controls. A non-exportable worker identity or operator process reduces copied-grant risk; fully adversarial hosts cannot be trusted to meter themselves.

Queue signed sequenced receipts locally, bound disk usage, reconnect using idempotent upload and reconcile duplicate/out-of-order receipts. If expiry is reached, stop new jobs/paid calls and checkpoint according to policy. Permanently disconnected enterprise installations use a customer-owned ledger and pre-agreed deployment/support licence, not an indefinitely renewable online token. Training grant expiry does not disable an unrelated perpetual local inference licence.

Provisioner `ensure_resources` and execution `submit` each require stable request identity, durable provider mapping and reconciliation before retry. An adapter may implement both through a single vendor API without merging their permissions. Only platform-created resources tagged with a trusted tenant/run lease may be auto-released; attached hosts are preserved. D15 defines initial observation/idle targets, not guaranteed provider deletion. Retained disks, reservations and storage require explicit owner policy and cost records.

Runpod Pod execution is not a nested Docker host: build/scan images outside the job, then request the image as the provider workload. Customer-operated single-tenant code can run under its accepted provider trust model. Arbitrary multi-tenant managed code remains subject to the dedicated isolation requirement and cannot enter a new provider merely because its template starts successfully. Colab is manually launched and never placed behind an unattended pool of accounts. ZeroGPU has a bounded serving adapter, not the generic job-consumer loop.

## Budgets, payer attribution and reconciliation

Admission must atomically reserve against tenant/project/workload caps and global capacity. Split a grant into bounded worker/provider reservations so concurrent trials cannot each spend the full budget. Account for training CPU/GPU, serving calls, embeddings, judge calls, agent steps/tools, failed/pruned/retried trials, image/startup time, storage, egress and retained logs. Support is a commercial cost, not a training token counter.

Example policy, not approval: for a £100 external-spend cap, initially reserve £80 for estimated work and retain £20 uncertainty headroom. Before each tranche, recompute committed + unsettled maximum + next reservation; admit only if ≤£100. Headroom is a proposed 20% default pending FIN measurement, not a guarantee against uncapped provider charges. Strong bounds require provider-side caps, per-call token/tool limits, local proxy enforcement and dedicated credentials; some late fees/currency changes remain uncertain. Reject or require a larger explicitly approved envelope when the provider cannot bound exposure sufficiently.

Reserve known maximum response tokens and agent steps before calls. Cancel stops new spending; it may not terminate already accepted provider work. Do not release unsettled reservation simply because the worker died. Reconcile provider receipts/billing exports; record estimated → observed → invoiced → reconciled states with rate-card version and currency. Hash/deduplicate receipts, retain correction entries and track unreconciled age. Invoice disputes are FIN-owned, not resolved by changing evidence. The default reference workload has external cap **£0** and no paid execution authority. A paid Runpod execution needs a new reviewed cost limit and trusted grant; the same task/data/evaluation contract can be preserved. Customer payment directly to the provider does not remove admission or reconciliation requirements.

For ZeroGPU, independently test identity/quota attribution and prepaid-credit behaviour. When a no-charge call cannot be established and enforced, zero-spend automation is ineligible; a separately disclosed user-operated external demo may remain possible. Do not pool one credential to promise distinct user allowances. Retained disks and provider reservations continue to have a payer after a process stops.

Assistant usage is a separate reservation/metering category: model calls/tokens, local inference wall time, peak memory, code-repair attempts and VM time. External assistant APIs, if explicitly bound later, consume a distinct trusted grant and data-transfer permission; a zero-cost local plan never silently falls back to them. Pause can leave storage or a remote invocation billable; cleanup and late charge reconciliation remain mandatory.

## Release builder and portable inference

Take an approved candidate digest and frozen service contract; build in a clean restricted environment. Resolve and hash-lock dependencies; include or legally reference model/adapter/tokenizer, fitted preprocessing, feature calculations, calibration/postprocessing, prompts, routing/workflow/policy and retrieval/index recipes. Treat wheels, plugins, custom model code and pickle-compatible formats as executable. Prefer safe numeric formats for weights and reviewed `skops`-style loading for the small sklearn pipeline; still inspect allowed types and pin libraries [S05]. No unrestricted loading of uploaded pickle/joblib artifacts in shared services. `trust_remote_code` is disabled by default.

Required package contents: importable inference application core; **runnable `predict.py`** that loads the same full pipeline; wheel/environment lock and optional OCI image; ServiceSpec/OpenAPI/MCP descriptors; schemas; startup/health/resource configuration; installation and binding guide; executed explanatory notebook; EvaluationReport JSON and offline HTML justification; provenance; SBOM; licence/notice inventory; signatures/attestations and rollback/runbook. The actual script and notebook are future M1 deliverables, not implemented in this planning session.

Illustrative future invocation (interface example only):

```text
python predict.py --release ./release --binding ./binding.json --input ./request.json
```

`predict.py` invokes the application core directly, not an author's notebook or hosted control plane. Bound inputs, report structured errors and support a no-network verification mode. Tests compare its outputs to both transports. Packaging an external provider wrapper does not make provider weights exportable or disconnected operation possible.

Sign only after deterministic manifest/digest checks, malware/dependency scanning, rights review and evidence verification. Keep signing authority inaccessible to build jobs. Publish by digest; immutable tags/versions never retarget silently. A signature proves provenance/integrity under a trusted key, not task quality.

The release builder runs in a separately qualified clean build environment. Notebook/serverless convenience must not require privileged container builds or embedded credentials. A Gradio/MCP Space calls the same application operation through an additional thin adapter; it is not assumed to provide the chosen OpenAPI paths, OAuth rules or protocol revisions. Qualify those separately or limit the demo's declared interfaces. Exported customer services retain the primary HTTP/MCP adapters and operate independently of the training provider and our hosted coordination.

Release evidence additionally records the requirement revision and generated-code provenance that produced it. Include feature-role/exclusion rules and any output rounding/postprocessing in the tested pipeline and service semantics. The local development assistant model/template belongs in RunManifest provenance, not the routing release runtime dependency graph. The recipient can use `predict.py`, HTTP and MCP with the assistant and development coordinator stopped. A generative service has its own model binding and must not accidentally inherit the developer assistant.

## HTTP and MCP over one implementation

Use Pydantic models for input/output types and deterministic validation, with FastAPI for HTTP and the official MCP Python SDK for tools. Export JSON Schema and OpenAPI; manually review semantic descriptions and examples. Proposed OpenAPI compatibility target is **3.1.0**, despite current upstream OpenAPI 3.2.1 [S14]: upgrade only after client/codegen support tests. No proprietary wrapper framework is required.

| Business operation | HTTP | MCP | Semantics |
|---|---|---|---|
| Route one support document — M1 installed service | `POST /v1/route` | `route_document` | Pure recommendation; scope `support:route`; same errors/review flags |
| Submit experiment — coordination service | `POST /v1/jobs` | `submit_workload_job` | Scope `workload:run`; idempotency key; trusted grant required |
| Get job state/result | `GET /v1/jobs/{id}` and `/results` | `get_job`, `get_job_result` | Object authorisation; bounded/paginated result references |
| Control a development job | `POST /v1/jobs/{id}/control` | `control_workload` | `job:pause`, `job:resume` or `job:cancel` by action; persist receipt and return actual state |
| Grounded extraction/draft — M3 | `POST /v1/extract` or `/draft-jobs` | `extract_fields`, `submit_draft_job` | Cited, schema-validated output; no message sending |
| Simulated action proposal — M4 | `POST /v1/simulation-jobs` | `submit_simulation_job` | Resettable simulator only; no real external mutation |

The coordination job tools are not automatically installed on every inference service. Expose only bounded operations in that release's ServiceSpec, with separate endpoint audiences/scopes. Future consequential operations require separate propose/approve/commit operations and one-time action grants. Review tool descriptions as part of release evidence; annotations such as read-only do not enforce permissions.

HTTP requires TLS for remote use, OAuth/OIDC-derived access tokens with issuer/audience/signature/expiry checks and operation/resource authorisation. Local HTTP binds loopback and uses a generated owner-only credential/profile; loopback is not a multi-user security boundary. Local MCP stdio inherits an explicitly configured least-privilege OS/profile identity, never tenant IDs from tool arguments. Non-loopback binding is refused until remote auth policy is configured. Origin/host checks, token-safe redirects and SSRF protection apply.

Payload limits are measured in bytes before parsing and in characters after decoding; reject oversized body with 413, invalid schema with 422, unauthenticated 401, forbidden 403, missing/not-visible 404, conflicting idempotency or exhausted approved budget 409, rate/quota 429 with retry/reset detail, unavailable dependency 503 and elapsed request deadline 504. RFC-style problem details may wrap the shared error body. Retryability depends on operation idempotency and actual effect status, not status code alone.

List pagination defaults 50, max 200, opaque authorised cursors and stable order. Long jobs return 202 plus job ID after durable admission. The M1 desktop conversation requires server-sent progress with durable replay; polling remains the fallback for reconnect/MCP clients. Neither transport is the durable execution record. A disconnected client can reconnect with job ID/idempotency key. HTTP version `/v1` describes business semantics; underlying model/prompt/policy and release IDs are included separately.

### Current MCP facts and planned compatibility

Verified upstream revision **2026-07-28** uses per-request protocol/capability metadata and a stateless core; earlier **2025-11-25** uses initialisation/session semantics [S10]. The official Python SDK **2.2.0** documents both eras, but explicitly lists the Tasks extension as not implemented [S12]. Therefore plan dual-version stdio/Streamable HTTP with SDK-managed framing and **explicit durable job tools**. Do not advertise Tasks, sampling, elicitation or other capabilities unless implemented and tested. Tool input/output schemas are typed; successful results use structured output, and application failures use the appropriate structured tool error without leaking internals [S11].

For remote MCP, implement current OAuth resource discovery, audience-bound tokens and scope enforcement, including issuer validation. Do not pass caller tokens through to arbitrary downstream services. Legacy handshake and modern per-request behaviour get separate tests; semantic operations remain identical. Current transport cancellation can abandon an in-flight response; durable jobs survive that disconnect and require `cancel_job`. For a short pure inference call, cancellation is best effort and may stop work if the backend permits; compute already used still counts. No disconnect proves an external effect did not occur.

Plan compatibility evidence for a pinned official Python client, a separately implemented official TypeScript client and at least one named design-partner host/client revision. No host compatibility is presently tested. MCPB is an optional local installation bundle format [S13], not a replacement for model/hardware compatibility or the release manifest. Public MCP Registry metadata is a later distribution concern.

The platform development API also exposes `send_workload_instruction`, `get_workload_events`, `control_workload` and `get_change_proposal` with the same identity, permissions and semantic errors over HTTP/MCP. These are not installed routing operations. Model-server protocol compatibility is separately qualified and never treated as application HTTP/MCP parity. The desktop renderer uses our coordinator, not a direct unfiltered model endpoint.

## Hardware, provider and serving profiles

A provider profile declares execution mode/operations, while a hardware/software profile declares architecture, memory and dependencies. A release's inference compatibility is a third claim. Keep these identities separate.

| Profile class | Initial declaration | Gate and owner |
|---|---|---|
| V1 workload resources | D01: 4 CPU/8 GiB, no GPU required, bounded trials | Observed executor resources and family preflight; ML/PL |
| V1 installed inference | `cpu-linux-x86_64-py312`; proposed 2 CPU/4 GiB, Linux/native dependency lock | Clean recipient install, HTTP/MCP parity, D04 load; G2/G3 |
| GPU adaptation | `gpu-linux-x86_64-nvidia24`; proposed 24 GiB GPU, 8 CPU/32 GiB host, exact driver/CUDA/runtime unqualified | Actual memory/gradient/checkpoint evidence; M4 G1/G3; no assumed Colab GPU allocation |
| Alternate hardware | ARM64/Windows or other GPU sizes require distinct lock/profile and tolerances | Separate evidence; no universal container compatibility |
| Notebook/demo runtime | Colab lock and ZeroGPU/Gradio lock qualified separately from local and M4 pins | Resource/dependency/API tests; M1C/M3Z |

Provider priority and capability matrix are authoritative in [compute_backends.md](compute_backends.md#capability-profiles-and-qualification). The initial bindings are local-attached, Colab-interactive and Runpod attached/provisioned. HF Jobs follows; ZeroGPU is optional curated serving. AWS/Azure/CoreWeave are partner-led. Anaconda-compatible packaging is environment tooling, not a hosting backend; channel terms need review [S26]. Snowflake/Databricks may need a separate HTTP/MCP gateway rather than assuming model-serving APIs implement ServiceSpec [S24/S25]. Disconnected installations require preloaded permitted dependencies, local identity and signed update procedures.

Every supported profile needs a test report. Training success on Runpod does not qualify Runpod Serverless, a Space, a warehouse endpoint or another architecture for serving. A changed dependency/hardware/provider configuration requires the relevant regression and compatibility gate. Normal installed inference goes directly to the release runtime; the training provider and coordination service are absent from that path.

## Operations, failure ownership and SLOs

The control-plane availability target applies to our coordination service; it does not make Colab, ZeroGPU or a customer account meet a managed-compute SLO. Report admission, provider queue delay, image/model startup, execution, export and resource cleanup separately. Provider rejection and quota exhaustion are visible outcomes. Never describe an ambiguous provider status as stopped or free of charge.

| SLI / target | Measurement and rationale | Owner / evidence |
|---|---|---|
| Admission p95 ≤2 s | Eligible validated submissions durably accepted/rejected under ≤10 concurrent submits; excludes transfer time but reports validation rejection | PL; load and DB contention test G3 |
| Job infrastructure completion ≥99% | Eligible reference jobs reach honest terminal state within workload deadline + recovery allowance; task-evaluation FAIL is not infrastructure failure | PL; ≥100 fault-injected/reference jobs initially; pilot month before contractual use |
| Managed Team availability 99.5% monthly | Valid authorised in-limit requests receiving correct protocol responses within service deadline / all such requests; dependency failures included unless contract explicitly excludes them | SO; 30-day evidence; ≈216 minutes error budget for 30-day month |
| Warm routing p95 ≤300 ms | D04 load/profile, 20k-character boundary tested, no external model; also report p50/p99/error rate | SO/ML; measured acceptance G3 |
| Explicit pause/cancel durably accepted p95 ≤2 s; controlled local work drained/stopped ≤30 s after notice (D18) | Control response versus actual stop are separate; external calls may be uncancellable | PL; timeout/GPU/provider cases G3 |
| Evidence integrity 100% | Every promoted release has verified hashes, rights, approvals and test references; violation blocks promotion immediately | PUB/EO; no “error budget” for silently missing mandatory evidence |
| Recovery RPO ≤24 h, RTO ≤4 h for hosted coordination pilot | Encrypted daily snapshots; measured restore into clean environment; accepted jobs since snapshot reconciled or identified as lost | PL; tighten before stronger enterprise commitments |
| Installed CPU rollback ≤15 min | Previously qualified release/binding retained; schema compatibility checked; does not undo external effects | SO; clean operator drill G3 |

Free/local has no contractual uptime promise; local operator owns availability. Team starts with business-hours support, proposed one-business-day response, not resolution; emergency coverage is negotiated. Enterprise 24/7 requires staffing, redundancy, dependency contracts and price evidence. Cold start, image pull and scale-to-zero latency are separately reported; do not include them in a “warm” claim then market it as all requests. Reject overload with bounded queues, 429/503 and backoff; never silently drop accepted jobs.

The initial 100-job exercise tests failure paths; by itself it does not statistically establish a 99% population completion rate or a contractual SLO. SO/EO must assess confidence bounds and obtain representative operating history before making that claim. A single-host pilot and a later redundant managed deployment have different availability limits; qualify them separately.

On error-budget burn, pause discretionary deployment, diagnose and reduce load; security fixes can follow an expedited reviewed path. Observe redacted request/error/latency/usage/release metrics with OpenTelemetry; pin semantic convention versions because GenAI conventions evolve [S16]. Backup retention, incident/vulnerability handling and control-plane outage behaviour are detailed in [security_and_assurance.md](security_and_assurance.md).

## Preparation, analysis packaging and monitoring operations

M1 executes restricted SQL/Python loaded from an approved source revision or generated as CodeTask artifacts. Dependency additions require lock/profile review; neither SQL nor parser libraries run with coordinator credentials. Runtime SQL configuration is defence in depth; OS/VM policy enforces paths, network and resource boundaries. Preload approved parser/OCR artifacts for offline use; no implicit weight download or provider OCR fallback. Parser crash, incomplete extraction, low source coverage, timeout and ambiguous type/join decisions are distinct failures. Outputs commit atomically as a complete declared product or remain quarantined.

Analysis packaging includes the gold manifest and included/reference assets, preparation/analysis source, lock, runnable reproduction instructions, executed notebook, report JSON/HTML, rights, software inventory and hashes/signature policy. It excludes a fabricated ServiceSpec/model. Data may remain customer-side: the pack must declare access requirements and limitations of recipient reproduction. A service package still includes the entire evaluated inference path. Convert an analysis into a callable service only through a new ServiceSpec, operational evaluation and G2/G3.

| Bounded coordinator operation | HTTP proposal | MCP tool | Authority and behaviour |
|---|---|---|---|
| Prepare/inspect data | POST /v1/data-jobs | prepare_data | data:prepare; exact permitted snapshot refs/quality contract; durable job |
| Analyse a data product | POST /v1/analysis-jobs | analyse_data | analysis:run; typed WorkloadSpec/method/output refs; no arbitrary SQL passed as privileged tool arguments |
| Read output/version history | GET /v1/outputs/{id}; GET /v1/outputs/{id}/versions | get_output; list_output_versions | output:read; tenant/asset ACL and cursor limits; authorised summaries only |
| Check output | POST /v1/outputs/{id}/checks | check_output | monitoring:run; immutable MonitoringSpec, resource grant and target; durable job |

Long operations use existing status/results/pause/cancel semantics, D05/D06, same policy core, pagination and HTTP/MCP error mapping. Upload bytes use separate bounded transfer under D20; the job API is not a file dump. The minimal business tool set exposes task operations, not every filesystem/query helper. A returned job ID is not a completed analysis. M1 manually initiated checks can run customer-side; M2 optional schedules use the ledger with leases/fences and explicit daily/monthly cost bounds. Pausing a schedule stops new jobs; stopping an in-flight check follows normal cancellation semantics. No automatic monitor-driven promotion.

## Expanded task execution and filesystem release channel

Preparation resolves immutable collection members, validates the JoinPlan and reserves output/spill before materialisation. Discovery/materialisation can checkpoint at completed source/stage boundaries; partial gold is labelled incomplete and never accepted from a killed query. A lost commit acknowledgement is reconciled by logical materialisation key and fence; a retry may repeat computation/cost but cannot publish two logical outputs. Large projects are paged, not an unbounded all-pairs job. Runtime joins remain restricted SQL/code, not metadata-side execution.

Library-assisted CodeTasks reference TaskCapabilitySpec, exact docs/source diff/dependencies and three distinct environment profiles. Existing family lifecycle and cancellation semantics apply to E1–E6. A recipe without safe checkpointing declares restart-only; a fit-only/transductive analysis declares no unseen-row serving operation. Additional dependencies go through the reviewed builder and egress broker; no model-generated pip/shell action escapes the VM.

OutputBinding and an export broker are the filesystem counterpart of DeploymentBinding. Both are mutable environment-specific bindings; immutable release content remains the same. Stage, hash-check and commit a new version directory with an ExportReceipt; disk-full/cancel/path-race errors cannot corrupt prior output. A service bundle includes its Python/HTTP/MCP interfaces even if no server is started. Analysis bundles need no endpoint. HTTP/MCP/CLI use the same export policy and opaque destination handle; remote callers cannot supply arbitrary host paths. Normal installed inference remains independent of GUI, assistant, development harness and hosted coordination. See [desktop_experience.md](desktop_experience.md).
