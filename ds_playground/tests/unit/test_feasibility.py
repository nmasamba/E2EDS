import copy
import json
from pathlib import Path
from typing import Any

import pytest

from dsp.contracts.canonical import canonical_json
from dsp.contracts.errors import DspError, ErrorCode
from dsp.contracts.schemas import validate
from dsp.domain.feasibility import propose

EXAMPLES = Path(__file__).parents[3] / "examples"
SHA = "sha256:" + "a" * 64
REPORT = {"id": "qualification-local", "revision": "1.0.0", "sha256": SHA}
ISOLATION = {"id": "isolation-local", "revision": "1.0.0", "sha256": SHA}


def example(name: str) -> Any:
    """Load one of the suite's example objects (classical ML on 4 CPUs, 8 GiB, 10 GiB scratch)."""
    return json.loads((EXAMPLES / name).read_text())


def observed(**changes: Any) -> dict[str, Any]:
    """An observed host snapshot shaped like real discovery output, with some fields changed."""
    snapshot = example("hardware_snapshots.json")["snapshots"][0] | {
        "id": "hardware-observed",
        "planning_only": False,
        "evidence_source": "observed",
        "observed_at": "2026-10-02T00:00:00+00:00",
        "cpu": {
            "visible_logical_processors": 10,
            "effective_cpu_quota": 10,
            "available_to_plan_cpus": None,
        },
        "memory": {"total_gib": 64.0, "available_gib": 30.0, "effective_limit_gib": 64.0},
        "storage": [
            {
                "role": "combined",
                "domain_id": "state-volume",
                "available_gib": 700.0,
                "effective_quota_gib": None,
            }
        ],
        "accelerators": {"inventory_status": "observed_absent", "devices": []},
        "probes": [{"name": "cpu", "status": "observed", "safe_summary": "observed"}],
    }
    validate("HardwareSnapshot", snapshot | changes)
    return snapshot | changes


def gpu(memory_gib: float | None, runtime_check: str = "not_run") -> dict[str, Any]:
    """One visible accelerator."""
    return {
        "logical_device_id": "gpu-0",
        "vendor": "NVIDIA",
        "model": "example",
        "memory_gib": memory_gib,
        "available_memory_gib": memory_gib,
        "driver_runtime_label": None,
        "memory_domain_id": "gpu-0",
        "sharing": "unknown",
        "runtime_check": runtime_check,
    }


def local(**changes: Any) -> dict[str, Any]:
    """The suite's local binding, with the given top-level fields replaced."""
    return example("compute_binding.local.json") | changes


def plan(
    snapshots: list[dict[str, Any]], bindings: list[dict[str, Any]], **workload: Any
) -> dict[str, Any]:
    """Propose a plan for the suite's reference workload and check it against the contract."""
    proposed = propose(
        example("workload_spec.json") | workload, snapshots, bindings, plan_id="plan-1"
    )
    validate("WorkflowPlan", proposed)
    assert proposed["authorises_execution"] is False
    assert [stage["id"] for stage in proposed["stages"]][::8] == ["goal", "operate"]
    return proposed


def verdicts(proposed: dict[str, Any]) -> dict[str, str]:
    """Option to disposition for the alternatives of a plan."""
    return {option["option_id"]: option["disposition"] for option in proposed["alternatives"]}


def test_a_usable_quota_below_the_host_total_blocks_the_option() -> None:
    """A32: 64 GiB on the host but 6 GiB usable does not fit 8 GiB plus the host reserve."""
    limited = observed(
        memory={"total_gib": 64.0, "available_gib": 30.0, "effective_limit_gib": 6.0}
    )
    proposed = plan([limited], [local()])
    assert proposed["feasibility_outcome"] == "FAIL"
    assert proposed["recommendation"] == (
        "local-attached-v1 is blocked: needs 10 GiB memory; 6 usable within its limits."
    )
    assert proposed["planning_only"] is False
    exactly = observed(
        memory={"total_gib": 64.0, "available_gib": 30.0, "effective_limit_gib": 10.0}
    )
    assert "blocked" not in plan([exactly], [local()])["recommendation"]


def test_a_visible_accelerator_without_a_runtime_check_is_unqualified() -> None:
    """A32: seeing a GPU does not make it usable; several small devices are never added up."""
    needs_gpu = local(
        resource_requirements=local()["resource_requirements"]
        | {"gpu_count_min": 1, "gpu_vram_gib_min_each": 12}
    )

    def judged(devices: list[dict[str, Any]], status: str = "observed_present") -> str:
        seen = observed(accelerators={"inventory_status": status, "devices": devices})
        text: str = plan([seen], [needs_gpu])["recommendation"]
        return text

    assert "unqualified: an accelerator is visible but has not passed" in judged([gpu(16)])
    assert "blocked: needs 1 accelerators with 12 GiB each; 0 fit" in judged([gpu(8), gpu(8)])
    assert "blocked" in judged([gpu(None)])
    assert "blocked" in judged([], "observed_absent")
    assert "unknown: the accelerator inventory was not observed" in judged([], "unknown")
    assert "unqualified: this compute profile has not been qualified" in judged([gpu(16, "pass")])


