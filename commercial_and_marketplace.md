# Commercial model: software, coordination and customer compute

Planning edition **0.7.0** · 29 September 2026. Architecture and delivery proposals are unimplemented; upstream facts retain their own verification dates. No compute is provisioned or purchased by this plan.

Compute ownership is an axis across product tiers. Default to customer-direct provider billing; sell evidence, collaboration and operation with explicit responsibilities. All proposed prices, quotas, conversion and cost allocations are hypotheses except the dated facts in the research register.

## Product tiers and commercial boundary

Sell software access, hosted coordination/operation and compute as distinguishable items. The community core is commercially usable provider-neutral software, including basic attached execution and reference adapters; operating it still consumes hardware, electricity, storage, engineering time and any external API charges. A subscription does not imply unlimited training, provider tokens or support.

| Tier | Proposed scope and price experiment | Operator / payer | Boundary |
|---|---|---|---|
| Community/local | £0 software licence; SDK/CLI, generic runner, reference compute adapters, multi-format preparation/analysis, core evaluation/notebooks/report, output history/manual checks, HTTP/MCP and export | Customer operates/pays local or rented resources, storage and APIs | Basic attached/delegated execution remains locally usable; no vendor uptime/support commitment |
| Hosted free | £0 coordination; D07 limits plus quotas below; optional qualified ZeroGPU demonstration link/profile | Platform funds bounded coordination/CPU demo; customer pays its own providers and optional HF plan/credits | No guaranteed included GPU capacity, arbitrary code, paid GPU overflow or unlimited traces |
| Team | Test **£249/workspace/month**, up to 5 users; collaboration, shared output history, authorised scheduled checks/approvals/CI/private catalogue; business-hours support | Platform operates coordination; customer runtime by default; managed compute separately itemised | Proposed 20 projects, 2,000 trial records/month, 20 GB retained results, 90-day telemetry; usage expansion opt-in |
| Enterprise | Test annual minimum **£24,000** for defined private deployment/fleet/identity/support scope; quote after discovery | Customer or platform according to responsibility schedule; infrastructure separately identified | No automatic 24/7 SLA or unlimited professional services |
| Design-partner pilot | Test **£8,000–£15,000** for one bounded 6-week customer evaluation/handoff engagement after core readiness | Named operators; actual cloud/API costs pre-approved separately | Scope, data readiness, acceptance and reusable IP explicitly contracted |

Numbers are chosen to test ability to fund support and recurring value, not inferred willingness to pay. FIN/PO own ratification at G4. Pilot services can fund learning but must not be counted as recurring subscription margin. A lower-price toolkit alternative (£99/month hypothesis) is tested if buyers only value templates/export; a £499 plan needs evidence of more support/operational value.

The Community core includes the M1 local conversational UI, model gateway, command/event history and guarded code tools; essential intervention is not a paid feature. Users supply the assistant hardware/model storage as well as workload compute. A locally cached 5.03 GB candidate model does not consume the platform's 1 GB free retained-results quota. The download, disk, power and support burden are real costs. Hosted free coordination includes no hosted assistant token allowance by implication; attaching an external model API requires explicit rights, budget and billing disclosure.

Team value remains collaboration, approvals, maintained release history and support. The local assistant and generic compute integration remain independent of hosted subscription. An offline installation can use preloaded weights/runtime and local conversation without phone-home. Weight/runtime licences and redistribution notices are separate from the core's proposed Apache licence; pinned-binary/model distribution review remains open [S43–S45].

Hardware discovery, explainable workflow selection and the basic stage/conversation/report workspace are part of the proposed free local core in every tier. They incur local operating cost but no implicit hosted GPU allowance. Customers operate/pay for collectors on their own hosts; the platform owns software maintenance and operates collection only for explicitly managed resources. Inventory sharing is private/opt-in to authorised coordination, never a requirement for local use. Hosted subscription does not purchase additional machine capacity.

Edition 0.6 adds 20–32 estimated engineering days (£13,000–£20,800 at £650/day) for mixed-format preparation, gold/analysis output paths, tabular prediction and version/manual-check evidence. M1B brings 12–18 days of grounded text forward from M3 without adding them twice; delivery_plan.md owns totals. The workspace/discovery designs remain in [gui_workflow.md](gui_workflow.md) and [hardware_discovery_and_planning.md](hardware_discovery_and_planning.md). This is one-time development effort, separate from the monthly unit model below. Measure diagnostic/support minutes, false-ready recommendations, onboarding abandonment and intervention errors before claiming lower support cost. No new provider rate, paid tier or willingness-to-pay claim is inferred.

