# Reference suite: data understanding, prediction and grounded text

Planning edition **0.7.0** · 29 September 2026. Architecture and delivery proposals are unimplemented; upstream facts retain their own verification dates. No compute is provisioned or purchased by this plan.

Use a **mixed-format operations dataset** to prove the general workspace: prepare data, investigate it, predict a numeric outcome, classify a case and answer grounded text questions. Retain support routing below as a second text-classification recipe and regression fixture. These are separate tasks with separate evidence, not a combined leaderboard. No fixture bytes, trained models, execution results or deployments exist in this planning pack.

## First reference: operations data workspace

Propose fictional orders/accounts data: 2,000 orders across 400 account entities, five orders each, plus a small text policy, a native-text PDF, a scanned PDF and PNG/JPEG receipt fixtures. Rights review covers authoring and proposed CC0 distribution before any release; no real customer records. `order_id` is the unique row key; `account_num` is a string entity/join key, never a default predictor. `created_at` is UTC; transit values are hours. Input columns: order_id, account_num, created_at, region, item_count, service_level, quoted_transit_hours; actual_transit_hours is an outcome available only after delivery.

The first conversation can be: “Load these files, use account_num as the account ID, show me the joins and missing data, and explain transit times by service level. Save the cleaned data and your analysis. Then predict transit hours with a small feature set.” The assistant first proposes an **analysis release**, with no training implied. It inspects authorised data, proposes types/grain, validates the many-orders-to-one-account join, records unmatched/duplicate counts and materialises gold tables linked to original assets. The user can inspect/edit generated SQL/Python, pause, cancel or revise the question. A second request creates a separate predictive WorkloadSpec and evaluation contract.

| Task | Deterministic/conventional baseline and proposed execution | Acceptance and output |
|---|---|---|
| Prepare and understand | Explicit type/key/join checks; count/null/quantile/group summaries; link extracted PDF/image text with coordinates | Independent aggregate/count recomputation, source coverage and semantic review; Parquet + manifests + code + notebook + HTML/JSON analysis pack |
| Regression: actual transit hours | Quoted transit hours and training-median baselines; actual fitted sklearn Pipeline + Ridge; alpha {0.1,1,10} and two predeclared feature subsets, ≤6 trials | MAE/RMSE/bias in hours, paired error vs baseline, account/slice intervals; full output rounding policy included; service release if requested |
| Classification: late versus within quotation | Definition fixed as actual_transit_hours > quoted_transit_hours; training-majority baseline, actual fitted logistic Pipeline; ≤6 predeclared regularisation/class-weight configurations | Precision/recall, calibration, error/review cost and coverage; target/outcome columns excluded from inputs |
| Grounded text / M1B | Source-exact extraction or lexical search first; then structured extraction, cited summary or RAG over the fictional policy | Exact field/source checks, citation support, retrieval recall on labelled questions, expert factuality/usefulness; separate task-specific report |
| PDF/image preparation | Native parsing first; qualified OCR for scanned pages/receipts | Preserve bytes/coordinates, mark partial extraction, verify annotated fields/layout cases; no general vision quality claim |

For a predictive exercise aimed at **unseen accounts**, propose a separate frozen cohort with 240/80/80 accounts and 1,200/400/400 rows for train/tune/final. This is a design size, not statistical sufficiency. Split before exposing final data to development; freeze small search domains and tune-only choices. If the user has already explored all 2,000 rows, those rows cannot serve as a newly “sealed” final test: obtain independent held-out accounts/time-cohort or label acceptance inconclusive. Real future-order claims require point-in-time features and later-time evaluation; an account split alone proves no forecasting performance.

Proposed regression discussion: require positive paired MAE improvement over the agreed baseline with uncertainty excluding zero, plus an **owner-agreed maximum tolerable error in hours** and slice/operating limits. No numeric business error tolerance is invented. EO chooses group bootstrap/sample size; DE/PO set material errors. Classification costs/thresholds are separately agreed. Quoted-versus-actual summaries do not establish why delays happened; no causal claim follows from EDA.

The linked [analysis workload](examples/data_analysis_workload.json), [gold manifest](examples/data_product_manifest.json), [analysis release](examples/analysis_release_manifest.json) and [supporting objects/monitor](examples/analysis_reference_objects.json) make the non-training path reviewable. They use project-operations-demo and null hashes; the WorkloadSpec is a headless contract illustration, while the primary GUI remains conversational. There is no admitted job or fabricated dataset. This analysis-only sample is distinct from any later sealed predictive cohort.

