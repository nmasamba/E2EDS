# Product strategy for conversational data science and AI delivery

Planning edition **0.7.0** · 29 September 2026. Architecture and delivery proposals are unimplemented; upstream facts retain their own verification dates. No compute is provisioned or purchased by this plan.

The product offers a reliable path from unfamiliar data and a user question to a reproducible analysis, reusable dataset or accepted service release. It does not require customers to buy GPU capacity from the platform. Buyer, pricing and adoption claims below remain hypotheses.

## Initial buyer, user and trigger

Recommend an initial buyer hypothesis of **Head of Data/Engineering in a small data-rich B2B team**, with 2–10 practitioners as a discovery filter, not an established market segment. The primary daily user is a **data scientist**. Software engineers investigating an unfamiliar dataset are first-class users from M1; AI/ML engineers add specialised model/application development. Restrict initial pilots by risk, data size and task readiness rather than by document-intake industry.

The adoption trigger is a concrete question and a messy, mixed-format data bundle: the user needs trustworthy joins, quality findings, an explanatory analysis or baseline predictor, with code they can inspect and reuse. Some tasks end at analysis; others must cross the handoff to an operational service. Test both journeys against the customer's existing notebook/SQL/IDE workflow. No training or deployment ceremony is imposed on an exploratory question.

| Persona | Job to accomplish | First useful surface | Evidence of value |
|---|---|---|---|
| Data scientist — primary | Prepare data, investigate, fit and explain an appropriate baseline | Conversation, gold-table explorer, code/notebook/report | Time to checked insight; correction burden; reproducibility |
| Software engineer — first-class | Understand schemas, keys, relationships and data behaviour; reuse a script or integrate output | Data preview/dictionary, SQL/Python diffs, export and optional API | Time to correct answer; join/interpretation errors; successful reuse |
| AI/ML engineer | Develop grounded applications, tune models and adapt weights | Task-specific contracts, experiments and evidence | Useful quality/cost trade-offs and release effort |
| Platform operator | Bind compute, install, monitor and recover | Hardware/plan view, manifests and runbooks | Unassisted installation, recovery and operating cost |
| Reviewer/domain/data owner | Validate meaning, rights, important claims and acceptance | Lineage, quality findings and task-specific report | Review time and resolved material findings |
| Publisher | Maintain private recipes, analysis packs and service releases | Catalogue, rights and version history | Repeat adoption and maintenance burden |

The interface supplies guidance; it cannot infer authoritative business meaning or data rights. Domain experts remain accountable for grain, units, error costs and use. No customer, interview, pilot or demand has been established.

## Value and build-versus-integrate boundary

Promise: “Bring your data and question; develop a checked, reproducible answer or deployable capability with code, provenance and continuing control.” Sell reduced time and uncertainty across preparation, analysis and operational handoff. General-purpose code generation alone is not a defensible business.

Potential durable assets are reusable task-specific data/evaluation contracts, compatibility evidence, packaging and operating experience, and trusted release history. These become advantages only if customers repeatedly reuse them. Generating an API or MCP wrapper is readily replicated. Customer data and cross-tenant learning are not assumed to be a moat.

### Build-versus-buy decision

