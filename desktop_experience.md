# Desktop experience, local harness and filesystem delivery

Planning edition **0.7.0** · 29 September 2026. Planning only: no application, dataset, model, deployment or monitoring job has been implemented or run. Upstream facts retain their own verification dates. No spending or publication is authorised.

## Primary product — R26/R27, ADR28/ADR29

Build a **GUI-native desktop application**: launch it like an ordinary app, choose a project/output folder, describe the work and inspect/intervene continuously. The app starts or reconnects to a per-user local harness that owns the ledger, model gateway, job control, artifacts and authorised filesystem access. Starting the harness is lightweight and model-independent. Loading weights, building environments, mounting sources or using paid compute still follows explicit policy and grants. No terminal setup is required for ordinary use once the qualified installer and runner prerequisites are present.

The CLI/SDK is a supported fallback and automation surface. Concise progress is its default, with structured events, full authorised logs/diffs and pause/cancel/resume/export available on demand. It does not lose evidence or permission checks. Hosted collaboration may provide a browser projection later; it is not required for the local desktop or filesystem output.

Recommend **Tauri 2.12.0 as the desktop-shell qualification candidate**, with a small web renderer and the existing Python harness as an external process [S63/S64]. Tauri supports packaged sidecars per target architecture and scoped frontend capabilities; neither feature isolates generated Python. Keep business logic in Python and untrusted execution in the existing qualified runner VM. This adds Rust/webview packaging expertise and OS-specific signing/accessibility work. Electron is the fallback if pilot OS/webview behaviour defeats this approach, at the cost of a different runtime footprint; a Python-native widget toolkit reduces language count but needs its own rich report/graph and accessibility assessment. No competing shell is added to the initial build.

D16's Linux x86-64 host remains the initial combined qualification candidate. Native GUI delivery does not imply Windows/macOS/ARM64 support. O24 asks PO/PL to choose the first pilot desktop OS at M0; choosing another OS revises installer, webview, assistant, filesystem and VM profile/estimate before commitment. A desktop can later connect to a qualified remote runner, so UI host and training/output host need not match.

## Visual direction: an open research workspace

Use a quiet editorial canvas with generous whitespace, clear typography, thin rules and context-linked detail. Replace the dashboard grid with a flowing activity trail, curved dataset relationship links and evidence that opens beside the item it explains. Reserve bordered surfaces for genuine controls, tables, code or focused decisions. Standard desktop window chrome, menus and readable rectangular tables remain useful; the goal is reduced visual enclosure, not removing familiar affordances.

| Element | Recommended treatment | Functional constraint |
|---|---|---|
| Work trail | Slim vertical line with circular stage markers; selected stage expands its short summary | Text/icon state plus colour; all nine canonical stage IDs remain reachable; optional grouping cannot hide gates |
| Source map | Named source markers connected by restrained curves; nearby grain/key labels | List/table equivalent, keyboard navigation and deterministic layout; only scoped/paged visible subset, no giant forced graph |
| Main canvas | Report-like flow of question, result, table/chart and source notes | Show actual committed artifacts; no fabricated measurements or hidden reasoning transcript |
| Evidence margin | Contextual fold-out alongside a claim, join or code change | Factual why/evidence/limits, review owner and version; no hover-only information |
| Conversation | Persistent capsule composer anchored at the bottom; readable commands and attachments | Pause/Cancel remain outside the composer; native menu/keyboard commands reach the control broker independently of a busy renderer |
| Outputs | Simple shelf/list of named files, versions and status with “Open output folder” | Missing/partial/stale/exported states separate; no endpoint required for a report |
| Resource status | Small fixed location for local harness, selected compute, unsettled spend and privacy | Never hidden behind decorative animation; unknown capacity is explicit |

Avoid ornamental motion, blob-shaped data tables, tiny text, opaque glass, colour-only status and a canvas that requires dragging to discover essential controls. Support keyboard focus order, screen readers, contrast/zoom, reduced motion and dense list mode. High data density should expand via search/filter/virtualised tables, not increasingly tiny circles. Destructive cancel and reversible pause need distinct labels; no ambiguous icon-only controls.

Alternatives considered: a spatial laboratory could make relationships vivid but risks navigation and accessibility; an editorial notebook is legible but hides cross-source structure. Recommend the editorial workspace with an optional relationship canvas and evidence margin. Test whether users find the current job, join assumptions, code, output folder and stop control without coaching. PO/UX owns usability criteria; style preference alone is not success evidence.

A generated **preview-only visual concept** accompanies this conversation. It is not an implemented screen, measured dataset or authoritative relationship diagram. The written contracts and nine stage IDs govern the design. The image was produced with the built-in image-generation tool; no app/UI prototype was built. Its design prompt: “Create a calm desktop research workspace with an open warm-white canvas, flowing stage trail, curved source relationship map, contextual evidence margin, persistent conversation and Pause/Cancel controls, plus an output shelf and Open output folder; avoid a grid of cards and label it as an illustrative design concept.”

