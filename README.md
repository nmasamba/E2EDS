# Training & Inference Platform — desktop data science and AI workspace

Planning edition **0.7.0** · 29 September 2026. Architecture and delivery proposals are unimplemented; upstream facts retain their own verification dates. No compute is provisioned or purchased by this plan.

Build a **GUI-native, general conversational data-science and AI platform** for data scientists, software engineers and AI/ML engineers. Given any number of authorised datasets, a task, existing code, constraints and compute, it discovers and explains relationships, prepares governed datasets, loads/amends/writes Python or SQL, inspects actual results, evaluates them honestly, and produces a versioned output in a chosen filesystem folder or, when requested and qualified, an installed service. Users retain an open conversation and can pause, cancel or change requirements throughout.

The initial buyer hypothesis is a Head of Data/Engineering in a small data-rich B2B team. The primary daily user is a **data scientist**; software engineers exploring unfamiliar data are a first-class user group. Document intake is one reference recipe, not the primary product boundary. Start with private projects/catalogue and design partners; demand and willingness to pay remain unverified.

There are **two valid completion paths**: (1) a reproducible data/analysis release containing task-ready data, code, notebook, report and evidence; (2) an evaluated deployable service release with Python, HTTP/MCP and independent installation. This explicitly revises the original service-only requirement R11/ADR23 for exploratory tasks. The platform's job/control interfaces support both paths; a static report does not need its own endpoint.

“Gold” means typed task-ready tables **plus linked source assets, document spans, image references or corpora where needed**. Use Parquet/JSON and embedded DuckDB initially, with replaceable PDF/OCR adapters. Preserve provenance, uncertain extraction and rejected records. Gold preparation must not fit ML preprocessing on final-test data. See [data_products_and_tasks.md](data_products_and_tasks.md).

| Execution option | Role in the recommended plan | Readiness stage |
|---|---|---|
| Local or customer-provided host | Independent core and generic attached runner; customer owns host lifecycle | M1 core; remote attachment in M1R |
| Colab | User-operated notebook training/development with persistent export | M1C interactive profile |
| Runpod | Customer-funded execution; attach first, then delegated provisioning/cleanup | M1R first automated provider integration; actual GPU SFT in M4 |
| Hugging Face ZeroGPU | Curated, bounded generative inference demonstration | Optional M3Z; no generic training or included GPU guarantee |
| Hugging Face Jobs | Batch executor after the common contract is proven | Next adapter, or pilot-led substitution for Runpod |
| AWS, Azure, CoreWeave | Integration with a partner's approved estate | Partner-led qualification, not a default cloud prerequisite |

Basic runner software and reference adapters belong in the proposed Apache-2.0 core. Users pay their provider directly by default. Software access, hosted coordination, operational support and platform-funded compute are separate commercial items. Provider choice does not confer data rights, budget authority or tested compatibility.

The project catalogue has no fixed dataset-count ceiling; ingestion/discovery/materialisation jobs remain bounded by resources and D20/D22. Joins declare keys, grain, cardinality and timing; unrelated sources can stay separate. See [multi_dataset_planning.md](multi_dataset_planning.md).

The platform owns workload/service contracts, evaluation integrity, admission and budget policy, release evidence and the task-oriented data workspace. It integrates tracking, training libraries and provider execution primitives. Provisioning, workload execution and serving have separate contracts; durable coordination/storage has a separately selected host. Colab and ZeroGPU have specific execution roles within this design.

## Hardware-aware onboarding and visible workflow

Start with a lightweight, read-only hardware check **before loading the local assistant**. Inspect the selected execution environment through its installed coordinator/runner; the GUI device may be elsewhere. Show observed capacity, unknowns and qualification separately. Combine task/data needs, approved policies and budget with those findings to recommend an explainable workflow; recheck before dispatch/resume. Detection does not authorise downloads, cloud fallback or spending. See [hardware_discovery_and_planning.md](hardware_discovery_and_planning.md).

