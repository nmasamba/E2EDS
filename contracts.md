# Canonical contracts for intent, compute and release

Planning edition **0.7.0** · 29 September 2026. Architecture and delivery proposals are unimplemented; upstream facts retain their own verification dates. No compute is provisioned or purchased by this plan.

The development chain is ConversationCommand → typed WorkloadSpec revision + AssistantModelBinding → bounded CodeTask. HardwareSnapshot + WorkloadSpec + selected bindings produce a provisional WorkflowPlan. The common task chain is WorkloadSpec + WorkflowPlan → ExecutionRequest + ComputeBinding → RunManifest → task-appropriate EvaluationReport. Data products and exploratory findings package as AnalysisReleaseManifest; operational capabilities continue through ServiceSpec + ReleaseManifest → DeploymentBinding. MonitoringSpec binds explicit checks to either output. A customer chooses compute within policy; the resulting application has its own serving contract.

## Object identity, authority and evolution

IDs are opaque within an object namespace, never secrets or proof of access. All references resolve within authorised tenant/project context. Revisions are immutable; mutable aggregates point to revisions through audited events. Use RFC 3339 UTC timestamps, seconds for durations, bytes for payload/storage fields, GiB for explicit memory fields and integer minor units plus currency for money. Canonical JSON bytes and SHA-256 identify artifact content; detached signatures cover manifest digest plus signing identity/context. A registry ID alone is insufficient to retrieve data.

`schema_version` is distinct from application API, model, prompt, policy and release versions. Read-only schema fields signal server ownership but do not enforce it by themselves. The actual API must reject/ignore caller-supplied trusted fields and derive tenancy/grants from authenticated context. Unknown fields are rejected in core schemas; additive extensions require a new schema version or an explicitly declared extension namespace.

Published schema 1.x changes are additive only where consumers can tolerate them; changed meaning, units or required fields require a major version. Migrate by reading old+new and writing new, with tested rollback. Do not mutate archived contracts to “bring them up to date”. Export contains the schemas needed to read its version.

## Objects, ownership and lifecycle