## Harness startup, lifecycle and security

The desktop shell starts one authenticated harness instance per user/profile, or reconnects using a local instance lock and authenticated handshake. Bind any local HTTP endpoint to loopback only, with short-lived app credentials, strict origin/CSRF checks and no permissive CORS; prefer an OS-protected local channel for shell control where available. HTTP/MCP clients use separately scoped credentials, not a UI token copied into logs. Filesystem selection returns opaque scoped handles, not unrestricted shell permissions.

The renderer cannot spawn arbitrary processes, evaluate returned code, browse all files or load remote content into its privileged context. A narrow broker may launch only pinned harness/model binaries with fixed schemas. Untrusted reports/docs/code render in a separate inert/sanitised viewer with no privileged IPC, network or script execution; do not embed an untrusted iframe inside the privileged main window [S64]. Ordinary OS user compromise remains outside this isolation promise. Generated code remains in the runner VM, not the desktop sidecar's full user context.

| Event | Proposed behaviour |
|---|---|
| Window closes | Detach observation; if jobs are active, present the persisted choice “continue locally” or “pause then quit”; default is pause then quit (D24). Closing never silently means cancellation. |
| Explicit Quit | Request pause/drain, persist state and stop owned idle processes after receipt; unresolved remote work/cost remains visibly pending. An OS force-kill may bypass this path. |
| Shell crash/reopen | Reconnect to existing harness and replay ledger; do not duplicate workers or restart jobs from UI assumptions. |
| Harness crash or computer sleep | Leases/heartbeats expire; reconcile actual worker/provider state on wake/restart before new dispatch; no background guarantee while machine sleeps. |
| Update | Stage verified signed update; defer active job/environment replacement or require controlled checkpoint/drain. No silent dependency/model upgrade. |

Customer operates and pays for the local shell/harness/storage and selected compute. Platform operates optional hosted coordination; managed runtime ownership/cost remain separately contracted. A customer service continues without the desktop, assistant, development harness or hosted control plane, subject to its own declared dependencies.

## Filesystem as a first-class delivery destination

At intake propose a project folder and output type. A trusted folder picker/CLI path grant creates a local OutputBinding; an LLM cannot grant itself arbitrary writes by naming a path in prose. Use native menu/keyboard Pause and Cancel through a small control broker so a stalled renderer cannot monopolise the only control surface. The portable release contains relative artifact paths and hashes; machine paths, keys and credentials stay in the binding. Export a private analysis bundle by default; service workloads can also export an installable bundle without starting an endpoint. `requested_delivery=filesystem_bundle` is valid for both output kinds. Starting an HTTP/MCP service is a separate authorised action after its gates.

| Relative path / role | Analysis output | Service output |
|---|---|---|
| `manifest.json`, `evidence/`, `rights/`, `environment/` | Immutable manifest, checks/provenance, notices/locks | ReleaseManifest, evaluation, rights, lock/SBOM/signatures |
| `data/`, `assets/` | Permitted gold tables or explicit authorised references; linked sources where rights permit | Only necessary permitted runtime inputs or bindings; no automatic customer training-data copy |
| `notebooks/`, `code/`, `reports/` | Reproduction notebook, Python/SQL and self-contained HTML/JSON findings | Training notebook, preparation/inference pipeline and justified selection report |
| `predict.py`, interface schemas, installation guide | Not required unless task requests callable behaviour | Full inference entry point, HTTP/MCP contract and declared environment instructions |

These are illustrative layout roles, not files implemented by this session. Existing support example paths remain its concrete contract. D23 sets write-to-new-version as default: stage under the approved destination on the same filesystem, enforce byte/free-space limits, verify allowed relative paths/content hashes, then atomic rename where supported. Record an ExportReceipt with output/binding revision, files/digests, result and timestamp; do not update the current pointer before commit. Other filesystems need a tested publish-marker protocol or an explicit unsupported status. Cancellation or disk-full leaves a labelled incomplete staging area; never overwrite prior good output or claim successful export. Resolve symlinks/path traversal and destination races at write time, not only at the file picker.

External edits are allowed in a working copy. Hash comparison marks divergence; importing edits creates new code/output revisions and applicable evaluation. A saved folder is useful without the app; later monitoring is opt-in and does not silently watch every directory or transmit file contents. Deleting a project cannot promise deletion of copies already exported beyond platform control; owners receive a scoped deletion/rights notice.

## First implementation slice and evidence

Start a native window and local harness with no model. Choose authorised source/output folders, show unknown/observed hardware, ingest multiple synthetic sources, explain a proposed relationship, pause a bounded task, resume explicitly and export a checked analysis bundle. Reopen the app and inspect its exact versions. Add the actual fitted baseline and independent full-service installation to finish M1. A44/A45 test startup/close/crash, permissions, accessibility and transactional filesystem output; no GUI or export runtime test has occurred here.
