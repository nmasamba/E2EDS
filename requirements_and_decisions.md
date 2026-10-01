# Requirements and decisions for customer-supplied compute

Planning edition **0.7.0** · 29 September 2026. Architecture and delivery proposals are unimplemented; upstream facts retain their own verification dates. No compute is provisioned or purchased by this plan.

These tables are the suite-wide authority for requirements R01–R27, defaults D01–D24 and decision owners. M1 covers bounded preparation/EDA and classification/regression; the platform architecture supports qualified attached, interactive, delegated and curated-function paths. Numerical targets remain proposals until approved.

## Established requirements

| ID | Requirement | First evidence / owner |
|---|---|---|
| R01 | Four distinct ML/AI families remain: classical fitting, generative application optimisation, generative weight training, agent evaluation/adaptation; data_analysis is a separate non-training path | Adapter capability matrix; ML Lead; M1/M1B/M3/M4 |
| R02 | Useful free local core, commercially usable, exportable | Offline installation and licence review; Product Owner/Legal; G2 |
| R03 | Customer inference does not depend on hosted control plane per request | Disconnect test; Platform Operator; G3 |
| R04 | HTTP/MCP share application semantics and policy | Golden parity/negative auth cases; Application Lead; G2 |
| R05 | Provenance, sealed evaluation, budgets and tenant separation | Access, budget-race and isolation evidence; Evaluation/Security/Platform; G1/G3 |
| R06 | Improvement cannot silently promote production changes | ChangeProposal and deployment-authorisation audit; Product Owner; G4 |
| R07 | Data, secrets, corpora and customer releases private by default | Export/egress/privacy checks; Data Owner/Security; G0/G3 |
| R08 | Software, coordination and compute priced separately | Entitlement/UsageRecord reconciliation; Finance; G4 |
| R09 | Replaceable backends with declared compatibility | Independent installation by supported profile; Platform; G3 |
| R10 | Enterprise controls have evidence and accountable owners | ObligationControlMapping plus exceptions; Compliance; G4 |
| R11 | Revised by latest user direction/ADR23: versioned reproducible data/analysis release for exploration; full deployable service release for operational capabilities | AnalysisReleaseManifest or ReleaseManifest with evidence; no bare notebook or score; PUB/PO; G2 |
| R12 | Small useful system and private-catalogue-first investigation | Buyer evidence and reuse; Product Owner; G0/G5 |
| R13 | Bring customer-supplied compute through a qualified attached host or delegated provider account; available in basic local core | ComputeBinding, preflight and portability tests; PL/SEC; M1R/G3 |
| R14 | Colab interactive execution and ZeroGPU curated demos are explicit profiles; provisioning, execution and serving are independently qualified | Profile matrix and capability-denial tests; PL/PO; M1C/M1R/M3Z |
| R15 | Plain language is the primary M1 input; durable conversation, visible real progress and pause/cancel/resume/change instructions remain available during work | A24–A27; PO/Application Lead/PL; M1 G3 |
| R16 | Local assistant proposes plans and generates/executes data-science code through controlled tools; no requirement for hosted model access | Assistant qualification and containment A28/A30; ML/SEC/PL; M1 G1/G3 |
| R17 | User field roles, feature constraints and output transforms become typed, enforced requirements with provenance; changes create reviewed revisions | A26/A29; ML/EO/DO; G1/G2 |
| R18 | Development assistant and workload/service models have separate bindings, resource budgets, versions and readiness evidence | D16/D17, export without assistant A30; PL/PUB; G2/G3 |
| R19 | Recommended requirement: discover the selected environment before assistant load and recheck at admission; rank workflows by task, capacity, policy and budget with honest unknowns | Proposed ADR21; A31–A33; PL/ML/SEC; G3 |
| R20 | GUI follows a visible stage-and-artifact workflow with continuous conversation and interactive evidence, extending through independent evaluation and release | User direction; proposed ADR22; A34; PO/Application Lead/EO; M1/G2/G3 |
| R21 | Accept bounded tabular, PDF, image and text inputs; prepare governed task-ready tables with linked assets and provenance | User direction; D20, A35/A36; DO/ML/SEC; M1 G1/G3 |
| R22 | Load, amend or generate Python/SQL/notebook code and produce analysis, classification/regression, NLU/RAG/summarisation through explicit task adapters | User direction; task matrix in data_products_and_tasks.md; ML/EO; M1/M1B |
| R24 | Open-ended dataset collections, bounded profiling and evidence-backed relationship/join planning; never force unrelated sources together | User direction; ADR26/D22; A39–A41; DO/DE/ML/PL; M1 |
| R25 | Expand across requested library task categories through documented code adaptation and qualified task/runtime contracts | User direction; ADR27; task_expansion.md; A42/A43; ML/EO/SEC; M1 mechanism, later E1–E6 |
| R26 | Desktop GUI is primary and starts/reconnects to a local harness; CLI/SDK is a capable fallback with equivalent controls/evidence | User direction; ADR28; A44; PO/UX/PL/SEC; M1 |
| R27 | Deliver versioned outputs to the user's authorised filesystem, independently of endpoint startup; preserve service interfaces where applicable | User direction; ADR29/D23; A45; PUB/DO/PL; M1 |
| R23 | Version and monitor datasets, analyses and operational releases, with owners, explicit schedules and controlled changes | User direction; MonitoringSpec, A37/A38; DO/analysis owner/SO; M1 manual, M2 scheduled |

