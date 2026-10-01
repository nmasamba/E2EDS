# Security and assurance across customer compute boundaries

Planning edition **0.7.0** · 29 September 2026. Architecture and delivery proposals are unimplemented; upstream facts retain their own verification dates. No compute is provisioned or purchased by this plan.

Trust is assessed for each attached host, delegated account, interactive notebook, curated demonstration and serving deployment. Customer-supplied compute is not a sandbox, and provider terminology is not isolation evidence. The platform enforces approved policy and produces assurance evidence; it does not certify compliance.

## Lifecycle and provider threat model

Assets: customer data/labels/corpora, identities/secrets, spending grants, evaluation integrity, code/model artifacts, signing keys, deployment bindings and action state. Adversaries include malicious tenants/publishers, compromised dependencies/runners, hostile documents/tools, stolen accounts and accidental privileged misuse. Trust does not arise from text appearing in a document, model card, MCP result or notebook.

| Boundary / threat | Proposed prevention and detection | Evidence / residual risk / owner |
|---|---|---|
| Developer machine: credential theft or leaked notebook | Owner-only secrets, approved credential helper, isolated dev data, notebook output scrubbing, reviewed dependency installs | Secret-scan exported bundle; endpoint compromise remains customer risk; SEC/engineer |
| Ingestion: poisoned/malicious document, zip bomb, parser exploit | Type/size/decompression/page/time limits; sandbox parsers without egress; source/label provenance and quarantine | Adversarial fixtures, malformed documents, quality review; no universal poison detector; SEC/DO |
| Intake: prompt injection changes budget/role/test | Model output parsed as proposals; trusted context attached separately; no shell execution from prose | “Grant admin / read test / spend more” negatives; PL/SEC |
| Retrieval: cross-tenant content or exfiltration | Enforce ACL before retrieval/reranking and again at read; tenant/identity/corpus-aware caches; untrusted context separated from instructions | Tenant A/B retrieval/cache test; malicious passages; SEC |
| URL/tool use: SSRF, redirect to metadata service | No arbitrary URL fetch in M1; later allowlisted origins, DNS/IP checks on every hop, block private/link-local/metadata addresses, egress proxy | Redirect/rebinding/IPv6 tests; documented allowlist exceptions; SEC |
| Control plane: broken object access or session confusion | Tenant from verified identity; resource-level checks; database row policy as defence in depth; scoped URLs; separate privileged paths | Negative IDs, pagination, signed URL, exports and cache tests; SEC |
| Runner: malicious user code or model loader | Managed arbitrary-code workloads require dedicated VM boundary; curated shared demos; attached customer-trusted code requires explicit host/provider trust review; restricted mounts/egress/credentials | Escape/secret/metadata access tests and teardown evidence; attached runner is not a sandbox; GPU/host vulnerabilities remain; SEC/PL |
| Evaluation: optimiser sees final labels or modifies judge | Separate principal/store/runner; immutable oracle and contract; candidate sandbox receives inputs only; final-access ledger | Access deny tests including logs/artifacts/exception channels; EO/SEC |
| Build/registry: supply-chain substitution | Digest-pinned inputs; hash locks; dependency/SBOM/license scan; restricted builder; separate signer; verify before load | Tampered artifact, unsigned release and compromised-key drills; PUB/SEC |
| Serving: denial of service, billing abuse | Payload/complexity/concurrency limits, grant reservations, bounded queue/time, idempotency and rate limits | Load/cost-race/cancel tests; provider billing lag remains; SO/FIN |
| Agent tools: duplicate or unauthorised effect | Allowlisted typed actions, separate proposal/commit grants, durable action IDs and reconciliation | Simulator duplicate-ACK/timeout/permission fixtures; code rollback cannot undo real effects; SO/EO |
| Telemetry: raw PII/secrets retained or sent across borders | Allowlisted attributes, payload capture off, explicit debug consent, redaction, encryption, access/retention controls | Canary secrets/content scan and residency review; redaction is imperfect; DO/SEC |
| Delegated provider account: resource theft, runaway spend or accidental deletion | Separate provisioner identity; scoped project/region/images, ownership ledger, bounded reservation; never delete attached/unrelated resources | A18/A19/A21; unclear provider state stays unknown; PL/FIN/SEC |
| Consumer notebook: broad mounted storage, owner bypass or sensitive AI prompts | Narrow approved mounts; train/tune only; reviewed data treatment; independent evaluator elsewhere | A20/A22; consumer availability does not establish residency or independent sealing; DO/EO |
| Shared demonstration: pooled credentials, quota billing or private data upload | Curated operation, correct user attribution, explicit provider-credit behaviour and no automatic paid fallback | A23; unobservable no-charge allowance blocks zero-spend automation; PUB/FIN/SEC |