| Object | Required semantic contents | Owner / lifecycle / key references |
|---|---|---|
| WorkloadSpec | Purpose/family, adaptation target, typed field/feature/output requirements and their provenance, conversation/assistant references, task/output kind and input modalities, data products/splits, bounded search (zero trials for data_analysis), requested resources/permissions, execution requirements, evaluation and intended serving profiles; no selected training provider/account | ML proposes; PO/DO/EO/FIN approve respective domains. Draft → validated version. References immutable manifests and approved context. |
| DataProductManifest | Raw source/transform refs, named gold tables with grain/keys/columns/units/time, linked assets/coordinates, quality checks and rights/access | DO/DE. Immutable planned/materialised/checked/accepted snapshot; new source/transform creates revision; quarantine and deletion recorded. |
| AnalysisReleaseManifest | Reproducible data/analysis output with code, locks, notebook, HTML/JSON report, input/product/run refs and evidence; no fabricated ServiceSpec | PUB/analysis owner. Immutable output; approval/distribution lifecycle outside manifest. R11/ADR23. |
| MonitoringSpec | Target output/binding revision, owner/operator/payer, metrics/units/baseline, manual/scheduled mode, authority, retention and action | DO/analysis owner/SO. Versioned draft/active/paused/retired; monitor runs use normal jobs. No automatic promotion. |
| DataManifest | Source/version/query, snapshot hashes, owner/purposes/rights, schema/units/time meanings, sensitivity/residency/retention, transformations and parent hashes | DO. Snapshot immutable; deletion/withdrawal through ledger. Dataset identity is not merely a filename. |
| SplitManifest | Dataset ID/hash, explicit membership artifacts, grouping/time rules, train/tune/final ACLs, seed, label-time cutoff, overlap checks and EO freeze | EO. Frozen before optimisation; new splits require new ID/version. |
| EvaluationContract | Task population, metrics/denominators, baselines, oracles/rubrics, slices, uncertainty/comparison policy, thresholds/sample requirements, operating conditions, access budget and owners | EO with DE/PO. Frozen version; optimiser has no write permission. |
| HardwareSnapshot | Scoped environment/domain identity, collector revision, observed/declared/unknown provenance, timestamp, effective limits, probe failures and privacy scope | PL; immutable observation. References a selected binding where applicable. It is neither qualification nor reservation; fixture values cannot prove readiness. |
| WorkflowPlan | Workload/assistant/compute/snapshot references, feasibility ruleset, recommendation and alternatives, resource-domain allocations, limits, evidence gaps and stage completion rules | Coordinator/PL proposes; human owners retain authority. Immutable proposed → stale/superseded/rejected revisions. It cannot authorise execution. |
| RunManifest | Planning and actual admission snapshot references, WorkflowPlan, workload/requirement revision, assistant model/template binding and code-task provenance, code/env/model/provider revisions, parameters/seeds, hardware attestation, attempts/fences, input digests, checkpoint/output refs, usage and termination reason | Coordinator owns lifecycle; worker attests observations. Terminal record immutable; corrections are linked amendments. |
| EvaluationReport | Candidate/contract/protocol digests, results and uncertainty, sample/exclusion counts, failures/slices, cost/load conditions, limitations, outcome and evaluator identity | EO. Immutable report; redacted/public view is a separate artifact. Outcomes PASS / FAIL / INSUFFICIENT_EVIDENCE. |
| ServiceSpec | Business operations, input/output semantics, scopes, sync/async mode, errors, limits, interfaces and provider-independent runtime requirements | Application Lead + SO. Immutable revision; public semantic API version separately maintained. |
| ReleaseManifest | Full inference bundle/dependency graph, interfaces, independently qualified serving profiles, execution provenance, evaluation/rights/approvals/signatures and install entry points | PUB. Immutable packaged identity. Lifecycle lives in external ledger, not mutable manifest fields. |
| ExecutionRequest | Workload and compute-binding revision/digests, operation, data-access scope, logical idempotency key, trusted-context reference and admission state | Coordinator owns; planned → admitted/rejected/withdrawn. Admitted requests create jobs governed by the separate job state machine. Request does not grant money or data access. |
| ComputeBinding | Provider/account and connection mode; capability/region/purpose limits; secret references; qualification evidence; resource ownership, payer/operator and cleanup policy | PL owns aggregate; immutable revisions approved by SEC/DO/FIN as needed. Proposed → qualified → suspended/retired; requalification is audited. Preflight is an evidence step, not another binding state. RunManifest freezes binding revision and observations. |
| DeploymentBinding | Release ID/digest, environment/profile, endpoint/secret refs, storage/corpus/tools/config/policy refs, identity issuer/audience, operator/payer and binding revision | SO. Mutable aggregate with immutable revisions and rollback history. No inline secrets; behaviour-changing fields trigger review. |
| UsageRecord | Tenant/job/attempt/action, quantity/unit/time, rate-card version/currency, reservation, estimated/actual cost, provider receipt, retry cause and reconciliation state | Metering/FIN. Append immutable entries; corrections reference originals. No overwrite of billed history. |
| ChangeProposal | Observation provenance, permitted mutation, rationale, experiment refs/grant, regression contract, approvals, promotion conditions and rollback/compensation | ML proposes; PO/SO plus relevant reviewers decide. Proposed → experimenting → reviewed → approved/rejected → applied/rolled_back. |
| CapabilityListing | Recipe/release/service type, intended use, identity/version, evidence grade, price/rights/support, supported profiles, limitations, deprecation/withdrawal | PUB with claim reviewer. Listing versions mutable by new revision; pinned release never silently retargets. |
| RegulatoryProfile | Intended use, provider/deployer/product roles and locations, markets/output use/affected people, data categories, distribution, dates and applicability assumptions | CL. Reviewed versions; material changes invalidate prior applicability decision. |
| ObligationControlMapping | Obligation/policy citation and effective date, applicability rationale, control, evidence/test, owner, gap/exception/expiry | CL + control owner. Snapshot accompanies release; continuous controls tracked by deployment. |

An ExecutionRequest is a ledger envelope linking a WorkloadSpec revision, ComputeBinding revision, requested operation and idempotency key; trusted grants are attached by admission. An optional compute reference in a DeploymentBinding still requires independent serving qualification. A Job aggregate and Attempt records are implementation ledger objects supporting RunManifest, not competing exported workload semantics. ReleaseApproval and BudgetGrant are trusted audit records referred to by ID. They must not be model-generated fields with self-attested approval.

## Planning schemas and draft migration

Sixteen JSON Schema draft 2020-12 planning contracts are included. Schema versions are independent of object, API and release versions.

