# Library-backed task expansion and code adaptation

Planning edition **0.7.0** · 29 September 2026. Planning only: no application, dataset, model, deployment or monitoring job has been implemented or run. Upstream facts retain their own verification dates. No spending or publication is authorised.

## Recommendation — R25 / ADR27

Make the platform extensible by **task capability**, with a documentation-assisted implementation path. Retain distinct execution families and a common lifecycle. Namespaced task IDs refer to a versioned TaskCapabilitySpec rather than requiring a platform fork for every estimator or task. A library import is not a support declaration: qualification is specific to task, operation, modality, library/model revisions and runtime profile.

The long-term backlog includes all task categories in the requested ecosystems. Maintain a dated upstream taxonomy and a coverage ledger with proposed, experimental, qualified, deprecated or unsupported status and a reason. Include newly introduced upstream categories at a planned review; the moving set of every function/model is not a fixed delivery commitment. M1 implements the extension mechanism and existing bounded recipes. Later waves broaden evidence-backed coverage. Selecting a model or discovering documentation never automatically installs it.

| Support level | User may do | Claim permitted |
|---|---|---|
| Proposed | Inspect plan, docs, missing prerequisites and estimates | An approach is identified; no execution/support claim |
| Experimental generated workflow | Authorised code runs in a qualified sandbox with pinned inputs/limits and task checks | This particular run's measured result; limitations and unsupported recovery/service operations visible |
| Qualified reusable capability | Repeat through reviewed adapter, declared oracle, failure/recovery and profile tests | Only documented task/operation/version/profile scope; new customer suitability still needs evaluation |

## Code adaptation protocol

1. Resolve intended result, task family, data/relationship products, baseline, oracle, output kind, error costs and execution/output architectures. The assistant may propose a plan even when a target is currently unavailable.
2. Inspect authorised existing code and lock files without executing them. Prefer an applicable qualified recipe, then a reviewed imported implementation, then bounded generated code. Record why reuse is or is not suitable.
3. Request relevant **version-matched official documentation** through a restricted documentation broker. Store URL, package/revision, retrieval time, content digest, allowed-use notice and cited sections as DocumentationEvidence attached to CodeTask. Use approved cached/offline docs when disconnected. If only a different version is available, flag the mismatch; a guessed API is not verified.
4. Produce a reviewable implementation/dependency diff and typed tool plan. Pin package hashes and model revisions through the normal build process; identify executable model-loading hooks, native kernels and optional extras. Public docs and code examples are untrusted reference content, never policy instructions or permission grants. Do not send customer data/schemas/secrets as search terms by default.
5. Deterministic admission checks task registration, rights, requested operation, environment/ABI, RAM/VRAM/scratch, egress policy, permissions and reservation. The docs broker fetches references; the generated runner still has no unrestricted network or package manager. A dependency addition follows a controlled build, not a shell command that bypasses CodeTask.
6. Execute bounded syntax/import/schema checks, then a small semantic fixture and task-appropriate evaluation. Record real errors and at most D17's two code repairs. Smoke success does not prove statistical validity. Refuse or mark inconclusive when the oracle, data or target profile is missing.
7. Collect code/diff/docs/lock/run evidence, reproduce on the output target and package. EO/ML/SEC approve reusable qualification at G1–G3; PO/SO approve release and operation. A one-off experimental run does not register a globally trusted adapter.

ImplementationProposal is a CodeTask/ChangeProposal role, not a second orchestrator. It records parent code, task capability ref, documentation evidence, dependency changes, expected outputs, affected contracts, checks, allowed repair budget and required decisions. Existing immutable artifact storage and run ledger suffice; no separate vector database, autonomous installer or framework-per-task control plane.

## Coverage programme and later waves

Primary upstream categories were checked 29 September 2026 [S57–S62]. The rows below are our roadmap grouping, not a statement that these libraries implement identical interfaces or that this product currently supports them.

