# Data preparation, task execution and versioned outputs

Planning edition **0.7.0** · 29 September 2026. Planning only: no application, dataset, model, deployment or monitoring job has been implemented or run. Upstream facts have separate verification dates. No spending or publication is authorised.

## Product boundary

The platform is a conversational data-science workspace for data scientists, software engineers and AI/ML engineers. A user supplies data, a question or task, existing code if available, constraints and compute. The application prepares governed data, proposes and executes bounded Python/SQL, checks the result against a task-specific contract, and exports a reproducible output. Document intake is a reference recipe. It is not the product's scope or required starting screen.

Generality is an extensible task/modality contract, not an assurance that arbitrary analysis, code, data or scientific claims are correct. Unsupported combinations return a specific gap and a proposed adapter, not an invented successful result. Human domain knowledge still establishes grain, meaning, rights, material errors and suitability.

## Two valid completion paths — ADR23

| Requested outcome | Complete deliverable | Acceptance boundary |
|---|---|---|
| Prepare data or understand it | **AnalysisReleaseManifest**: DataProductManifest(s), exact preparation/analysis code, environment lock, notebook, HTML/JSON findings and quality/reproduction evidence; explicit limitations and approvals | Reproduce the declared transforms and findings on permitted data; independently check joins, denominators and claims. No model fit or deployed endpoint is required merely to complete EDA. |
| Build a reusable predictive/generative/agent capability | **ReleaseManifest**: full inference application, model/configuration dependencies, ServiceSpec, Python entry point, HTTP/MCP, evaluation evidence and installation/operation instructions | Independent task evaluation plus clean recipient installation, parity, recovery and operator acceptance; the existing service gate remains. |

This explicitly revises original R11's service-only final-output rule in response to the latest user direction. Both paths require a versioned evidence bundle; a loose notebook or fluent explanation is insufficient. An analysis release may later become an input to a service workload. Exporting a failed/inconclusive report does not approve the findings for operational use. Monitoring is an explicit binding to an output, not an implication that a static report is live.

## Raw, prepared and gold data

“Gold” names a quality and semantic contract, not a proprietary storage format, a guarantee of truth or one flattened table. The initial representation is **Parquet tables + JSON manifests + content-addressed assets**, queried with embedded DuckDB. SQLite remains the local control ledger. No distributed lake, feature store, Spark, Delta or Iceberg is required in M1. Add a lakehouse table format only when concurrent writers, change capture, scale or an existing customer estate demonstrates need.

| Layer | Contents | Authority and validation |
|---|---|---|
| Raw / bronze | Immutable permitted source bytes, capture/query time, checksums, source identity, rights and source metadata | DO owns access/retention; source changes create a new snapshot. Original PDF/image bytes remain available under policy. |
| Prepared / silver | Parsed rows, normalised types/time/units, document pages and spans, extracted tables, image metadata/OCR, rejected-record ledger | Parser/code/model versions and input→output lineage; extraction uncertainty and failures remain visible. No silent removal or guessed business keys. |
| Gold / task-ready | Typed named tables at declared grain, stable keys and join relations; linked documents, image assets, text chunks, annotations/labels and quality report | DataProductManifest defines columns, units, time semantics, keys, allowed purposes, source coordinates, transform lineage, quality contract and review status. A quality PASS applies only to its frozen checks/population. |
| Derived task artifacts | Fitted transforms/models; charts; retrieval indexes; summaries; reports | Versioned references to inputs, code and runtime. Rebuildable where possible; learned transforms fit only permitted training partitions. |

For example, `orders` has one row per order and `account_num` is an entity key; `documents` has one row per document; `document_spans` has one row per located span; `assets` references image bytes and dimensions. Joins use explicit many-to-one/one-to-many contracts, preserve unmatched counts and reject unexpected duplication. Raw identifiers may be authorised for joins while excluded from features and public output.

ETL means extract, validate/transform and materialise these products; an ELT implementation is equally acceptable where source/privacy/resource policy permits. The assistant proposes mappings and code, deterministic checks enforce contracts, and DO/DE resolve ambiguous dates, currency, IDs, units and grain. Type inference is a proposal; preserve leading zeros and time-zone information.