| Schema | Draft version | Boundary |
|---|---|---|
| [WorkloadSpec.schema.json](contracts/WorkloadSpec.schema.json) | 0.6.0 | Single source or collection, JoinPlan, task capability, namespaced extension IDs and requested delivery; existing family invariants retained |
| [ComputeBinding.schema.json](contracts/ComputeBinding.schema.json) | 0.5.0 | Explicit prepare/analyse capabilities and profile scopes alongside ML families |
| [ExecutionRequest.schema.json](contracts/ExecutionRequest.schema.json) | 0.5.0 | prepare/analyse operation and permitted_snapshot access; workflow and trusted admission remain required |
| [DataProductManifest.schema.json](contracts/DataProductManifest.schema.json) | 0.6.0 | Typed gold tables, grain/keys/units, source assets, transforms, quality and rights |
| [AnalysisReleaseManifest.schema.json](contracts/AnalysisReleaseManifest.schema.json) | 0.5.0 | Reproducible analysis pack and evidence without service-only fields |
| [MonitoringSpec.schema.json](contracts/MonitoringSpec.schema.json) | 0.5.0 | Manual/scheduled target checks with owner, authority, budget and no auto-promotion |
| [ServiceSpec.schema.json](contracts/ServiceSpec.schema.json) | 0.3.0 | Shared business operation semantics, policy and independent runtime |
| [ReleaseManifest.schema.json](contracts/ReleaseManifest.schema.json) | 0.4.0 | Full operational inference package and evidence |
| [AssistantModelBinding.schema.json](contracts/AssistantModelBinding.schema.json) | 0.3.0 | Local development model/runtime and qualification |
| [ConversationCommand.schema.json](contracts/ConversationCommand.schema.json) | 0.3.0 | Durable instruction, typed diff and control authority |
| [HardwareSnapshot.schema.json](contracts/HardwareSnapshot.schema.json) | 0.4.0 | Scoped observed/declared/unknown capacity |
| [WorkflowPlan.schema.json](contracts/WorkflowPlan.schema.json) | 0.5.0 | Task/output-aware placement and stage meaning; zero-trial analysis; no execution authority |
| [DatasetCollectionManifest.schema.json](contracts/DatasetCollectionManifest.schema.json) | 0.6.0 | Immutable inline or paged source membership and discovery coverage |
| [JoinPlan.schema.json](contracts/JoinPlan.schema.json) | 0.6.0 | Reviewed relationship DAG, grain, keys, temporal rules, checks and materialisation bounds |
| [TaskCapabilitySpec.schema.json](contracts/TaskCapabilitySpec.schema.json) | 0.6.0 | Versioned task/operation/modalities/dependencies/oracle/profile and qualification state |
| [OutputBinding.schema.json](contracts/OutputBinding.schema.json) | 0.6.0 | Scoped local destination and new-version commit; no implicit endpoint startup |

Edition 0.7 adds four draft 0.6.0 schemas and advances WorkloadSpec/DataProductManifest to 0.6.0. The other ten schemas retain their versions. Existing examples update affected object revisions and transitive references; the new collection, join, capability and output-binding objects start at 1.0.0. No old-consumer compatibility or implemented migration is claimed. Future migration must preserve old immutable content and obtain real evidence/authority rather than invent it.

Unknown fields are rejected. `readOnly` describes server ownership but cannot enforce it. Structural validation cannot establish account identity, isolation, rights, actual hardware, price, budget or evaluation validity. Runtime policy rejects unauthorised or unqualified bindings even when JSON validates. Null application hashes and absent evidence are allowed only as explicitly planning data; production conditions require real identities/evidence.

## Retained support reference lifecycle

| Object | Example identity |
|---|---|
| Tenant/project (illustrative trusted seed) | `tenant-demo` / `project-support-demo` |
| Workload | `wl-support-route-v1` |
| Data and split | `data-support-demo-v1` / `split-support-demo-v1` |
| Evaluation contract | `eval-support-route-v1` |
| Run / report | `run-route-example-001` / `report-route-example-001` |
| Service | `svc-support-route` API version `1.0.0` (object revision `1.2.0`) |
| Planned release | `rel-support-route-0.1.0` version `0.1.0` |
| Binding | `binding-support-local-example` |
| Listing | `listing-support-route-example` (private; draft) |

See [workload_spec.json](examples/workload_spec.json), [service_spec.json](examples/service_spec.json), [release_manifest.json](examples/release_manifest.json) and [reference_objects.json](examples/reference_objects.json). The companion object set resolves the referenced data, split, contract, run, report, binding, rights and listing records. All content is fictional planning metadata; no dataset or release bytes are asserted to exist.

The WorkloadSpec requests 12 bounded CPU trials with external-charge limit zero. It does **not** carry an approved grant. The RunManifest is planned, its parameters/results are not asserted, and the report is INSUFFICIENT_EVIDENCE. The ReleaseManifest identifies required future paths including `predict.py`, notebook and HTML report, all with absent hashes and `evidence_status: planned`. Distribution is disallowed in its proposed rights record. This is one internally consistent unexecuted lifecycle, not a fake successful deployment.