Nonfunctional requirements: deny-by-default authorisation; durable accepted jobs; no duplicate committed results; bounded resource use; recoverable authoritative state; documented unsupported guarantees; schema evolution; deletion propagation; accessible diagnosis of failed/inconclusive outcomes. Observability must not copy raw customer content by default.

## Shared proposed defaults

| ID | Default | Rationale, evidence needed and decision owner |
|---|---|---|
| D01 | Classical reference envelope: ≤12 trials, 1 concurrent, 4 vCPU, 8 GiB RAM, no GPU required, ≤2 hours execution, ≤10 GiB scratch | Provider-independent workload sizing; compare observed binding resources at preflight. CPU fit is one initial lifecycle proof, not a platform hardware restriction; ML/PL, G1/G3. |
| D02 | External charges default £0.00; examples use GBP integer minor units | Demonstrator needs no paid provider. Nonzero grants require Finance-approved trusted context. |
| D03 | Worker heartbeat 15 s; lease 60 s; controlled local process termination target 30 s after cancellation notice; at most 2 automatic retries after the initial attempt for eligible transient failures | Remote termination is requested and reconciled, never assumed within 30 s. Detect orphaned work with finite overlap; crash/partition tests at G3; Platform Operator |
| D04 | Support reference route request ≤64 KiB UTF-8 JSON, text ≤20,000 characters; 30 s server deadline; warm profile 2 vCPU/4 GiB, 5 requests/s, burst 10 | Protect small service; measure Unicode bytes, memory, load/cold start; Application/Platform Leads |
| D05 | Job submission ≤1 MiB manifest, data/artifacts via separate bounded transfer; one logical idempotency key per tenant+operation+payload | Avoid queue as bulk data transport; race and retry evidence; Platform Lead |
| D06 | Idempotency records retained 7 days after terminal state; caller retry window 7 days | Proposed balance between recovery and storage; business effects may require longer durable action ledger; service owner |
| D07 | Free hosted: 1 user, 2 private projects, 100 task/trial records/month shared pool, 1 GB retained results/traces, 30-day expiry | Metadata coordination including zero-trial preparation/analysis, not 100 free training jobs. Additional quotas and cost evidence in commercial plan; Product/Finance |
| D08 | No raw production prompts/documents in telemetry by default; operational metrics 30 days free, 90 days Team; evidence retained under agreed project policy | Minimise sensitive copies; costs/deletion drill at G3; Data Owner |
| D09 | Routing demo: 6,000 synthetic cases, grouped 60/20/20 train/tune/final; 4 classes; one sealed evaluation authorisation per frozen finalist | Exercise workflow, not demand proof. Sample size and anti-template leakage reviewed by Evaluation Owner at G0. |
| D10 | Sealed evaluation returns aggregate report to optimiser; case-level failures restricted to evaluator/domain reviewers | Limit adaptive leakage; final-set access ledger and export tests at G1; Evaluation Owner |
| D11 | Proposed managed coordination/qualified service availability 99.5% monthly; warm V1 routing p95 ≤300 ms at D04; no free/shared-compute SLA | Scope each promise by component, provider dependencies and operator; Colab/ZeroGPU allowances are not included capacity commitments; SO, G3/G4. |
| D12 | Evaluation outcomes: PASS, FAIL, INSUFFICIENT_EVIDENCE; gate outcomes use the same meanings | Unknown evidence cannot turn into acceptance; Evaluation Owner |
| D13 | One active attempt per initial remote binding; no cross-provider automatic fallback; no paid execution without an explicit trusted grant | Limits blast radius and unreviewed data movement; A17–A23; PL/DO/FIN |
| D14 | Optional ZeroGPU demo: one curated operation, one active call per platform identity, proposed 30-second application execution target and 120-second total response deadline; no paid overflow enabled by our adapter | Small demo scope, independent of vendor allowances; benchmark at M3Z, PO/PL. No latency or availability guarantee. |
| D15 | Provider-resource reconciliation every 60 seconds; proposed idle stop request after 300 seconds for platform-created interactive resources; batch resources released at terminal execution | PL validates provider minimums/cleanup latency at G3; attached customer resources are never destroyed by this policy. Verified deletion, retained-storage decisions and settled charges remain separate. |
| D16 | Initial combined local development host: Linux x86-64, 8 logical CPU cores, 32 GiB RAM, 30 GiB free disk; assistant cap 12 GiB/2 CPU threads; restricted runner VM 8 GiB/4 vCPU | Estimated from 5.03 GB model plus runtime/cache, D01 workload and host reserve. No GPU required for the CPU qualification candidate. PL/ML measure at G1/G3; D04 exported service remains separate. |
| D17 | Assistant: 8,192 total tokens (≤6,144 input / ≤2,048 output), 1 generation, 300 s per call; ≤20 calls, ≤2 code repairs and ≤1,800 s cumulative generation per task | Bounded context/cost/loops; first limit reached stops generation. Test adequacy, context preservation and CPU responsiveness, then revise openly; ML/EO/PO at G1. No speed claim. |
| D18 | Conversation text ≤16 KiB; authorised explicit pause/cancel acceptance p95 ≤2 s under local qualification load; safe drain ≤30 s for controlled local work | Separate command durability from actual stopping; unknown remote work is not stopped. PL/SEC/PO test hung model/runner, reconnect and races at G3. |
| D19 | Passive discovery: ≤2 s per probe, ≤10 s total; availability display stale after 60 s; fresh relevant checks at every dispatch/resume regardless of display age | Proposed responsiveness/freshness limits, not benchmarks; unknown findings preserve setup access. PL/PO measure at A31/A33/G3. Runtime smoke checks use separate authorised resource limits. |
| D20 | Initial ingestion batch: ≤100 files, ≤250 MiB total, ≤50 MiB/file, ≤500 PDF pages total, ≤25 megapixels/decoded image/page, ≤100,000 rows and ≤200 columns/table | Bound parser expansion and local support; no silent truncation or project dataset-count ceiling. A materialisation also satisfies D22. PL/DO/PO qualify actual formats/resources at A35/G3, revise on measured workloads. Hosted quotas may be smaller. |
| D21 | Analysis path: zero optimisation trials/concurrent trials, one bounded job at a time within D01 CPU/RAM/scratch/2-hour envelope; manual monitoring by default | EDA is not training. D17 still caps assistant calls/repairs. Scheduled checks require owner, source authority, cadence and reservation; DO/PL/FIN; M1/M2. |
| D22 | Initial materialisation: ≤100,000 rows and ≤200 columns/output table; output/anchor row ratio ≤2; D01/D21 job resource bounds; stricter declared grain invariants take precedence | Conservative join-explosion guard, not a measured scale limit. DO/PL/EO qualify actual counts/cardinality/spill; explicit larger profile or partitioning required beyond it. |
| D23 | Filesystem output defaults to a new version directory under an explicitly scoped root; no silent overwrite, source mutation or endpoint startup | PUB/PL/SEC test path/race/disk-full/cancel/commit receipts at A45/G2/G3; preserve prior good output. |
| D24 | Desktop close with active work defaults to pause-then-quit; user may explicitly choose background continuation, recorded per workspace | PO/PL test crash/sleep/quit/reconnect and remote reconciliation at A44/G3. Closing observation is not cancellation; no background guarantee on a sleeping machine. |