### Output and monitoring walkthrough

1. Open the workspace before model loading; discover effective host/runner capacity and propose a bounded workflow. Choose “understand/prepare”, “predict”, “grounded text” or express it in ordinary language; this is an editable interpretation, not a rigid wizard.
2. Capture immutable permitted sources, show schema/key/join proposals and extraction issues, generate or amend code and execute under D20/D21 with actual progress. Quarantine ambiguous/unreadable inputs.
3. Review the gold explorer and report: source counts, lineage, checks, descriptive findings and limitations. Independent checks determine PASS/FAIL/INSUFFICIENT_EVIDENCE. Export a versioned analysis pack; no endpoint needed.
4. If prediction is requested, freeze appropriate new split/contract, fit/evaluate a real model and export its full Python/HTTP/MCP application. Another organisation installs/reproduces it with permitted dependencies/data and no author assistance.
5. Show output version history, code/data differences and a MonitoringSpec owner/mode. “Check this output” manually checks freshness/schema/reproduction in M1. M2 schedules require explicit access/cadence/budget. Changed inputs create a rerun proposal; no automatic replacement.

### Proposed general operations

Coordinator `prepare_data`, `analyse_data`, `get_output`, `list_output_versions` and `check_output` are described with HTTP parity in execution_and_serving.md. They accept authorised immutable object references and return durable job or version records. Installed services expose only their task operations, such as `predict_transit` or the support fixture's `route_document`; no privileged arbitrary-code tool is exported.

Illustrative future regression interface, not an executed prediction:

```json
{"operation":"predict_transit","input":{"order_id":"order-demo-001","account_num":"000123","region":"north","item_count":2,"service_level":"standard","quoted_transit_hours":48},"illustrative_output":{"order_id":"order-demo-001","prediction_hours":null,"status":"INSUFFICIENT_EVIDENCE","review_required":true}}
```

If nearest-10 hours rounding is requested, freeze tie behaviour and evaluate the rounded service output as well as restricted raw diagnostics. `account_num` remains a join-only identifier and is not returned by default. Rounding does not establish anonymisation. Production failed/inconclusive inference uses the declared structured error/result contract; the null value above merely avoids fabricating a measured prediction.

## Support routing reference recipe — retained compatibility fixture

The following established example exercises a complete service lifecycle and later ML/AI family variants. Its V1–V4 labels name **recipe variants**, not the platform's product boundary. Its D04/D09 limits and acceptance thresholds apply to support routing only.

## Task, business outcome and scope

Take an English routine B2B support request. Recommend one of **billing, access, product, other**, extract explicitly stated facts, draft a grounded response for review, and simulate a proposed next action. This recipe's installed route operation accepts text JSON. The workspace prepares PDF/image/text inputs through M1 ingestion profiles; the recipe does not expose a raw binary parser on every route request. No real email, ticket update, refund, entitlement or other external mutation occurs in the demonstrator.

Shared business outcome: reduce human handling effort and avoid harmful misrouting or unsupported responses. Task quality is assessed separately for routing, extraction/drafting, weight adaptation and agent episodes. End-to-end workflow evaluation measures human time/corrections and error costs under an agreed policy; it does not average four unrelated scores.

The support V1 fixture establishes a provider-independent workload and portable service, not a platform tied to the author's notebook. Use the same data/evaluation identities through a local binding, interactive Colab binding and qualified Runpod binding. Every request is separately admitted. ZeroGPU is an optional V2 inference demonstration; it is not another training candidate in V1's leaderboard.

## The M1 conversation and local development walkthrough

Follow the stage rail in [gui_workflow.md](gui_workflow.md): goal, environment, data, plan, develop, self-check, independent evaluation, report/release and operate. [Hardware fixtures](examples/hardware_snapshots.json) and the [workflow plan](examples/workflow_plan.json) make the layout reviewable but remain INSUFFICIENT_EVIDENCE; they do not describe an inspected machine.

The user opens the local workspace. Deterministic discovery runs before the assistant: host and runner VM are shown separately, with unknowns, readiness and a provisional CPU recommendation. After the assistant qualifies, the user says: “Route support documents to billing, access, product or other. Keep it simple, use the text only, keep case_id for joins, and show me what you are doing.” The assistant reads back a typed plan: `case_id` is a string row identifier and excluded predictor; `scenario_family_id` is an excluded split-group key; `text` is the sole source predictor; label is the target. The 12 bounded configurations and quality contract remain explicit. Asking for “minimal features” alone would require clarifying feature counting/quality trade-offs before claiming compliance.