Use the Bridgewater screenshots for visible progress and evidence, then develop our own open research workspace: a flowing work trail, optional dataset relationship canvas, editorial report surface, contextual evidence margin and persistent conversation. Avoid a grid of boxed cards; retain accessible tables and familiar controls. Our stages extend through independent evaluation, release and operation. Checkmarks follow committed evidence; self-review never replaces sealed evaluation. Users can pause, cancel or change requirements from the same workspace, with visible impacts on prior results. See [gui_workflow.md](gui_workflow.md). This is a proposed experience, not a reproduction of Bridgewater's implementation or performance.

## What runs locally

The proposed M1 setup is a native desktop shell (Tauri 2.12.0 qualification candidate) that starts or reconnects to a local Python harness/coordinator, SQLite/artifact store, a separate **llama.cpp + Qwen3-8B Q4_K_M assistant**, and a restricted VM for generated Python/SQL. The assistant is the development agent; analysis SQL/Python, fitted scikit-learn pipelines and later generative workloads are separate task artifacts. The GUI is primary; CLI/SDK remains a capable fallback with the same controls and full authorised evidence. Exported inference does not load the assistant or contact the hosted control plane. [desktop_experience.md](desktop_experience.md) specifies launch/close/crash behaviour, visual direction and filesystem delivery.

Propose an **8-core, 32 GiB RAM Linux x86-64 host** for initial qualification, with no GPU requirement for the initial local assistant, bounded ETL and tabular task profiles. This is an estimate, not tested compatibility or a requirement for the much smaller exported service. A GPU is optional for assistant acceleration and separately required by the proposed later SFT profile. Exact pins, offline installation, resource limits, security, ownership and qualification are in [local_model_runtime.md](local_model_runtime.md).

Plain-language input, live evidence-based progress and intervention are **required in M1**. Durable messages/events survive reconnects. Pause/cancel have a control path independent of generation; changes become typed, versioned diffs with explicit effects on results and approvals. Only genuinely material ambiguities or authority changes require a decision. See [conversational_control.md](conversational_control.md).

## Navigation

| File | Review purpose |
|---|---|
| [product_strategy.md](product_strategy.md) | Buyer, value, alternatives, adoption and pilot hypotheses |
| [requirements_and_decisions.md](requirements_and_decisions.md) | Requirements, owners, assumptions, decisions and seven-book traceability |
| [architecture.md](architecture.md) | Components, authority, trust boundaries, lifecycle and failure flows |
| [contracts.md](contracts.md) | Canonical objects and semantic invariants |
| [contracts/](contracts/) | Sixteen draft schemas, including data products, analysis releases and monitoring; versions are listed in contracts.md |
| [examples/](examples/) | Linked, unexecuted lifecycle, assistant/control examples and a separate regression-intent illustration |
| [hardware_discovery_and_planning.md](hardware_discovery_and_planning.md) | Early discovery, environment selection, feasibility rules, freshness and admission |
| [gui_workflow.md](gui_workflow.md) | Stage rail, activity/artifact workspace, continuous conversation and interactive report |
| [local_model_runtime.md](local_model_runtime.md) | Local model setup, hardware estimates, code execution, offline operation and qualification |
| [conversational_control.md](conversational_control.md) | Plain-language intent, live visibility, interruption, revision and recovery semantics |
| [multi_dataset_planning.md](multi_dataset_planning.md) | Open-ended sources, profiling, join graph, cardinality/time semantics and bounded scale |
| [task_expansion.md](task_expansion.md) | Documentation-assisted code changes and scikit-learn/HF/SciPy/arch/Gymnasium/Unsloth expansion |
| [desktop_experience.md](desktop_experience.md) | GUI-native local harness, visual concept, CLI fallback and filesystem bundles |
| [data_products_and_tasks.md](data_products_and_tasks.md) | Raw-to-gold preparation, task matrix, code lifecycle, output kinds and monitoring |
| [data_and_evaluation.md](data_and_evaluation.md) | Splits, acceptance metrics, uncertainty, sealed evaluation, notebooks and report |
| [execution_and_serving.md](execution_and_serving.md) | Adapters, durable jobs, budgets, isolation, HTTP/MCP, runtime profiles and SLOs |
| [compute_backends.md](compute_backends.md) | Provider profiles, attach/provision contracts, ownership, cleanup and qualification |
| [security_and_assurance.md](security_and_assurance.md) | Threats, privacy, rights, jurisdiction, controls and operation |
| [commercial_and_marketplace.md](commercial_and_marketplace.md) | Tiers, unit economics, sensitivity, rights and catalogue evolution |
| [delivery_plan.md](delivery_plan.md) | Milestones, effort, gates, acceptance scenarios and first build-session brief |
| [reference_workload.md](reference_workload.md) | Tabular/mixed-format tasks, support regression recipe and independent acceptance |
| [research_sources.md](research_sources.md) | Dated primary evidence, component revisions and remaining verification |
| [planning_validation.md](planning_validation.md) | Checks on this pack, separate from future product tests |
| [suite_coherence.md](suite_coherence.md) | File-by-file revision audit, shared decisions and consistency checks |
| [SUITE_MANIFEST.json](SUITE_MANIFEST.json) | Planning-suite file inventory and content hashes; not application evidence |