GB means decimal storage billing units; GiB means binary memory/scratch allocation. Times are UTC RFC 3339; durations are seconds; latencies use milliseconds. Currency values must include ISO 4217 currency; no implicit conversion.


## Intake and assumption provenance

Each inferred field records JSON Pointer, typed proposed value, source reference (user statement, uploaded artifact, authorised system observation or model proposal), extraction confidence, materiality, confirmation status and confirming actor/time. Extraction confidence estimates interpretation certainty only; it is not model quality, legal certainty or decision probability. Preserve original text separately with access/retention controls.

| Intake domain | Required fields / validation |
|---|---|
| Purpose | Requested output kind (analysis_release or service_release), task kind, business task, intended/prohibited use, workflow, end users, affected parties, outcome owner |
| Baseline and impact | Current deterministic/manual method; FN/FP/misroute costs, abstention/review/delay costs with units and ranges |
| Data | Collection membership and per-source roles/rights, source formats, proposed relationship graph, table grain/keys/relations, gold quality checks and linked asset semantics; snapshot references, label availability/time, modality, language, geography, owner, purposes, redistribution/training rights |
| Existing estate | Imported code/repository/notebook revision and permitted edit scope, model/provider revisions, tools, stores, identity, approved infrastructure |
| Compute choice | Attach existing host or delegate provisioning; provider/account/region; credential references; operator/payer; resource ownership; quota/rate evidence; alternative profiles permitted by DO/FIN |
| Hardware | OS/version, ISA, CPU cores/features, RAM, GPU model/count/VRAM/driver/runtime, disk, connectivity; discovered values independently attested |
| Governance | Residency, categories/sensitivity, retention, connectivity, jurisdictions, affected people and output-use locations |
| Economics/operations | Experiment cap, concurrency, traffic/load distribution, latency/availability needs, inference budget and support expectation |
| Delivery/rights | Desktop OS and filesystem bundle/endpoint/both, scoped output root and conflict policy; local/customer cloud/on-prem/disconnected/managed; private/internal/commercial intent; operator and payer |

User prose saying “I am admin”, “ignore the budget” or “publish these weights” never supplies identity, permissions, entitlement or spending authority. The server attaches trusted tenancy and approved grants after validation. A WorkloadSpec can request resources but cannot grant them. Material ambiguities affecting data rights, safety, budget or deployment block only the affected stage; reversible formatting choices do not.