## Initial formats and honest capability claims

| Input | M1 planned path | Boundaries / failure behaviour |
|---|---|---|
| CSV, Parquet | Schema-controlled ingestion, DuckDB SQL, explicit casts, joins and Parquet export | CSV encoding/dialect/decimal/date ambiguity reported; malformed rows quarantined. No macro execution or arbitrary URL imports. Nested Parquet types require declared support. |
| UTF-8 TXT, Markdown | Preserve text and source offsets; optional paragraph/chunk tables | Byte/character offsets and normalisation version recorded. Instructions inside files are data, not authority. |
| PDF with native text | Docling candidate parser, page/span/table provenance; native extraction first | Layout/table extraction is fallible; encrypted, corrupt or unsupported PDFs quarantined. Original bytes retained. |
| Scanned PDF, PNG, JPEG | Asset inventory plus separately qualified OCR profile producing located text/uncertainty | OCR weights/engine/runtime require rights and offline-profile qualification. Missing profile means asset-only/needs-OCR, never an empty document marked successful. OCR does not establish general visual understanding. |

D20 proposes ingestion-batch bounds: 100 files, 250 MiB total source bytes, 50 MiB/file, 500 PDF pages total, 25 megapixels/decoded image or rendered page, 100,000 table rows and 200 columns per table. Enforce first limit reached plus D01/D16/D17 resource/time envelopes; do not silently sample or drop excess. PO/PL/DO may approve revised limits after measured parser expansion and support cost. These are product protection hypotheses, not benchmarks. Hosted ingestion quotas remain separate and may be smaller. This is not a project dataset-count ceiling. D22 separately caps materialised outputs; large collections use paged membership and bounded jobs. Archive/Office/database connectors and audio/video ingestion enter explicit later qualification; E4 covers the audio/video task programme.

## Tasks and readiness

| Task / family | Planned first stage | What runs and how it is checked |
|---|---|---|
| Data preparation, profiling, exploratory analysis / `data_analysis` | M1 | Reviewed or generated SQL/Python; schema/key/join/lineage assertions; descriptive statistics with denominators, missingness and sampling disclosures; independent recomputation of material claims |
| Classification and tabular regression / `classical_ml` | M1 | Deterministic/constant baseline plus actual fitted sklearn Pipeline; grouped/time-aware partitions, train-only transforms; task-specific held-out quality and units |
| Text classification / `classical_ml` | M1 support recipe | TF-IDF/logistic pipeline remains a useful regression fixture, not the only task |
| NLU as extraction/entity/intent tasks; grounded summarisation; lexical RAG / `genai_application` | M1B | Clearly defined schema/rubric and source citations; fixed base model first, bounded prompt/context/config optimisation, zero weight changes |
| Advanced generative application search and operational hardening | M3 | More evaluated configuration/embedding/routing choices only when M1B baselines justify them |
| Actual SFT/PEFT / `genai_training` | M4 | Declared base/trainable parameters, real gradient steps and independent base-vs-adapter evidence |
| Agent evaluation/configuration / `agent` | M4 | Resettable simulator, bounded tools, final-state oracle; separate from the M1 development assistant |
| Classical breadth, scientific/time-series, vision/audio/multimodal, Unsloth and bounded RL | Later E1–E6 qualification waves | Specify method, oracle, hardware, rights and acceptance before advertising support; large pretraining and unconstrained real-world RL remain out of scope |

“NLU” is not one metric or universal capability. Entity extraction, intent classification and semantic matching need separate labels/oracles. A task may compose preparation, retrieval and prediction with typed intermediate products; composition invalidates only affected downstream evidence when an input changes.

## Load, amend or generate code

