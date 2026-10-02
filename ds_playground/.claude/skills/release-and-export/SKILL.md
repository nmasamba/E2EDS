---
name: release-and-export
description: Rules for analysis packs, service bundles, predict.py, HTTP and MCP over one core, signing, staged filesystem export and recipient installation. Use when touching the release builder, dsp_service, the HTTP/MCP adapters, OutputBinding or export code.
---

# Release and export

**Read first:** `../execution_and_serving.md` ("Release builder and portable inference", "HTTP and MCP over
one implementation"); `../desktop_experience.md` "Filesystem as a first-class delivery destination";
`../contracts.md` semantic checks 6, 8, 10; D04, D23; scenarios A09–A12, A30, A45.

## Two outputs

| | Analysis release (`AnalysisReleaseManifest`) | Service release (`ReleaseManifest`) |
|---|---|---|
| Contains | gold manifest, preparation/analysis code, environment lock, notebook, report JSON + HTML, SBOM, reproduction guide | pipeline, model, environment lock, `predict.py`, notebook, evaluation report JSON, selection report HTML, SBOM, `ServiceSpec`, install guide |
| Never contains | a fabricated ServiceSpec, model or score | the assistant, the harness, credentials, training data by default |

Layout roles: `manifest.json`, `evidence/`, `rights/`, `environment/`, `data/`, `assets/`, `notebooks/`,
`code/`, `reports/`, and for services `predict.py` plus interface schemas. Relative paths and hashes only;
**no machine paths, keys or credentials** in portable content. A failed or inconclusive result is still
exportable, clearly marked unapproved.

## Service core

- One application operation in `dsp_service`; `predict.py`, FastAPI and the MCP server are thin adapters over
  it with the same `RequestContext`, limits and error codes. `dsp_service` imports nothing from the harness
  or the assistant.
- Persist sklearn pipelines with skops and an allowed-type check. No pickle or joblib loading of untrusted
  artifacts. Verify signature and digests **before** loading executable content.
- HTTP: loopback by default with an owner-only credential; refuse non-loopback binding until remote auth is
  configured. Limits per D04. Status mapping: 413 oversized, 422 invalid, 401, 403, 404, 409 idempotency or
  budget, 429, 503, 504. OpenAPI 3.1.0.
- MCP: official Python SDK 2.2.0, stdio and Streamable HTTP, typed structured results, explicit durable job
  tools. Do not advertise Tasks, sampling or elicitation.
- Shared error codes are in `../contracts.md` "Trusted context and structured errors". A structured failure
  is not success because the transport returned 200.

## Signing

Deterministic manifest → SHA-256 over canonical bytes → detached Ed25519 signature; the key lives in the OS
secret store, never in the build job or the bundle. A signature proves integrity and origin, not quality.

## Filesystem export (D23)

A trusted folder picker or CLI path grant creates an `OutputBinding` with an opaque handle; prose never grants
a path. Protocol: stage under the approved root on the same filesystem → enforce byte and free-space limits →
verify relative paths and content hashes → atomic rename to a **new version directory** → write an
`ExportReceipt`. Resolve symlinks and traversal at write time. Cancel or disk-full leaves a labelled
incomplete staging area and the prior good output untouched. Export never starts an endpoint.

## Tests that must exist

Same input, principal and release through `predict.py`, HTTP and MCP → same result, denial and error (A09);
service answers with harness and assistant stopped (A10, A30); previous release reinstalled within the
rollback target (A11); flipped byte, swapped dependency, missing evidence, wrong signer → load refused (A12);
denied root, traversal, symlink race, disk full, interrupted transfer, cancel before and after commit,
repeated receipt lookup (A45); a clean environment installs from the bundle alone.

## Avoid

A second implementation of preprocessing for serving; `latest` pointers as evidence; training provider
recorded as a serving guarantee; marking a profile "tested" without a test report on that profile.