## Compute modes and who pays

Compute mode is independent of Community/Free/Team/Enterprise entitlement. Attach mode: customer creates, operates and pays for the host; our runner controls only authorised jobs. Delegated mode: customer pays the vendor; platform operates scoped resource lifecycle under contract, while customer retains account, key, region and budget authority. Platform-funded mode is optional later and must state infrastructure cost and service fee separately. Subscription cancellation stops new hosted work but must not destroy unrelated attached resources or disable installed licensed inference.

ZeroGPU is an optional demonstration allowance/profile, not a new promise of free training. Retain D07 and the CPU demo envelope; GPU demos are separately opt-in and subject to D14 and external quota. The adapter does not enable paid credits/automatic paid fallback. Any external account plan or prepaid-credit behaviour must be disclosed before connecting it. Native provider quota and platform quota have different identities and counters. Publication of a Space remains outside this planning session.

## Free coordination, demonstrations and quota exhaustion

Retain the brief's 1 user, 2 private projects, 100 task/trial records/month, 1 GB retained traces/results and 30-day retention. A task/trial record means a bounded metadata record for customer-run work, not paid model training. Raw model weights can stay in customer storage with digest references; a 1.5 GB model will not fit inside a 1 GB free artifact quota.

| Additional proposed quota | Purpose / exhaustion behaviour |
|---|---|
| 10,000 coordination API requests/month; 60/minute, burst 100 | Bounds coordination load; return 429 with reset/retry details; local operation unaffected |
| 1 GB ingestion/month and 1 GB simultaneous retained bytes | Prevent churn around a retention cap; reject new ingestion before upload, retain existing data until its stated expiry |
| 10,000 trace/metric events/month; 64 KiB maximum event | Trial count alone cannot constrain telemetry; reject oversized events and report omitted counts |
| 50 MB maximum artifact upload; signed transfer size enforcement | Large releases exported locally/customer store; never truncate a model silently |
| 100 curated routing-demo calls/month; 1 concurrent call; 600 CPU-seconds/month | CPU-only demo; no user code, GPU, provider/judge/embedding calls or agent exploration |
| Proposed £0.25/month internal variable-hosting envelope per free account, plus global operator-approved cap | Internal abuse stop/admission limit; not a user charge or full-cost guarantee |

Quotas are deterministic, visible and checked before work; bytes, calls, time, concurrency and spend are independent limits. Trials failed/cancelled still consume actual resources and appropriate record quota; duplicate event retries are deduplicated. No automatic paid overage. Users explicitly opt into a paid plan and a distinct managed-spend cap. Paid limits and rate cards are versioned; do not derive them from a prompt.

Send in-product expiry notices 7 days and 1 day before retention deletion where feasible. Export remains available until stated expiry, including after cancellation or quota exhaustion. Subscription cancellation stops renewal; active jobs follow cancellation and reconciliation policy; retained data becomes read/export-only until deletion. Customer-installed Apache core and already licensed releases remain usable under their terms. High-priority security withdrawal follows the published policy, not a surprise commercial kill switch.

Essential private-by-default projects, tenant isolation, authentication, secure transport and export are not premium features. Team adds organisational workflows/capacity, not repair of an insecure free design.

A customer may run a qualified local or external binding while using free coordination; those provider resources are customer-funded and still subject to their explicit grant. The optional ZeroGPU demonstration has separate D14 and native-account limits. It is not a grant of pooled GPU hours, and the CPU demo quota does not automatically convert into GPU capacity.

## Unit economics and sensitivity

Customer-direct compute is excluded from platform revenue and compute cost in the base model. The customer still pays its provider; platform economics include coordination, artifact/telemetry overhead, connector maintenance, support and reconciliation. Platform-funded execution is a separate opt-in offering with its own rate and exposure policy. No provider-specific savings are assumed.

### Transparent monthly unit model

Working currency GBP. For this illustration only, assume **£0.80/USD**; it is not a checked market exchange rate. All figures exclude VAT, acquisition costs and corporate overhead unless stated. Active free users are individual accounts; paid Team units are organisations. “Paid/free ratio” below is a steady-state sizing ratio, not measured funnel conversion.