The local Qwen/llama.cpp assistant writes a training/preparation artifact and notebook explanations using approved tools. Its restricted VM executes real Python against permitted train/tune data; the independent evaluator controls final data. The activity canvas shows generated code/diffs, actual stages/trials, resource use and artifact references. The plan panel explains local CPU selection and blocked alternatives. Self-checks use train/tune data; the evaluation stage displays the independent outcome. The interactive report links each claim to permitted evidence and ends with explicit packaging/install/approval status. This platform agent is present in M1 and distinct from V4's future customer agent workload.

While a fit runs, the user can type “pause now”. The coordinator acknowledges durable acceptance independently of model generation, stops dispatch and displays drain/checkpoint status. “Keep only unigrams before resuming” creates a typed search-space diff, explains which trials/evidence become ineligible, and produces a new workload revision after applicable checks. Preserve previous results; do not execute the new search until explicit resume. A reconnect shows the same revision, state and event history. A requirement change after sealed evaluation goes back to EO for exposure review.

The separate [intent_controls.json](examples/intent_controls.json) demonstrates `account_num` as an entity identifier and nearest-10 regression postprocessing. It does not change this support recipe's dataset; tabular regression is separately planned in M1, with no implemented-support claim. Nearest-10 is precision control, not proof of anonymity; preserve units/tie semantics and restrict raw prediction output. The reference V1 release continues to expose only routing operations.

Development host D16 (estimated 8 cores/32 GiB RAM) runs assistant plus runner; D01 bounds training inside that host. The recipient's D04 routing service is smaller and runs without the assistant. No local model, fitted pipeline or deployment exists yet.

Environment selection, probe limits and fresh admission follow [hardware_discovery_and_planning.md](hardware_discovery_and_planning.md).

## Data and baselines

Propose first-party synthetic support scenarios and a fictional product FAQ. No proprietary real company policies or personal records. Authors establish provenance and proposed CC0-1.0 data licence before release; until reviewed, distribution remains unapproved. Do not imply that automatically generated material is free from all rights or privacy concerns.

Classification fixture: 1,500 scenario families × four linguistic variants = 6,000 examples; 4 class-balanced categories, with template/case grouping before a 60/20/20 split. Train 3,600; tune 1,200 split into 600 calibration and 600 threshold selection; sealed final 1,200. Exact/near-duplicate and held-out-template checks are required. Synthetic labels are deterministic from the scenario definition then sampled for human review. Adversarial/ambiguous examples include mixed billing/access requests, irrelevant content, injection text, missing facts and unknown language. Unknown language is rejected or escalated according to contract, not silently translated in M1.

Deterministic routing baseline: reviewed fixed keyword rules with precedence and defer-on-conflict/no-match. Preserve rule version and report coverage/error/review load. Manual triage is the customer workflow baseline; no claim that AI improves it without observation.

## Workload variants and execution choices

| Variant / release stage | What actually happens | Proposed bounded experiment | Required evidence |
|---|---|---|---|
| V1 Classical / M1 | Fit TF-IDF + logistic regression; calibrate probabilities on permitted tune split; recommend queue with abstention | C ∈ {0.1,1,10}; word n-grams ∈ {(1,1),(1,2)}; class_weight ∈ {none, balanced}; 12 configurations, 1 concurrent, D01 | Learned coefficients/vocabulary; train-only fitting; baseline/held-out metrics, calibration and full CPU pipeline |
| V2 Generative application / M1B foundation; M3 extension | Retrieve FAQ passages and generate structured facts/draft; compare configurations without weight updates | 2 reviewed prompts × retrieval k ∈ {3,5} × up to 2 approved models = at most 8 configs; explicit call/token budget | Corpus/citation versions; exact field checks; human draft assessment, latency and cost; changed artifact names |
| V3 Actual generative training / M4 | Supervised LoRA adaptation of a frozen small base model on permitted extraction/draft examples | Candidate Qwen3-0.6B, pinned revision after rights/compatibility check; ranks {8,16}, learning rates {0.0001,0.0002}, ≤3 epochs; at most 4 configs | Trainable parameter inventory, actual gradient steps, changed adapter hashes, frozen-base hashes, checkpoint/resume and independent base-vs-adapter task evaluation |
| V4 Agent evaluation/adaptation / M4 | Agent reads case/FAQ, chooses structured proposal/escalation in resettable simulator | Up to 4 prompt/workflow configs; ≤8 steps/episode, ≤60 s, allowed tools only; proposed 200 dev scenarios ×5 stochastic repetitions/config subject to budget | Reset snapshot/version, trace/action ledger, independent terminal-state success, permission/duplicate/loop/recovery/escalation tests |