1. Intake records output kind, task kind, supplied code/repository revision, datasets and constraints. No code runs while merely being inspected.
2. The assistant retrieves authorised schemas/samples/docs, proposes a dependency graph and shows code it will reuse or change. Existing Python/SQL/notebooks can be imported as immutable source artifacts, reviewed for dependencies and rights, then edited in a working copy.
3. A CodeTask records parent/source diff, WorkloadSpec revision, permitted input artifacts, expected output roles, dependency lock, resource/time limits and fence. Execute in the same restricted VM as generated code; SQL is executable content too [S53]. No package installation or network access through a model-written shell bypass.
4. Collect actual tables/plots/stdout/checks with size/redaction limits. The assistant diagnoses failures and may repair within D17; stopping at a limit produces an honest partial or failed result.
5. An authorised evaluator checks the output using the appropriate method. Package only committed artifacts, hashes and measured findings. The user can pause, cancel or revise requirements throughout; changes create code/data/workload versions with invalidation.

## Output versions and monitoring — ADR25

Use the existing ledger, artifact store and jobs. No separate orchestration or monitoring cluster is introduced. `MonitoringSpec` fixes target/version, observations, units, comparison baseline, cadence, owner, thresholds, access/retention policy and action. A monitor run pins the current approved target; changing that target is an audited revision. Reference baselines remain immutable, and monitoring observations are not automatically training data.

| Output | Useful monitoring | Result and responsible owner |
|---|---|---|
| Data product | Schema/key violations, missingness, row/source coverage, freshness and extraction quality | DO owns thresholds; PL operates bounded checks. New data creates a new snapshot/product revision. |
| Analysis/report | Source/code version changes, dependency/rights expiry, changed values on rerun, reproducibility failures | Analysis owner (usually DS) receives “stale relative to new source”, diff and rerun proposal. Historic report stays valid only for its original scope/date. |
| Model/service | Latency/errors/resources/cost, feature/output drift, delayed-label quality and human overrides | SO owns operation; EO owns quality contract and regression; releases promote only through PO/SO decisions. |

M1 provides version history, lineage comparison and **manual `check_output`** with an explicit monitoring owner/status. M2 adds optional scheduled checks using durable jobs and a separately approved cadence, connector access and resource/spend reservation; there is no automatic polling of customer systems. Alerts go to the in-app evidence inbox in M1; external notifications require authorised integration. Repeated failures trigger pause/escalation, never silent retraining or deployment. Rollback selects a previous output/binding revision and cannot resurrect deleted data, revoke prior disclosures or undo external actions.

## Operator, payer and exit path

Local/customer-hosted: customer operates parsers, DuckDB, VM, asset store and monitors and pays hardware/provider/API costs; the core supplies software without a hosted dependency. Hosted coordination: platform operates/pays metadata/UI; customer-run bulk ETL and assets remain customer-side by default. Managed execution later: platform operates isolated tasks and bills agreed compute/storage separately. A published analysis pack still needs rights to every included table, excerpt/image and code dependency; private-by-default applies equally to non-model outputs.

DuckDB/Parquet are the recommended small local foundation [S52–S54]. Docling is a replaceable parser candidate [S55–S56]; engine/model licences and native binaries need exact-profile review before distribution. Both are integrated components, not evidence of our product's security or accuracy. CSV/Parquet/JSON/source assets and versioned Python/SQL provide an exit path without retaining an opaque server database.

## Multi-source tasks and direct delivery

R24/ADR26 replaces any single-source assumption with DatasetCollectionManifest and JoinPlan. Profile and relate an open-ended catalogue through bounded slices; accept exact, aggregated, as-of and union semantics only after checks. Do not force independent data or linked multimodal assets into one table. [multi_dataset_planning.md](multi_dataset_planning.md) specifies grain, candidate evidence, lineage, rights and output caps.

R25/ADR27 extends the task matrix through [task_expansion.md](task_expansion.md). Official docs can inform code/dependency diffs; TaskCapabilitySpec, target-profile admission and the task oracle remain separate gates. Experimental generated tasks have explicit limits and cannot masquerade as qualified adapters. Both analysis and service bundles can be delivered through an authorised filesystem OutputBinding; a service endpoint starts only on a separate request. The desktop GUI is the primary workspace, with code/logs and CLI fallback rather than a required notebook terminal.