| Cost item | Free account assumption | Team workspace assumption |
|---|---:|---:|
| Coordination/storage/egress/observability/curated demo variable allocation | £0.18/month, including full 1 GB cap at assumed storage rate | £11/month total variable infrastructure |
| Support | 0.5 minutes/account/month × £50/hour = £0.4167 | 0.5 hours/workspace/month × £50/hour = £25 |
| Payment costs | £0 | Blended **estimate** 3% of subscription + £0.20, not a processor quote |
| Training/GPU/model API/embeddings/judges/agent exploration | £0 platform-provided; customer pays its own usage | £0 included; separately billed or customer-owned |
| Variable total used in model | **£0.60** rounded | **£43.67** at £249 price |

Propose fixed shared hosting/security/tooling allowance **£350/month** for a low-load pilot coordination service, unquoted and not enough to imply enterprise HA. Propose **£18,000/month** ongoing staffing cost as a planning assumption, separate from per-account support allocation (staff model excludes that directly attributed support time to avoid double counting). Validate both through staffing/hosting plans; fixed staffing is the largest commercial uncertainty.

For free accounts `F`, paid workspaces `N`, price `P`, paid support hours `h`, staff cost `K`:

`Revenue = N × P`

`Variable cost = F × 0.60 + N × (11 + 50h + 0.03P + 0.20) + unrecovered_managed_usage`

`Monthly operating contribution = Revenue − Variable cost − 350 − K`

Base scenario F=1,000, N=30, P=£249, h=0.5, K=£18,000: revenue **£7,470**; free subsidy **£600**; paid variable cost **£1,310.10**; contribution before fixed hosting/staff **£5,559.90**; after fixed hosting/staff **−£12,790.10/month**. This is not a profitable scale under the assumptions. Break-even requires **93 paid workspaces** at the same free count and cost profile, before acquisition/overhead. A 3% paid/free ratio is not enough here.

### Sensitivity (same F=1,000 unless stated)

| Scenario | Revenue | Contribution after £350 hosting and £18,000 staffing |
|---|---:|---:|
| 10 paid × £249; 0.5 h support | £2,490 | −£16,896.70 |
| 30 paid × £249; 0.5 h support — base | £7,470 | −£12,790.10 |
| 100 paid × £249; 0.5 h support | £24,900 | £1,583.00 |
| 30 paid × £499; 0.5 h support | £14,970 | −£5,515.10 |
| 100 paid × £249; 2 h support | £24,900 | −£5,917.00 |
| 100 paid × £249; free support rises to 5 min/account | £24,900 | approximately −£2,167.00 |

The final scenario increases the free subsidy by £3.75/account above the base, leaving all else unchanged. Support containment through documentation and successful independent installation is a product requirement with direct margin consequences. Free growth must be gated by operator-approved total subsidy/capacity, not only per-account quotas.

### Managed compute and API accounting

For each workload: `cost = workload CPU/GPU time + assistant inference compute or API tokens + workload model tokens + embedding volume + judge calls + code repairs + agent tool/episode use + storage-duration + egress + observability + retry waste`. Each quantity carries units, selected rate revision and reconciliation status. Add support explicitly in contribution analysis. Proposed managed-operation fee: test transparent 15% on approved pass-through usage or a flat operation fee, separately disclosed; neither is included in the base model or asserted as acceptable to buyers.

Sensitivity must include long-context token growth, judge repetitions, failed trials, GPU idle/image time, high trace retention and external billing lag. BYOK charges are incurred directly by the customer; show estimated quantities without double-invoicing provider usage. Model unit economics per task and per accepted business outcome, not only per request. No GPU subsidy, trial credit or vendor promotional allowance is assumed durable.

### BYOC support and subsidy sensitivity

Base subscription accounting: customer-paid GPU/API spend is neither platform revenue nor platform cost. Coordination, connector maintenance, failed-job support, logs and reconciliation labour remain our costs. The dated CPU reference calculation below is only a sensitivity input, not the selected hosting bill of materials. Colab, HF, Runpod and CoreWeave selected-account/region rates, commercial terms, refunds, storage and residual billing are OPEN before paid G3 admission. No current vendor price or savings claim is invented here.

Per run, estimate `compute + startup + interruptions/retries + storage + transfer + evaluation APIs + cleanup exposure`; record native currency/rate timestamp, conversion policy and uncertainty separately. Customer billing reconciliation does not require central per-call metering of an offline service.