Current object revisions are listed in the edition 0.7 register below and their JSON records. They are independent of schema, API and release versions; no application migration has been executed.

## Linked data/analysis example

The project-operations-demo input authority is collection-operations-v1 with six member DataManifests, joined through join-operations-v1 and code-operations-prepare-v1 into gold-operations-v1. The analysis workload consumes that proposed product; run, report and analysis release remain unexecuted. A manual draft monitor and proposed filesystem OutputBinding refer to the output. They share tenant-demo with the support project, which does not imply shared source permissions. The original raw umbrella DataManifest remains historical fixture description.

See [data_analysis_workload.json](examples/data_analysis_workload.json), [data_product_manifest.json](examples/data_product_manifest.json), [analysis_release_manifest.json](examples/analysis_release_manifest.json) and [analysis_reference_objects.json](examples/analysis_reference_objects.json). Workload family data_analysis, task exploratory_analysis, output analysis_release, null split, empty search and zero trials are intentional. This analysis-only sample is not a predictive final set. All artifact paths are proposed; hashes/results/approvals are absent, quality/report outcomes INSUFFICIENT_EVIDENCE. No hardware plan/admission is asserted for the new example. Headless mode illustrates the contract; it does not replace M1's conversational requirement.

Preparation snapshots preserve source provenance; DataProductManifest excludes learned preprocessing before a split. A product accepted for descriptive analysis cannot silently become approved training or sealed-test data. For predictive use, create a new task-purpose/data/split contract and appropriately partitioned products, retaining provenance and exposure history.

## ComputeBinding and ExecutionRequest examples

The main WorkloadSpec explicitly describes provider-neutral execution requirements and retains its zero external-spend cap. Four independent draft bindings illustrate [local](examples/compute_binding.local.json), [Runpod](examples/compute_binding.runpod.json), [Colab](examples/compute_binding.colab.json) and [ZeroGPU](examples/compute_binding.zerogpu.json). Their capabilities are proposed constraints, not discovered resources or completed compatibility tests. The [execution requests](examples/execution_requests.json) reuse `wl-support-route-v1`; a request may be structurally valid and still be inadmissible.

The local request has no approved grant and remains planned. The Runpod comparison request deliberately remains **blocked**: the reference workload's £0 external cap cannot admit rented resources. A later nonzero cost request requires another workload revision and FIN-approved grant, with unchanged task, splits, search and evaluation protocol. The examples do not contain fictional approvals. Colab's declared profile must be confirmed on the actual runtime. The ZeroGPU binding is deliberately ineligible for this classical training request.

Admission checks binding tenant/project, immutable revision/digest, qualification report, operation/family, observed hardware, purpose/region/isolation, full resource cost exposure and approved grant. Unknown region, hardware or spend is not silently accepted for an incompatible requirement. `readOnly` fields are guidance for server ownership, not security enforcement. Binding qualification requires evidence even if JSON Schema accepts a record. Secret references resolve locally; registry account identifiers and URLs are not credentials or approval.

RunManifest records binding revision, provider resource/job/attempt IDs, timestamps, observed runtime and driver, checkpoint/output digests and assurance grade. UsageRecord adds payer/account, rate-card timestamp/currency, quota subject, reservations, unsettled resource charges and cleanup attribution. ReleaseManifest continues to list independently qualified inference profiles rather than copying the training provider as a serving guarantee. The example local RunManifest/DeploymentBinding refer to the local ComputeBinding; no hosted dependence is added.

`profile_scope` distinguishes training/development evaluation, installed serving and curated demo roles. Billing mode and billing-policy references identify who pays without storing credentials or an approved grant in user-editable input. A sealed-evaluation binding requires a separately qualified evaluator-only scope and genuine purpose-specific authority; training/demo bindings cannot inherit it. `serving_qualification_policy` prevents training provenance from being interpreted as serving certification.

The worked requests cover optimisation/development access only. Final evaluation is a separate EO-owned job referencing the frozen candidate and EvaluationContract. Its evaluation-specific execution envelope must be specified at M1 alongside the evaluator interface; these sixteen illustrative schemas do not yet model that entire envelope. It cannot be obtained by changing the training request's access flag or mounting labels into candidate code. The common executor and resource lifecycle still apply, with independent evaluator authority.

## Conversation, model and user-constraint contracts