The first-release intake is a persistent conversation, with structured forms as a secondary view. Field roles distinguish entity ID, row ID, predictor, target and split group; IDs preserve their declared string semantics and are excluded from predictors by default. Feature objectives distinguish hard limits from soft preferences and specify counting units. Output rules fix increment, units, tie behaviour and raw-value exposure. “Anonymise by rounding” is represented as a precision transform plus an unresolved privacy requirement, not asserted anonymity. [conversational_control.md](conversational_control.md) defines source/confirmation, change impact and truthful intervention states.

The assistant can generate and run code inside an approved task envelope without approval for each cell. New permissions, data movement, budgets, final criteria and production promotion still require their owners. Live control authorization comes from authenticated context; uploaded content and quoted text cannot cancel or change work.

## Decision rights

| Role | Accountable decisions | Cannot unilaterally do |
|---|---|---|
| UX Owner (UX) | Desktop task comprehension, accessibility, visual hierarchy and intervention usability | Convert decorative status into execution evidence or waive security controls |
| Product Owner (PO) | Intended use, buyer, workflow acceptance, release approval | Override data rights, security or evaluator results |
| Domain Expert (DE) | Label rubric, error costs, relevance of slices, human impact | Change final labels after seeing candidate identities without audited adjudication |
| Data Owner (DO) | Access, purposes, retention, sharing, deletion response | Claim source-row deletion erases learned information |
| Analysis Owner (AO; usually the data scientist) | Scope and meaning of descriptive findings, reproducibility acceptance, report/version upkeep and monitoring requests; works with DO/DE/EO | Turn exploratory correlation into causal evidence or approve source access/budgets alone |
| ML/AI Lead (ML) | Recipes, bounded search, reproducibility evidence | Read sealed final examples as optimiser or choose an easier oracle |
| Evaluation Owner (EO) | Frozen contract, independent final evaluation, evidence sufficiency | Promote a release or bill a customer |
| Platform/IT Operator (PL) | Qualify bindings and adapters; own delegated resources, reconciliation, recovery and fleet operation | Delete unrelated attached resources, equate a provider product label with isolation, or infer business acceptance from uptime |
| Security Reviewer (SEC) | Threat acceptance, identity/egress/isolation controls | Waive another owner's legal obligations |
| Compliance/Legal Reviewer (CL) | Applicability, licence and contractual review | Certify all customer uses automatically |
| Finance/Budget Owner (FIN) | Trusted grants, native-currency rate evidence, uncertainty margins, cleanup reserves and payer attribution | Treat a provider account/API key as unlimited spending authority or infer invoice settlement from cancellation |
| Publisher (PUB) | Package integrity, distribution rights and listing claims | Publish customer-specific releases without rights |
| Service Operator (SO) | Deployment acceptance, SLOs, monitoring, incident response | Treat release approval as acceptance of unstaffed 24/7 operation |

Roles may be held by one person in a small local trial, with a visible conflict declaration. Managed customer acceptance requires separate optimiser/evaluator credentials; PO and SO provide separate release and operational decisions. SEC/DO/CL retain domain-specific vetoes. Exceptions have scope, expiry, compensating controls and the relevant owner, never an LLM approver.

## Prioritised architecture decisions

