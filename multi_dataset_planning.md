# Multi-dataset discovery and relationship planning

Planning edition **0.7.0** · 29 September 2026. Planning only: no application, dataset, model, deployment or monitoring job has been implemented or run. Upstream facts retain their own verification dates. No spending or publication is authorised.

## Product contract — R24 / ADR26

A project can contain an open-ended number of datasets. There is no one-dataset assumption, fixed number of source slots, or project-level dataset-count ceiling in the contract. Actual storage, permissions and compute remain finite. Each job reads a pinned, authorised subset within an admitted envelope; large collections are paged and work is split into bounded batches. D20's 100-file limit is an **ingestion batch limit**, not a project limit or a promise to join every source simultaneously. Reject, partition or request an explicit larger profile when a task exceeds its envelope; never silently ignore excess inputs.

Distinguish a logical dataset from its tables, physical files/partitions and document/image/audio assets. A CSV shard is not necessarily a new dataset; a workbook/database can contain several tables. `DatasetCollectionManifest` records an immutable membership revision, source aliases, exact DataManifest revisions, intended roles, access/purpose policy and a digest. Its membership can be inline for small examples or in content-addressed pages for larger collections. Pagination is transport, not a mutable snapshot. Source refresh creates a new collection revision; previous runs still resolve their exact sources. WorkloadSpec refers to the collection, keeping the D05 submission small.

## Discovery, evidence and authority

1. Enumerate only authorised metadata; record inaccessible, unreadable and unprofiled sources without revealing unauthorised source existence. Inventory and file parsing are interruptible durable jobs.
2. Profile schema, meaning/units/timezones, row grain, candidate/composite keys, uniqueness, nulls, ranges, temporal coverage, label availability and source-of-record authority. A sampled profile records sample method/size/coverage; it cannot prove a whole-table key constraint.
3. Generate relationship candidates using declared foreign keys and customer definitions first, then bounded name/type/semantic matching, overlap statistics and temporal compatibility. Block candidates by compatible domains; do not compare every column pair or send all rows/schemas to an LLM. Show discovery coverage and remaining work when the budget expires.
4. Propose a JoinPlan with measurable evidence and unresolved meaning. Matching names or values are clues, not proof of identity. Routine joins can proceed under previously confirmed semantics and passing checks. A material ambiguity about entity identity, grain, timing, source precedence or rights goes to DO/DE; no invented confidence score grants approval.
5. Validate full relevant key/cardinality/availability constraints before accepting materialised gold. Execute a bounded preview and estimate expansion/spill, then admit the actual materialisation. Preview rows are labelled; missing checks yield INSUFFICIENT_EVIDENCE.
6. Preserve input/output counts, rejected/unmatched records, column and row/source lineage, exact code/plan versions and checks. Reconcile these before downstream analysis. A many-to-many explosion or changed grain is a failed contract, not an optimisation opportunity to hide.

DO owns identity, purpose, permitted linkage and retention. DE owns business grain, timestamp meaning and source precedence. ML owns code and computational method; EO owns independent correctness checks and predictive separation. PL owns capacity/recovery; SEC owns access and exfiltration boundaries. The assistant proposes and explains; it cannot approve rights, broaden access or change the task oracle.

## Relationship operators and initial scope

| Relationship | M1 handling | Required meaning/checks |
|---|---|---|
| Exact equijoin, including composite keys | Inner/left/semi/anti joins, namespaced columns | Normalisation, cardinality, null/unmatched policy, output grain; preserve string IDs/leading zeros |
| One-to-many facts | Aggregate a child table at the required grain before joining, or intentionally retain detail | Declared grouping/aggregates; sums/counts reconcile; no accidental double-counting |
| Time-dependent dimension | Bounded as-of/validity-interval recipe | Entity keys, event cutoff, effective and available-at times, deterministic tie rule, no overlapping versions |
| Schema-compatible union | Align names/types/units then union; preserve source identity | Explicit deduplication policy; no implicit set semantics or unit conversion |
| Document/image evidence link | Link assets/spans by approved identity/provenance | Assets need not become repeated rows; retain extraction uncertainty and coordinates |
| Independent dataset/reference corpus | Keep separate and explain why | A relevant source need not participate in a relational join |
| Fuzzy/entity resolution or inferred cross-domain identity | Later E1 extension, separate qualification | False-link/false-nonlink oracle, review threshold, rights and collision analysis; never silently substitute for exact joins |
| Audio/video/multimodal alignment | E4 after parsers/task profiles | Timebase, sample/frame alignment, entity associations and modality-specific labels |