| Option / current evidence | What it already solves | Our remaining proposed contribution | Decision / trade-off |
|---|---|---|---|
| MLflow 3.16.1 [S01–S03] | ML tracking/registry, GenAI tracing/evaluation/prompts, model serving; current docs also expose MCP-related functions | Independent final-evaluation authority, workload admission/budget contracts, complete application release dossier, recipient acceptance | Integrate; do not rebuild tracker or treat its registry as the release-policy authority. |
| W&B / Weave [S20] | Experiment/artifact tracking, evaluation and tracing; current catalogue includes SFT/RL/inference products | Test whether cross-environment handoff and domain evidence justify an additional layer | Benchmark existing workflow during discovery. Do not claim these platforms lack governance or deployment. |
| LangSmith [S21] | Agent/application observability, evaluation, deployment and commercial collaboration | A common release contract spanning classical fitting and weight training as well as applications | Integrate trace exports later; no initial LangChain dependency. |
| Databricks managed MLflow/model serving [S25] | Registered custom models, managed scoring; pyfunc can include processing | Customer-independent release contract and installation outside that managed environment | Offer a later adapter if partners already use it. Native serving is not an arbitrary HTTP/MCP host. |
| BentoML [S17] | Packages service code, dependencies and model artifacts; OCI path | Evaluation authority, budgets, release rights and recipient acceptance | Keep behind a future builder adapter; start with minimal typed service. Revisit at batching/GPU composition need. |
| Existing notebooks/SQL/IDE + customer stack + CI templates | May already provide enough tracking, identity and deployment | Possibly a preparation/analysis toolkit is sufficient; measure whether the full lifecycle adds value | Explicit competitive baseline. If a template solves the problem, avoid selling a replacement platform. |

These are documented capability comparisons, not independent performance benchmarks. Pricing plans describe vendor terms, not willingness to pay for this product. The proposed integration boundary is small: use library estimators and Optuna; use PyTorch/Transformers/PEFT/TRL later; use official MCP SDK; use standard schemas, containers and telemetry. Own the links and enforcement between stages that prevent an attractive score becoming an unsupported operational claim.

Provider execution is an integrated commodity capability: Colab supplies the interactive environment, HF Jobs and Runpod supply execution primitives, and CoreWeave/AWS can supply an established customer estate [S35–S42]. Integrate those primitives. The proposed contribution is consistent authority, evaluation evidence and recipient release acceptance across the selected profiles. GPU brokerage and connector count alone do not establish differentiated value.

## Catalogue products

| Product | Buyer receives | Acceptance requirement | Recurring obligation |
|---|---|---|---|
| Trainable recipe | Versioned method, data contract, bounded search/evaluation instructions and compatible adapter | Rights and dataset fit review; customer-specific training and evaluation | Recipe maintenance and dependency/security updates |
| Deployable release | Signed application bundle, model/dependency graph, interfaces, evidence and supported profiles | Install/preflight plus relevant customer-data evaluation | Customer operates; publisher supports only contracted versions/profiles |
| Managed service | Versioned endpoint and evidence with service agreement | Provider qualification, privacy/residency, task acceptance and operational SLO | Platform operator pays infrastructure then charges transparently; customer owns intended use and outcomes |

Start with first-party recipes, private analysis/data packs and private customer service releases. An analysis pack is a deployable/reproducible recipe output, not a fourth managed endpoint product; label it explicitly with AnalysisReleaseManifest and no endpoint promise. A listing must distinguish “ready to install on profile X” from “validated on customer Y's workload”. Customer-specific artifacts are private unless rights explicitly permit distribution.

## The primary product surface

Use the stage rail, expanding activity/artifact canvas and interactive report specified in [gui_workflow.md](gui_workflow.md). The supplied Bridgewater screenshots guide presentation, while the platform's own independent evaluation, release and operating gates determine the lifecycle. [Hardware discovery](hardware_discovery_and_planning.md) helps users avoid an infeasible setup before model loading, and records why a workflow is recommended. Inspectable decisions and controlled intervention are adoption hypotheses, not proof of defensibility or customer value.

## Adoption through customer-supplied compute