M1 explicitly plans bounded CSV/Parquet, UTF-8 text, PDF and PNG/JPEG ingestion, including a separately qualified OCR profile. D20, native dependency/model-rights review and A35 are mandatory for each advertised format. Arbitrary publisher code is not admitted to a shared free runner.

The generic runner authenticates jobs and reports usage; it is not a malicious-code isolation mechanism. The provider/hypervisor/host administrator can be inside the customer's trust boundary. Record the actual isolation properties before accepting private data; a product name such as Secure Cloud, an ordinary Pod or a CUDA device allocation is not independent proof of tenant isolation. Unreviewed provider profiles start with synthetic data only. Arbitrary shared managed execution still requires ADR07 evidence; attach mode does not weaken that requirement.

## Local model, conversation and generated-code boundary

The M1 assistant runs as a low-privilege supervised local process; its API listens on loopback with a locally protected key. Local desktop or optional browser access still needs authentication; loopback HTTP additionally needs Origin/Host checks and CSRF protection; loopback is not authorisation. Do not expose the model server publicly or copy its key into desktop renderer or browser code. Disable built-in model-server agents/tools, auto-downloads, prompt logging and unapproved network access. Review model parser/runtime vulnerabilities, quantised weights, templates and exact runtime binary before loading; a GGUF file is untrusted input even without Python deserialisation.

The model proposes typed tool calls; our dispatcher checks trusted principal, requirement revision, scope, budget and fence. Only authenticated direct-user messages reach the control channel. Content from datasets, documents, outputs and quoted instructions cannot promote itself into pause, grant or system policy. Protected policy and canonical constraints survive context compaction. Dedicated control handling preserves pause/cancel during model overload or failure; it cannot guarantee delivery to an offline remote worker.

Generated code requires a dedicated restricted VM with no host secrets/home mounts, no network by default, immutable permitted inputs and bounded output/scratch. M1 can attach a customer-provided reviewed guest; attaching a process is not sufficient isolation. The local administrator and hypervisor remain trusted, and no hostile-owner/evaluator-independence claim follows. Static code checks are not a sandbox. Candidate artifacts and notebook HTML are untrusted on ingestion: bound/parsing checks, sanitised preview, no active notebook output scripts, and restricted evaluator/build environments apply.

Keep conversation, code patches and tool results private and access-controlled; redact credentials/content from streamed status and persistent logs. Rounding a value does not establish anonymisation, and an account identifier may remain personal/linkable data [S47]. D18 controls and A24–A30 add evidence at G1/G3. See [local_model_runtime.md](local_model_runtime.md) and [conversational_control.md](conversational_control.md).

## Discovery and workspace security

Collectors use fixed allowlisted probes against selected/attached environments; no LLM-generated shell, privilege elevation, network scan or credential enumeration. Minimise hardware identifiers and keep local inventory private unless authorised for coordination/support. Agent-provided observations are authenticated evidence with scope/time, not a trusted attestation against a malicious host administrator. Unknown effective limits or isolation block affected admission. See [hardware_discovery_and_planning.md](hardware_discovery_and_planning.md).

The GUI is a permission-filtered ledger/artifact view, not an authority boundary. Escape logs, notebook/report text and source metadata; do not execute artifact HTML or code in the privileged coordinator origin. Isolate approved report previews, deny untrusted active content and keep offline reports self-contained. Artifact links enforce tenancy and roles independently. Displaying an independent evaluation cannot grant the optimiser final-case access. Hardware recommendations and chat corrections cannot enlarge grants, weaken evaluation or promote production. [gui_workflow.md](gui_workflow.md) defines truthful state and stale/disconnected handling.

## Identity, tenancy, delegated authority and secrets

Use organisation/project membership and object-level capabilities derived from an approved identity provider or local deployment profile. Validate issuer, audience, signature, expiry and scopes for every remote request; apply the same RequestContext and policy inside the application core for HTTP and MCP. Tool descriptions/annotations are advisory. A signed request is not automatically authorised to read a release, dataset or result.

