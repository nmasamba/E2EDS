---
name: assistant-gateway
description: Rules for the provider-neutral model gateway, AssistantModelBinding, the llama.cpp supervisor, the typed tool loop, intent extraction and assistant qualification, with open models first and proprietary models as an opt-in. Use when touching anything under the assistant, model gateway or tool dispatcher.
---

# Assistant gateway

**Read first:** `../local_model_runtime.md`; `../conversational_control.md` "From language to enforceable
intent"; D17; `docs/decisions.md` (assistant models deviation).

## Bindings

Exactly one module opens a connection to a model. A model is selected only by an explicit, versioned
`AssistantModelBinding`; there is **no fallback** between bindings. On load failure, OOM, hang or deadline:
`assistant_unavailable`, conversation and work preserved, controls still live.

| Order | Binding | Notes |
|---|---|---|
| 1 | Local open model: llama.cpp `b11104`, `Qwen3-8B-Q4_K_M.gguf` (rev `7c41481f…`, SHA-256 `d98cdcbd…5785`) | Default and first test target. Loopback `127.0.0.1:8081`, API key from the secret port, thinking off, built-in server tools/agents/web UI off, no auto-download, no prompt logging. Verify the file hash before load. |
| 2 | Open model on an OpenAI-compatible endpoint (HF router, Ollama, vLLM) | Opt-in. |
| 3 | Proprietary provider (Anthropic, OpenAI) | Opt-in. For Anthropic use the `claude-api` skill for current model IDs and parameters. |

Bindings 2 and 3 need the new binding schema version, a per-project data policy (what may leave the machine;
never sealed data, never secrets), the key in the OS secret store, and an owner-approved spend limit. Show
the placement and data transfer before first use.

## Limits (D17, per binding)

8,192 total tokens (≤ 6,144 in, ≤ 2,048 out), one generation at a time, 300 s per call, ≤ 20 calls and ≤ 2
code repairs and ≤ 1,800 s generation per task. First limit reached stops generation. Rebuild context from
canonical state and bounded evidence; never truncate away user constraints. Do not put every schema or manual
in the context: page the catalogue, use profile summaries.

## Tool loop

The application owns the loop; the model proposes the next typed call. Tools: inspect approved schema/sample,
propose a typed requirement patch, create/edit a code artifact, submit a validated code task, inspect redacted
results, request a permitted trial, assemble an evidence report, propose a release. Validate every call
against its JSON Schema, then check principal, revision, scope, budget and fence before dispatch. There is no
shell tool, no grant tool, no sealed-data tool.

## Intent extraction

Text → typed WorkloadSpec fields, each with source message and span, confidence (nullable, extraction only),
materiality and confirmation status. Ask only about ambiguities that change imminent material work. Reference
cases: "use account_num as the ID" (string entity ID, excluded predictor, leading zeros kept, group split when
generalising to unseen accounts); "keep features minimal" (soft objective; ask counting unit and hard cap);
"round to the nearest 10" (precision transform, ties away from zero, not anonymity).

## Tests and qualification

- `live_model` tests run against binding 1 first. A hosted or proprietary binding is tested only after that
  passes; record results per binding and never merge them.
- Typed tool-response probe at readiness; a responding endpoint is not qualification.
- Qualification suite (`../local_model_runtime.md` "Qualification"): 60 interpretation/change cases, 20
  adversarial/control cases, 10 pipeline tasks × 3 repeats; zero unauthorised dispatches or lost commands;
  target ≥ 27/30 tasks. Report counts, intervals and every failure. Measure latency, peak memory, repairs.

## Avoid

An agent framework; model prose as canonical JSON or as a number in a report; a "thinking" panel; raising
limits or weakening permissions because the model struggles — change the binding and requalify instead.
