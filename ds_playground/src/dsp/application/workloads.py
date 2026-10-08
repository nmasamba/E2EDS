"""The workload the product can run this sprint: the deterministic test job, as a WorkloadSpec."""

from typing import Any

from dsp.application.grants import PROJECT
from dsp.contracts.errors import TrustedContext
from dsp.ports import Ledger

WORKLOAD_ID = "workload-test-job"


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