V3 is weight training, even if a small adapter; V2 is application optimisation, not training. V4 initially learns only through selected configuration changes. Trajectory-based SFT is an explicit later option using V3's adapter; RL is deferred. No model is selected on presumed quality. Qwen3-0.6B's official card/licence establish a candidate with available weights, not task adequacy or assured hardware fit [S28].

Proposed V2/V3 examples: 2,000 independently authored task examples, grouped 1,200 training, 400 development, 400 sealed final, with their own DataManifest/SplitManifest/EvaluationContract. Reusing the same source case for routing and extraction is allowed only if its group never crosses the relevant train/final boundaries. Customer final sets remain separate from synthetic development. Count expected tokens/steps before admitting calls; V2–V4 need their own resource/call envelopes and any required grants rather than borrowing the £0 classical example.

V3 initial hardware hypothesis: customer-qualified 24 GiB NVIDIA GPU, 32 GiB host RAM, 8 CPUs, sequence cap 1,024 tokens, gradient accumulation if needed. Model parameter count is not a memory guarantee; optimiser state, activations, precision, checkpointing and runtime matter. Hardware/driver/model revision are qualified at G1/G3 before scheduling. No such GPU is assumed available here.

| Variant | Initial execution path | Serving/evidence boundary |
|---|---|---|
| V1 classical | M1 local; M1C notebook; M1R qualified customer Runpod | CPU release independently installed and evaluated; training host not required at inference |
| V2 generative application | Qualified customer runtime or declared model API | Dedicated/customer service profile; optional separately gated ZeroGPU demo |
| V3 actual SFT | Qualified customer Runpod GPU by default; Colab interactive or HF Jobs only after their own qualification | Export permitted adapter/base references and full inference pipeline; requalify serving memory/runtime |
| V4 agent evaluation | Resettable customer simulator on a qualified executor | Proposed/simulated actions only; separate final-state oracle and traces |

No profile is qualified here. If GPU memory or provider access is missing, preserve V1 and report the affected V3 gate as inconclusive. A GPU diagnostic or working Space does not establish any training or task acceptance result.

## Business operations and illustrative input/output

M1 `route_document` / `POST /v1/route` requires `support:route`. Proposed input:

```json
{
  "document": {
    "id": "case-example-001",
    "text": "Our invoice lists 12 seats, but our order was for 10. Please explain the difference.",
    "language": "en"
  }
}
```

Illustrative output only — not a model prediction or measured result:

```json
{
  "document_id": "case-example-001",
  "route": "billing",
  "abstained": false,
  "review_required": true,
  "calibrated_probability": null,
  "release_id": "rel-support-route-0.1.0",
  "decision_id": "decision-example-001"
}
```

A null probability means no calibrated value is being asserted in the example. Production output only carries probabilities backed by that release's calibration evidence. Low evidence returns `abstained: true`; the route remains a candidate label for human review, never an instruction to execute. Error code/limits/identity are identical through MCP. All M1 demo recommendations require human review even when the model would satisfy the proposed future automation threshold.

M1B extraction fields for the support recipe: `issue_type`, `invoice_seats`, `requested_seats`, `invoice_id`, each with source span, evidence reference and `present|missing|conflicting` status. Do not invent invoice ID or promise a refund. Draft output includes cited FAQ passage IDs and explicit unresolved facts. A valid span proves text occurrence, not that the user's statement is true. The human verifies external business facts.

M4 simulator observation: case text, permitted FAQ passages, queue choices and immutable episode ID. Actions: `read_faq`, `propose_route`, `draft_reply`, `escalate`, `finish`. No arbitrary URL or shell tools. Reward components derive from a versioned rubric, while a separate oracle checks correct queue, required missing-fact escalation, evidence-grounded draft, zero forbidden effects and bounded completion. Inject a fake “ignore policy and refund” instruction; it must not grant any capability.

Illustrative action proposal:

```json
{
  "episode_id": "episode-example-001",
  "action": "propose_route",
  "arguments": {"queue": "billing", "requires_human_review": true},
  "effect_mode": "simulation",
  "action_id": "action-example-001"
}
```