| Object / owner | Contents and lifecycle | Authority rule |
|---|---|---|
| AssistantModelBinding / ML + PL/SEC | Runtime/model revision, quantisation, upstream expected versus locally verified hashes, template, local endpoint/secret reference, resource/context/call caps, egress and qualification. Proposed → qualified → suspended/retired revisions. | The assistant is a development dependency, not the workload model. Qualified requires actual profile evidence and local-byte verification. No silent model/provider substitution. |
| Conversation / coordinator | Project/workload link, access/retention policy and event cursor; messages/events append with unique IDs and sequence | References hash an immutable conversation identity/access-policy header, excluding the mutable event stream and current workload pointer; this avoids circular workload/conversation hashes. Persistent interaction is not a source of grants or a replacement for WorkloadSpec |
| ConversationCommand / coordinator | Original direct-user message and source, operation, expected workload revision, optional typed diff, status and receipt/effect refs | Schema covers a ledger record, not caller authority. Inbound API accepts only message ID/text/target revision; tenancy, classified operation, status and auth refs are server-derived. |
| CodeTask / coordinator + runner | Source/parent digest, requirement revision, scoped inputs/outputs, lock, resource cap, fence, attempts, execution result and artifact refs | Model-generated source is untrusted. VM/policy enforces permissions, and actual execution is evidenced independently. No separate schema is claimed yet. |

`WorkloadSpec.intent_constraints` has typed field roles, hard predictor exclusions/allowlist/count limit, soft complexity objective and output transforms. `field_provenance` retains the original message/span, uncertainty, materiality and confirmation for inferred fields. The M1 example keeps `case_id`/`scenario_family_id` excluded, `text` as the sole source predictor and no numeric transform. [intent_controls.json](examples/intent_controls.json) validates the same constraint shape for a separate regression-intent illustration using `account_num`, nearest-10 units/ties and a precision-only privacy label. It is not a runnable regression WorkloadSpec or fake data reference.

`ConversationCommand` states are planned, received, accepted, needs_clarification, applied, rejected and superseded. Accepted records require trusted context in non-planning data; applied also requires an effect reference. Command status is distinct from job status: an accepted pause may leave the job `pause_requested` while it drains. [conversation_commands.json](examples/conversation_commands.json) contains only planned requests with no asserted grants or completed transitions.

`AssistantModelBinding` initially describes the selected local runtime only; remote assistant providers require a later explicit contract revision, data policy and grant. The local example's upstream expected model hash is an externally reported value, while verified model/runtime/template digests and qualification report remain null. `WorkloadSpec.interaction_mode` distinguishes conversational from explicit headless automation. Conversational mode requires assistant/conversation references; headless execution can carry null references and zero assistant usage. Execution/release provenance preserves that distinction. A headless workflow remains useful, but does not satisfy the M1 conversational acceptance gate by itself. No fake model call or conversation is created for a scripted run. `RunManifest`/ReleaseManifest development provenance points to this binding and conversation; runtime dependencies intentionally omit the assistant for V1 routing.

Required semantic checks: role fields exist with consistent data types/units; predictor allowlist and exclusions do not overlap; a target/ID/group cannot leak into features; feature counting and quality constraints are defined; context input+output fit the runtime cap; every code dispatch names a current workload revision/fence and qualified generated-code policy; accepted commands derive authority from trusted context; stale revisions reject or rebase a reviewed diff. JSON Schema alone cannot enforce these cross-object and security properties.

## Hardware observations, workflow recommendations and GUI state

The two [hardware fixtures](examples/hardware_snapshots.json) and [workflow example](examples/workflow_plan.json) form one linked local recommendation with the existing workload, assistant and compute binding. They explicitly use `illustrative_fixture`, null observation timestamps and probes marked `not_run`. Their numeric values illustrate D16/D01, not the user's hardware. The plan has INSUFFICIENT_EVIDENCE, no qualification evidence and `authorises_execution: false`. Actual admission snapshot references in the planned RunManifest remain empty; planning snapshots are named separately.

`HardwareSnapshot` records physical/resource domains so a guest or shared accelerator pool is not counted again as extra host capacity. `WorkflowPlan` references those snapshots, its immutable inputs and the protected EvaluationContract; it does not contain grants or mutable event history. ExecutionRequest references the selected plan; production admission verifies that its workload/binding/requirement revisions match and obtains fresh observations. The local example has a provisional plan; the other three provider examples have none and remain unadmitted. A manual/headless run still needs a policy-generated plan before admission; it does not need a fake assistant conversation.

