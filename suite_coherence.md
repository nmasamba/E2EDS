# Suite coherence audit — edition 0.7.0

Planning edition **0.7.0** · 29 September 2026. Planning only: no application, dataset, model, deployment or monitoring job has been implemented or run. Upstream facts retain their own verification dates. No spending or publication is authorised.

## Shared decisions

The product is a GUI-native general data-science/AI workspace, with a per-user local harness, persistent conversation and a capable CLI fallback. Data scientists are primary daily users; software engineers are first-class users. R11/ADR23 permits analysis releases; service outputs retain independent installation and HTTP/MCP parity. Document intake remains one fixture. ADR26–29 add open-ended dataset collections/joins, docs-assisted task expansion, native desktop and scoped filesystem delivery.

| Authority | Shared semantics | Consumers |
|---|---|---|
| requirements_and_decisions.md | R01–R27, D01–D24, ADR01–29, O01–24 and owners | Entire suite |
| multi_dataset_planning.md | Project source count open-ended; D20 per ingestion batch, D22 per materialisation; JoinPlan semantics | Contracts, data/evaluation, hardware, GUI, delivery/security |
| task_expansion.md | Task/operation/library/model/profile-specific support; docs are untrusted; E1–E6 backlog | Execution, commercial, research, contracts, delivery |
| desktop_experience.md | GUI primary, Tauri candidate, local harness, CLI parity, new-version filesystem export | Architecture, GUI, security, compute/runtime, README |
| delivery_plan.md | M1 95–145 days; M0–M2 155–236; M0–M5 203–313; optional M3Z adds 4–7 | README and commercial arithmetic |
| contracts.md and JSON | Sixteen schema versions, linked example revisions and semantic checks | All interface/reference discussions |

## File-by-file update coverage

| Document | Substantive revision |
|---|---|
| README.md | New desktop/multi-source mission, filesystem completion, extension roadmap, navigation/counts/effort |
| product_strategy.md | Native multi-source adoption trigger, pilot hypotheses and updated Unsloth alternative |
| requirements_and_decisions.md | R24–27/D22–24/ADR26–29/O21–24, UX decision rights, intake and literature traceability |
| architecture.md | Native harness, source/join/task contracts, docs/export brokers and data-to-output flow |
| contracts.md | New objects and schemas, WorkloadSpec extension/migration, version register and semantic limits |
| data_products_and_tasks.md | Batch versus project limits, qualified breadth and filesystem task output |
| data_and_evaluation.md | Join correctness, temporal availability, unsupervised/scientific/multimodal/RL oracles |
| execution_and_serving.md | Materialisation checkpoints, docs-assisted task admission, export commit and optional serving |
| security_and_assurance.md | C21–24: linkage, docs/code, privileged renderer, local export; separate component rights |
| commercial_and_marketplace.md | GUI/export in core, no unlimited resource promise, task metering, revised build cost |
| delivery_plan.md | Native/multi-source first slice, B33–37/A39–45, revised totals and E1–E6 readiness increments |
| reference_workload.md | Six-source operations fixture, join/temporal roles and desktop-to-filesystem walkthrough |
| research_sources.md | S57–64 dated primary facts, licence/version gaps, maintenance, effort and exit paths |
| compute_backends.md | Separate UI/execution/output hosts, profile intersections and verified local export |
| local_model_runtime.md | Desktop supervision, paged source/docs context, separate VM and export broker |
| conversational_control.md | Join/task/destination instructions, scoped authority and native lifecycle distinction |
| hardware_discovery_and_planning.md | Cardinality/spill/export estimates and three target profiles; OS gate |
| gui_workflow.md | Open editorial visual direction, relationship graph/list, native lifecycle and output shelf |
| multi_dataset_planning.md | New detailed relationship, scale, authority, refresh and worked-example specification |
| task_expansion.md | New code/docs adaptation protocol, coverage programme and library-specific distinctions |
| desktop_experience.md | New visual design, shell trade-offs, harness lifecycle and filesystem contract |
| suite_coherence.md / planning_validation.md | Regenerated revision audit and actual planning checks |

Four new schema files and four new example files join the prior tree; all prior files remain. WorkloadSpec/DataProductManifest are draft 0.6.0; the four new schemas are also 0.6.0; five schemas remain 0.5.0, two 0.4.0 and three 0.3.0. There are 23 Markdown documents, 16 schemas, 22 example files and the inventory (62 files); the ZIP mirrors that exact tree. The preview-only generated UI concept is displayed in the conversation and is not part of the executable or contract evidence.

## Coherence risks explicitly resolved

No AWS-first host, single-dataset assumption, browser-first desktop requirement, hard project dataset-count ceiling or API-only output remains authoritative. New breadth does not make all upstream tasks/hardware supported. A namespaced task needs a registered capability and semantic admission; documentation cannot enlarge permissions. A source collection does not grant member access; a JoinPlan does not prove identity or correctness. Dataset changes invalidate affected descendants; a filesystem copy cannot silently replace an approved output. The local owner can still bypass local controls, and an exported copy outside platform control cannot be forcibly erased.

All application behaviours remain planned. Null hashes, no measured join/profile/task results, no approvals, no admitted new analysis run and no export receipt are intentional. Primary evidence dates are preserved per source. Planning validation checks only documents/contracts/arithmetic; A01–A45 remain future product tests.