def test_a_declared_inventory_drafts_a_plan_but_qualifies_nothing() -> None:
    """A32: user-declared capacity is used on paper and can never make an option eligible."""
    tested = local(qualification={"status": "tested", "report_ref": REPORT, "reviewer_ref": "x"})
    declared = observed(evidence_source="user_declared", observed_at=None)
    proposed = plan([declared], [tested], planning_only=False)
    assert proposed["feasibility_outcome"] == "INSUFFICIENT_EVIDENCE"
    assert "unqualified: its inventory is declared by the user" in proposed["recommendation"]
    small = declared | {"cpu": declared["cpu"] | {"effective_cpu_quota": 2}}
    assert "blocked: needs 5 processors; 2 usable" in plan([small], [tested])["recommendation"]


def test_a_paid_option_is_blocked_at_a_zero_charge_cap() -> None:
    """A32: with a cap of zero, paid providers are blocked whatever their hardware."""
    paid = [example(f"compute_binding.{name}.json") for name in ("runpod", "colab", "zerogpu")]
    proposed = plan([observed()], [*paid, local()])
    assert proposed["selected_option_id"] == "local-attached-v1"
    assert verdicts(proposed) == {
        "runpod-provisioned-v1": "blocked",
        "colab-interactive-v1": "blocked",
        "hf-zerogpu-demo-v1": "blocked",
    }
    reasons = {option["option_id"]: option["reason"] for option in proposed["alternatives"]}
    assert (
        reasons["runpod-provisioned-v1"] == "needs paid compute and the external charge cap is zero"
    )
    assert reasons["hf-zerogpu-demo-v1"] == "does not support this workload family"
    assert proposed["operating_bounds"]["max_external_charge_minor"] == 0


def test_fixture_and_unknown_inventories_never_qualify_anything() -> None:
    """A32: an illustrative fixture, however generous, leaves every option unknown."""
    tested = local(qualification={"status": "tested", "report_ref": REPORT, "reviewer_ref": "x"})
    fixtures = example("hardware_snapshots.json")["snapshots"]
    for snapshots in (fixtures, [observed(evidence_source="unknown", observed_at=None)]):
        proposed = plan(snapshots, [tested], planning_only=False)
        assert proposed["feasibility_outcome"] == "INSUFFICIENT_EVIDENCE"
        assert proposed["recommendation"].endswith("unknown: its hardware has not been observed.")
        assert proposed["qualification_evidence_refs"] == []


def test_unobserved_capacity_is_unknown_not_assumed() -> None:
    """A32: a probe that found nothing leaves the option unknown rather than fitting or failing."""
    blind = observed(memory=dict.fromkeys(("total_gib", "available_gib", "effective_limit_gib")))
    assert plan([blind], [local()])["recommendation"].endswith(
        "unknown: usable GiB memory were not observed."
    )
    no_disk = observed(storage=[])
    assert "usable GiB scratch were not observed" in plan([no_disk], [local()])["recommendation"]


def test_only_real_evidence_on_a_real_workload_passes() -> None:
    """A32: PASS needs an observed fit, a tested profile, qualified isolation, a real workload."""
    tested = local(qualification={"status": "tested", "report_ref": REPORT, "reviewer_ref": "x"})
    isolated = observed(isolation_readiness="qualified", isolation_evidence_ref=ISOLATION)
    passed = plan([isolated], [tested], planning_only=False)
    assert (passed["feasibility_outcome"], passed["planning_only"]) == ("PASS", False)
    assert passed["qualification_evidence_refs"] == [REPORT, ISOLATION]
    assert passed["hardware_snapshot_refs"][0]["sha256"].startswith("sha256:")
    assert passed["allocations"] == [
        {
            "role": "workload",
            "physical_domain_id": "host-demo",
            "cpu_cap": 4,
            "memory_cap_gib": 8,
            "gpu_count": 0,
            "profile_id": "local-attached-v1",
        },
        {
            "role": "host_reserve",
            "physical_domain_id": "host-demo",
            "cpu_cap": 1,
            "memory_cap_gib": 2,
            "gpu_count": 0,
            "profile_id": "feasibility-rules-1.0.0",
        },
    ]
    for weaker in (
        plan([isolated], [tested]),
        plan([observed()], [tested], planning_only=False),
        plan([isolated], [local()], planning_only=False),
    ):
        assert weaker["feasibility_outcome"] == "INSUFFICIENT_EVIDENCE"
        assert weaker["planning_only"] is True


def test_the_same_inputs_give_the_same_plan_and_bad_inputs_are_refused() -> None:
    """R19: planning is deterministic; no snapshot, no option or a non-GBP budget is refused."""
    first = plan([observed()], [local()])
    assert canonical_json(first) == canonical_json(plan([observed()], [local()]))
    assert first["runtime_estimate_seconds"] is None
    workload = example("workload_spec.json")
    euros = copy.deepcopy(workload)
    euros["requested_resources"]["currency"] = "EUR"
    for bad in (
        (workload, [], [local()]),
        (workload, [observed()], []),
        (euros, [observed()], [local()]),
    ):
        with pytest.raises(DspError) as raised:
            propose(*bad, plan_id="plan-1")
        assert raised.value.code is ErrorCode.INPUT_INVALID