Illustrative monthly sensitivity at the existing £249 Team price, base contribution £205.33/workspace, 1,000 active free accounts, £18,350 fixed costs and £600 base free-variable cost:

| Additional scenario (estimate, not a vendor quote) | Added platform cost | Break-even Team workspaces |
|---|---:|---:|
| BYOC billed directly; original support assumption | £0 | 93 |
| BYOC support adds 15 minutes per Team at £50/hour | £12.50/Team | 99 |
| Platform voluntarily funds £1 GPU usage per active free account | £1,000/month | 98 |
| Platform funds £5 GPU usage per active free account | £5,000/month | 117 |
| £1/free GPU allowance plus 15-minute extra Team support | £1,000/month + £12.50/Team | 104 |

These scenarios test exposure, not forecasts or quotas. Recommend the first boundary and measure support inflation in the pilot. FIN/PO own any subsidy decision; no automatic subsidy is authorised. A ZeroGPU link may still incur publisher plan, integration and support costs, even when customer usage falls within an external allowance. First-provider connector effort is included in M1R; each additional supported adapter needs a maintenance owner, pinned compatibility fixtures and withdrawal policy.

Local-model sensitivity: the base model still includes £0 platform-paid assistant inference. If hosted assistant use is later subsidised at an **assumed £2 per active free account/month**, F=1,000 adds £2,000 monthly variable cost and raises base break-even from 93 to 103 Team accounts (ceil((£18,350 + £600 + £2,000)/£205.33)). This is arithmetic, not an API price quote. An extra 15 support minutes per Team account at the assumed £50/hour lowers contribution to £192.83; combining it with that subsidy gives 109 accounts. Measure model/VM installation support, first-task success and interruption-related rework in the pilot before including any hosted assistant allowance. Customer-paid local inference is not platform compute revenue.

## Licences, customer ownership and offline use

Recommend Apache-2.0 for the local core, workload/service specifications and first-party integration SDK [S27]. This supports commercial use and redistribution subject to its conditions; trademarks, third-party rights and customer artifacts remain distinct. Exact licence drafting and dependency compliance are CL-owned. Do not claim Apache grants ownership of third-party model outputs or datasets.

Potential proprietary modules: hosted collaboration UI/service, organisation identity/fleet administration, supported enterprise automation and curated domain assurance packs. Generic runner contracts, local attached execution and the reference provider adapters are proposed Apache-2.0 core; paid operational conveniences cannot be a hidden prerequisite for BYOC. Keep deterministic policy validation, local evaluation, secure local API/MCP and artifact export in the community core. Deployable release runtimes must not depend on a proprietary phone-home service just to serve authorised requests. Closed modules use explicit commercial terms; no silent relicensing of third-party code.

Customer contract proposal: customer retains its data, proprietary corpora, task-specific labels and customer-specific releases, subject to third-party/base-model rights; platform receives only rights necessary to perform the requested processing/support. Generic platform code and independently created recipes remain platform IP. Any reuse/publication/training across customers needs separate permission and a defined privacy treatment. Jointly developed IP and withdrawal responsibilities are agreed, not inferred.

Maintain separate manifests for runtime software, weights/adapters, source/training/evaluation data, knowledge sources and service terms. Pin rights at exact revisions; package notices/attributions and inspect redistribution conditions. Proprietary provider dependencies have separate service terms and can make an otherwise open wrapper non-self-hostable. Evaluation sets may be shareable only as access-controlled re-evaluation services; export of evidence must not expose confidential tests.

For disconnected deployment, sell a clearly defined deployment licence for proprietary packs and/or annual support/update subscription. Community Apache code remains governed by Apache terms. Optional annual offline entitlement files need disclosed expiry behaviour; do not stop licensed inference when support ends unless the contract explicitly establishes a time-limited deployment right. No hidden call-home or assumed central per-call billing.

## Catalogue stages and claim integrity

| Stage | Supply / buyer discovery | Readiness and repeat usage |
|---|---|---|
| Private first-party | Tabular preparation/analysis and prediction recipes plus support text fixture; private data/analysis/service releases; direct design-partner discovery | G0–G4; repeat analysis/release and independent reproduction without author; evidence review and operating owner |
| Curated first-party public | Rights-cleared demo recipes/releases; content/partner referrals | G5, documented claims, safe defaults, installation/support workload measured |
| Third-party publishers — deferred | Vetted domain providers with real maintenance capacity | Publisher identity/rights, abuse/takedown, signing/scanning, independent claim review and transaction support |