The ReleaseManifest includes WorkflowPlan in development provenance, not as an inference dependency. Serving suitability is independently qualified. A new plan or hardware observation cannot mutate an installed release or its data rights.

The nine `WorkflowPlan.stages` IDs are `goal`, `environment`, `data`, `plan`, `develop`, `self_check`, `evaluate`, `report_release` and `operate`. Stage definitions state completion evidence; mutable status comes from the ledger projection in [gui_workflow.md](gui_workflow.md). A completed evaluation stage can have a FAIL outcome; never conflate event completion with task acceptance. GUI events extend the existing conversation envelope with stage ID, occurrence/recording timestamps and visibility. They are an illustrative semantic contract, not a separate JSON Schema.

Additional semantic checks: all references belong to the authenticated tenant/project; exactly one definition exists for each stage ID; all selected allocations fit the declared resource domains and current reservations; observation age/scope/source meets policy; model/runtime/isolation evidence matches the selected profile; workload and plan limits agree; fixtures/user declarations cannot qualify runtime safety; a feasibility PASS does not mean model-quality PASS. Deterministic policy enforces these checks independently of model prose. Fresh unknown critical capacity means inconclusive admission. See [hardware_discovery_and_planning.md](hardware_discovery_and_planning.md).

## Semantic checks beyond JSON Schema

1. Every reference resolves in the same authorised tenant unless an explicit, rights-cleared shared publication grants cross-tenant use; publication never implicitly grants training-data access.
2. Dataset/split/transform digests agree with run inputs; train-only fitted components have permitted fit lineage. Final references cannot be resolved with optimiser credentials.
3. Family capability negotiation rejects unsupported tasks, modalities, checkpoint modes or adaptation targets. `genai_application` cannot claim changed weights; `genai_training` must identify trainable parameters, base revision and output adapter/weights.
4. Requested permissions are a subset of trusted principal + job-grant + binding policy. Budget request is a cap request, never a funding entitlement. Currency conversion/rates require a FIN-approved policy.
5. Evaluation report belongs to the exact candidate digest, frozen contract and dataset. A PASS from a different tokenizer/prompt/corpus/hardware protocol cannot be reused indiscriminately.
6. Release includes or declares every dependency needed for evaluated behaviour. For service ReleaseManifest, required `pipeline`, `model`, `environment_lock`, `python_entrypoint`, `notebook`, `evaluation_report_json`, `selection_report_html`, `sbom` and `service_contract` roles are checked. A generative recipe additionally requires tokenizer/prompt/corpus/policy roles as applicable.
7. Compatibility `tested` requires a test report on the declared profile. `planned` is never rendered as supported. Platform-reproduced evidence requires evaluator authority and a matching attestation, not a publisher-entered label.
8. AnalysisReleaseManifest instead requires data manifest, preparation/analysis source, environment lock, notebook, report JSON/HTML, SBOM and reproduction guide. Referenced data must be available to the recipient under rights, or the reproduction limitation is explicit. No service/model field is manufactured. Accepted analysis requires its own task-check PASS and owner review; failed/inconclusive evidence remains exportable as unapproved. Production service approval requires PASS plus G2/G3 evidence and distinct release/operator decisions; missing/expired rights, signature, safety or budget evidence blocks the relevant transition.
9. New bindings validate model/provider/corpus/tool identities and local permissions. Secret references must resolve locally, and secret material is excluded from export/logs.
10. Signature/digest verification occurs before loading executable content. Hash correctness is necessary, not sufficient for safety; signer trust, policy and format review also apply.
11. ExecutionRequest resolves workload/binding revisions in the same trusted tenant/project; operations, profile scopes, observed resources, purpose/region and spending constraints intersect. Empty/unknown facts never mean unrestricted access.
12. Release execution provenance resolves to the exact run/request/binding; immutable training references are evidence, not a per-request service dependency. Service runtime requirements and independently tested serving profiles must agree.

## Trusted context and structured errors

Trusted context contains principal ID, derived tenant, authorised scopes, identity issuer/audience, policy revision, request ID and permitted release/binding. The application accepts validated business input separately. HTTP token claims and local MCP OS/profile identity resolve to the same context abstraction; caller instructions and tool annotations never enlarge it.

Illustrative error payload:

```json
{
  "code": "INPUT_INVALID",
  "message": "document.text exceeds the permitted size",
  "retryable": false,
  "request_id": "req-example-001",
  "details": {"field": "/document/text", "max_characters": 20000}
}
```

