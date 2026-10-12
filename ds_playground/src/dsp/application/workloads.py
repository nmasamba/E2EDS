"""The workload the product can run this sprint, and how its requirements change.

A change instruction becomes a typed patch on the WorkloadSpec with an impact preview; applying
it writes a new immutable revision under compare-and-swap on the expected revision, and marks the
evidence that depended on the changed part stale through a small dependency graph. Budget and
evaluation changes need the owner's own action and are refused here.
"""

import re
from collections.abc import Callable
from typing import Any

from dsp.application.grants import PROJECT
from dsp.contracts.errors import DspError, ErrorCode, TrustedContext
from dsp.contracts.schemas import validate
from dsp.ports import Ledger

WORKLOAD_ID = "workload-test-job"
FEATURES = "/intent_constraints/features"
GRAMMAR = {
    "exclude": re.compile(r"^exclude (?:the )?field (?P<field>[A-Za-z_][A-Za-z0-9_]*)$", re.I),
    "budget": re.compile(r"^set (?:the )?budget to (?P<minor>\d+)$", re.I),
    "evaluation": re.compile(r"^(?:change|set|replace) (?:the )?evaluation\b", re.I),
}
OWNER_ACTION = {
    "budget": "/requested_resources/max_external_charge_minor",
    "evaluation": "/evaluation_contract_ref",
}
DEPENDENCIES = {
    FEATURES: ("result", "checkpoint"),
    "/requested_resources": ("reservation",),
    "/evaluation_contract_ref": ("evaluation",),
}


def base_workload(ctx: TrustedContext) -> dict[str, Any]:
    """Return revision 1.0.0: the smallest schema-valid WorkloadSpec the hung test job can carry.

    It is a planning record: no data is bound and no evaluation contract exists, so its references
    carry no digests and a plan made from it stays INSUFFICIENT_EVIDENCE. The field roles are the
    orders fixture's, so a requirement change has a field to exclude.
    """
    unbound = {"revision": "0.1.0", "sha256": None}
    return {
        "schema_version": "0.6.0",
        "planning_only": True,
        "id": WORKLOAD_ID,
        "revision": "1.0.0",
        "tenant_ref": ctx.tenant,
        "project_ref": PROJECT,
        "family": "data_analysis",
        "purpose": {
            "task": "test_worker",
            "intended_use": "Exercise jobs, controls and revisions with the test worker; no data.",
            "prohibited_uses": ["any use beyond testing this workspace"],
            "outcome_owner": ctx.principal,
        },
        "adaptation": {
            "target": "analysis_code",
            "method": "test_worker",
            "base_model_ref": None,
            "trainable_parameters": [],
            "environment_ref": None,
        },
        "data_manifest_ref": {"id": "data-not-bound"} | unbound,
        "split_manifest_ref": None,
        "evaluation_contract_ref": {"id": "evaluation-not-defined"} | unbound,
        "search_space": [],
        "requested_resources": {
            "cpu_cores": 1,
            "memory_gib": 1,
            "gpu_count": 0,
            "scratch_gib": 1,
            "max_trials": 0,
            "max_concurrent_trials": 0,
            "wall_time_seconds": 600,
            "max_external_charge_minor": 0,
            "currency": "GBP",
        },
        "requested_permissions": [],
        "target_profiles": ["local-native-draft"],
        "assumptions": [],
        "authorisation_context_ref": None,
        "required_outputs": ["worker_result"],
        "execution_requirements": {
            "allowed_execution_modes": ["process"],
            "allowed_connection_modes": ["attach"],
            "required_operations": ["analyse"],
            "data_access": "permitted_snapshot",
            "data_processing_policy_ref": {"id": "data-policy-not-defined"} | unbound,
            "checkpoint_policy": "stage_boundary_or_restart",
            "provider_fallback": "requires_new_admission",
            "minimum_isolation": "customer_controlled",
            "no_external_charge_only": True,
        },
        "intent_constraints": {
            "field_roles": [
                {
                    "field": "order_id",
                    "role": "row_id",
                    "data_type": "string",
                    "nullable": False,
                    "public_output": "authorised_join_only",
                },
                {
                    "field": "region",
                    "role": "predictor",
                    "data_type": "string",
                    "nullable": False,
                    "public_output": "excluded",
                },
                {
                    "field": "item_count",
                    "role": "predictor",
                    "data_type": "integer",
                    "nullable": False,
                    "public_output": "excluded",
                },
            ],
            "split_group_fields": [],
            "features": {
                "allowed_fields": ["region", "item_count"],
                "excluded_fields": ["order_id"],
                "count_basis": "source_fields",
                "hard_max_count": None,
                "soft_objective": "none",
                "quality_policy": "frozen_evaluation_contract",
            },
            "output_transforms": [],
            "privacy_status": "not_requested",
        },
        "field_provenance": [
            {
                "field": "/intent_constraints",
                "source_kind": "planning_example",
                "message_id": None,
                "source_span": None,
                "extraction_confidence": None,
                "materiality": "low",
                "confirmation_status": "proposed",
                "confirmed_by": None,
            }
        ],
        "assistant_model_binding_ref": None,
        "conversation_ref": None,
        "interaction_mode": "headless",
        "task_kind": "exploratory_analysis",
        "output_kind": "analysis_release",
        "input_modalities": ["tabular"],
        "data_product_refs": [],
        "dataset_collection_ref": None,
        "join_plan_ref": None,
        "task_capability_ref": None,
        "requested_delivery": "filesystem_bundle",
    }


def current_workload(ctx: TrustedContext, ledger: Ledger) -> dict[str, Any]:
    """Return the latest workload revision: the newest stored one, else built-in revision 1.0.0."""
    stored = ledger.latest(ctx, "WorkloadSpec", WORKLOAD_ID)
    return stored if stored else base_workload(ctx)