## Shared assumptions

| ID | Proposed default | Consequence / confirmation |
|---|---|---|
| A01 | UK-first low-risk B2B data preparation/analysis, prediction and grounded text tasks; English initial text profile | No clinical, employment, credit or entitlement decisions. Product Owner confirms at G0; jurisdiction remains contextual. |
| A02 | Three design partners, private catalogue | No third-party publisher programme until repeated adoption passes G5. No partners are claimed to exist. |
| A03 | First reference suite covers ETL/EDA plus CPU classification/regression on Linux x86-64/Python 3.12 | This is a workload sizing choice. The architecture is provider-neutral from M1; each notebook/GPU/serving profile needs independent evidence. |
| A04 | Customer-supplied compute and independently installed inference | Attach or delegate resource lifecycle; local SQLite/CAS or qualified collaborative ledger; training provider and hosted coordination are absent from normal installed inference. |
| A05 | No approved money, hardware fleet or cloud account | Example caps express proposed policy, not spending authority. The planner is read-only in this session. |
| A06 | Apache-2.0 local core/specifications; proprietary hosted/team extensions | Legal and commercial review at G0/G4; core export, privacy and secure local operation stay available. |
| A07 | Customer-supplied compute across tiers; local core, Colab interactive, Runpod first proposed automated GPU adapter; ZeroGPU curated demonstration profile | Hugging Face Jobs follows or substitutes on pilot evidence. AWS/Azure/CoreWeave are partner-led. Durable managed hosting remains a separate open decision; no account or expenditure is authorised. |
| A08 | No arbitrary customer code in shared hosted free demos | Curated, signed recipes only; generated/custom code requires a qualified isolation boundary. |
| A09 | Local assistant and conversation are first-release requirements | Candidate runtime/model and D16 hardware are unqualified; G1/G3 must establish useful behaviour. Forms/CLI alone do not fulfil M1. |

## Architectural decisions

1. One modular Python core and typed policy boundary; required native desktop conversation and local harness, independent control path, thin HTTP/MCP and optional demonstration adapters. No initial distributed scheduler, feature store or platform Kubernetes requirement.
2. WorkloadSpec holds task/resources and execution requirements. ExecutionRequest selects an immutable ComputeBinding revision; trusted context supplies authority. Model prose cannot grant permissions, change provider, spend money or inspect final data.
3. Separate provisioner, executor and serving adapter. A successful training job establishes no serving compatibility. Job state, resource cleanup and charge reconciliation remain distinct.
4. Task-appropriate independent checks, sealed evaluation for predictive claims, immutable analysis or full-pipeline service releases and versioned operating bindings. A local owner can bypass local access controls; disclose that assurance limit.
5. One business implementation supplies HTTP/MCP semantics; explicit durable job tools handle long work. Preserve the pinned protocol/client readiness work in the source register.
6. The assistant proposes typed changes and runs generated code through a restricted tool dispatcher. Message history is durable; a new instruction never overwrites an active immutable workload or silently changes production.
7. Improvement proposes experiments and new releases. Human owners approve task, data access, spending, acceptance and operation. Production does not change silently.