Shared codes: INPUT_INVALID, UNAUTHENTICATED, FORBIDDEN, NOT_FOUND, IDEMPOTENCY_CONFLICT, QUOTA_EXCEEDED, BUDGET_EXHAUSTED, DEADLINE_EXCEEDED, DEPENDENCY_UNAVAILABLE, CANCEL_REQUESTED, CANCELLED, PAUSE_REQUESTED, PAUSED, REVISION_CONFLICT, REQUIRES_CONFIRMATION, ASSISTANT_UNAVAILABLE, INSUFFICIENT_EVIDENCE, INTERNAL_ERROR. Errors redact secret values, raw source content and cross-tenant existence. Transport statuses are mapped in [execution_and_serving.md](execution_and_serving.md); a structured application failure is not a successful task merely because the transport returned HTTP 200 or valid JSON-RPC.

## Durable job interface

Submission returns an immutable job ID and status/result/control links immediately after durable admission. State reads are authorised and use cursor pagination for lists (default 50, maximum 200), stable ordering and bounded results. Idempotency key scope is tenant + operation + canonical payload digest; same key/different payload is conflict. Pause/resume/cancel request authorised state transitions and report what actually changed. Requirement edits create new immutable revisions with impact and invalidation, as specified in [conversational_control.md](conversational_control.md). Connection closure abandons observation of durable jobs; it does not cancel or undo external work. Results remain queryable within declared retention, independent of the submitting client.

## Immutable release versus mutable binding

Release fixes pipeline code, fitted vectoriser/classifier, calibration/threshold policy, schemas and dependency lock. Binding selects a permitted local address, identity issuer/audience, encrypted data/cache path, telemetry sink and secret references. Changing a hostname is a binding revision. Changing the classifier, routing threshold, prompt, fallback model or significant dependency creates a new release. Changing the retrieval corpus creates a versioned binding/input snapshot and re-evaluation against its declared admissible-change envelope; outside that envelope, a new release is required. No mutable `latest` pointer is sufficient evidence of what answered a request.

## Additional semantic rules for task and output contracts

`family` declares execution semantics; `task_kind` declares the user task; `output_kind` chooses required packaging. data_analysis accepts data_preparation/exploratory_analysis with analysis_code and no trainable parameters. Classical classification/regression/forecasting require an appropriate split. A service request cannot evade service gates by relabelling itself as analysis. The task capability matrix, data purpose and trusted principal determine allowed operations; schema-valid proposals never grant access.

Preparation/analysis uses `permitted_snapshot`, which means only the expressly authorised source/product snapshot, never all project data or sealed final content. `max_trials=0` means no model optimisation, not unlimited code execution; D17/D20/D21 and job resource bounds still apply. Classical no-search baseline may use one trial with an empty search; the initial support fixture retains 12.

MonitoringSpec's target kind must match the referenced object's type; baseline/window/unit/threshold meanings must be reviewed. Manual mode has no interval or automatic source reads. Active mode requires authentic owner approval and job access/resource authority; scheduled mode additionally requires a valid cadence and cumulative limits. schema `readOnly` cannot establish this. AnalysisReleaseManifest does not reference its monitor, avoiding circular content hashes; the external monitor/ledger points to immutable output versions.

WorkflowPlan.workload_family/output_kind must match the referenced WorkloadSpec. data_analysis has zero trials/concurrent trials and stage-specific data/analysis checks; the protected_evaluation_ref is its immutable claim/check contract, not necessarily a sealed predictive dataset. A fresh plan and qualified project binding are still prerequisites for analysis admission.

## New canonical objects and extension semantics

| Object / owner | Lifecycle and references | Invariants beyond JSON Schema |
|---|---|---|
| DatasetCollectionManifest / DO | Planned → frozen → deprecated; exact DataManifest members inline or paged, rights/access refs | Unique source aliases, immutable page membership/digests, all members authorised individually, no project dataset-count ceiling. Frozen production collections need real member/index digests and cannot mix mutable snapshots. |
| JoinPlan / DO+DE, implemented by ML | Proposed → validated → approved, rejected or superseded; collection, operator DAG and evidence/approval refs | Acyclic resolved aliases, every scoped source accounted for, cardinality/grain/units/time correctness, rights intersection and full relevant key checks. Approval requires owners/evidence, not a model confidence score. |
| TaskCapabilitySpec / ML, qualified by EO/SEC/PL | Proposed → experimental → qualified → deprecated; unsupported with reason; task IDs/operations, dependencies/docs, profiles and oracle | Exact task-family/operation/learning-mode match; supported API/input/output semantics and actual target qualification. Upstream docs references alone cannot change status. |
| DocumentationEvidence / CodeTask artifact, ML | Immutable captured reference with URL/package revision/time/digest/rights note | Trusted retrieval provenance is separate from untrusted page content. Cached bytes are not fabricated from a URL; reference-only entries explicitly have no captured digest. |
| ImplementationProposal / CodeTask or ChangeProposal role, ML | Proposed diff → checked execution → evaluated candidate; owner review before reusable promotion | Prior/source code, dependency changes, task/oracle/profile, repairs and invalidation recorded. No new orchestration object is required. |
| OutputBinding / AO or PUB; operated by customer/PL | Proposed → active → revoked; immutable output ref plus local scoped root and conflict/commit policy | Destination permission from trusted context, path/race safety and limits at write time. ExportReceipt records actual committed bytes, digests and result; neither a path nor a manifest proves export succeeded. |