| ADR | Recommendation and alternative | Status / owner / gate |
|---|---|---|
| ADR01 | Start private general data workspace with tabular/mixed-format reference suite; alternative narrow intake-only product or public marketplace | PROPOSED; PO; G0 |
| ADR02 | Modular monolith + transactional job ledger; alternative broker/workflow engine | PROPOSED; PL; M1/G3. Add engine only for measured orchestration burden. |
| ADR03 | Customer or platform authority uses SQLite/local CAS for single-user operation and PostgreSQL/object store for collaboration; compute providers are not authoritative coordination stores | PROPOSED; PL; G3. One contract across placement options; no hosted sign-up for basic BYOC. |
| ADR04 | MLflow as tracking integration, our ledger as release authority; alternative use tracker as everything | PROPOSED; ML/PL; G1. Canonical exports permit replacement. |
| ADR05 | FastAPI/Pydantic + official MCP Python SDK over one core; alternative BentoML | PROPOSED; Application Lead; G2. BentoML reconsidered for measured batching/GPU composition benefit. |
| ADR06 | Independent evaluator and locked final-set access; alternative optimiser-owned scoring | REQUIRED direction R05; EO/SEC; G1 |
| ADR07 | Dedicated VM boundary for untrusted customer code; curated shared demos; alternative stronger shared sandbox | PROPOSED; SEC; G3. Container alone does not grant malicious-code multi-tenancy. |
| ADR08 | Apache-2.0 core/specifications, generic runner and reference compute adapters; optional proprietary organisation/fleet administration and supported automation | OPEN legal/business ratification; PO/CL; G0/G4. Basic BYOC, local validation, privacy and export cannot depend on a paid connector. |
| ADR09 | Provider-neutral BYOC: local and Colab interactive profiles; Runpod first automated adapter; optional ZeroGPU demo; HF Jobs next or pilot-led substitute; AWS/Azure/CoreWeave partner-led | REVISED direction from user discussion; implementations PROPOSED. PL/DO/PO/FIN; G3 per mode. Durable control-plane host is separately selected. |
| ADR10 | Immutable analysis/data or full application release according to requested output; mutable bindings constrained by policy | REQUIRED direction R11; PUB/PL; G2 |
| ADR11 | Explicit durable job API/MCP tools; no Tasks dependency | PROPOSED based on SDK gap [S12]; Application Lead; G2 |
| ADR12 | Native Python pipeline first; ONNX or other export only after semantic parity evidence | PROPOSED; ML/PUB; G2. Avoid incomplete tokenizer/preprocessing export. |
| ADR13 | Single-process lexical retrieval first; embeddings/index backend only when evaluated benefit exists | PROPOSED; ML; M1B/M3/G1 |
| ADR14 | Framework-neutral agent episodes; configuration search and trajectory SFT before RL | PROPOSED; ML/EO; M4 |
| ADR15 | Separate provisioner, execution adapter and serving adapter; one ComputeBinding capability/policy snapshot and provider request/resource ledger | PROPOSED; PL/SEC/FIN; M1R/G3. Provider names alone never imply supported behaviour. |
| ADR16 | Optional ZeroGPU curated demo profile across tiers; no sustained training or arbitrary tenant code through this adapter | PROPOSED; PO/SEC; M3Z/G3 and public G5 if published |
| ADR17 | Required local conversational development agent; separate model gateway and workload adapters; alternative hosted-only assistant or optional chat rejected for M1 scope | REVISED requirement R15/R16; proposed implementation; PO/ML/PL; G1/G3 |
| ADR18 | Qualify llama.cpp + Qwen3-8B Q4_K_M, CPU profile first; replaceable model/runtime; Ollama optional later | PROPOSED pins [S43–S46], prerelease/runtime licence capture and hardware unqualified; ML/SEC/PL; G1/G2/G3 |
| ADR19 | Durable HTTP messages + SSE/replay; deterministic explicit controls independent of generation; immutable requirement revisions and dispatch fences | PROPOSED; Application Lead/PL; A24–A27/G3; polling fallback for clients |
| ADR20 | Generated Python/SQL executes in a restricted dedicated VM through typed tools, with code hashes and bounded repairs; no raw host shell | PROPOSED extension of ADR07; SEC/ML; A28/G3. Customer-provided guest image first; automatic hypervisor provisioning deferred. |
| ADR21 | Deterministic runner-side discovery and feasibility policy before model loading; separate HardwareSnapshot and immutable WorkflowPlan; alternative browser-only/LLM-estimated inventory rejected | PROPOSED; PL/ML/SEC; A31–A33/G3. No new scheduler, provisioner authority or automatic purchase. |
| ADR22 | Stage rail + activity/artifact canvas + persistent conversation + interactive report over existing ledger/outbox; alternative chat-only or general DAG editor | PROPOSED user-directed experience; PO/Application Lead/EO; A34/G2/G3. Self-check and independent evaluation stay distinct. |
| ADR23 | General task-oriented workspace; analysis release is a valid endpoint; service release mandatory only for operational capability outputs | REVISED product direction from user; R11 correction explicit. PO/ML/PUB; G0/G2. Alternatives: force all tasks into endpoints, or abandon operational handoff; neither recommended. |
| ADR24 | Parquet/JSON task-ready tables plus linked assets, embedded DuckDB and replaceable parser/OCR adapters | PROPOSED; DO/ML/PL/SEC; G1/G3. Alternative flatten all data or mandate distributed lakehouse; loses meaning or adds premature operation. |
| ADR26 | Versioned DatasetCollectionManifest + JoinPlan, bounded discovery and materialisation; no fixed project dataset count and no forced mega-table | PROPOSED; DO/DE/ML/PL; G0/G1/G3. Alternative ad hoc implicit joins cannot preserve meaning or scale coverage. |
| ADR27 | Versioned TaskCapabilitySpec and docs-assisted CodeTask diffs; proposed/experimental/qualified support per operation/profile | PROPOSED; ML/EO/SEC; G1–G3. Alternative unrestricted docs-to-shell generation does not establish semantics, security or portability. |
| ADR28 | GUI-native desktop, Tauri 2.12.0 qualification candidate, per-user Python harness; CLI/SDK fallback | PROPOSED; PO/UX/PL; O24/M0/G3. Replaces browser-first local packaging; domain core and HTTP/MCP contracts remain. |
| ADR29 | First-class filesystem OutputBinding and transactional version-directory export, separate from service startup | PROPOSED; PUB/DO/PL/SEC; G2/G3. Portable releases keep relative paths; local root authority never comes from prose. |
| ADR25 | Version every output; manual MonitoringSpec checks in M1, authorised durable scheduled checks in M2 | PROPOSED; DO/analysis owner/SO/FIN; G3/G4. Alternative endpoint-only monitoring misses stale datasets/reports. |

## Consequential unresolved decisions