Apply access control to object storage paths, artifact downloads, data previews, retrieval indexes, caches, reports and logs. Storage namespace alone is insufficient; cryptographic URLs have short TTL, recipient scope and audit records. Avoid cross-tenant deduplication that reveals existence. Use tenant-aware cache keys and invalidate on ACL/data changes. Shared MLflow access must go through the product boundary or use independently secured tenant instances; do not assume its basic-auth UI constitutes complete tenancy enforcement.

Secret references resolve in deployment bindings/customer runners. Never include secret bytes in released bundles, prompts, desktop renderer or browser code, notebook outputs or traces. Prefer workload identity and short-lived tokens to long-lived keys. Builder, evaluator, signer and service identities have different privileges. Break-glass access requires a named human, narrow scope, audit and expiry. Free-tier privacy and secure transport are baseline controls, not paid upgrades.

ComputeBinding is trusted configuration after review, not a caller-provided permission grant. Platform validates account ownership/delegation and restricts region, resource shape, image, purpose, network and spend. Prefer short-lived delegated identity where available. If a provider offers only API keys, store the minimum scope in the appropriate secret manager; use a dedicated project/account if scopes are too broad. Workers do not receive provisioner credentials. Revocation blocks new work and triggers reconciliation of active leases/resources.

## Privacy, residency and separate rights

Default raw data stays with the customer. Hosted coordination stores contract metadata and explicitly permitted summaries; a customer may choose managed data processing after residency, purpose and subprocessors are reviewed. Distinguish operational monitoring, evaluation examples, expert annotations and training data. Production input is not training consent.

Record ownership and the right to use, adapt, redistribute, host and sublicense separately for code, weights, adapters, datasets, evaluation sets and generated outputs. Customer-specific artefacts remain private; training does not confer publication rights. Base-model licences and provider terms may restrict portability, redistribution or use even when the runtime code is Apache-2.0. Synthetic examples can also contain copied or personal content; audit provenance before labelling them first-party/CC0.

Retention is purpose-specific. Propose 30-day free operational results/traces, 90-day Team operational telemetry, project-agreed release evidence and 35-day encrypted rotating backups. Customer contract/legal holds may change these; record exceptions and expiry. Warn before quota/retention expiry, permit export and delete derived copies according to the lineage procedure. Backups are access-restricted, expire on schedule and replay tombstones after restore. Immutable audit digests must not retain recoverable personal content indefinitely without purpose.

Deletion from training sources does not erase learned information. DO/CL assess continued lawful use and impact; ML evaluates retraining, exposure tests, validated unlearning where available or withdrawal. Withdraw a release if required rights no longer hold and safe remediation cannot be established. Neither a hash nor an “anonymised” label is proof that data is nonpersonal.

Do not mount a whole personal drive, user home or credential directory by default. Use least-scope artifact stores, explicit manifests and output scrubbing. Keep private data out of consumer notebook AI assistance unless the applicable data handling has been reviewed and authorised. Do not infer contractual region/privacy assurances from free access. Interactive runtime administrators cannot also serve as an independent sealed-evaluation trust boundary for their own experiment.

ZeroGPU initial design is first-party curated inference; user code, private checkpoints, arbitrary URLs, write-capable tools and cross-tenant caches are excluded from that profile. Publisher reviews source, licenses, model rights, logs and visibility before publication. A public Space and MCP listing require G5; building a draft demonstration locally grants no publication authority. User HF identity/quota attribution must be tested for the selected API/MCP path; never use one shared credential to imply each user has a separate allowance.

## Jurisdiction and dated official evidence

Propose a UK-first low-risk B2B data/analysis and predictive pilot, with an EU applicability questionnaire. It captures intended use, provider/deployer/importer/distributor roles, establishment/operating locations, markets, output-use locations, affected people, data categories, product integration, distribution and relevant dates. Location alone does not classify a system. General-purpose-model adaptation may alter a participant's role; CL must review this before distributing weights or making provider claims.

**VERIFIED-EXTERNAL, 18 September 2026:** the Commission's current AI Act guidance says general applicability began 2 August 2026, with earlier prohibited-practice and GPAI phases. Its AI Omnibus notice says the amendment entered into force 27 July 2026 and gives Annex III high-risk dates of **2 December 2027** and Annex I product-related dates of **2 August 2028**. These are reported as enacted by the official notice, not merely proposed. [Commission framework](https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai), [Omnibus entry-into-force notice](https://digital-strategy.ec.europa.eu/en/news/ai-omnibus-enters-force).