No universal gold mega-table is required. A task may consume several fact/dimension tables, a corpus and asset links. Gold is a versioned set of task-ready products with declared semantics. Predictive tasks split at the right entity/time boundary before learned preparation; identity discovery itself must not reveal sealed outcomes or use future labels to select relationships.

## JoinPlan semantics

The plan records collection revision; input aliases; operator graph; key expressions and normalisation; cardinality before/after aggregation; join kind; output grain; selected columns/precedence; null/unmatched/duplicate policy; point-in-time rule; required checks; resource limits; unresolved decisions and reviewer evidence. Expression fields are proposed code, never trusted SQL. The typed graph must resolve aliases, be acyclic, have unique output names and have a declared handling for every in-scope source. Unrelated/excluded sources carry a reason. Permission on the collection alone grants no access to members.

Result limits are explicit: D22 proposes at most 100,000 rows and 200 columns per initial materialised output table, an output/input-anchor row ratio at most 2, and the existing 8 GiB RAM/10 GiB scratch/7,200 s job envelope. These are conservative protection hypotheses, not scale benchmarks; PL/DO may approve larger profiles after measured expansion. A declared one-row-per-order product has ratio 1 as its semantic invariant, which is stricter than the general cap. An intended detail join can request a different grain/budget; the optimiser cannot loosen either.

Use embedded DuckDB with partitioned files and durable materialisation stages first. Persist metadata/indexes in the existing relational catalogue; cached profile sketches and candidate edges are derived from source/algorithm versions. When measured spill, concurrency or refresh requirements exceed one host, evaluate a remote analytical engine behind this same contract. Dataset count alone does not justify a distributed database or scheduler.

## Worked operations example

The proposed synthetic fixture has 2,000 orders, 400 accounts, child order items, delivery events, policy versions and linked documents/receipts. These are intended fixture dimensions, not measured records. [examples/dataset_collection.json](examples/dataset_collection.json) and [examples/join_plan.json](examples/join_plan.json) are linked planning records.

| Source | Grain / intended role | Proposed relationship |
|---|---|---|
| `orders` | One order; anchor; string `order_id`, `account_num`, event `created_at` | Preserve one row/order; ID columns excluded from predictors |
| `accounts` | One account in fixture | Many orders to one account on `account_num`; duplicate account key fails |
| `items` | One item line, available at order time | Aggregate quantities/count at order_id before joining; later item changes are excluded at prediction time |
| `events` | One delivery event, often after order time | Aggregate actual completion for retrospective analysis/labels only; never use future delivery as an input feature |
| `policies` | Account policy version with validity and available-at time | Account match plus effective interval at order creation, available no later than cutoff; overlapping versions fail |
| `documents` | Policy text/PDF and receipt image collection | Provenance links; no unconditional cross join into numeric facts |

User instruction: “Use account_num to connect accounts. Give me one row per order. Use the policy known when the order was placed; keep delivery outcomes for evaluation.” The GUI shows the typed graph, pre/post-aggregation grain, unmatched counts (unavailable until run), approved ID semantics and code diff. If account_num is not unique in accounts, pause the affected materialisation and ask whether it is a versioned dimension or a dirty key. Unrelated EDA can continue within its existing grant.

## Refresh, monitoring and evidence gates

Collection membership, source schema/key changes and JoinPlan changes invalidate affected derived products, analyses and models through lineage. A manually requested check compares the pinned baseline with new authorised snapshots; M2 schedules remain opt-in. Monitor join match rate with numerator/denominator, key violations, row expansion and temporal availability separately. No automatic acceptance of a new source relationship. Deletions propagate through joined outputs, cached previews, reports and exports under the declared ownership policy; model-remediation decisions remain explicit.

A39–A41 in [delivery_plan.md](delivery_plan.md) require >100-source catalogue paging, bounded discovery, exact/as-of/aggregate failure fixtures, no dropped inputs, sealed separation and interrupted materialisation recovery. G0 freezes meaning/rights; G1 establishes correctness; G3 establishes actual capacity/isolation. No scale, join-discovery recall or correctness benchmark has been run in this planning session.