Every listing includes task/users/unsupported uses; input meanings/output semantics; recipe/release/service kind; publisher and immutable artifact identity; licences/price/data handling/support owner; supported runtime/hardware/client/protocol profile; quality/cost/latency with dataset/sample/load/hardware/date; evidence grade; known limitations; maintenance/deprecation/withdrawal. Evidence grades are **publisher-reported**, **platform-reproduced** or **independently reviewed**, each backed by identity and scope. Planning examples have no measured performance claims.

A buyer can inspect a sample contract/report, run compatibility preflight, evaluate on permitted representative data and then decide installation or subscription. New customers do not inherit behavioural acceptance merely because an existing customer accepted the same model. Renewal value comes from maintained recipes, repeat releases and trustworthy operation.

The official MCP Registry currently hosts public server metadata pointing to packages/endpoints; it does not support private servers and does not host code or certify quality. Use our private catalogue for private capabilities, with a registry-compatible metadata projection where appropriate. Official registry code is not presented as a supported turnkey private registry [S13]. Public publication requires namespace verification, compliant metadata/package ownership and review against current publication rules at G5. PyPI/OCI host distributable bytes; MCPB optionally bundles a local server. Discovery is neither endorsement nor a security audit.

Publisher withdrawal: revoke new installs/listing claims; notify affected operators; retain legally required minimal audit metadata; provide replacement or migration guidance and contractual notice. Remove private content and rights-infringing artifacts as required. Existing offline copies cannot be remotely guaranteed erased. A critical security/rights withdrawal has a different urgency from ordinary deprecation.

Marketplace transaction fees, third-party revenue share and publisher tools remain unpriced hypotheses. Before building them, demonstrate repeat adoption, measure support/takedown cost and establish demand for third-party capabilities. Do not count hypothetical marketplace GMV in the base economics.

## Pilot evidence for economics and adoption

Track activation → complete local release → independent installation → customer acceptance → paid conversion → second release, with denominators and time windows. Meter real storage/request/trace/egress/compute/provider costs, support minutes, install failures, security review time, churn and budget reconciliation lag. Obtain regional cloud estimates and identity/network costs before hosting. FIN signs a revised model; PO decides whether evidence supports Team pricing, enterprise service work, a toolkit business or stopping the initiative.

Separate compute-provider invoices from software conversion. Measure setup time per binding, failed-run recovery, orphan-resource exposure, quota attribution failures and connector maintenance effort. A zero-cost platform GPU line can coexist with nonzero customer compute cost and substantial platform support cost. PO/FIN choose the first provider from measured pilot constraints, not an assumed cheapest-GPU ranking.

## Dated CPU reference arithmetic

The following previously verified arithmetic is retained as a historical example, not a current procurement quote or infrastructure recommendation. Selected provider/account/region prices must be verified for the actual binding before paid admission.

**VERIFIED-EXTERNAL, 18 September 2026:** AWS's Fargate pricing example for Linux/x86 in **US East (N. Virginia)** lists $0.000011244/vCPU-second and $0.000001235/GB-second; billing includes image-download time with a one-minute minimum. Extra services/networking can add cost. These are reference rates, **not a London-region quote** or a proposed deployment order. [AWS Fargate pricing](https://aws.amazon.com/fargate/pricing/).

At those rates, 1 vCPU + 2 GB for one hour costs `(0.000011244 + 2×0.000001235) × 3600 = $0.0493704`; 730 continuously running hours cost approximately **$36.04**, excluding database, load balancer, IPv4, NAT/egress, logs, storage, backups, tax and support. A 600-second monthly CPU demo envelope at the same allocation costs approximately **$0.00823/account** for this compute alone. These calculations show why support and idle shared infrastructure matter more than the curated CPU demo, not that a complete platform costs pennies.

The S3 official page was checked, but a reliable selected-region rate was not obtained from the rendered table. Use a deliberately labelled **assumption** of $0.03/GB-month object storage for budgeting, replacing it with an official regional quote before G3. Do not present it as the current AWS price. Request/egress/database/log costs below are allowances awaiting a bill of materials. GPU and model-API quotes are **unverified** and excluded from base subscription margin; no paid capacity is assumed.

## Economics and catalogue scope for general data work