The final legislative link was reached but the legal-text endpoint presented a JavaScript access challenge. Therefore exact amended article wording, transitional exceptions and the effect on specific roles are **not fully verified here**. The Service Desk Article 2 page reproduces the 2024 scope text, including output used in the Union; it is useful screening evidence but explicitly identifies its older source. CL must check consolidated law before customer release, rather than combining old articles with new dates as if that were a legal opinion. [Article 2 service desk](https://ai-act-service-desk.ec.europa.eu/en/ai-act/article-2), [final amendment link](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=OJ:L_202601744).

For GDPR, plan applicability analysis of establishment, offering/monitoring, controller/processor roles, purposes/lawful basis, data categories, transfers, individual rights, DPIA need and significant automated decisions. The EDPB's current guidance covers individual rights and exceptions; deleting personal data is not an unconditional promise regardless of legal context. [EDPB rights guide](https://www.edpb.europa.eu/sme/be-compliant/respect-individuals-rights_en). Exact EU consolidated legislative text could not be read in this session; article-level mappings below are **review topics**, not final applicability determinations.

For the initial UK hypothesis, use current UK GDPR/DPA framework and ICO AI/lawful-basis guidance; assess applicable Data (Use and Access) Act changes and commencement with qualified review instead of copying EU automated-decision rules. [ICO AI guidance](https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/artificial-intelligence/), [ICO lawful-basis guide](https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/lawful-basis/a-guide-to-lawful-basis/). Specific amendment effects remain OPEN. Sectoral rules, consumer/product safety, cyber/product obligations and procurement requirements are added only when use/distribution triggers them. Do not claim the initial synthetic demo meets medical-device, financial or employment compliance.

## Control-to-evidence map

An ObligationControlMapping contains official citation/version/effective date, applicability rationale, control implementation, evidence digest, owner, exception, expiry and review status. Internal policies can be stricter than statutory minima without mislabelling them as law.

| Control ID | Requirement / applicability-review topic | Planned control and evidence | Accountable owner |
|---|---|---|---|
| C01 | R07; purpose/lawful use, privacy and dataset/model rights | DataManifest, purpose grants, rights inventory, retention/deletion drill | DO/CL |
| C02 | R05; evaluation validity and data governance | Sealed principals, split/point-in-time tests, signed independent report | EO |
| C03 | R05/R08; financial authority and billing accuracy | Trusted grants, reservation race test, retry cost receipts and reconciliation | FIN/PL |
| C04 | R04/R07; access/security review | HTTP/MCP parity, tenant isolation/egress negatives, secret scan | SEC |
| C05 | R11; technical documentation/provenance | Release manifest, SBOM, provenance, licence checks and signature | PUB |
| C06 | R06; human oversight/change authority | ChangeProposal, regression report, named approval and staged-promotion audit | PO/SO |
| C07 | R10; operational security and resilience | SLO/load/backup-restore/incident drills, vulnerability review | SO/SEC |
| C08 | Individual-rights/DPIA/transfer topics where applicable | Data-flow map, processor terms, rights request workflow, qualified DPIA decision | DO/CL |
| C09 | AI Act transparency/intended-use/high-risk/GPAI role topics | RegulatoryProfile, output notices/provenance where applicable, qualified classification | CL/PO |
| C10 | Marketplace claims and consumer/commercial rights | Claim review, evidence grade, hardware/load qualifications, withdrawal process | PUB/CL |
| C11 | R13/R14; provider authority and resource ownership | Qualified binding, scoped account, native IDs, ambiguous create/stop, no deletion of unrelated resources; A18–A21 | PL/SEC/FIN |
| C12 | R07/R14; notebook/shared-demo data and quota scope | Permitted movement, retained-store inventory, profile-specific quota identity and no private-demo upload; A22/A23 | DO/SEC/PUB |

Classification/status defaults to `unreviewed` or `not_applicable_with_rationale`, never inferred PASS from a country field. Reassess for changed intended use, roles, data distribution, geography, model/base provider, material behaviour or relevant law. No launch through G4 with unresolved material applicability or ownership questions.

Additional controls C13–C15: **C13 conversation authority** maps R15/R17 to authenticated command receipts, revisions, replay/deduplication and A24–A27 (PL/SEC); **C14 local assistant and code isolation** maps R16/R18 to pinned runtime/model inventory, no-egress/VM evidence and A28/A30 (SEC/ML/PL); **C15 user constraint preservation** maps R17 to role/feature/postprocessing tests, output/privacy review and A29 (ML/DO/EO). These extend the obligation mapping without asserting compliance certification.

| Control ID | Requirement / control | Evidence | Owner / gate |
|---|---|---|---|
| C16 Hardware discovery and admission | R19; fixed probes, minimal inventory, fresh capacity and scope checks | A31–A33; unknown/permission/race cases and profile qualification | PL/SEC; G3 |
| C17 Workspace evidence and control integrity | R20/R05; role-filtered events/artifacts, replay and stage reduction, self-check separate from evaluation | A34; spoofed progress, sealed-link denial, reconnect and unsafe-content cases | Application Lead/EO/SEC; G2/G3 |

## Operating responsibilities, incidents and recovery

Assign operator per component as in architecture.md. Encrypt backups, test restoration into a clean environment, verify artifact references and apply deletion tombstones before reopening access. Proposed hosted coordination RPO/RTO is D11's companion operational table: 24 h/4 h. A lost 24-hour window of accepted jobs must be explicitly identified/reconciled; use WAL/PITR and tighter RPO before claiming stronger durability. Customer-installed services keep their own required state backups; hosted-plane backups cannot restore local customer actions.

Incident process: named incident commander classifies scope → contain tokens/egress/releases → preserve minimally necessary evidence → notify contractual/security contacts and competent authorities where applicable after legal assessment → reconcile actions/billing → restore qualified version → publish internal post-incident corrective plan. Response clocks are determined by the applicable regime/contract; do not invent a universal notification deadline.

Vulnerability intake uses a published security contact and supported-version policy. Proposal: support current and previous minor release for six months, subject to critical fixes; maintain a signed advisory and revocation feed. Triage actively exploited critical issues within one business day in the pilot support model; patch/mitigation timing is risk-assessed, not guaranteed in this plan. Offline customers receive signed advisories/updates through agreed channels, with known revocation-delay limitations. Urgent withdrawal blocks new installation and triggers operator action; it does not silently brick a disconnected service unless that behaviour was explicitly contracted.

Rollback restores code/model/binding only within a declared data-schema compatibility window. Agent actions need an effect ledger, reconciliation and domain-approved compensation. A sent email, payment or changed external record is not automatically undone by reinstalling an earlier release. The reference simulator avoids real effects; future action adapters must demonstrate safe ambiguity handling before enabling commits.

The component operating agreement names who holds provider credentials, responds to orphaned billable resources, stops delegated jobs and retains/deletes checkpoints. Customer-direct billing is not permission for the platform to abandon delegated cleanup. Provider outages, quota exhaustion and account revocation have separate runbooks from coordination outages. Changing region, data recipient, external model or significant execution behaviour triggers the relevant applicability and control review.

## Bounded improvement loops

| Loop | Observations | Permitted mutations and budget | Independent oracle / promotion | Rollback and owner |
|---|---|---|---|---|
| Workload improvement | Authorised train/tune data, trial metrics, errors/resources | Enumerated parameters/model/prompt/retrieval/workflow; original grant and family limits | Frozen EvaluationContract; final access controlled by EO; PO approval after PASS | Keep last candidate/artifacts; no production impact until release; ML/EO |
| Service improvement | Permitted redacted telemetry, delayed labels, adjudicated feedback, incidents | New data snapshot/recipe/config within ChangeProposal; separate FIN grant, never free reuse of all traffic | Independent refreshed acceptance data as needed; regressions/slices/ops/rights; staged deployment and PO+SO promotion | Previous qualified release and binding; reconcile/compensate effects; SO |
| Platform improvement | Authorised tenant-scoped experiment/resource history; opt-in aggregated statistics | Resource estimators, scheduler policy and suggested defaults; offline replay first and capped canary budget | Holdout historical jobs, shadow estimates, overrun/fairness/reliability measures; PL+SEC/FIN approval | Versioned scheduler/default policy revert; PL |

For platform learning, cross-customer use requires explicit rights and a defined privacy treatment (e.g. aggregation thresholds, minimisation and a documented reidentification assessment). No cross-tenant raw traces by default. Suggested default changes affect new reviewed WorkloadSpecs, not already approved jobs.

Each ChangeProposal specifies what may adapt, immutable controls, measurements, human decision and rollback limits. The optimiser can never enlarge permission/spend limits, modify its judge/test/acceptance standard, inspect sealed data, disable logging or silently change production. Synthetic examples support development; they cannot alone prove the loop improved real customer outcomes. Evaluate biased feedback, ground-truth delay and behaviour changes induced by earlier releases before attributing improvement.

## Data/analysis assurance extension

| Control | Obligation/policy purpose and design | Evidence / accountable owner |
|---|---|---|
| C18 Parser and SQL containment | Treat imported/generated SQL, native parsers and OCR/model loaders as executable content. Dedicated restricted VM, allowlisted mounts, no network, approved dependencies, D20 decoded-size/page/pixel/resource bounds; disable unapproved extension loading. | A28/A35; malformed/bomb/path/egress fixtures, lock and transitive rights inventory; SEC/PL |
| C19 Gold semantics and claim integrity | Carry purpose/ACL/retention/lineage through rows, extracted spans, images, joins and reports. Review grain, keys, units, quarantine and independent recomputation. No anonymity or causal inference from formatting/EDA. | A35/A36; quality/source-coverage report and DO/DE/EO decisions |
| C20 Output monitoring authority | Explicit target, source access, owner, cadence, budget and retention; manual M1 default; no autonomous source polling, retraining or promotion | A37; schedule/manual receipts, deny/revoke/stop tests; DO/SO/FIN |

Reject encrypted/unsupported files safely; do not crack protections. Bound image decoding and PDF rendering before allocating unbounded buffers; parser timeouts need process/VM enforcement. Disable model auto-downloads and remote OCR in the offline profile; prefetch only reviewed weights under separate authority. User data stays inside its approved environment. Library/configuration options are defence in depth, not the tenant sandbox [S53/S56].

Analysis packs can expose sensitive joins and small aggregates even without a trained model. Apply row/column access, export review, redaction and retention to gold tables, notebooks, HTML and cached queries. Source-row deletion propagates through analysis artifacts as well as ML artifacts; immutable identity does not require keeping personal bytes forever. Treat CSV formula injection on export and active HTML/script content as hostile. Suppress executable spreadsheet formulas by the declared export policy and render reports with escaped content/no remote scripts.

RegulatoryProfile covers intended use of datasets, analyses and services; exploratory status alone does not remove privacy or other obligations. No additional legal classification is inferred merely from broadening supported input formats. Existing dated official sources and qualified CL review remain the applicability basis. Customer ownership/rights do not automatically permit publishing a derived gold table, extracted image or analysis pack.

## Desktop, relationship and documentation controls

| Control | Threat / invariant | Evidence / owner |
|---|---|---|
| C21 | Linking datasets can re-identify people or widen purpose/access; apply per-member checks and purpose intersection, not collection-only authority | A39–A41 access and temporal/key fixtures, lineage/deletion review; DO/SEC/EO |
| C22 | Malicious/outdated docs or dependency examples can induce code execution/exfiltration; approved versioned broker, no customer content in public queries by default, reviewed diffs/builds and runner deny-egress | A42/A43 docs injection, version mismatch, package/model hook and target tests; ML/SEC/PUB |
| C23 | Compromised renderer/report can reach native files/processes; bundled UI only in privileged context, narrow IPC, authenticated harness, no report iframe with native access | A44 origin/IPC/renderer and crash tests on actual OS/webview; PL/SEC |
| C24 | Generated filenames, symlink races or interrupted export can escape scope/overwrite evidence; opaque trusted OutputBinding, resolved paths, staged new-version commit and receipts | A45 traversal/race/disk-full/cancel/restore tests; PL/PUB/DO |

These are planned controls. Tauri capabilities reduce frontend access but are not the generated-code sandbox [S64]. The existing VM boundary remains; root/local-owner compromise is not defeated by application roles. Files exported to customer-controlled folders follow the customer's encryption, access, backup and retention policy. Removing platform copies does not erase uncontrolled external exports; record affected recipients and remediation ownership. Joining pseudonymous IDs or rounding outputs does not automatically anonymise them.

Unsloth Core versus optional Studio/Desktop UI rights are reviewed separately [S62]; exact package/subtree/transitive/model notices are O23, not inferred from a repository badge. Desktop code signing, update verification, per-OS installers and third-party codecs/models add supply-chain scope; deferred platforms are not advertised as supported. Existing jurisdiction profiles remain context-specific; adding audio/biometrics, quant decisions, RL or a new market triggers CL reassessment, not automatic compliance certification. See [desktop_experience.md](desktop_experience.md) and [task_expansion.md](task_expansion.md).