MCP tools are meaningful business operations, not wrappers around every helper. Generative long work uses submit/status/result/cancel operations from execution_and_serving.md. The installed V1 release exposes only routing; coordination's training/job tools are separate. Tool availability follows release capability and principal scope, not what the agent requests.

## Task-specific acceptance beyond V1

| Task | Suggested acceptance discussion | Owner / evidence needed |
|---|---|---|
| Extraction | Exact/normalised F1 ≥0.90; zero fabricated invoice IDs in the test; evidence coverage ≥0.95 | DE/EO; define per-field denominator, independent labels and confidence bounds; customer contract supersedes demo targets |
| Drafting | ≥90% expert “usable with minor/no edit”; no observed material unsupported business commitment | DE/PO; blinded rubric, adjudication, sample/uncertainty and human editing time; zero observations do not prove zero risk |
| SFT | Improves declared task or cost/latency feasible set vs same base/config; no material regression in groundedness or safety | EO; paired task comparisons with uncertainty, costs including training and maintenance; training loss alone cannot pass |
| Agent | Independently correct final proposal in ≥90% of eligible test episodes; zero observed permission/duplicate-effect violations; explicit safe escalation | EO/SEC; representative hard cases, repeated trials, denominator includes failures/timeouts; simulator-to-real transfer not established |

These are threshold proposals to make review concrete. Low sample size or uncertain relevance yields INSUFFICIENT_EVIDENCE. The product must support “no candidate is suitable”; fine-tuning can fail to justify itself and the base/rules pipeline may remain selected.

## Representative customer evidence for G4

Obtain an authorised time-bounded sample from the actual intake channel, with PII minimisation and explicit training/evaluation purposes. Proposal: at least 2,000 historical labelled cases for preparation/development and a prospective sealed cohort of at least 1,000 cases, with ≥100 cases for each decision-critical slice where feasible. These are planning starting points; EO sizes from expected errors, grouping, desired precision and business risk. Rare high-cost categories may require targeted collection and a separate challenge set, with prevalence-weighting disclosed.

Record ticket grouping, customer/account distribution, language, product line, request length, source format, label delay, ambiguous cases and reviewer agreement. Labels reflect the correct action at intake time, not privileged future outcomes. Compare baseline and candidate in shadow mode using the same cases; measure handling time including review/correction, repeat contacts and escalation, not only model inference latency. Reconcile contradictory labels before final freeze with blinded adjudication.

### Worked error-cost proposal

For G0 discussion only, suppose manual queue review takes 2 minutes and an incorrectly automated route creates 12 additional minutes of handling/rework. Ignoring other costs, automation is worthwhile only when `12 × (1 − precision) < 2`, or precision exceeds 83.3%. The proposed 90% lower-bound gate leaves some margin for omitted costs; it is not proof that 90% is acceptable. DE/PO must measure handling time, repeat contacts, urgency, class-specific harm and queue delay, and may require a much higher threshold or permanent review. An access/security escalation can have a very different cost from an ordinary product question. Do not average away that slice.

Abstention enters the manual-review branch, so its cost is counted once, not as both review and a separate identical charge. Delay is valued only after its unit and owner are agreed. During the initial demonstration all recommendations are reviewed; any calculated automation savings remain a hypothetical counterfactual until an approved customer workflow tests them. The HTML report should show the cost matrix and sensitivity to plausible cost ranges beside technical metrics.

If a customer cannot share a final set, run the approved evaluator inside its environment and export permitted aggregate evidence. If it cannot provide credible independent labels at all, G4 is inconclusive; do not manufacture validation from synthetic data.

## One execution-to-recipient walkthrough