| ID / priority | Question and recommendation | Alternatives | Owner / blocking gate |
|---|---|---|---|
| O01 / P0 | Which buyer and reference customer? Qualify data-rich B2B teams with upcoming data investigations or predictive/text tasks; include DS and software-engineer daily users. | Internal enterprise platform team; AI consultancy | PO / customer pilot G0; synthetic M1 may proceed |
| O02 / P0 | Which data and allowed purposes? Customer-authorised tables/documents/text/images with semantic owners; labels only where the task needs them. | Rights-cleared public data; synthetic demo | DO/CL / any customer-data access G0 |
| O03 / P0 | What error costs/thresholds matter? Sign reference contract after workflow observation. | Conservative all-human review | DE/PO/EO / final acceptance G1/G4 |
| O04 / P0 | What budget/hardware/account exists? Begin no external charges and CPU profile. | Approved GPU/provider grants | FIN/PL / admission to paid execution G3 |
| O05 / P0 | Licence boundary and model redistribution? Apache core; explicit capability rights. | Open-only core/service funding | CL/PO / redistribution G2, commercial G4 |
| O06 / P0 | Market/use classification? UK B2B low-risk workflow, with EU applicability screening. | Other market/sector | CL / customer G0 and G4 |
| O07 / P1 | Which first provider account/profile is available? Recommend Runpod single-tenant customer account; HF Jobs if partner already uses it. Durable coordination host remains separately open. | Qualified existing host; partner AWS/Azure/CoreWeave; HF Jobs-first | PL/PO/DO/FIN / affected M1R and G3; local M1 continues |
| O08 / P1 | Team price/support? £249/workspace/month hypothesis, business-hours support. | £99 toolkit or £499 higher support | PO/FIN/SO / G4 |
| O09 / P1 | Exact dependency/image locks, Qwen revision and GPU driver matrix? Spike selected versions before locking. | Older supported patches/smaller model | ML/SEC / G1/G2 for that family |
| O10 / P2 | Public distribution and fees? Wait for ≥2 repeat partners and claim-review process. | First-party-only indefinitely | PO/PUB/CL / G5 |
| O11 / P1 | Provider region, contractual data treatment, isolation and credentials? Begin synthetic inputs on customer account; qualify each deployment. | Dedicated customer VM; restrict provider to nonsensitive work | SEC/DO/CL / real customer data and G3 |
| O12 / P1 | Current rate cards, quota attribution, spending bound and cleanup authority? Use account-specific evidence; default grant remains zero. | Manual provision/cleanup with explicit ownership; different provider | FIN/PL / paid admission and G3 |
| O13 / P2 | ZeroGPU Gradio/spaces versions, rights, visibility and MCP profile? Qualify curated operation and pin dependencies at M3Z. | Keep private local demo; dedicated service deployment | PUB/SEC/Application Lead / M3Z and public G5 |
| O14 / P0 | Is the proposed local assistant useful on available hardware? Qualify the pinned model/runtime and Linux CPU profile first; exact-revision notices/build hashes and guest image remain to be captured. | Smaller/larger reviewed model, older reviewed runtime, separately approved external assistant | ML/PL/SEC/PO / M1 G1/G2/G3; no account/hardware assumed |
| O15 / P1 | What do “minimal”, ID and rounded output mean for a customer? Confirm counting unit, quality trade-off, entity/row identity, target units and privacy need. | Hard feature maximum; different split or output/privacy policy | DE/DO/EO/PO / affected field/pipeline acceptance, not unrelated status or draft work |
| O16 / P1 | Which discovery/runtime profiles can be qualified? Start with D16 Linux CPU host plus supplied VM; distinguish unknown from unsupported. | Later smaller-memory, GPU, ARM64 or Windows profiles | PL/ML/SEC / profile-specific G3; does not block planning or another qualified profile |
| O17 / P1 | Can users understand and safely control the proposed workspace? Observe stage comprehension, plan changes and interruption tasks in pilots. | Simpler stage/activity view if report controls confuse users | PO/Application Lead/EO / M1 usability and G4; no preference study has run |
| O18 / P0 | Which task bundle proves broad value? Recommend ETL/EDA + tabular classification/regression, then M1B grounded text; benchmark both DS and software-engineer journeys. | Intake-only product; different bounded domain fixture | PO/EO / G0 and G4; no launch-sector demand assumed |
| O19 / P0 | Which exact parser/OCR models and transitive native dependencies are rights-cleared and safe offline? Qualify DuckDB 1.5.5 and Docling 2.130.0 candidates; pinned licences/model inventory remain gaps. | Native-text-only PDF profile and asset-only images until OCR qualifies; replace parser | ML/SEC/CL/PL / affected M1 format G2/G3, not tabular work |
| O21 / P1 | How many sources, bytes and relationship candidates must the first pilot handle? Recommend paged metadata, bounded batches and one-host materialisation before distributed execution. | Larger remote engine or narrower approved subsets | DO/PL/PO / task G0 and scale G3; other bounded tasks continue |
| O22 / P1 | Which E1–E6 recipes justify first expansion? Recommend clustering/anomaly after M1, then the highest-value partner task. | Scientific, multimodal or training-first pilot | PO/ML/EO / each expansion's scope gate; core M1 unaffected |
| O23 / P0 per component | Resolve exact dependency/model licences, documentation version and executable extras for each task and desktop build. Recommend minimal pinned core packages; Unsloth UI excluded. | Reviewed replacement library/shell | CL/ML/SEC/PUB / affected build G2 and profile G3; missing component not advertised |
| O24 / P0 | Which desktop OS is the first pilot? Provisional Linux x86-64 D16; choose one native installer/profile at M0. | macOS/ARM64 or Windows profile with revised VM/model/package work | PO/UX/PL / desktop M0/G3; no universal OS support claim |
| O20 / P1 | What is each customer's gold grain, IDs, join policy, analysis claim standard and monitor owner? Freeze data/task-specific contract; manual checks first. | Different grain/targets or no scheduled monitor | DO/DE/EO/analysis owner / affected task G0/G1/G4 |

