# Hardware discovery and workflow configuration

Planning edition **0.7.0** · 29 September 2026. Proposed behaviour only; no customer hardware has been inspected and no application or compatibility test has run.

## Recommendation and boundary

Make automatic, read-only discovery an early part of onboarding, then repeat the relevant checks at admission and resume. The installed coordinator starts a small deterministic collector before loading an assistant model. It can explain missing capacity and offer manual configuration even when no LLM fits. The desktop GUI presents the findings; it is not the authoritative inventory of the execution host. A remotely displayed GUI, local assistant, training VM and installed service may occupy four different environments.

Recommend a **feasible workflow for the stated task and preferences**, not a universally “best” configuration. Hardware establishes capacity constraints; task quality, data rights, split integrity, model suitability, operating limits and budget establish the rest. An available GPU is neither an instruction to use it nor evidence that fine-tuning is useful. Detection never grants account access, provisions resources, installs drivers, downloads weights or approves spending.

The M1 scope is the proposed Linux x86-64 CPU profile, local assistant host and an already supplied restricted runner VM. M1C/M1R extend the same evidence contract to Colab and attached/delegated hosts. Accelerator inventories are informative until the exact workload/runtime profile is qualified. Apple Silicon, other ARM64, Windows and additional GPU stacks remain separate qualification work. This expands the existing preflight design; it does not promise universal hardware support.

## What is collected and from where

| Observation | Deterministic source / interpretation | Why it changes the plan |
|---|---|---|
| OS, instruction architecture, required CPU features, executable/runtime versions | Allowlisted local OS/runtime APIs; fixed-argument diagnostics; explicit unsupported/permission errors | Match binary, wheel and model-loader profile before installing or loading |
| CPU capacity | Visible logical processors, affinity, effective quota and configured reservations, separately recorded | Cap usable threads/concurrency; advertised cores are not necessarily schedulable capacity |
| Host/guest RAM | Installed/visible total, available memory, effective limits and existing reservations | Allocate assistant, runner and host headroom without counting the same physical memory twice |
| Scratch/artifact/model storage | Free bytes and applicable quota on each declared mount; device/domain labels without raw paths in shared summaries | Include downloads, temporary copies, checkpoints, export and retention; a single host disk figure is insufficient |
| Accelerator inventory | Visible vendor/device, per-device memory, driver/runtime information and sharing/partition flags where available | Candidate offload/training profile; never add separate devices' VRAM as if one tensor automatically fits |
| Runtime usability | Version/pin inspection first; explicitly authorised bounded smoke check in the selected environment afterwards | Detect a visible accelerator with an unusable driver/build or a model that fails to load |
| VM and runner readiness | Authenticated existing guest connection, assigned limits, image identity and isolation qualification evidence | CPU virtualisation flags alone do not prove that a restricted VM is ready |
| Connectivity and provider context | Declared offline/egress policy, authorised endpoint checks, provider account/profile metadata if connected | Keep data/secret/region restrictions distinct from compute availability; no general network scan |

Browser memory signals are approximate and deliberately constrained for privacy [S49]. NVIDIA documents separate driver-supported CUDA information and installed toolkit identity, plus qualifications on GPU memory reporting [S50]. Linux cgroup limits can constrain CPU bandwidth and memory independently of host totals [S51]. These facts motivate the runner-side design; none verifies our collector. Specific APIs/flags must be locked and tested on the selected profile at G3.

Store a minimal `HardwareSnapshot`: environment scope, binding identity where applicable, collector version, observation provenance, timestamps, limits, unknown reasons and probe results. Omit serial numbers, MAC addresses, unrelated process names, usernames, full home paths and credentials. Local discovery remains local by default. Authorised hosted coordination receives only the fields needed for scheduling/support, with the project's retention and deletion policy. Export a redacted compatibility summary rather than a customer's entire machine inventory.

## Discovery, checks and freshness