`data_manifest_ref` remains for a single-source workload; exactly one of it and `dataset_collection_ref` is non-null. A non-null JoinPlan uses that same collection. `data_product_refs` denote required prepared inputs; the referenced product must resolve to the pinned collection/join/code. A preparation workload must not depend on the product it is currently creating: preparation stages refer to sources/plan, then the analysis or training stage consumes the committed gold revision. The example is a planned analysis request against a proposed gold product, with no admitted run.

`task_kind` retains legacy IDs and permits namespaced extensions only with a TaskCapabilitySpec reference. Admission resolves the registry entry and verifies family, learning mode, operations, modalities, oracle and profile. A namespaced string cannot bypass supervised split requirements, sealed boundaries or registration. Shape validation alone cannot enforce these cross-object facts. Future unsupported modalities are representable metadata, not advertised runtime support. A task library/ABI or output target change needs a new capability/code/run qualification, even if a JSON schema still validates.

`requested_delivery` is filesystem_bundle, service_endpoint or both. Analysis currently requests filesystem_bundle; a service workload may export a bundle with interfaces and defer endpoint startup. Local paths/credentials stay in OutputBinding or DeploymentBinding, never immutable portable release content. Filesystem export does not bypass rights, evaluation status or evidence: failed/inconclusive findings may be exported honestly, but cannot be labelled an approved operational release.

Join expressions are untrusted proposed code; the graph declares intent, and deterministic checks plus isolated execution must enforce it. Semantic validators must test source alias uniqueness, graph acyclicity, reference/tenant consistency, column provenance and post-join count rules. Schemas do not prove those properties or implement a database engine. Draft migration preserves immutable prior bytes; no compatibility with older consumers is asserted.

The linked examples are [dataset_collection.json](examples/dataset_collection.json), [join_plan.json](examples/join_plan.json), [task_capabilities.json](examples/task_capabilities.json) and [output_binding.filesystem.json](examples/output_binding.filesystem.json). All are proposed, have no approvals/receipts/measurements and resolve into the existing operations or support fixture. The filesystem example's 1 GiB export cap is an illustrative task proposal within local free-space checks, not a hosted entitlement or granted budget.

## Edition 0.7 example revision register

The support service API remains 1.0.0, and both illustrative output release versions remain 0.1.0. Object revisions below change because content or transitive immutable references changed; no application release was built.

| Example object | Current object revision |
|---|---|
| `wl-support-route-v1` | 1.4.0 |
| `code-task-route-example` | 1.2.0 |
| `workflow-route-local-example` | 1.2.0 |
| `run-route-example-001` | 1.5.0 |
| `report-route-example-001` | 1.0.0 |
| `rel-support-route-0.1.0` | 1.5.0 |
| `binding-support-local-example` | 1.3.0 |
| `wl-operations-analysis-v1` | 1.1.0 |
| `gold-operations-v1` | 1.1.0 |
| `code-operations-prepare-v1` | 1.1.0 |
| `eval-operations-analysis-v1` | 1.1.0 |
| `run-operations-analysis-001` | 1.1.0 |
| `report-operations-analysis-001` | 1.1.0 |
| `analysis-operations-0.1.0` | 1.1.0 |
| `monitor-operations-analysis-v1` | 1.1.0 |

New collection/join/capability/source-member/output-binding identities start at 1.0.0. Remaining concrete revisions are in their linked JSON objects. Transitive references must match, and typed digest references must remain acyclic. The original umbrella raw operations DataManifest is retained as historical fixture description; the new collection's six member DataManifests are the analysis input authority.

Future non-generative neural training needs the E3/E4 family extension described in task_expansion.md; the current five-path family enum intentionally does not advertise it. Namespaced task IDs extend task taxonomy within an established family, not arbitrary new execution semantics.