## Literature-to-control traceability

Principles below are supplied design lenses, not verified quotations or endorsements of contemporary components.

| Principle / book | Requirement | Design choice | Failure prevented | Verification | Accountable owner |
|---|---|---|---|---|---|
| Authoritative versus derived state — DDIA | R05/R09 | Transactional metadata + immutable artifacts; rebuildable tracker/search projections | Conflicting source of truth | Rebuild from manifests; compare hashes | PL |
| Partial failures and evolution — DDIA | R05 | Attempts, leases/fencing, idempotent commits, versioned schemas | Duplicate results; stale workers | Crash before/after commit and lease partition tests | PL |
| Changeability and ownership — Software Engineering at Google | R04/R11 | Typed contracts, owners, compatibility policy, dependency locks | Wrapper/implementation divergence | Consumer contract tests; deprecation review | Application Lead |
| Reliability experienced by users — SRE | R03/R10 | Separate availability/quality SLOs, overload and restore runbooks | “Up” endpoint with unusable output; unrecoverable evidence | Black-box probes, load and restoration drills | SO |
| Context/data change — Designing ML Systems | R01/R05/R06 | Group/time splits; same inference pipeline; delayed-label monitoring | Leakage, serving skew, unnoticed regression | Point-in-time audit; paired regression | ML/EO |
| Reusable patterns with preconditions — ML Design Patterns | R01/R05 | Train-only transforms, calibration on permitted partitions, task-specific metrics | Incorrect reusable recipe; misleading imbalance score | Fold-level provenance; slice/denominator review | ML |
| Evaluation-led foundation applications — AI Engineering | R01/R06 | Frozen rubrics, human calibration, quality/cost/latency feasible set | Judge gaming; expensive unhelpful generation | Blind human comparisons and operational measurement | EO |
| Grounded and bounded actions — Generative AI Design Patterns | R04/R07 | Cited retrieval, structured output, resettable episodes, action scopes | Injection, unsupported claims, repeated effects | Adversarial inputs; final-state/action-ledger checks | SEC/EO |
| DDIA partial failure | R05/R13 | Provider resource/attempt IDs and separate cleanup/charge states | Lost create response causes duplicate paid instance; deleted worker loses evidence | A19–A21; inventory reconciliation and staged artifact commit | PL/FIN |
| Software Engineering at Google: changeability | R09/R14 | Separate provisioner/executor/serving contracts with profile versions | Vendor SDK semantics leak into WorkloadSpec | A17; contract fixtures and profile upgrade review | PL |
| SRE: user-observed reliability | R03/R14 | Track queue, startup, execution and cleanup separately; scoped SLOs | Free shared queue marketed as managed-service availability | A23; measured cold/queued timings | SO |
| Designing ML Systems / ML Design Patterns | R01/R05 | Same snapshots/pipeline; hardware-specific rerun evidence | Provider migration changes preprocessing or numerical behaviour silently | A17/A22; EO-defined tolerances and lineage | ML/EO |
| AI Engineering / Generative AI Design Patterns | R06/R07/R14 | Approved compute choices; no quota-driven permission or provider expansion | Agent moves private data or spends on paid fallback | A18/A23; rejected migration/overflow requests | SEC/FIN |

Additional traceability for this revision:

| Principle / book | Requirement | Design choice | Failure prevented | Verification | Accountable owner |
|---|---|---|---|---|---|
| Durable state and partial failure — DDIA | R15/R17 | Message receipts, replay cursor, revision compare-and-swap and tool fences | Lost interruption, duplicate action or stale requirement commit | A24–A27 fault cases | PL |
| Changeability — Software Engineering at Google | R16/R18 | Model gateway, separate assistant binding, code provenance and profile regression | Runtime/model update silently changes developer behaviour | Pin/update/rollback qualification | ML/PL |
| User-experienced reliability — SRE | R15 | Independent control path with measured acceptance latency and honest stop state | Busy model freezes user's authority | Hung-generation/load scenario A24 | PL/PO |
| Evaluation-led and bounded action — AI Engineering / Generative AI Design Patterns | R16/R17 | Held-out assistant cases, VM tools, immutable constraints and limited repairs | Plausible invented results, injection or runaway code | A28–A30 plus independent human review | EO/SEC |
| Data context and pattern preconditions — Designing ML Systems / ML Design Patterns | R17 | Typed entity/group roles, feature-count semantics and released-output metrics | ID leakage, invalid split or misleading rounding claim | A29 and lineage/slice checks | ML/DO/EO |
| Authoritative observations — DDIA; changeability — Software Engineering at Google | R19/R20 | Versioned snapshots/plans; rebuildable stage projection with shared contracts | Stale capacity or narrative presented as actual state | A31–A34; replay/version checks | PL |
| User reliability — SRE; context — Designing ML Systems; pattern preconditions — ML Design Patterns | R19 | Assistant-independent bootstrap, effective capacity and fresh reservations | Unsupported hardware, UI deadlock or memory overcommit | A31–A33; profile/load evidence | PL/ML |
| Evaluation-led and bounded actions — AI Engineering / Generative AI Design Patterns | R20/R05/R06 | Inspectable plan and report; self-check separate from EO evaluation; corrections become proposals | Self-review marketed as acceptance, chart/query leakage or silent adaptation | A34; final-data access and change audit | EO/SEC/PO |