1. Start the coordinator and GUI without the assistant. Display the conversation immediately in a model-loading/unavailable state; exact pause/cancel/status controls and manual setup remain available.
2. Discover only the selected local environment and already attached runners. D19 proposes a two-second timeout per passive probe and ten-second overall deadline; incomplete results return with reasons. Do not install discovery tools or elevate privileges to make the inventory look complete.
3. Separate **observed**, **user-declared**, **unknown** and **illustrative fixture** evidence. A declared inventory can draft a plan but cannot satisfy a safety-critical capacity or isolation gate. A permission failure is not “no GPU”. A provider's advertised instance size is not an observed allocation.
4. Build a provisional plan from the task, policy and inventories. Show what fits on paper, what is unqualified and what is blocked. Offer a bounded runtime check only within existing authorised resource/connectivity limits; explain any model import/download separately. No stress test or representative customer-data benchmark occurs during passive detection.
5. At dispatch or resume, recheck effective CPU/memory/disk, binding revision and runtime/isolation readiness; acquire resource and spending reservations atomically. D19 marks availability displays older than 60 seconds as stale. This display TTL never substitutes for fresh admission checks. Recheck on environment/binding change or pressure notification as well.
6. Record the snapshots actually used in the RunManifest. Resource pressure after dispatch invokes the declared checkpoint/cancel policy. An observation is not a reservation, and a reservation cannot guarantee that unrelated host processes will leave capacity available.

A failed assistant load returns to setup with its actual error and preserved conversation. It must not trap the user behind a model-dependent onboarding agent. The fallback manual/CLI path remains usable, but M1's conversational acceptance still requires a useful qualified local assistant.

## Deterministic feasibility and explainable recommendation

The model may propose an approach or explain the result. A versioned, deterministic policy computes eligibility. The minimum useful implementation is a rule table over declared profiles and resource bounds, not another learned scheduler or cluster service.

| Step | Input / output | Rule |
|---|---|---|
| Filter | WorkloadSpec, approved context, binding/profile capabilities | Reject incompatible family, operation, region, egress, isolation, rights or charge policy before ranking |
| Size | Data rows/features/format; model size/context; algorithm and profile estimates | Include preprocessing, KV/cache, activations/optimizer state where relevant, evaluation, scratch and environment overhead; expose unknowns and estimate provenance |
| Place | Assistant host, workload runner, evaluator and serving profile | Separate memory/resource domains and qualification; shared-memory pools are counted once; CPU/GPU contention may require serial execution |
| Compare | Eligible options and user preferences | Hard constraints first. Default prefers an already available, qualified local CPU route for V1 within D01/D16 and zero external charges; trade-offs remain visible |
| Explain | Selected option, alternatives, rejection reasons, evidence gaps | Explain why the recommendation fits and which measurements could change it; no invented speed/cost/quality score |
| Authorise | Reviewed WorkflowPlan plus current WorkloadSpec and trusted grants | Plan selection does not admit work. Existing coordinator revalidates, reserves and dispatches through ExecutionRequest |

`WorkflowPlan` is an immutable decision record referencing workload, assistant binding, hardware snapshots and proposed placements. It records ruleset version, bounds, assumptions, alternatives, evidence outcome and stage-to-artifact dependencies. UI state is a derived projection of durable jobs/commands; it is not mutable state inside this plan. Changing its inputs produces a new version and supersedes the old recommendation.

Within an approved range the planner may reduce trial concurrency or choose allowed batch sizes, with the choice recorded. Changing assistant model/quantisation/context, data placement, features, precision, search coverage or model-training strategy may alter behaviour: show the diff, affected evidence and authority requirements. It cannot silently reduce the evaluation population or acceptance standard to fit a smaller machine. If no qualified option fits, say so and keep drafting possible.

## Worked reference and honest alternatives

The linked [hardware fixtures](examples/hardware_snapshots.json) illustrate an eight-logical-core, 32 GiB host and its four-vCPU, 8 GiB guest. They are invented contract examples, **not observations of the user's computer**. D16 allocates 12 GiB/two threads to the assistant, 8 GiB/four vCPU to the guest, with remaining host capacity as reserve. The guest's 8 GiB is part of the host's 32 GiB, not extra capacity. Available memory, disk overhead and qualification still require measurement.