| Wave | Coverage inventory | First usable increment / distinct acceptance |
|---|---|---|
| E1 classical breadth | scikit-learn supervised models, ensembles, multiclass/multilabel/multioutput and semi-supervised; clustering/biclustering, mixture/density models, decomposition/manifold, covariance and anomaly/novelty; preprocessing, selection, calibration and inspection compositions | Clustering plus anomaly recipes after M1; held-out or domain-labelled task checks, stability and utility. Training-only transforms remain mandatory even when unsupervised. Fuzzy linking is a separately evaluated sub-item. |
| E2 scientific/time series | SciPy statistics, optimisation, signal/image processing, interpolation, integration, linear/sparse algebra; arch volatility, unit-root/cointegration, bootstrap and comparison methods | A signal/statistical analysis and volatility forecast; time-of-availability joins, rolling-origin evaluation and appropriate dependent-data uncertainty. SciPy/arch are not a universal forecasting or quant stack; add another library only for an evidenced missing method. |
| E3 vision | HF image classification/features, detection/segmentation, keypoints/masks/depth, zero-shot vision, image-to-text; image generation/transformation and 3D categories retained in backlog | Image classification and detection first, with image/label rights, geometry transforms and independent slice/annotation checks. Generative images/3D require additional model libraries/profiles and separate safety/quality methods. OCR ingestion alone qualifies none of these. |
| E4 NLP, audio, video and multimodal breadth | HF text/token/zero-shot classification, masking, embeddings/similarity/ranking, QA/table-QA/translation/generation; speech recognition/synthesis, audio classification/transformation; document/visual retrieval, audio/text/image/video combinations, video classification/generation/transformation | Extend M1B/M3 with one audio and one multimodal task; timebase/resampling/frame/schema alignment, human evaluation and model-specific processor evidence. Catalogue every remaining HF task category, including any-to-any; no single universal pipeline claim. |
| E5 training optimisation | Optional Unsloth Core backend for selected SFT/PEFT recipes, later supported preference/multimodal training | Same permitted training/evaluation data and task contract as M4's PyTorch/PEFT/TRL baseline; actual weight changes, export/resume and measured quality/resources on the selected target. No vendor speed or memory multiplier is promised. |
| E6 bounded RL | Gymnasium environment contract; a separately selected learning algorithm and optional qualified training backend | Resettable simulation, independent success oracle, bounded episodes/steps, reward provenance, termination/truncation and simulator/transfer checks; trainable policy explicitly identified. No unconstrained real-world RL or large-scale pretraining. |

Gymnasium is the recommended maintained Gym successor [S61]. It supplies environments/API; a learning algorithm, reward and evaluation still have to be selected. Legacy Gym environments need an explicit compatibility wrapper/test. RL is a later qualified learning capability, not a renamed agent prompt search. M4 simulation/configuration evaluation remains useful without E6.

HF task coverage may require Transformers, Datasets, PEFT/TRL or Diffusers and task-specific processors; choose the minimum for the selected recipe. Model weights, datasets, codecs/simulators and application code have separate rights. A hub task tag or model card cannot establish that a given model trains, exports or runs on our intended hardware.

Each wave's initial increment estimate is in [delivery_plan.md](delivery_plan.md). These are discovery estimates for the stated first recipes, **not estimates to finish the entire category inventory**. The full expansion backlog remains uncommitted pending task demand, oracle/data access, rights, profile evidence and support cost.

## Adapter contract and target architecture

TaskCapabilitySpec declares family, operations, modalities, input/output schemas, learning target, evaluation approach, dependency/docs refs, resource estimates, profiles and unsupported behaviours. Existing prepare/validate/execute/checkpoint/cancel/collect/fail semantics remain mandatory. A batch-only algorithm may export a reproducible analysis/prediction file without a request-serving claim. Non-inductive methods must not pretend to predict unseen rows; record transductive/fit-only semantics and rerun cost.

Plan separately for **desktop/assistant**, **execution**, and **output replay or inference**. Check OS/ISA, Python/native ABI, CPU instruction requirements, RAM, GPU vendor/driver/runtime/VRAM, precision, storage, network and licences. A local assistant may generate code for a customer GPU elsewhere; only actual target evidence qualifies the release. Changing model, precision, preprocessing, algorithm or fallback to fit hardware creates a reviewed diff and applicable regression evaluation. No silent semantic substitutions.

## Build versus integrate and exit

Integrate upstream algorithms and official documentation; own task contracts, safe code admission, lineage/joins, evaluation integrity and packaging evidence. Unsloth now advertises its own local UI/model training and document features [S62]; notebooks, existing IDE agents and MLflow also cover significant parts of this workflow. Our value hypothesis must be established through correct multi-source interpretation, controlled intervention and reproducible handoff, not generic code generation or a claim that the market is empty.

Candidate exact versions, licence evidence gaps and maintenance observations are in [research_sources.md](research_sources.md). Do not bundle an upstream UI merely because its core package has a permissive licence. Exit paths are ordinary source/diffs, data/lineage manifests, locks, evaluation reports and runtime-neutral operation contracts; adapters can be replaced without rewriting customer intent or erasing evidence.


## Later family extensions

The five current dispatch paths (four ML/AI families plus data_analysis) are not a claim that all future algorithms fit them. Non-generative neural classification/detection training must not be relabelled generative training just because it uses Transformers. E3/E4 include a proposed `neural_ml` family adapter/schema migration before those training claims: identify pretrained base/processor, frozen versus trainable parameters, supervised/self-supervised objective, checkpoint state and task oracle. Pretrained inference, adaptation and training are separate advertised operations. ML/EO own this extension and its cross-contract tests; unsupported family requests remain rejected until registered and qualified. Existing four-family semantics stay invariant. Adding a new task inside an existing family needs a registered TaskCapabilitySpec; adding genuinely new execution semantics may also need a reviewed schema/adapter version.