def parse_change(text: str) -> tuple[str, str] | None:
    """Return (kind, argument) when the text is a change instruction the grammar knows.

    Keywords are matched whatever their case; a field name keeps the case it was typed with.
    """
    phrase = text.strip().rstrip(".!")
    for kind, pattern in GRAMMAR.items():
        if found := pattern.match(phrase):
            return kind, found.groupdict().get("field") or found.groupdict().get("minor") or ""
    return None


def patch_for(text: str, workload: dict[str, Any]) -> list[dict[str, Any]]:
    """The typed patch a change instruction means on this workload, or why there is none.

    Excluding a field moves a currently allowed predictor to the excluded list. A budget or an
    evaluation change is typed on the owner's path so the record shows what was asked.
    """
    parsed = parse_change(text)
    if parsed is None:
        raise DspError(ErrorCode.INPUT_INVALID, "not a change instruction the grammar knows")
    kind, argument = parsed
    if kind == "budget":
        return [{"op": "replace", "path": OWNER_ACTION[kind], "value": int(argument)}]
    if kind == "evaluation":
        return [{"op": "replace", "path": OWNER_ACTION[kind], "value": None}]
    features = workload["intent_constraints"]["features"]
    roles = {role["field"]: role["role"] for role in workload["intent_constraints"]["field_roles"]}
    if roles.get(argument) != "predictor" or argument not in features["allowed_fields"]:
        raise DspError(ErrorCode.INPUT_INVALID, f"{argument} is not an allowed predictor field")
    allowed = [field for field in features["allowed_fields"] if field != argument]
    excluded = [*features["excluded_fields"], argument]
    return [
        {"op": "replace", "path": f"{FEATURES}/allowed_fields", "value": allowed},
        {"op": "replace", "path": f"{FEATURES}/excluded_fields", "value": excluded},
    ]


def owner_action(patch: list[dict[str, Any]]) -> str | None:
    """The kind of change in the patch that needs the owner's own action, if any."""
    for kind, path in OWNER_ACTION.items():
        if any(operation["path"].startswith(path) for operation in patch):
            return kind
    return None


def _applied(workload: dict[str, Any], patch: list[dict[str, Any]]) -> dict[str, Any]:
    changed: dict[str, Any] = {**workload}
    for operation in patch:
        parts = operation["path"].strip("/").split("/")
        target = changed
        for part in parts[:-1]:
            target[part] = {**target[part]}
            target = target[part]
        target[parts[-1]] = operation["value"]
    return changed


def impact_of(
    ctx: TrustedContext, patch: list[dict[str, Any]], workload: dict[str, Any], ledger: Ledger
) -> dict[str, Any]:
    """What the change touches and which evidence it makes stale, through the dependency graph."""
    changed = sorted({operation["path"] for operation in patch})
    invalidates = sorted(
        {
            kind
            for path in changed
            for root, kinds in DEPENDENCIES.items()
            if path.startswith(root)
            for kind in kinds
        }
    )
    stale, held = [], []
    for job in ledger.current(ctx, "Job"):
        if job["workload_ref"]["revision"] != workload["revision"]:
            continue
        for kind in ("result", "checkpoint"):
            if kind in invalidates and job[kind]:
                stale.append({"job": job["id"], "kind": kind, "sha256": job[kind]["sha256"]})
        if job["state"] in ("queued", "running", "checkpointed"):
            held.append(job["id"])
    return {"changed": changed, "invalidates": invalidates, "stale": stale, "holds": held}


def revise(
    ctx: TrustedContext,
    patch: list[dict[str, Any]],
    expected_revision: str,
    message_id: str,
    text: str,
    *,
    ledger: Ledger,
    clock: Callable[[], str],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Apply a typed patch as a new immutable revision and return it with its impact.

    A patch on the owner's paths is refused with REQUIRES_CONFIRMATION. The expected revision
    must be the current one (REVISION_CONFLICT otherwise); two edits that both read the same
    revision are serialised by the workload aggregate, and the second conflicts. Old revisions
    and the results recorded against them are untouched.
    """
    if kind := owner_action(patch):
        raise DspError(
            ErrorCode.REQUIRES_CONFIRMATION,
            f"a {kind} change ({OWNER_ACTION[kind]}) needs the owner's own action, not a message",
        )
    current = current_workload(ctx, ledger)
    if expected_revision != current["revision"]:
        raise DspError(
            ErrorCode.REVISION_CONFLICT,
            f"the requirements are at {current['revision']}, not {expected_revision}",
        )
    impact = impact_of(ctx, patch, current, ledger)
    successor = _applied(current, patch) | {
        "revision": f"{int(current['revision'].split('.')[0]) + 1}.0.0",
        "field_provenance": [
            *current["field_provenance"],
            {
                "field": FEATURES,
                "source_kind": "direct_user_message",
                "message_id": message_id,
                "source_span": text,
                "extraction_confidence": None,
                "materiality": "high",
                "confirmation_status": "confirmed",
                "confirmed_by": ctx.principal,
            },
        ],
    }
    validate("WorkloadSpec", successor)
    aggregate = f"workload:{WORKLOAD_ID}"
    body = {
        "workload": WORKLOAD_ID,
        "from": current["revision"],
        "to": successor["revision"],
        "patch": patch,
        "impact": impact,
        "message_id": message_id,
        "at": clock(),
    }
    ledger.commit(
        ctx,
        aggregate,
        ledger.seq(ctx, aggregate),
        f"{WORKLOAD_ID}:{successor['revision']}",
        "workload.revised",
        body,
        [("WorkloadSpec", current), ("WorkloadSpec", successor)],
    )
    return successor, impact