The [workflow example](examples/workflow_plan.json) provisionally recommends CPU routing with the existing Qwen/llama.cpp candidate and one trial at a time. Its outcome is INSUFFICIENT_EVIDENCE and it cannot authorise execution. Actual throughput/time estimates are absent; D01/D17 are caps, not forecasts.

| Situation | Recommendation / consequence |
|---|---|
| D16-sized host, qualified assistant and VM, fresh capacity sufficient | Use the local V1 workflow under existing limits; still evaluate the fitted model independently |
| 16 GiB host or missing VM | Explain the shortfall. Investigate a smaller qualified assistant or serial execution, or attach an approved runner; no assertion that these alternatives already work |
| Visible but unqualified GPU | Keep CPU route if it fits; offer explicit profile qualification. Do not automatically offload or claim SFT readiness |
| Training GPU available but assistant also needs it | Reserve disjoint capacity only if proven safe; otherwise serialise under the declared profile, or retain CPU assistant |
| Paid remote option with zero external grant | Show blocked reason and estimated prerequisites; do not provision. Runpod/CoreWeave/AWS remain customer choices subject to their own gates |
| Colab or ZeroGPU selected | Observe the actual notebook/function allocation in its supported scope. Neither becomes a persistent local-assistant host by inventory discovery |
| No collector or disconnected runner | Accept a labelled manual inventory for provisional planning; require current scoped evidence before execution |

## Ownership and acceptance

PL owns collectors, freshness, reservations and compatibility tests; ML owns sizing assumptions and assistant/workload adequacy; SEC owns diagnostic allowlists and isolation; DO owns inventory sharing and data movement; FIN owns grants; PO owns useful onboarding. The customer operates/pays for local and attached collectors with its host. The platform operates the same module only for expressly managed resources, funded by the separate managed-compute/service terms.

A31–A34 in [delivery_plan.md](delivery_plan.md) test absent-model bootstrap, incomplete/contradictory inventories, resource races and truthful GUI projections. G3 PASS requires those tests on each claimed profile. A false-ready result or bypassed spending/isolation rule is FAIL; unavailable or unqualified capacity is INSUFFICIENT_EVIDENCE. No compatibility evidence exists yet. See [gui_workflow.md](gui_workflow.md) for the visible decision experience.

## Task-aware preparation and output planning

Inputs to feasibility now include file bytes, compressed/decoded expansion estimates, PDF pages, image pixels, table row/column bounds, OCR/layout-model requirements, SQL temporary spill, source assets and export space. Sampling/profile estimates are labelled estimates; unknown expansion uses a conservative bound or refuses the affected job. D20 is a product limit, not a claim that every combination fits D16. Query/parser memory belongs to the existing runner allocation; never add it as fictitious extra host RAM.

Recommend CPU SQL/EDA or classical fitting when appropriate; detecting a GPU does not convert an investigation into fine-tuning. An analysis-only task has no inference-service capacity requirement. A service task needs separate serving discovery/qualification. Local assistant, OCR/extraction model and customer task model are distinct loading/allocation decisions. M1 manual monitors and M2 approved schedules also reserve resources; an idle source does not authorise a scan.

## Joins, library-generated code and desktop placement

Add source counts, candidate discovery coverage, input/output grain, expected cardinality amplification, decoded assets, temporary spill and final export free space to resource estimates. Source-count openness is not unbounded discovery concurrency. Propose staged materialisation when the admitted host cannot hold all data; prohibit silent omission of sources or automatic provider upgrades. D22 is a guard, not evidence that its upper bound fits every query.

Match three profiles separately: desktop/assistant host, execution worker, and output replay/inference target. A TaskCapabilitySpec supplies package/native ABI, accelerator/vendor/driver, memory and operation requirements. Version-matched docs inform estimates but do not prove a target works. Tauri sidecars are built per target; the chosen desktop still needs OS/webview/accessibility and runner-VM evidence. D16 Linux x86-64 is provisional; O24 owns first pilot OS. Record compilation, precision or dependency changes as a new implementation/qualification, never infer support from a detected GPU. See [desktop_experience.md](desktop_experience.md) and [task_expansion.md](task_expansion.md).