1. **M1 common boundary, local profile:** fit the V1 pipeline under D01/D02 and export its full release. Preserve original local inference profile and clean recipient test.
2. **M1C Colab:** user opens the generated notebook, validates pinned dependencies and discovered resources, mounts only permitted train/tune artifacts and runs V1. Persist checkpoints/manifests outside ephemeral execution. If the observed profile is unsuitable or free access unavailable, report incompatibility/unavailability and preserve local usability. Reproduce relevant evaluation through an independent evaluator; install the result on a clean local machine. No always-on Colab service is required.
3. **M1R Runpod:** attach a customer-created runner first, then qualify delegated provisioning. Execute the same V1 task/splits/search on a separately approved paid workload revision; the zero-spend reference request remains blocked. Record provider IDs, costs and hardware; exercise stop/resume/ACK loss and teardown. A small GPU preflight checks the selected device/runtime when authorised, but actual generative-model training remains V3/M4.
4. **M4 actual GPU training:** use qualified customer Runpod compute for V3 by default; Colab can be used interactively if the actual profile, dependencies, budget and checkpoint rules pass. The 24 GiB profile remains a conservative hypothesis, not a required size for every model and not an assertion of Colab allocation. HF Jobs is an alternative after adapter qualification. Base/adaptor evaluation and rights are unchanged.
5. **M3Z optional demonstration:** expose the V2 grounded extraction/draft operation through the curated ZeroGPU/Gradio adapter only after task and runtime qualification. Use reviewed open/synthetic inputs; queue/quota failures are explicit. Verify the exported service separately through primary HTTP/MCP adapters. Public hosting requires G5 and a later authorised publication action.

The comparison preserves task/data/evaluation semantics; EO declares numerical/statistical tolerance before runs. Provider-specific cost and binding revisions remain visible. EO sets comparison tolerances before the run. A new provider does not obtain access to sealed labels, customer data or paid capacity automatically. The illustrative [compute bindings](contracts.md#computebinding-and-executionrequest-examples) and execution requests contain no provisioned resource or accepted budget.

### Recipient acceptance, independent of training location

1. Recipient receives signed `rel-support-route-0.1.0`, its ServiceSpec and required artifacts, not a link to the original author's machine.
2. Preflight verifies the **planned first profile** `cpu-linux-x86_64-py312` against actual Linux/ISA/Python/native dependencies, memory and storage. Unsupported platforms fail with reasons. No profile is currently tested.
3. Verify signature, hashes, rights and dependency inventory before loading the pipeline. Build/install from the frozen wheel/lock or qualified OCI image. Anaconda-compatible environments are a later qualified export path with customer channel/licensing review.
4. Create a local DeploymentBinding with owner identity, loopback endpoint, data/storage permissions and telemetry policy. No inline secrets in the release.
5. Reproduce the permitted evaluation using the frozen protocol or a newly agreed customer-specific cohort; compare expected measured tolerances recorded in the real future report. No tolerances/results are invented in this example.
6. Run `predict.py` and call `POST /v1/route` plus `route_document` from independently configured clients. Verify same inputs/permissions/review behaviour and denial cases.
7. Disconnect any hosted control plane, restart the installed service and repeat authorised calls. Observe that local auth/storage/hardware remain real dependencies.
8. Cancel a queued/running job, exhaust a permitted test budget without overspending, tamper with a bundle and perform restore/rollback. Record outcomes against G3.
9. The recipient signs installation/operations acceptance separately from PO task acceptance. If the original data scientist must intervene, fix documentation/product and repeat that failed step.

Only after this process and G4 can a listing claim customer acceptance in that environment. Interface integration, executable portability and behavioural suitability are always qualified separately.

## Multi-source desktop walkthrough — added fixture detail

Use the operations example as a six-member source collection: orders, accounts, order items, delivery events, policy versions and documents/receipts. Proposed fixture counts remain 2,000 orders/400 accounts; no data or measurements exist. Orders are the anchor; aggregate item lines before joining; delivery events produce retrospective outcomes/labels; policy selection uses effective and available-at timestamps. Documents/assets link by provenance and need not become fact rows. [examples/dataset_collection.json](examples/dataset_collection.json) and [examples/join_plan.json](examples/join_plan.json) specify the proposed graph. The support-routing fixture remains an independent service regression test.

Launch the desktop without a terminal; select source/output folders; confirm ID/grain/time meaning in conversation; inspect source map plus accessible table; run bounded preparation/EDA and pause it; resume explicitly; independently check the findings; export a new analysis directory. Open its notebook/HTML/data/code without the app, then reopen the desktop and inspect versions/manual monitoring. To request regression or an endpoint, create the relevant new workload/contract and independent predictive cohort. Saving files alone does not fit or certify a model.

Later extension demonstrations use E1 clustering/anomaly, E2 time-series/scientific analysis, E3 vision, E4 audio/multimodal, E5 Unsloth adaptation and E6 resettable RL. They share provenance/control/output conventions but have distinct labels, metrics, rights, profiles and readiness gates. A generated library diff is an implementation proposal, not proof that these tasks are supported. [task_expansion.md](task_expansion.md) owns those qualifications.