## Invariants and permitted adaptation

Mutable within an approved task: approved ETL/analysis source and query choices within fixed data/method bounds; within an experiment, fitted parameters; enumerated hyperparameters; prompts, retrieval k and workflow choices named in the search space; explicitly trainable adapters. Invariant during it: data partitions, evaluation oracle/rubric, rights, security scopes, grants, logging and promotion rules. Human authority intervenes when agreeing the task, releasing data, authorising spend, freezing evaluation, accepting residual risks, approving a release and accepting its operation. A later change to an invariant creates a new reviewed contract and may require a fresh independent evaluation set.

## Traceability for the general data workflow

| Principle / book | Requirement | Design choice | Failure prevented | Verification | Owner |
|---|---|---|---|---|---|
| DDIA authority/evolution | R21/R23 | Raw snapshots, gold manifests and rebuildable views; versioned refresh | Silent source change or lost lineage | A35/A37 reproduction and invalidation | DO/PL |
| Software Engineering at Google changeability | R22/R11 | Imported/generated code diff, locks and output-specific packaging | Unrepeatable analysis and endpoint-only scope | A36/A38 recipient replay | Application Lead/PUB |
| SRE user reliability | R24 | Open-ended dataset collections, bounded profiling and evidence-backed relationship/join planning; never force unrelated sources together | User direction; ADR26/D22; A39–A41; DO/DE/ML/PL; M1 |
| R25 | Expand across requested library task categories through documented code adaptation and qualified task/runtime contracts | User direction; ADR27; task_expansion.md; A42/A43; ML/EO/SEC; M1 mechanism, later E1–E6 |
| R26 | Desktop GUI is primary and starts/reconnects to a local harness; CLI/SDK is a capable fallback with equivalent controls/evidence | User direction; ADR28; A44; PO/UX/PL/SEC; M1 |
| R27 | Deliver versioned outputs to the user's authorised filesystem, independently of endpoint startup; preserve service interfaces where applicable | User direction; ADR29/D23; A45; PUB/DO/PL; M1 |
| R23 | Monitoring owner, manual/scheduled mode, bounded job and alerts | “Monitored” claim without running checks | A37 run/stop/cost evidence | SO/PL |
| Designing ML Systems and ML Design Patterns | R05/R21 | Grain/point-in-time contracts; split before learned preparation | Gold ETL leaks final labels or duplicates outcomes | A02/A35/A36 | ML/EO |
| AI Engineering and Generative AI Design Patterns | R22/R16 | Task-specific oracles and cited extraction; restricted code and assets | Fluent unsupported analysis or injected tool command | A28/A35/A38 | EO/SEC |

## Additional literature traceability

| Principle | Requirement | Design choice | Failure mode | Verification | Owner |
|---|---|---|---|---|---|
| DDIA: authoritative identities, derived state, partial failure | R24/R27 | Immutable collection/join/output versions; staged export and receipt | Silent source refresh or half-written bundle | A39/A41/A45; pinned membership and interrupted commit | DO/PL/PUB |
| Software Engineering at Google: understandable change and compatibility | R25/R26 | Version-matched docs, reviewable code/dependency diff, task/profile ledger and native packaging | Latest-doc API mismatch or unsupported OS claim | A42/A43/A44; exact locks and recipient replay | ML/PL/UX |
| SRE: observable user reliability | R26/R27 | Model-independent controls, crash reconciliation, truthful export state | Lost job/duplicate run on window reopen | A44/A45; receipts, leases, pause and restoration | PL/SO |
| Designing ML Systems / ML Design Patterns: contextual data correctness | R24 | Grain/cardinality/as-of rules, train-only learned preparation | Duplicated facts, future leakage, wrong identity | A40/A41 and EO independent queries | DO/DE/EO |
| AI Engineering: evaluation-led adaptation | R25 | Experimental run separated from reusable qualification | Code executes but task/model unsuitable | A42/A43; task oracle and target evaluation | ML/EO |
| Generative AI Design Patterns: constrained actions and grounded context | R25/R26/R27 | Untrusted docs through broker; narrow desktop IPC; scoped file output | Prompt injection becomes host command or arbitrary write | C22–C24, A42/A44/A45 | SEC/PL |

Across these refinements, code/joins/task choices may adapt within an approved envelope; rights, sealed boundaries, budget, output meaning and acceptance authority remain invariant. Human authority intervenes on material semantics or authority changes, not every reversible editor action.