1. **Start with guided local setup:** open the workspace without hosted sign-up or a loaded model. Deterministic discovery shows selected-host capacity and gaps; register approved compute and qualify the assistant. Describe the task in the persistent conversation and review its typed interpretation and explainable workflow recommendation. Hardware alone does not select the task or authorise paid compute. A hosted subscription is not needed for the basic runner.
2. **Prove the requested output:** run a tabular/mixed-format preparation and EDA task, then a real classification/regression task through the common workload contract. Export the requested analysis pack or full inference pipeline and evidence. Use Colab interactively or customer-funded Runpod when that profile and account pass admission.
3. **Handoff independently:** give the recipient the release, compatible serving profile, data/dependency binding instructions and evaluation protocol. Verify HTTP/MCP and recovery without the training account or author.
4. **Add team coordination:** pay for shared review, approvals, history, private catalogue, fleet administration and support when those reduce measured handoff work. Keep essential security and export in every tier.
5. **Maintain deliberately:** propose and evaluate new releases when outcomes, data or dependencies warrant it. Updates use the same rights, budget and promotion rules.
6. **Offer controlled demonstrations:** after qualification, ZeroGPU may expose a curated first-party example. Public exposure requires G5. It is an acquisition experiment with external quotas, not private customer training or proof of commercial demand.

## Pilot hypotheses and stop rules

All numbers below are proposals owned by the Product Owner, agreed with a buyer at G0; none is a result.

| Hypothesis | Proposed experiment and evidence | Decision rule |
|---|---|---|
| H1: preparation/analysis and handoff are material repeated problems | 8–12 discovery interviews; inspect at least 3 actual recent data investigations or handoffs and their artefacts, with consent | Proceed if at least 3 qualified teams identify an upcoming analysis or service task, owner and measurable pain; otherwise narrow or stop. |
| H2: workspace saves work beyond notebooks/SQL/IDE and MLflow/CI | Within-partner comparison against an existing analysis/handoff, with similar task complexity; record engineering/reviewer/operator hours | Target ≥30% reduction in median end-to-end human effort, with uncertainty and confounders reported; small samples give directional evidence only. |
| H3: independent operation is usable | Two recipient organisations or independent teams install supported bundles without the author present | Both complete evaluation/client/restore walkthrough; unresolved author-only steps block G3. |
| H4: output improves the actual workflow | Task-specific paired customer exercises: analysis claim correctness/time, predictive error/review load, or grounded-answer correction effort | Meet signed quality/cost contract; no promotion on synthetic results alone. |
| H5: there is paid demand | Offer a scoped paid pilot and transparent Team terms; collect budget-owner decisions and rejection reasons | At least 2 paid pilot commitments before hosted general availability; quote acceptance, not survey enthusiasm. |
| H6: repeat use creates a product | Observe a second workload/release within 60 days after acceptance | At least 2 partners independently repeat; otherwise consider a consulting/toolkit business. |
| H7: compute portability reduces setup/recovery burden | Same business/data/evaluation contract on local and qualified Runpod bindings; Colab export exercise; independent recipient install | A17–A22 and recipient walkthrough pass for the declared modes; report setup/support hours and total cost; qualify customer value through H2/H4/H5. |
| H9: early discovery and visible workflow reduce setup/control errors | Observe manual versus guided setup, time to first admitted task, false-ready recommendations and users explaining stage/plan/change consequences | PO/PL freeze pilot criteria before observations. Any unsafe false-ready admission fails the affected G3 gate; small-sample preference alone does not prove value. |

The 30% effort target is chosen to be noticeable against integration and switching costs, not from a benchmark. Record baseline team experience, scope and release complexity. Do not infer market size or statistically robust conversion from three partners.

## AI assistance informed by the attachment

The attachment's workflow concepts become explicit assistive features: turn a goal into a reviewable plan; suggest data-quality checks and transformations; draft notebook explanations/plots; propose suitable simple baselines; help diagnose execution failures; explain trade-offs and assemble a release report. Every suggestion cites the inspected manifest or run output. A model does not attest that a run happened or invent figures for an HTML report.

Plain language and an interruptible conversation are required in M1. The local assistant writes Python/SQL and notebook cells, submits them through restricted tools, inspects actual results and repairs bounded errors. Immutable source snapshots, sandbox policy and the independent evaluator constrain that loop. Users see the plan, code changes, progress, spend and evidence and can pause, cancel or revise requirements by text. A local model enables this experience without hosted provider access; CLI/forms remain secondary and degraded recovery paths. Model capability must be qualified, not assumed from parameter count. See [local_model_runtime.md](local_model_runtime.md) and [conversational_control.md](conversational_control.md). M1 includes bounded tabular, text, PDF and image ingestion/qualified OCR, as specified in data_products_and_tasks.md. General vision, audio/video and arbitrary document formats remain later capabilities.

