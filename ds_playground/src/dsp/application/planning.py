from collections.abc import Callable
from typing import Any

from dsp.application.workloads import current_workload
from dsp.contracts.errors import TrustedContext
from dsp.contracts.schemas import validate
from dsp.domain.feasibility import propose, ref
from dsp.ports import Ledger

LOCAL_DRAFT = {
    "planning_only": True,
    "id": "compute-local-draft",
    "revision": "0.1.0",
    "provider": "local",
    "profile_id": "local-native-draft",
    "capabilities": {
        "declared_families": ["data_analysis"],
        "declared_operations": ["analyse"],
        "gpu_capable": False,
        "external_billing_possible": False,
    },
    "resource_requirements": {
        "cpu_cores_min": 1,
        "memory_gib_min": 1,
        "gpu_count_min": 0,
        "gpu_vram_gib_min_each": 0,
        "scratch_gib_min": 1,
    },
    "limits": {"max_execution_seconds": 600},
    "qualification": {"status": "planned", "report_ref": None},
}


def propose_plan(
    ctx: TrustedContext, *, ledger: Ledger, new_id: Callable[[], str]
) -> dict[str, Any]:
    """Propose a provisional plan for the current workload from the latest snapshot and record it.

    The plan supersedes the previous one. It never authorises execution.
    """
    previous = ledger.current(ctx, "WorkflowPlan")[-1:]
    plan = propose(
        current_workload(ctx, ledger),
        ledger.current(ctx, "HardwareSnapshot")[-1:],
        [LOCAL_DRAFT],
        plan_id=f"plan-{new_id()}",
        supersedes=ref(previous[0]) if previous else None,
    )
    validate("WorkflowPlan", plan)
    proposed = {
        "plan": {"id": plan["id"], "revision": plan["revision"]},
        "outcome": plan["feasibility_outcome"],
        "selected_option_id": plan["selected_option_id"],
    }
    event = f"{plan['id']}:proposed"
    ledger.commit(ctx, f"plan:{plan['id']}", 0, event, "plan.proposed", proposed, [plan])
    return plan
