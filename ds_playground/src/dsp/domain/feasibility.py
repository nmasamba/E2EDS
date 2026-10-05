"""A deterministic rule table from workload, hardware snapshots and compute options to a plan.

It follows ../hardware_discovery_and_planning.md "Deterministic feasibility": every option gets
one disposition and one reason. Nothing here estimates speed, cost or quality, and no plan
authorises execution: admission rechecks and reserves at dispatch.
"""

from typing import Any

from dsp.contracts.canonical import canonical_json, digest
from dsp.contracts.errors import DspError, ErrorCode

RULESET = "feasibility-rules-1.0.0"
RESERVE = {"cpu": 1, "memory_gib": 2}  # kept free for the host when the workload shares it
RANK = {"eligible": 0, "unqualified": 1, "unknown": 2, "blocked": 3}
STAGES = {
    "goal": "Intended use and material constraints resolved by their owners",
    "environment": "Scoped discovery and a viable proposed placement; refreshed before admission",
    "data": "Rights and partition controls established",
    "plan": "Current immutable plan and the required authority recorded",
    "develop": "Committed analysis artifacts or candidate, with lineage",
    "self_check": "Development checks completed with their actual outcomes",
    "evaluate": "Independent report with an explicit outcome",
    "report_release": "Requested bundle with its packaging and installation evidence",
    "operate": "Declared operator and handoff within the approved scope",
}


def ref(obj: dict[str, Any]) -> dict[str, Any]:
    """Return the typed reference to an object; planning records carry no digest."""
    sha256 = None if obj.get("planning_only", True) else digest(canonical_json(obj))
    return {"id": obj["id"], "revision": obj["revision"], "sha256": sha256}


def _snapshot_for(binding: dict[str, Any], snapshots: list[dict[str, Any]]) -> Any:
    for snapshot in snapshots:
        bound = snapshot["compute_binding_ref"]
        if bound["id"] == binding["id"] if bound else binding["provider"] == "local":
            return snapshot
    return None


def _needs(workload: dict[str, Any], binding: dict[str, Any], snapshot: dict[str, Any]) -> Any:
    """What the option must have, and what the snapshot says is usable, per resource."""
    asked, floor = workload["requested_resources"], binding["resource_requirements"]
    shared = snapshot["scope"] == "assistant_host"
    scratch = [
        volume["available_gib"]
        if volume["effective_quota_gib"] is None or volume["available_gib"] is None
        else min(volume["available_gib"], volume["effective_quota_gib"])
        for volume in snapshot["storage"]
        if volume["role"] in ("scratch", "combined")
    ]
    return (
        (
            "processors",
            max(asked["cpu_cores"], floor["cpu_cores_min"]) + RESERVE["cpu"] * shared,
            snapshot["cpu"]["effective_cpu_quota"],
        ),
        (
            "GiB memory",
            max(asked["memory_gib"], floor["memory_gib_min"]) + RESERVE["memory_gib"] * shared,
            snapshot["memory"]["effective_limit_gib"],
        ),
        (
            "GiB scratch",
            max(asked["scratch_gib"], floor["scratch_gib_min"]),
            max(scratch) if scratch and None not in scratch else None,
        ),
    )


def judge(workload: dict[str, Any], binding: dict[str, Any], snapshot: Any) -> tuple[str, str]:
    """Return one option's disposition and reason; the first rule that applies decides."""
    asked, offers = workload["requested_resources"], binding["capabilities"]
    floor, proof = binding["resource_requirements"], binding["qualification"]
    if workload["family"] not in offers["declared_families"]:
        return "blocked", "does not support this workload family"
    if offers["external_billing_possible"] and asked["max_external_charge_minor"] == 0:
        return "blocked", "needs paid compute and the external charge cap is zero"
    if proof["status"] == "unsupported":
        return "blocked", "this compute profile is recorded as unsupported"
    if snapshot is None or snapshot["evidence_source"] in ("unknown", "illustrative_fixture"):
        return "unknown", "its hardware has not been observed"
    for unit, needed, usable in _needs(workload, binding, snapshot):
        if usable is None:
            return "unknown", f"usable {unit} were not observed"
        if usable < needed:
            return "blocked", f"needs {needed:g} {unit}; {usable:g} usable within its limits"
    wanted = max(asked["gpu_count"], floor["gpu_count_min"])
    if wanted:
        seen = snapshot["accelerators"]
        if seen["inventory_status"] not in ("observed_present", "observed_absent"):
            return "unknown", "the accelerator inventory was not observed"
        each = floor["gpu_vram_gib_min_each"]
        fitting = [
            device
            for device in seen["devices"]
            if not each or (device["memory_gib"] is not None and device["memory_gib"] >= each)
        ]
        if len(fitting) < wanted:
            return (
                "blocked",
                f"needs {wanted} accelerators with {each:g} GiB each; {len(fitting)} fit",
            )
        if any(device["runtime_check"] != "pass" for device in fitting):
            return "unqualified", "an accelerator is visible but has not passed a runtime check"
    if snapshot["evidence_source"] != "observed":
        return "unqualified", "its inventory is declared by the user, not observed"
    if proof["status"] != "tested" or not proof["report_ref"]:
        return "unqualified", "this compute profile has not been qualified"
    if snapshot["isolation_readiness"] != "qualified" or not snapshot["isolation_evidence_ref"]:
        return "unqualified", "its isolation has not been qualified"
    return "eligible", "fits the observed capacity and is qualified"


