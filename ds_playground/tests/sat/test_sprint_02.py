import json
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from dsp.adapters import discovery as adapter
from dsp.contracts.schemas import validate
from dsp.domain.feasibility import propose
from dsp.harness import workspace
from dsp.harness.app import SHELL_ORIGIN, create_app
from dsp.harness.instance import connect
from dsp.interfaces.cli import app as cli

EXAMPLES = Path(__file__).parents[3] / "examples"
WINDOW = {"Authorization": "Bearer secret", "Origin": SHELL_ORIGIN}
ROUTES = ("/v1/grants", "/v1/hardware", "/v1/plan", "/v1/events")


def run(*arguments: object) -> Any:
    """Invoke the CLI in-process; it talks to a real harness on the temporary profile."""
    return CliRunner().invoke(cli, [str(argument) for argument in arguments])


def test_sprint_2_folders_hardware_and_plan_survive_a_restart(
    home: Path, tmp_path: Path, harness_stopped: Callable[[Path], bool]
) -> None:
    """R19, R20, R26: with no model, grant folders, observe, plan; stop, reopen, same state.

    The window's side of the sprint's acceptance line is `make e2e`; this is the CLI's.
    """
    for name in ("data", "out"):
        (tmp_path / name).mkdir()
    assert run("grant", tmp_path / "data", "--purpose", "source_root").exit_code == 0
    assert run("grant", tmp_path / "out", "--purpose", "output_root").exit_code == 0
    assert "processors" in run("hardware").output
    assert run("plan").output.startswith("INSUFFICIENT_EVIDENCE: local-native-draft")
    first = connect(home)
    pid = first.get("/v1/status").json()["pid"]
    before = [first.get(route).json() for route in ROUTES]
    assert [event["type"] for event in before[3]["events"]] == [
        "grant.created",
        "grant.created",
        "discovery.finished",
        "plan.proposed",
        "plan.proposed",
    ]
    assert run("stop").exit_code == 0
    assert harness_stopped(home)
    reopened = connect(home)
    assert reopened.get("/v1/status").json()["pid"] != pid
    assert [reopened.get(route).json() for route in ROUTES] == before
    assert str(tmp_path) not in json.dumps(before)


@pytest.mark.disable_socket
def test_a31_bootstrap_and_truthful_discovery(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, evidence: Callable[..., None]
) -> None:
    """A31, D19: no model, no network, a denied GPU probe and a silent probe: partial and usable."""
    release = threading.Event()

    def denied() -> dict[str, Any]:
        raise PermissionError

    def flawed(state: Path) -> dict[str, Callable[[], dict[str, Any]]]:
        real = adapter.probes(state)
        return real | {"accelerators": denied, "memory": lambda: release.wait(30) or {}}

    monkeypatch.setattr(workspace, "probes", flawed)
    (tmp_path / "home").mkdir()
    app = create_app("secret", 4100)
    workspace.mount(app, tmp_path / "home")
    api = TestClient(app, base_url="http://127.0.0.1:4100")
    started = time.monotonic()
    snapshot = api.post("/v1/hardware", headers=WINDOW).json()
    elapsed = time.monotonic() - started
    release.set()
    validate("HardwareSnapshot", snapshot)
    statuses = {probe["name"]: probe["status"] for probe in snapshot["probes"]}
    assert statuses == {
        "system": "observed",
        "cpu": "observed",
        "memory": "timed_out",
        "storage": "observed",
        "accelerators": "permission_denied",
    }
    assert elapsed < 10
    assert snapshot["accelerators"]["inventory_status"] == "unknown"
    assert snapshot["memory"]["total_gib"] is None
    plan = api.get("/v1/plan", headers=WINDOW).json()
    assert plan["recommendation"].endswith("unknown: usable GiB memory were not observed.")
    assert api.get("/v1/status", headers=WINDOW).json()["status"] == "ok"
    assert api.get("/v1/grants", headers=WINDOW).json() == {"grants": []}
    evidence(
        "A31",
        "truthful-discovery",
        "PASS",
        "real probes, with the accelerator probe denied, the memory probe silent, sockets blocked",
        "partial findings within D19 with unknowns and reasons; setup and controls stay usable; "
        "no install, elevation or external call",
        f"discovery returned in {elapsed:.1f} s with {json.dumps(statuses)}; accelerators unknown, "
        "not absent; a plan was still proposed with its option unknown; status and grants answered",
        "no assistant model or runner exists yet, so 'no model' and 'unavailable runner' hold "
        "trivially",
        "browser-side hardware signals are not used at all",
    )


def test_a32_hardware_does_not_confer_eligibility(evidence: Callable[..., None]) -> None:
    """A32: quota, an unchecked GPU, declared and fixture inventories, and paid options at zero."""
    workload = json.loads((EXAMPLES / "workload_spec.json").read_text())
    local = json.loads((EXAMPLES / "compute_binding.local.json").read_text())
    paid = json.loads((EXAMPLES / "compute_binding.runpod.json").read_text())
    fixture = json.loads((EXAMPLES / "hardware_snapshots.json").read_text())["snapshots"][0]
    host = fixture | {
        "planning_only": False,
        "evidence_source": "observed",
        "observed_at": "2026-10-02T00:00:00+00:00",
        "probes": [{"name": "cpu", "status": "observed", "safe_summary": "observed"}],
    }
    gpu = local | {
        "resource_requirements": local["resource_requirements"] | {"gpu_count_min": 1},
    }
    device = {
        "logical_device_id": "gpu-0",
        "vendor": "NVIDIA",
        "model": "example",
        "memory_gib": 16,
        "available_memory_gib": 16,
        "driver_runtime_label": None,
        "memory_domain_id": "gpu-0",
        "sharing": "unknown",
        "runtime_check": "not_run",
    }
    cases = {
        "host RAM above the usable quota": (
            host | {"memory": host["memory"] | {"total_gib": 64, "effective_limit_gib": 6}},
            local,
            "blocked",
        ),
        "a visible accelerator with no runtime check": (
            host | {"accelerators": {"inventory_status": "observed_present", "devices": [device]}},
            gpu,
            "unqualified",
        ),
        "a declared-only inventory": (
            host | {"evidence_source": "user_declared", "observed_at": None},
            local,
            "unqualified",
        ),
        "a paid option at a zero charge cap": (host, paid, "blocked"),
        "an illustrative fixture inventory": (fixture, local, "unknown"),
    }
    seen = {}
    for name, (snapshot, binding, expected) in cases.items():
        validate("HardwareSnapshot", snapshot)
        plan = propose(workload, [snapshot], [binding], plan_id="plan-a32")
        validate("WorkflowPlan", plan)
        seen[name] = plan["recommendation"]
        assert f" is {expected}: " in plan["recommendation"], name
        assert plan["feasibility_outcome"] != "PASS"
        assert plan["authorises_execution"] is False
    evidence(
        "A32",
        "hardware-is-not-eligibility",
        "INSUFFICIENT_EVIDENCE",
        "the suite's reference workload and bindings against five inventories",
        "feasibility respects actual scope and evidence, preserves quality, data and rights "
        "constraints, and leaves zero-budget paid options blocked; fixture and manual inventories "
        "cannot qualify a runtime",
        json.dumps(seen),
        "every case exercised gave the expected disposition, but the rule table does not yet "
        "filter on operation, region, egress, isolation policy or data rights, because the "
        "policy and rights objects they need do not exist until later sprints",
        "several small accelerators and shared-memory pools are covered by unit tests, not here",
    )