## Delivery and evidence

The first meaningful release (M1) accepts bounded CSV/Parquet, text, PDF and PNG/JPEG inputs through qualified parsing/OCR profiles; prepares linked gold data; produces reproducible EDA; actually fits tabular classification and regression; and completes one full Python/HTTP/MCP service handoff. Asset ingestion is not a claim of general image understanding. Missing OCR qualification is visible and blocks OCR claims, not tabular work.

M1B adds grounded extraction/NLU, summarisation and lexical RAG as a local usable slice before requiring hosted collaboration. M1C/M1R qualify Colab and customer-funded Runpod. M2 adds optional team coordination and scheduled monitoring. M3 extends generative search; M4 covers actual weight training and resettable customer-agent simulation. ZeroGPU remains optional curated inference, with no generic training claim. Later E1–E6 waves explicitly expand classical supervised/unsupervised, scientific/time-series, vision/audio/multimodal and training/RL tasks. These are a task-by-task qualification backlog, not current support. Broad hardware and third-party public publishing still require evidence; unconstrained real-world RL remains excluded. Official documentation can guide generated diffs, but cannot replace task, security and target-runtime checks.

[delivery_plan.md](delivery_plan.md) defines owners, revised effort and G0–G5 gates. Feasibility requires real parsing/lineage checks, reproduced analysis, actual fitted baselines, sealed predictive evaluation, code isolation and interruption, and independent service installation. Value requires observed time/correction/support costs and repeat paid use across more than one task type.

## Status vocabulary

* **REQ**: requirement established by the brief. Changing it requires an explicit recorded decision.
* **PROPOSED**: recommended design or target; no owner has approved it merely because it appears here.
* **VERIFIED-EXTERNAL**: a primary source was read on the date recorded in the source register (recorded per source, including 28 September 2026). It establishes the stated upstream fact, not our implementation's behaviour.
* **ESTIMATE**: arithmetic or judgement based on stated assumptions, requiring pilot measurements.
* **OPEN**: consequential choice with owner and gate in the decision register.
* **IMPLEMENTED / TESTED**: reserved for future application evidence. In this pack these labels apply only to document/schema checks explicitly recorded in planning_validation.md.

Examples have `planning_only: true`. Null hashes, absent signatures, pending compatibility and an `INSUFFICIENT_EVIDENCE` report are deliberate. They are not deployable releases or fabricated test results.

## Edition and scope

Edition **0.7.0** makes the desktop GUI/local harness and filesystem output first-class, adds open-ended multi-dataset collection/join planning, and extends the task backlog through versioned documentation-assisted code adaptation. All prior Markdown documents are substantively revised or regenerated, including this README. The four ML/AI families plus data-analysis path remain distinct. R11/ADR23 still allows analysis releases; operational capabilities retain full release/interface/evaluation gates.

The pack contains **23 Markdown documents, 16 schemas, 22 example files and a suite inventory: 62 files**, plus the ZIP of that tree. New contracts cover DatasetCollectionManifest, JoinPlan, TaskCapabilitySpec and OutputBinding; WorkloadSpec/DataProductManifest advance to draft 0.6.0. API version 1.0.0 and reference release 0.1.0 are unchanged. Example hashes/measurements remain null and approvals absent.

M1 is estimated at **95–145 person-days** for the complete defined slice; M1B adds **12–18**. The next concrete milestone is a native window and local harness that selects source/output folders, profiles several datasets, explains and validates a join, supports pause/resume, and exports a reproduced analysis pack. M1 completion additionally fits classification/regression and proves independent Python/HTTP/MCP service installation. No application is implemented here.

The major decisions are first pilot desktop OS/profile (O24), representative multi-source data/scale/semantics (O20/O21), first expansion recipes (O22), exact dependency/model rights and locks (O23), and demonstrated buyer value/funding. They gate their affected work; routine reversible choices continue under proposed defaults. Google Cloud-specific references from the original attachment remain excluded; user-requested Colab is still an explicit interactive compute profile.