Pilot hypothesis H8: a local conversational agent reduces engineer correction/handoff time without losing explicit requirements. Compare assisted and manual completion of the same scoped tasks, including interruptions; measure complete-release rate, errors, elapsed human time and local setup/support minutes. PO/EO own the paired pilot design; do not declare value from chat satisfaction alone. Assistant-generated code and API wrappers already exist in the market: the value proposition remains controlled evidence and independent service handoff, with usable intervention throughout.

## Product scope and support boundary

M1 is a general data workspace with bounded formats and tasks: ETL to linked task-ready products; descriptive analysis; actual tabular classification/regression; and a complete installed-service path. The support-routing recipe remains a useful text-classification fixture. M1B adds grounded extraction, summarisation and lexical RAG before team hosting; M3 expands evaluated generative configuration choices. A data scientist or software engineer can receive a complete analysis release without training a model or operating an API.

The platform owns typed intent/data/output contracts, code-task authority, evaluation integrity, reproducible evidence and a task-oriented user experience. Integrate DuckDB/Parquet and a replaceable Docling parser [S52–S56], tracking, model libraries and provider primitives. Existing analytical and agent tools already cover much of this work; pilots must show that continuity across data, code, intervention and versioned evidence removes real work beyond those tools.

Keep provider-neutral customer compute and private-catalogue-first delivery. Core preparation, local assistant, analysis, code export, essential privacy and manual output checks belong in the free local software. Team fees fund coordination, shared history/approvals, maintained integrations and support. Actual PEFT/SFT and resettable customer-agent workloads follow in M4. The platform's own development agent remains M1.

Add H10: at least one data scientist and one software engineer complete both a tabular investigation and a document/text preparation task without author assistance; record failures, minutes, corrections and artifact reuse. PO/EO freeze task-specific success criteria at G0. Add H11: at least two partners use a second task type within 60 days; failure suggests a narrower toolkit or service business rather than a general platform. These are proposed evidence gates, not customer claims.

## Multi-source desktop adoption and expansion

The primary experience is a native desktop research workspace that starts its local harness and writes useful versioned files. The adoption trigger is now concrete: a data scientist or software engineer has several unfamiliar tables/documents/assets, needs to establish their relationships and answer a question, and wants code plus checked outputs without assembling a notebook environment or hosting an endpoint. Private multi-dataset collections are open-ended; bounded per-run quotas remain. The saved analysis pack is useful before model training is justified.

H8 (PROPOSED): design partners repeatedly need cross-source interpretation and inspect/correct at least one meaningful join or grain assumption; measure correction time and independently checked output quality. H9: users can launch the desktop, locate a running task, pause it and find a reproducible folder without CLI assistance; observe errors and support time. H10: docs-assisted generated implementations reduce time for an unfamiliar task without increasing invalid scientific claims, unsafe dependencies or target-profile failures. PO/EO/UX own these pilot tests; no demand, success rate or willingness to pay is established.

Unsloth's current local UI/training and file-oriented features [S62] join MLflow, notebooks/IDE coding agents and data-preparation tools in the alternatives set. Integrate its reviewed Core training functionality only when an E5 recipe justifies it; do not copy or bundle the separately licensed UI. The value hypothesis is accountable multi-source semantics, continuous intervention and independently reproducible outputs across analysis and services. API/MCP generation, attractive UI and generic code generation alone are insufficient differentiation.

Recommend the bounded M1 multi-source/desktop slice first, then E1 clustering/anomaly or a higher-value partner task. [task_expansion.md](task_expansion.md) records the wider category programme without implying that all upstream functions/models are already supported. See [desktop_experience.md](desktop_experience.md) for the primary GUI and filesystem path.
