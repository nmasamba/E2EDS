"""Admission rules for one ExecutionRequest (../compute_backends.md, admission section).

Pure: the caller's authority is settled before this is reached, and the application reserves what
``reservation`` asks for atomically. The rule table is the planner's own (``judge`` and ``needs``),
applied to the latest observation less what other live jobs already hold.
"""

from typing import Any

from dsp.contracts.errors import ErrorCode
from dsp.domain.feasibility import judge, needs

UNITS = {"processors": "cpu_cores", "GiB memory": "memory_gib", "GiB scratch": "scratch_gib"}
DATA_ACCESS = {
    "prepare": "permitted_snapshot",
    "analyse": "permitted_snapshot",
    "evaluate": "sealed_evaluator_only",
    "infer": "inference_only",
}


def reservation(workload: dict[str, Any], binding: dict[str, Any]) -> dict[str, Any]:
    """What the request takes from the domain: the larger of its ask and the option's floor."""
    asked, floor = workload["requested_resources"], binding["resource_requirements"]
    return {
        "cpu_cores": max(asked["cpu_cores"], floor["cpu_cores_min"]),
        "memory_gib": max(asked["memory_gib"], floor["memory_gib_min"]),
        "scratch_gib": max(asked["scratch_gib"], floor["scratch_gib_min"]),
        "external_charge_minor": asked["max_external_charge_minor"],
        "currency": asked["currency"],
    }


def refusal(
    operation: str,
    workload: dict[str, Any],
    binding: dict[str, Any],
    snapshot: dict[str, Any] | None,
    held: dict[str, float],
) -> tuple[ErrorCode, str] | None:
    """Return why the request is refused, or None when it may be admitted.

    In order: the operation must be declared by the workload and offered by the binding; an
    accelerator needs a binding that has one; any external charge needs a spend grant, and none
    exists, so the charge is zero or the request is refused; then the planner's rule table against
    the latest observation (none observed is "unknown", so nothing is admitted blind), and finally
    the capacity left after what live jobs hold.
    """
    asked = workload["requested_resources"]
    if operation not in workload["execution_requirements"]["required_operations"]:
        return ErrorCode.INPUT_INVALID, f"operation {operation} is not declared by the workload"
    if operation not in binding["capabilities"]["declared_operations"]:
        return ErrorCode.INPUT_INVALID, f"the compute option does not offer {operation}"
    if asked["gpu_count"] and not binding["capabilities"]["gpu_capable"]:
        return ErrorCode.QUOTA_EXCEEDED, "an accelerator is requested and the option has none"
    if asked["max_external_charge_minor"]:
        return (
            ErrorCode.FORBIDDEN,
            "an external charge needs a spend grant from the owner; none exists",
        )
    disposition, reason = judge(workload, binding, snapshot)
    if disposition == "blocked":
        return ErrorCode.QUOTA_EXCEEDED, reason
    if disposition == "unknown" or snapshot is None:
        return ErrorCode.DEPENDENCY_UNAVAILABLE, reason
    for unit, needed, usable in needs(workload, binding, snapshot):
        free = usable - held.get(UNITS[unit], 0)
        if free < needed:
            return (
                ErrorCode.QUOTA_EXCEEDED,
                f"needs {needed:g} {unit}; {free:g} free after what live jobs hold",
            )
    return None
