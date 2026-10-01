---
name: contract-change
description: Recipe for adding or changing a JSON Schema, canonical object, error code or API shape in DS Playground, including new schema versions for owner deviations. Use for any work under src/dsp/contracts.
---

# Contract change

**Read first:** `../contracts.md` (identity, evolution, "Semantic checks beyond JSON Schema"), the affected
`../contracts/*.schema.json` and its `../examples/` file.

## Facts

- Dialect: JSON Schema draft 2020-12; every object has `additionalProperties: false`; enable format assertion.
- Common shapes: ID `^[A-Za-z0-9][A-Za-z0-9._:-]*$` (max 160), revision `^\d+\.\d+\.\d+$`, digest
  `^sha256:[a-f0-9]{64}$`, typed ref `{id, revision, sha256|null}`.
- `planning_only: true` records carry null evidence; `false` records need real digests. All suite examples
  are planning records.
- `readOnly` is guidance only. The API must ignore caller-supplied trusted fields (tenant, authorisation,
  state) and derive them from trusted context.
- Canonical bytes: UTF-8 JSON, sorted keys, no insignificant whitespace; SHA-256 over those bytes. Detached
  signatures cover the digest. No timestamps or random IDs inside hashed content unless the schema has them.

## Recipe

1. **Never edit `../contracts/`.** Suite schemas are vendored into `src/dsp/contracts/schemas/suite/` (package data) and checked against
   `../SUITE_MANIFEST.json` digests.
2. A change is a **new schema file with a new `schema_version`** in `src/dsp/contracts/schemas/app/`; the old version stays
   readable. Objects the suite describes without a schema (CodeTask, RunManifest, EvaluationContract,
   EvaluationReport, DataManifest, SplitManifest, ExportReceipt) get app-owned schemas the same way.
3. Validate plain dicts against the schema. Add a typed model only where code needs one; the schema stays
   the source of truth.
4. Tests: what the code writes validates against the schema; schema-valid examples are accepted; at least one
   invalid and one boundary fixture per new rule; prior-version fixture still reads.
5. Rules the schema cannot express become **semantic validators** with tests: reference resolution in the
   same tenant, unique stage IDs, acyclic join graph, non-null refs when not planning, allowlist and
   exclusions disjoint, family ↔ task ↔ output consistency.
6. Log the change in `docs/decisions.md` (DEVIATION if it departs from the suite) and `CHANGELOG.md`.

## Done when

Schema meta-validates; every example and consumer conforms; `unknown` or `null` never satisfies a gate;
no interface accepts a trusted field from the caller.

## Avoid

Making generated pydantic output canonical; reusing an ID with a new meaning; catch-all fields; mutating a
stored revision; shape validation presented as authority.