def propose(
    workload: dict[str, Any],
    snapshots: list[dict[str, Any]],
    bindings: list[dict[str, Any]],
    *,
    plan_id: str,
    supersedes: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return the WorkflowPlan the rule table derives from these inputs; same inputs, same plan.

    The selected option is the best-ranked one (eligible, then unqualified, then unknown, then
    blocked), preferring options that cannot incur an external charge, then the given order.
    The outcome is PASS only for an eligible option on a real workload with qualification
    evidence, FAIL when every option is blocked, and INSUFFICIENT_EVIDENCE otherwise.
    """
    asked = workload["requested_resources"]
    if not snapshots or not bindings or asked["currency"] != "GBP":
        raise DspError(
            ErrorCode.INPUT_INVALID, "a plan needs a snapshot, a compute option and a GBP budget"
        )
    judged = [
        (binding, snapshot, *judge(workload, binding, snapshot))
        for binding in bindings
        for snapshot in [_snapshot_for(binding, snapshots)]
    ]
    billed = "external_billing_possible"
    chosen, where, disposition, reason = min(
        judged, key=lambda option: (RANK[option[2]], option[0]["capabilities"][billed])
    )
    passed = disposition == "eligible" and not workload["planning_only"]
    outcome = "PASS" if passed else "FAIL" if disposition == "blocked" else "INSUFFICIENT_EVIDENCE"
    conditions = ["Recheck capacity and reserve it at dispatch; this plan authorises nothing."]
    if disposition != "eligible":
        conditions.append(f"{chosen['profile_id']}: {reason}.")
    if workload["planning_only"]:
        conditions.append("The workload is a planning record; its evidence is not established.")
    floor = chosen["resource_requirements"]
    domain = where["resource_domain_id"] if where else "unobserved"
    allocations = [
        {
            "role": "workload",
            "physical_domain_id": domain,
            "cpu_cap": max(asked["cpu_cores"], floor["cpu_cores_min"]),
            "memory_cap_gib": max(asked["memory_gib"], floor["memory_gib_min"]),
            "gpu_count": max(asked["gpu_count"], floor["gpu_count_min"]),
            "profile_id": chosen["profile_id"],
        }
    ]
    if where and where["scope"] == "assistant_host":
        allocations.append(
            {
                "role": "host_reserve",
                "physical_domain_id": domain,
                "cpu_cap": RESERVE["cpu"],
                "memory_cap_gib": RESERVE["memory_gib"],
                "gpu_count": 0,
                "profile_id": RULESET,
            }
        )
    return {
        "id": plan_id,
        "revision": "1.0.0",
        "type": "WorkflowPlan",
        "schema_version": "0.5.0",
        "planning_only": outcome == "INSUFFICIENT_EVIDENCE",
        "tenant_ref": workload["tenant_ref"],
        "project_ref": workload["project_ref"],
        "state": "proposed",
        "workload_ref": ref(workload),
        "assistant_model_binding_ref": workload["assistant_model_binding_ref"],
        "selected_compute_binding_ref": ref(chosen),
        "hardware_snapshot_refs": [ref(snapshot) for snapshot in snapshots],
        "ruleset_revision": RULESET,
        "requirement_revision": workload["revision"],
        "feasibility_outcome": outcome,
        "qualification_evidence_refs": (
            [chosen["qualification"]["report_ref"], where["isolation_evidence_ref"]]
            if passed
            else []
        ),
        "authorises_execution": False,
        "selected_option_id": chosen["profile_id"],
        "recommendation": f"{chosen['profile_id']} is {disposition}: {reason}.",
        "allocations": allocations,
        "operating_bounds": {
            "trial_concurrency": asked["max_concurrent_trials"],
            "max_trials": asked["max_trials"],
            "max_task_seconds": min(
                asked["wall_time_seconds"], chosen["limits"]["max_execution_seconds"]
            ),
            "currency": "GBP",
            "max_external_charge_minor": asked["max_external_charge_minor"],
        },
        "runtime_estimate_seconds": None,
        "alternatives": [
            {"option_id": binding["profile_id"], "disposition": verdict, "reason": why}
            for binding, _, verdict, why in judged
            if binding is not chosen
        ],
        "required_conditions": conditions,
        "protected_evaluation_ref": workload["evaluation_contract_ref"],
        "refresh_policy": {
            "on_dispatch": True,
            "on_resume": True,
            "display_stale_after_seconds": 60,
        },
        "stages": [
            {"id": stage, "completion_evidence": text, "mandatory": True}
            for stage, text in STAGES.items()
        ],
        "supersedes_ref": supersedes,
        "workload_family": workload["family"],
        "output_kind": workload["output_kind"],
    }
