from collections.abc import Callable
from typing import Any

from dsp.application.grants import PROJECT
from dsp.application.workloads import current_workload
from dsp.contracts.errors import TrustedContext
from dsp.contracts.schemas import validate
from dsp.domain.feasibility import propose, ref
from dsp.ports import Ledger


def local_binding(ctx: TrustedContext, os: str, isa: str) -> dict[str, Any]:
    """Return the local compute option: this host, its native runner in the OS sandbox (B26).

    It is the app's ComputeBinding 0.6.0 (the owner's 2026-10-01 deviation): generated code runs
    as a native process in Seatbelt or bubblewrap, at single-user OS-sandbox assurance, never
    described as VM isolation. A planning record: it is proposed, not qualified, until the owner
    reviews the containment evidence as its qualification; admission stores it with the first
    request that pins it.
    """
    owner = ctx.principal
    return {
        "schema_version": "0.6.0",
        "planning_only": True,
        "id": "compute-local-native",
        "revision": "1.0.0",
        "tenant_ref": ctx.tenant,
        "project_ref": PROJECT,
        "state": "proposed",
        "provider": "local",
        "provider_account_ref": None,
        "connection_mode": "attach",
        "profile_id": "local-native-draft",
        "adapter_contracts": {
            "provisioner": None,
            "executor": "dsp-runner-os-sandbox-v1",
            "serving": None,
        },
        "capabilities": {
            "declared_families": ["data_analysis"],
            "declared_operations": ["analyse"],
            "execution_modes": ["process"],
            "checkpoint_mode": "restart_only",
            "gpu_capable": False,
            "external_billing_possible": False,
        },
        "resource_requirements": {
            "os": os,
            "isa": isa,
            "cpu_cores_min": 1,
            "memory_gib_min": 1,
            "gpu_count_min": 0,
            "gpu_vram_gib_min_each": 0,
            "scratch_gib_min": 1,
        },
        "observed_hardware": None,
        "limits": {
            "max_concurrent_attempts": 1,
            "max_execution_seconds": 7200,
            "automatic_paid_fallback": False,
            "automatic_provider_fallback": False,
        },
        "data_policy": {
            "allowed_classes": ["synthetic", "customer_confidential"],
            "allowed_purposes": ["data_analysis"],
            "allowed_regions": [],
            "region_confirmation_required": False,
            "customer_data_allowed": True,
            "sealed_data_access": False,
        },
        "credential_refs": [],
        "artifact_store_ref": "store-local",
        "budget_context_ref": None,
        "operator_ref": owner,
        "payer_ref": owner,
        "resource_owner_ref": owner,
        "isolation": {
            "trust_model": "customer_os_sandbox_single_user",
            "malicious_multitenant_approved": False,
        },
        "cleanup": {
            "authority": "job_process_only",
            "delete_attached_resources": False,
            "retained_storage_policy": "retain_approved_evidence_delete_temporary",
            "reconcile_interval_seconds": None,
            "idle_stop_request_seconds": None,
            "owner_ref": owner,
        },
        "qualification": {"status": "planned", "report_ref": None, "reviewer_ref": None},
        "limitations": [
            "OS-sandbox assurance for one local user (Seatbelt on macOS, bubblewrap and seccomp on "
            "Linux): not VM isolation, and not a boundary for hostile multi-tenant code.",
            "The local owner can bypass process and file separation; no hostile-host claim.",
            "Proposed, not qualified: the containment evidence awaits the owner's review.",
        ],
        "profile_scope": ["data_preparation", "data_analysis"],
        "billing_mode": "local_resources",
        "billing_policy_ref": {"id": "billing-policy-local", "revision": "1.0.0", "sha256": None},
        "generated_code_policy": "restricted_os_sandbox",
        "assurance": "os_sandbox_single_user",
    }


def propose_plan(
    ctx: TrustedContext,
    *,
    binding: dict[str, Any],
    ledger: Ledger,
    new_id: Callable[[], str],
) -> dict[str, Any]:
    """Propose a provisional plan for the current workload from the latest snapshot and record it.

    The plan supersedes the previous one. It never authorises execution.
    """
    previous = ledger.current(ctx, "WorkflowPlan")[-1:]
    plan = propose(
        current_workload(ctx, ledger),
        ledger.current(ctx, "HardwareSnapshot")[-1:],
        [binding],
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