Analysis is a useful free entry point: a data scientist/software engineer can prepare data, inspect findings and export reproducible code without buying a service deployment. Team value must be demonstrated in shared reviews, repeat work/version history, authorised monitoring, maintained integrations and support. Keep the three catalogue products (recipe, installable/reproducible release, managed service); label analysis/data packs explicitly as reproducible outputs with no endpoint. Dataset/analysis licences, source excerpts/images and code rights remain separate. Do not imply gold data is fit for another customer's task merely because it can be downloaded.

A tracked **task-run record** includes preparation/analysis as well as training. For hosted-free coordination propose a shared pool of 100 task/trial records/month (D07's ceiling), so EDA is not unmetered; the UI distinguishes zero-trial analysis from optimisation. Existing ingestion, retained-byte, event, request and demo-CPU limits still apply. Bulk source assets/model weights remain in customer storage by default. Free hosted quota exhaustion does not remove local export or privately operated analysis/inference. Scheduled checks consume task-run, event, data-scan and resource limits; no schedule is included by implication.

Extend UsageRecord quantities: source bytes, decoded pixels, PDF pages, OCR/layout-model seconds, SQL CPU/scratch high-water, generated model tokens, output/retained bytes, egress, manual/scheduled checks, reruns and support minutes. These are measured quantities, not invented provider prices. Estimate parser/model startup, rejected inputs and repeated attempts as well as successful work. A trial count alone cannot bound ETL cost.

Keep the base monthly model's £0 platform-paid bulk ETL/model compute under customer-supplied execution. Sensitivity: if the platform later subsidises parsing/analysis by an assumed £1 per active free account, 1,000 free accounts add £1,000/month; break-even becomes ceil((18,350 + 600 + 1,000)/205.33) = **98 Team workspaces**, versus 93 base. An extra 15 minutes/month of support per Team workspace costs £12.50 at £50/hour; combining it with that subsidy yields ceil(19,950/192.83) = **104 workspaces**. These are exposure assumptions, not cloud quotes, approved subsidies or conversion forecasts.

Pilot measurements must include data scientist and software-engineer tasks: source-format mix/pages/bytes, time to checked insight, incorrect joins/type repairs, analysis-to-prediction conversion, second task type, reproduction success, monitoring usefulness, compute per accepted output and support minutes. Do not sell a broad platform until repeat value is observed beyond the support recipe. Document intake may remain a useful sales example; it does not define the buyer or product.

## Desktop, open-ended collections and broad tasks

Community/local includes the native GUI/harness, basic multi-source contracts/joins, task-extension mechanism, CLI/SDK and filesystem export under the proposed Apache-2.0 boundary. The user operates/pays hardware, storage, external APIs and chosen provider compute. Hosted-free coordination still has D07/D08 byte/retention/request quotas; no project-level fixed dataset-count rule is introduced, but metadata/storage limits can require export or paid opt-in. Do not describe unlimited datasets as unlimited hosted storage, ETL scans, GPU work or support. Quota exhaustion preserves read/export/control and gives an explicit stopped/queued state, never automatic charging.

Meter source bytes/decoded pages/pixels, metadata/profile scans, relationship candidates, join output/spill, documentation fetch/cache, environment builds, model/judge/agent use, export egress and support by task. Core filesystem export is not a paid unlock. Offline deployment/support contracts do not need hidden per-call metering. The existing fixed/variable unit model remains a hypothesis: the M1 expansion changes build effort, not evidence of £0 running cost or a measured increase in conversion.

Edition 0.7 adds 24–38 engineering days (£15,600–£24,700) to M1; revised cumulative totals are 155–236 days (£100,750–£153,400) through M2 and 203–313 (£131,950–£203,450) through M5, excluding optional later waves and the same hardware/reviewer/compute items as delivery_plan.md. Adding £1/month of docs/profile coordination cost per 1,000 active free accounts would add £1,000/month and move the existing break-even hypothesis from 93 to 98 paid teams, all else unchanged. No new cloud quote or measured cost is claimed; FIN measures activity distributions and support effort in pilots.

Listings distinguish an experimental generated workflow from qualified reusable recipes, exported analysis bundles, installable releases and managed endpoints. List each tested operation/library/model/OS/ISA/accelerator profile and evidence date. A Python import, filesystem bundle, hub task tag or native installer is not a quality/compatibility guarantee. Private multi-source data, join semantics and customer releases remain private. E1–E6 publisher breadth waits for repeat adoption and each capability's support/rights evidence; marketplace fees remain hypotheses.
