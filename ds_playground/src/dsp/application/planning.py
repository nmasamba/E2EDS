from collections.abc import Callable
from typing import Any

from dsp.application.grants import PROJECT
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
    "capabilities": {"declared_families": ["data_analysis"], "external_billing_possible": False},
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


def profile_draft(ctx: TrustedContext) -> dict[str, Any]:
    """Return the resource request of the one workload that exists today, the built-in CSV profile.

    It is a draft, not a WorkloadSpec: no goal has been stated, no data is bound and no
    evaluation contract exists, so the plan made from it can only be a planning record.
    """
    return {
        "planning_only": True,
        "id": "workload-draft-csv-profile",
        "revision": "0.1.0",
        "tenant_ref": ctx.tenant,
        "project_ref": PROJECT,
        "family": "data_analysis",
        "output_kind": "analysis_release",
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
        "assistant_model_binding_ref": None,
        "evaluation_contract_ref": {
            "id": "evaluation-not-defined",
            "revision": "0.1.0",
            "sha256": None,
        },
    }


def propose_plan(
    ctx: TrustedContext, *, ledger: Ledger, new_id: Callable[[], str]
) -> dict[str, Any]:
    """Propose a provisional plan from the latest hardware snapshot and record it.

    The plan supersedes the previous one. It never authorises execution.
    """
    previous = ledger.current(ctx, "WorkflowPlan")[-1:]
    plan = propose(
        profile_draft(ctx),
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
